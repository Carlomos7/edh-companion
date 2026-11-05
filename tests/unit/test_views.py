"""present skill view model (views.py) and palette (palette.py): offline unit tests, plus live checks on the fixtures
and, when EDHC_REAL_PROJECT names a real project folder, on a temporary copy of it (the original is only read).

Run: python tests/unit/test_views.py
"""
import argparse, contextlib, copy, glob, io, json, os, re, shutil, subprocess, sys, tempfile, unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # works from discover and from `python -m unittest tests.unit...`
from _net import online  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(ROOT, "plugins", "edh-companion", "skills", "present", "scripts")
FIX = os.path.join(ROOT, "tests", "fixtures")
KRENKO = os.path.join(FIX, "krenko")
REAL = os.environ.get("EDHC_REAL_PROJECT")  # e.g. a big real project with legacy inline citations; never written
sys.path.insert(0, HERE)
import palette, views  # noqa: E402
import site_data  # noqa: E402

LIVE = unittest.skipUnless(online(), "needs Scryfall")


def load(p):
    with open(p, encoding="utf-8") as h:
        return json.load(h)


def research(findings, sources, **kw):
    return dict({"version": 1, "created": "2026-11-04", "scope": {"question": "q"}, "sources": sources, "findings": findings, "gaps": []}, **kw)


def src(i, kind="video", url=None, **kw):
    return dict({"id": i, "title": f"Title {i}", "url": url or f"https://www.youtube.com/watch?v={i}", "type": kind, "accessed": "2026-11-04"}, **kw)


def fnd(i, claim, ev, cls="community_opinion", conf="low", **kw):
    return dict({"id": i, "claim": claim, "class": cls, "confidence": conf, "evidence": ev}, **kw)


class Citations(unittest.TestCase):
    """Legacy inline citations become per-claim cites with correct video links; nothing is lost."""

    SRCS = [src("src-100"), src("src-101"), src("src-104"), src("src-105"), src("src-200", "article", "https://example.com/a")]

    def cites(self, claim, ev=("src-100",)):
        R = views.Research([(None, research([fnd("fnd-001", claim, list(ev))], self.SRCS))])
        clean = R.parsed[(None, "fnd-001")][0]
        return clean, {c["source_id"]: [(a["t"], a["url"].rsplit("t=", 1)[-1], a.get("note")) for a in c["at"]] for c in R.finding_cites(None, R.fnd[(None, "fnd-001")])}

    def test_forms_seen_in_real_research(self):
        cases = [
            ("A. [src-101 9:00, 9:40-10:40]", ("src-101",), {"src-101": [("9:00", "540s", None), ("9:40-10:40", "580s", None)]}),
            ("A. [video 4:52-5:01]", ("src-100",), {"src-100": [("4:52-5:01", "292s", None)]}),
            ("A (src-100 1:00-1:14) b.", ("src-100",), {"src-100": [("1:00-1:14", "60s", None)]}),
            ("A. [src-100 5:17 and 10:28]", ("src-100",), {"src-100": [("5:17", "317s", None), ("10:28", "628s", None)]}),
            ("A. [src-100 6:00 and 4:18; src-101 25:40]", ("src-100", "src-101"),
             {"src-100": [("6:00", "360s", None), ("4:18", "258s", None)], "src-101": [("25:40", "1540s", None)]}),
            ("A. [src-100 7:13-9:45, combos 8:14-8:49]", ("src-100",), {"src-100": [("7:13-9:45", "433s", None), ("8:14-8:49", "494s", "combos")]}),
            ("A. [video 1:23-2:50, 2:03 'for big spenders']", ("src-100",), {"src-100": [("1:23-2:50", "83s", None), ("2:03", "123s", "'for big spenders'")]}),
            ("A. [video 4:09 kill early, 4:37 weakness]", ("src-100", "src-101"), {"src-100": [("4:09", "249s", "kill early"), ("4:37", "277s", "weakness")], "src-101": []}),
            ("A. [video 5:36-6:20 (src-104); 2:08 (src-105)]", ("src-104", "src-105"), {"src-104": [("5:36-6:20", "336s", None)], "src-105": [("2:08", "128s", None)]}),
            ("A. [video 0:25-0:44, 1:35-1:40 (src-105)]", ("src-105", "src-100"), {"src-105": [("0:25-0:44", "25s", None), ("1:35-1:40", "95s", None)], "src-100": []}),
            ("A. [src-101 1:02:03-1:05:00]", ("src-101",), {"src-101": [("1:02:03-1:05:00", "3723s", None)]}),
        ]
        for claim, ev, want in cases:
            clean, got = self.cites(claim, ev)
            self.assertEqual(got, want, claim)
            self.assertNotRegex(clean, r"\d:\d\d", claim)  # the reference left the text
            self.assertTrue(clean.startswith("A"))

    def test_unresolvable_or_plain_brackets_stay_in_the_text(self):
        for claim in ("A [src-999 1:00] b.", "A [sic] b.", "Turn 4 at (26:00) b."):
            clean, got = self.cites(claim)
            self.assertEqual(clean, claim)
            self.assertEqual(got, {"src-100": []})

    def test_locators_and_every_cited_source(self):
        f = fnd("fnd-002", "Claim.", ["src-100", "src-101", "fnd-003"], locators=[{"source": "src-101", "at": ["9:00", "9:40-10:40"]}])
        g = fnd("fnd-003", "Other. [src-200 1:00]", ["src-200"])
        R = views.Research([(None, research([f, g], self.SRCS))])
        cites = R.finding_cites(None, f)
        self.assertEqual([c["source_id"] for c in cites], ["src-100", "src-101", "src-200"])  # all, not just the first
        self.assertEqual([a["t"] for a in cites[1]["at"]], ["9:00", "9:40-10:40"])
        self.assertEqual(cites[2]["at"][0]["url"], "https://example.com/a")  # an article can't deep-link: plain URL
        self.assertEqual([c["n"] for c in cites], [R.n[(None, s)] for s in ("src-100", "src-101", "src-200")])

    def test_time_url(self):
        t = views.time_url
        self.assertEqual(t("https://www.youtube.com/watch?v=abc&t=5s", "1:02:03"), "https://www.youtube.com/watch?v=abc&t=3723s")
        self.assertEqual(t("https://youtu.be/abc", "9:40-10:40"), "https://youtu.be/abc?t=580s")
        self.assertEqual(t("https://m.youtube.com/watch?v=abc", "0:25"), "https://m.youtube.com/watch?v=abc&t=25s")
        self.assertEqual(t("https://www.twitch.tv/videos/1", "1:02:03"), "https://www.twitch.tv/videos/1?t=1h2m3s")
        self.assertEqual(t("https://vimeo.com/123", "2:00"), "https://vimeo.com/123#t=120s")
        self.assertEqual(t("https://example.com/podcast.mp3", "2:00"), "https://example.com/podcast.mp3")
        self.assertIs(site_data.video_link, views.time_url)


class Headlines(unittest.TestCase):
    def test_never_cut_mid_word_and_body_keeps_everything(self):
        long = ("Planeswalker Project builds Azula around spells that already have flash and deliberately skips flash enablers such as "
                "Leyline of Anticipation and Vedalken Orrery, calling it fragile. Second.")
        for claim in (long, "Short claim. Second sentence.", "Budgetario names her biggest weakness: the list has few ways to give her haste, so a removal spell costs two or three turns of tempo."):
            R = views.Research([(None, research([fnd("fnd-001", claim, ["src-100"])], [src("src-100")]))])
            it = R.findings_view()[0]["items"][0]
            self.assertEqual(it["body"], claim)
            h = it["headline"].rstrip("…")
            self.assertTrue(claim.startswith(h) and len(h) <= views.HEAD_MAX, it["headline"])
            self.assertTrue(len(claim) == len(h) or not claim[len(h)].isalnum(), it["headline"])  # ends on a word boundary
        self.assertEqual(views.headline("Short claim. Second sentence."), "Short claim.")
        self.assertEqual(views.sentences("Use e.g. Big Score here. Then attack."), ["Use e.g. Big Score here.", "Then attack."])

    def test_label_quotes_and_summary(self):
        """Review of a real project: 20 headlines were a bare "Label" cut at its colon and 6 were cut inside a quotation."""
        label = ("Verdict on optimisation (model assessment): main-v3 is a coherent, protected, fair bracket-3 Avatar build with healthy "
                 "rocks and fixing. It is well below the community's engine power.")
        self.assertEqual(views.headline(label), label.split(". ")[0] + ".")  # the whole first sentence, not the label
        longer = ("Timing trap that applies to the accepted deck: Azula only copies spells cast while she is attacking, and Sozin's Comet "
                  "must resolve before attackers are declared, so it is not copied. More.")
        h, rest = views.headline_parts(longer)
        self.assertTrue(h.startswith("Azula only copies") and len(h) <= views.HEAD_MAX and rest == "More.", h)  # the conclusion after a short label
        quoted = ("Players overwhelmingly call Azula kill-on-sight: 'You can't even let them attack a single time with her' (r/EDH B3 thread), "
                  "'It's in the table's best interest not to let her attack. Ever.' and more quotes follow here, one after another.")
        inq = ("EDHRECast cuts the firebending 'family' from the average list because 'Ozai, Ashling and Electro want to keep mana "
               "whereas Azula wants to spend it': Ozai and Zuko are cut.")
        for claim, start in ((quoted, "Players overwhelmingly call Azula kill-on-sight: 'You"), (inq, "EDHRECast cuts")):
            h = views.headline(claim)
            cut = len(h.rstrip("…"))
            self.assertTrue(h.startswith(start) and claim.startswith(h.rstrip("…")), h)  # a quote after the colon: the left part is the point
            self.assertFalse(cut < len(claim) and views._inside(claim)[cut], h)  # never cut inside a quotation or brackets
        self.assertEqual(views.sentences("EDHRECast cuts Agni Kai ('not the card to copy ... fighting twice is a tall order'), and Comet. Next."),
                         ["EDHRECast cuts Agni Kai ('not the card to copy ... fighting twice is a tall order'), and Comet.", "Next."])
        R = views.Research([(None, research([fnd("fnd-001", longer, ["src-100"])], [src("src-100")]))])
        self.assertEqual(R.findings_view()[0]["items"][0]["summary"], "More.")  # the conclusion shows without opening Details
        self.assertLessEqual(len(views.summary_of("word " * 300)), views.SHORT_BODY + 1)

    def test_explicit_headline_wins(self):
        f = fnd("fnd-001", "Long claim text.", ["src-100"], headline="Flash enablers are a trap")
        it = views.Research([(None, research([f], [src("src-100")]))]).findings_view()[0]["items"][0]
        self.assertEqual((it["headline"], it["body"]), ("Flash enablers are a trap", "Long claim text."))


class Groups(unittest.TestCase):
    def test_grouping_order_labels_and_disputes(self):
        S = [src("src-1", author="Creator A"), src("src-2", "community", "https://www.reddit.com/r/EDH/x"), src("src-3", "stats", "https://edhrec.com/x")]
        F = [fnd("fnd-1", "A low.", ["src-1"]), fnd("fnd-2", "A high.", ["src-1"], conf="high"), fnd("fnd-3", "Reddit says.", ["src-2"]),
             fnd("fnd-4", "Stat.", ["src-3"], "popularity_metric", "high"), fnd("fnd-5", "Fact.", ["src-3"], "verified_fact"),
             fnd("fnd-6", "Mine.", ["src-3"], "model_assessment"), fnd("fnd-7", "Open.", [], "unresolved")]
        r = research(F, S, disagreements=[{"topic": "T", "positions": [{"position": "yes", "evidence": ["fnd-1"]}, {"position": "no", "evidence": ["src-2"]}]}])
        R = views.Research([(None, r)])
        fv = R.findings_view()
        self.assertEqual([(g["kind"], g["title"]) for g in fv], [("class", "Verified fact"), ("class", "Popularity data"), ("creator", "Creator A"),
                                                                ("creator", "Reddit"), ("class", "Claude's judgment"), ("class", "Unresolved")])
        self.assertEqual([i["id"] for i in fv[2]["items"]], ["fnd-2", "fnd-1"])  # confidence first
        self.assertTrue(fv[2]["items"][1]["disputed"] and not fv[2]["items"][0]["disputed"])
        dv = R.disagreements_view()
        self.assertEqual(dv[0]["positions"][0]["findings"], ["fnd-1"])
        self.assertEqual([c["source_id"] for c in dv[0]["positions"][0]["cites"]], ["src-1"])  # a finding id brings its sources
        self.assertEqual(set(views.CLASS_LABEL.values()), {"Verified fact", "Calculated", "Popularity data", "Community opinion", "Claude's judgment", "Unresolved"})


class AnchorsAndCites(unittest.TestCase):
    def test_ids_shared_by_two_projects_get_their_own_anchors(self):
        """A showcase: both projects have fnd-001 and src-001; anchors, cited_by and headlines stay per project."""
        a = research([fnd("fnd-001", "Alpha claim.", ["src-001"])], [src("src-001")])
        b = research([fnd("fnd-001", "Beta claim.", ["src-001"])], [src("src-001", "article", "https://example.com/b")])
        R = views.Research([("krenko", a), ("spider-research", b)], {"krenko": "krenko", "spider-research": "spider-research"})
        items = [i for g in R.findings_view() for i in g["items"]]
        self.assertEqual([i["anchor"] for i in items], ["f-krenko-fnd-001", "f-spider-research-fnd-001"])
        srcs = {s["anchor"]: s for g in R.sources_view() for s in g["items"]}
        self.assertEqual(set(srcs), {"s-krenko-src-001", "s-spider-research-src-001"})
        self.assertEqual(srcs["s-spider-research-src-001"]["cited_by"],
                         [{"id": "fnd-001", "anchor": "f-spider-research-fnd-001", "project": "spider-research", "headline": "Beta claim."}])
        self.assertEqual(items[0]["cites"][0]["anchor"], "s-krenko-src-001")
        single = views.Research([(None, a)], {None: "Fire Lord Azula (Avatar)"})  # one project: still the folder's slug
        self.assertEqual(single.findings_view()[0]["items"][0]["anchor"], "f-fire-lord-azula-avatar-fnd-001")

    def test_citing_a_finding_brings_only_its_own_sources(self):
        """fnd-140 on a real project: its claim is EDHRECast's (src-106), its explanation names the other side
        (src-100, src-104). A disagreement that cites fnd-140 must not list the other side's videos."""
        S = [src("src-106", author="JoeyDH (EDHRECast)"), src("src-100", author="Planeswalker Project"),
             src("src-104", author="Muscles & Magic The Gathering (Bobby Maximus)"), src("src-103", author="Slam Hammer")]
        f140 = fnd("fnd-140", "EDHRECast cuts the firebending family. [video 8:00-8:35]", ["src-106", "src-100", "src-104"],
                   explanation="Direct conflict with Planeswalker Project, who praises Ozai and Zuko, Firebending Master (2:17, 2:39) "
                               "and Muscles & Magic, who praises Ozai (4:59).")
        f143 = fnd("fnd-143", "EDHRECast explains an attack-step rule. [video 4:40-5:20]", ["src-106", "src-103"],
                   explanation="Slam Hammer reached the same conclusion on Chain Assassination after combat damage (17:47-18:15).")
        plain = fnd("fnd-150", "No times here.", ["src-104", "src-100"])
        r = research([f140, f143, plain], S, disagreements=[{"topic": "T", "positions": [{"position": "cut them", "evidence": ["fnd-140"]},
                                                                                           {"position": "x", "evidence": ["fnd-150"]}]}])
        R = views.Research([(None, r)])
        times = lambda cites: [(c["source_id"], [a["t"] for a in c["at"]]) for c in cites]
        pos = R.disagreements_view()[0]["positions"]
        self.assertEqual(times(pos[0]["cites"]), [("src-106", ["8:00-8:35"])])
        self.assertEqual(times(pos[1]["cites"]), [("src-104", [])])  # no cited times: its first source
        items = {i["id"]: i for g in R.findings_view() for i in g["items"]}
        self.assertEqual(times(items["fnd-140"]["cites"]), [("src-106", ["8:00-8:35"]), ("src-100", ["2:17", "2:39"]), ("src-104", ["4:59"])])
        self.assertEqual(times(items["fnd-143"]["cites"]), [("src-106", ["4:40-5:20"]), ("src-103", ["17:47-18:15"])])
        self.assertIn("?v=src-103&t=1067s", items["fnd-143"]["cites"][1]["at"][0]["url"])  # the right video at the right moment
        self.assertEqual(R.text_at(None, "Named by Lab Man (25:00), and Slam Hammer (3:08, 3:12)."), {"src-103": [{"t": "3:08"}, {"t": "3:12"}]})


class Completeness(unittest.TestCase):
    """Every finding, source, disagreement and gap of every research fixture appears in the views exactly once."""

    def check(self, r):
        R = views.Research([(None, r)])
        fv, sv, dv = R.findings_view(), R.sources_view(), R.disagreements_view()
        self.assertEqual(sorted(i["id"] for g in fv for i in g["items"]), sorted(f["id"] for f in r["findings"]))
        nums = [i["n"] for g in sv for i in g["items"]]
        self.assertEqual(sorted(i["id"] for g in sv for i in g["items"]), sorted(s["id"] for s in r["sources"]))
        self.assertEqual(nums, list(range(1, len(r["sources"]) + 1)))  # numbered in reading order
        self.assertEqual([d["topic"] for d in dv], [d["topic"] for d in r.get("disagreements", [])])
        for g in fv:
            for it in g["items"]:
                for c in it["cites"]:
                    item = next(i for x in sv for i in x["items"] if i["id"] == c["source_id"])
                    self.assertEqual((c["n"], c["anchor"]), (item["n"], item["anchor"]))
                    self.assertIn({"id": it["id"], "anchor": it["anchor"], "project": None, "headline": it["headline"]}, item["cited_by"])
                    for a in c["at"]:
                        self.assertIn(it["id"], next(m for m in item["moments"] if m["t"] == a["t"])["findings"])
        return R

    def test_fixtures(self):
        files = glob.glob(os.path.join(FIX, "**", "research.json"), recursive=True)
        self.assertTrue(files)
        for p in files:
            with self.subTest(p=os.path.relpath(p, FIX)):
                self.check(load(p))

    @unittest.skipUnless(REAL and os.path.exists(os.path.join(REAL or "", "research.json")), "EDHC_REAL_PROJECT not set")
    def test_real_project_legacy_citations(self):
        tmp = tempfile.mkdtemp()
        try:
            shutil.copy(os.path.join(REAL, "research.json"), tmp)
            r = load(os.path.join(tmp, "research.json"))
            R = self.check(r)
            for f in r["findings"]:
                clean = R.parsed[(None, f["id"])][0]
                self.assertNotRegex(clean, r"\[(?:src-|video)[^\]]*\d:\d\d", f["id"])  # every legacy reference parsed out
                norm = lambda s: {re.sub(r"\s*[-–]\s*", "-", t) for t in views.AT.findall(s)}
                text = f["claim"] + " " + (f.get("explanation") or "")
                legacy = norm(" ".join(m.group(0) for m in views.REF.finditer(text)))
                named = norm(" ".join(m.group(1) for m in views.BARE.finditer(text)))  # "Slam Hammer ... (17:47-18:15)"
                times = {a["t"] for c in R.finding_cites(None, f) for a in c["at"]}
                self.assertLessEqual(legacy, times, f["id"])  # every legacy time reaches a cite
                self.assertLessEqual(times, legacy | named | {t for l in f.get("locators") or [] for t in l.get("at", [])}, f["id"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Audit(unittest.TestCase):
    def audit(self):
        m = "[method: deck_check.py re-run on decklists/main.txt (--bracket 3 [x]), deck_hash aaa]"
        checks = [{"id": f"chk-a-{i}", "area": "other", "requirement": f"R{i}", "kind": "deterministic", "status": "pass", "detail": f"{m} ok {i}"} for i in range(4)]
        checks += [{"id": "chk-w", "area": "mana", "requirement": "Sources", "kind": "judgment", "status": "warning", "detail": "[method: judgment] few blue"},
                   {"id": "chk-f", "area": "count", "requirement": "100 cards", "kind": "deterministic", "status": "fail", "detail": "99 cards", "method": "counted by hand"},
                   {"id": "chk-u", "area": "combos", "requirement": "Combos", "kind": "sourced", "status": "unverified", "detail": None}]
        return {"checks": checks, "verdict": {"status": "fail", "summary": "FAIL (1 fail). The list has 99 cards. Fix it.", "limitations": ["x"]},
                "required_fixes": [{"check": "chk-f", "fix": "add a card"}], "recommended_next_steps": ["re-run"], "created": "2026-11-04",
                "auditor": {"independent": True}, "combo_findings": {"included": []}, "bracket_findings": {"assessment": "B3"}}

    def test_split_group_label(self):
        self.assertEqual(views.split_method("[method: a [b] c] result"), ("a [b] c", "result"))
        self.assertEqual(views.split_method("no prefix"), (None, "no prefix"))
        self.assertEqual(views.split_method("[method: unclosed"), (None, "[method: unclosed"))
        av = views.audit_view(self.audit(), {"state": "fail", "checks": []})
        self.assertEqual((av["verdict_label"], av["counts"]), ("Fail", {"fail": 1, "warning": 1, "unverified": 1, "pass": 4}))
        self.assertEqual([(g["status"], g["label"], g["open"]) for g in av["groups"]],
                         [("fail", "1 check failed", True), ("warning", "1 warning", True), ("unverified", "1 unverified", True), ("pass", "4 checks passed", False)])
        self.assertEqual(av["method_common"], "deck_check.py re-run on decklists/main.txt (--bracket 3 [x]), deck_hash aaa")
        p = av["groups"][3]["checks"][0]
        self.assertEqual((p["method"], p["result"], p["status_label"]), (av["method_common"], "ok 0", "Pass"))
        f = av["groups"][0]["checks"][0]
        self.assertEqual((f["method"], f["result"]), ("counted by hand", "99 cards"))  # the new method field wins
        self.assertEqual(av["summary"], {"lead": "The list has 99 cards.", "more": "FAIL (1 fail). Fix it."})
        self.assertEqual(av["required_fixes"][0]["title"], "100 cards")
        self.assertEqual((av["next_steps"], av["combos"], av["bracket"]["assessment"]), (["re-run"], {"included": []}, "B3"))
        for state, label in (("pass_with_warnings", "Pass with warnings"), ("incomplete", "Incomplete")):
            self.assertEqual(views.audit_view(None, {"state": state})["verdict_label"], label)

    def test_out_of_date_audit_shows_no_checks(self):
        av = views.audit_view(self.audit(), {"state": "audit out of date", "note": "v1 vs v2"})
        self.assertEqual((av["verdict_label"], av["groups"], av["note"]), ("Audit out of date", [], "v1 vs v2"))
        self.assertEqual(views.audit_view(None, {"state": "not audited"})["verdict_label"], "Not audited")


class RecsAndNotices(unittest.TestCase):
    def test_applied_vs_proposed(self):
        recs = [{"id": "rec-1", "status": "accepted", "add": "Consider", "cut": "Diresight", "reason": "r"},
                {"id": "rec-2", "status": "proposed", "add": "Big Score", "cut": "Shock", "reason": "r"},
                {"id": "rec-3", "status": "rejected", "add": "Azula, Cunning Usurper", "cut": "Sozin's Comet", "reason": "r"},
                {"id": "rec-4", "status": "proposed", "add": "Opt", "reason": "already played"},
                {"id": "rec-5", "status": "accepted", "add": "Ponder", "reason": "accepted but not in the list"},
                {"id": "rec-6", "status": "proposed", "cut": "Shock", "reason": "pure cut"}]
        rv = views.recs_view(recs, ["Consider", "Opt", "Shock", "Sozin's Comet"], lambda refs, text="": [])
        ids = {k: [r["id"] for r in rv[k]] for k in ("applied", "proposed", "rejected")}
        self.assertEqual(ids, {"applied": ["rec-1", "rec-4"], "proposed": ["rec-2", "rec-5", "rec-6"], "rejected": ["rec-3"]})
        self.assertEqual(rv["rejected_count"], 1)
        self.assertEqual(rv["proposed"][1]["status_label"], "Accepted")  # the label stays honest; the list decides "applied"

    def test_research_notices(self):
        r = research([fnd("fnd-1", "main-v3 runs Ozai. main-v3 is fair.", [])], [])
        lists = ["decklists/main-v1.txt", "decklists/main-v3.txt", "decklists/main-v4.txt"]
        self.assertIn("names main-v3.txt; the newest list is main-v4.txt", views.research_notices(r, {"version": 4}, lists=lists)[0]["text"])
        # file numbers are not versions: main-v4.txt is version 3 here, and research about main-v4 is current
        self.assertEqual(views.research_notices(research([fnd("fnd-1", "main-v4 is fair.", [])], []), {"version": 3}, lists=lists), [])
        self.assertEqual(views.research_notices(r, {"version": 4}), [])  # no decklists folder: nothing to compare
        self.assertEqual(views.research_notices(research([], [], created="2026-11-04"), {"version": 2, "updated": "2026-11-04T16:35:00"}), [])  # same day
        r["scope"]["deck"] = {"version": 4, "deck_hash": "aaaaaaaaaaaa"}  # scope.deck decides when present
        self.assertEqual(views.research_notices(r, {"version": 4, "deck_hash": "aaaaaaaaaaaa"}), [])
        self.assertIn("written for version 3", views.research_notices(dict(r, scope={"question": "q", "deck": {"version": 3, "deck_hash": "a" * 12}}), {"version": 4})[0]["text"])
        self.assertIn("card list changed", views.research_notices(r, {"version": 4, "deck_hash": "bbbbbbbbbbbb"})[0]["text"])
        old = research([], [], created="2026-10-01")
        self.assertIn("dated 2026-10-01", views.research_notices(old, {"version": 2, "updated": "2026-11-04"})[0]["text"])
        newer = views.research_notices(research([], [], version=2), {"version": 1, "research_version": 1})
        self.assertEqual(newer[0]["level"], "info")


def face(t):
    return {"type_line": t}


class CardTypes(unittest.TestCase):
    """One rule for groups, filters, charts and summaries (Scryfall shapes and deck_check records)."""
    CARDS = [
        ({"type_line": "Legendary Creature — Human Noble", "commander": True}, "Commander", ["Creature"], False),
        ({"type_line": "Basic Land — Island", "qty": 10}, "Land", ["Land"], False),
        ({"type_line": "Basic Snow Land — Forest", "qty": 2}, "Land", ["Land"], False),
        ({"type_line": "Land Creature — Forest Dryad"}, "Land", ["Land", "Creature"], False),  # Dryad Arbor
        ({"type_line": "Artifact Creature — Golem"}, "Creature", ["Artifact", "Creature"], False),
        ({"type_line": "Legendary Enchantment Creature — God"}, "Creature", ["Enchantment", "Creature"], False),
        ({"type_line": "Legendary Planeswalker — Jace"}, "Planeswalker", ["Planeswalker"], False),
        ({"type_line": "Battle — Siege"}, "Battle", ["Battle"], False),
        ({"type_line": "Artifact — Equipment"}, "Artifact", ["Artifact"], False),
        ({"type_line": "Artifact — Vehicle"}, "Artifact", ["Artifact"], False),
        ({"type_line": "Artifact — Spacecraft"}, "Artifact", ["Artifact"], False),
        ({"type_line": "Enchantment — Aura"}, "Enchantment", ["Enchantment"], False),
        ({"type_line": "Enchantment — Saga"}, "Enchantment", ["Enchantment"], False),
        ({"type_line": "Legendary Enchantment — Background"}, "Enchantment", ["Enchantment"], False),
        ({"type_line": "Enchantment — Class"}, "Enchantment", ["Enchantment"], False),
        ({"type_line": "Enchantment — Case"}, "Enchantment", ["Enchantment"], False),
        ({"type_line": "Enchantment — Room // Enchantment — Room", "layout": "split",
          "card_faces": [face("Enchantment — Room"), face("Enchantment — Room")]}, "Enchantment", ["Enchantment"], False),
        ({"type_line": "Kindred Instant — Goblin"}, "Instant", ["Kindred", "Instant"], False),
        ({"type_line": "Tribal Sorcery — Elf"}, "Sorcery", ["Tribal", "Sorcery"], False),
        ({"type_line": "Instant // Land", "layout": "modal_dfc", "card_faces": [face("Instant"), face("Land")]}, "Instant", ["Instant"], True),
        ({"type_line": "Legendary Creature — Elephant // Land", "layout": "modal_dfc",
          "card_faces": [face("Legendary Creature — Elephant"), face("Land")]}, "Creature", ["Creature"], True),
        ({"type_line": "Land // Land", "layout": "modal_dfc", "card_faces": [face("Land"), face("Land")]}, "Land", ["Land"], False),  # pathway
        ({"type_line": "Legendary Enchantment // Legendary Land", "layout": "transform",
          "card_faces": [face("Legendary Enchantment"), face("Legendary Land")]}, "Enchantment", ["Enchantment"], False),  # not modal
        ({"type_line": "Creature — Human Wizard // Creature — Human Insect Wizard", "layout": "transform",
          "card_faces": [face("Creature — Human Wizard"), face("Creature — Human Insect Wizard")]}, "Creature", ["Creature"], False),
        ({"type_line": "Enchantment — Saga // Legendary Creature — Avatar", "layout": "transform",
          "card_faces": [face("Enchantment — Saga"), face("Legendary Creature — Avatar")]}, "Enchantment", ["Enchantment"], False),
        ({"type_line": "Creature — Goblin Shaman // Legendary Creature — Goblin Shaman", "layout": "flip",
          "card_faces": [face("Creature — Goblin Shaman"), face("Legendary Creature — Goblin Shaman")]}, "Creature", ["Creature"], False),
        ({"type_line": "Legendary Creature — Angel", "layout": "meld"}, "Creature", ["Creature"], False),
        ({"type_line": "Instant // Sorcery", "layout": "split", "card_faces": [face("Instant"), face("Sorcery")]}, "Instant", ["Instant", "Sorcery"], False),
        ({"type_line": "Sorcery // Instant", "layout": "aftermath", "card_faces": [face("Sorcery"), face("Instant")]}, "Instant", ["Sorcery", "Instant"], False),
        ({"type_line": "Creature — Giant // Instant — Adventure", "layout": "adventure",
          "card_faces": [face("Creature — Giant"), face("Instant — Adventure")]}, "Creature", ["Creature", "Instant"], False),
        # deck_check records: no layout; a real back image means double-faced
        ({"type_line": "Instant // Land", "back_image": "https://cards.scryfall.io/back.jpg"}, "Instant", ["Instant"], True),
        ({"type_line": "Creature — Giant // Instant — Adventure", "back_image": None}, "Creature", ["Creature", "Instant"], False),
        ({"type_line": "Conspiracy"}, "Other", [], False),
        ({"type_line": "Plane — Dominaria"}, "Other", [], False),
        ({"type_line": "Ongoing Scheme"}, "Other", [], False),
        ({"type_line": "Vanguard"}, "Other", [], False),
        ({"type_line": "Dungeon"}, "Other", [], False),
        ({"type_line": "Artifact — Attraction"}, "Other", ["Artifact"], False),
        ({"type_line": "Artifact — Contraption"}, "Other", ["Artifact"], False),
        ({"type_line": "Stickers"}, "Other", [], False),
        ({"type_line": "Emblem — Jace"}, "Other", [], False),
        ({"type_line": "Token Creature — Goblin"}, "Other", ["Creature"], False),
        ({"type_line": None}, "Other", [], False),
        ({}, "Other", [], False),
    ]

    def test_each_case(self):
        for card, group, types, mdfc in self.CARDS:
            with self.subTest(card=card.get("type_line")):
                t = views.card_types(card)
                self.assertEqual((t["type_group"], [x for x in t["types"] if x not in ("Conspiracy", "Plane", "Scheme", "Vanguard", "Dungeon", "Stickers", "Emblem")], t["mdfc_land"]),
                                 (group, types, mdfc))
        self.assertEqual(views.card_types({"type_line": "Artifact — Equipment"})["subtypes"], ["Equipment"])
        self.assertEqual(views.card_types({"type_line": "Basic Snow Land — Forest"})["supertypes"], ["Basic", "Snow"])
        self.assertEqual(views.card_types(self.CARDS[19][0])["face_types"], [["Instant"], ["Land"]])

    def test_counts_cover_every_card(self):
        cards = [c for c, *_ in self.CARDS]
        counts, mdfc = views.type_counts(cards)
        self.assertEqual(sum(counts.values()), sum(c.get("qty", 1) for c in cards))
        self.assertEqual(list(counts), [g for g in views.GROUP_ORDER if g in counts])  # stable order
        self.assertEqual((counts["Commander"], counts["Land"], mdfc), (1, 14, 3))

    def test_same_rule_as_deck_check(self):
        """deck_check's type tally and the pages call the same classifier (edhcore.types), so counts can't drift."""
        with open(os.path.join(ROOT, "plugins", "edh-companion", "skills", "audit", "scripts", "deck_check.py"), encoding="utf-8") as h:
            src = h.read()
        self.assertIn("from edhcore.types import card_types", src)
        self.assertIn('card_types(c)["type_group"]', src)
        self.assertEqual(views.TYPE_ORDER, ("Land", "Creature", "Planeswalker", "Battle", "Artifact", "Enchantment", "Instant", "Sorcery"))


class Palette(unittest.TestCase):
    TEXT, UI = ("text", "muted", "accent", "accent2"), ("focus", "accent", "accent2")

    def assert_readable(self, p, why):
        for mode in ("l", "d"):
            r = p[mode]
            self.assertEqual(set(r), set(palette.ROLES))
            for k in self.TEXT:
                for bg in ("bg", "surface", "surface2"):
                    self.assertGreaterEqual(palette.contrast(r[k], r[bg]), 4.5, (why, mode, k, bg))
            for k in self.UI:
                for bg in ("bg", "surface"):
                    self.assertGreaterEqual(palette.contrast(r[k], r[bg]), 3, (why, mode, k, bg))
            self.assertGreaterEqual(palette.contrast(r["on_accent"], r["accent"]), 4.5, (why, mode))
            self.assertRegex(r["art_wash"], r"^#[0-9a-f]{8}$")
            for bg in ("bg", "surface"):
                self.assertGreaterEqual(palette.contrast(r["border"], r[bg]), 3, (why, mode, "border", bg))  # control outlines
                self.assertGreaterEqual(palette.contrast(r["gold"], r[bg]), 4.5, (why, mode, "gold", bg))  # exception text
            hero = palette.over(r["art_wash"], r["bg"])  # template .hero: art_wash over the page bg
            self.assertGreaterEqual(palette.contrast(r["hero_muted"], hero), 4.8, (why, mode, "hero_muted"))
            self.assertGreaterEqual(palette.contrast(r["hero_muted"], r["bg"]), 4.8, (why, mode, "hero_muted on bg"))

    def image(self, colors, tmp, name):
        """A 64x64 image painted with (rgb, share) bands."""
        from PIL import Image
        im, y = Image.new("RGB", (64, 64)), 0
        for rgb, share in colors:
            h = max(1, round(64 * share))
            im.paste(rgb, (0, y, 64, min(64, y + h)))
            y += h
        p = os.path.join(tmp, name + ".png")
        im.save(p)
        return p

    def test_many_hues_and_themes(self):
        for h in range(0, 360, 15):
            for L, C in ((.3, .1), (.6, .2), (.9, .05)):
                seed = palette.oklch_hex(L, C, h)
                self.assert_readable(palette.build("theme", seed, palette.oklch_hex(L, C, (h + 120) % 360)), seed)
        for t in ("#ffff00", "#000000", "#ffffff", "#c8102e", "#808080", "#00ff00"):
            p = palette.resolve({"accent": t})
            self.assertEqual(p["source"], "theme")
            self.assert_readable(p, t)
        red = palette.resolve({"accent": "#c8102e"})["l"]["accent"]
        self.assertLess(abs(palette.rgb_to_oklch(palette.hex_rgb(red))[2] - palette.rgb_to_oklch((200, 16, 46))[2]), 8)  # hue kept

    def test_artwork_and_fallbacks(self):
        tmp = tempfile.mkdtemp()
        try:
            red = self.image([((190, 30, 40), .6), ((30, 30, 30), .4)], tmp, "red")
            seeds = palette.art_seeds(red)
            self.assertLess(min(abs(palette.rgb_to_oklch(palette.hex_rgb(seeds[0]))[2] - 25), 360), 20)  # a red seed
            self.assert_readable(palette.resolve(art=red), "red art")
            for name, colors in (("black", [((5, 5, 8), 1)]), ("white", [((250, 250, 248), 1)]), ("grey", [((128, 128, 128), 1)])):
                p = self.image(colors, tmp, name)
                self.assertIsNone(palette.art_seeds(p), name)  # nothing usable: fall back
                self.assertEqual(palette.resolve(art=p, identity=("#1f6fd1", "#d0312d"))["source"], "identity")
            near_black = self.image([((12, 10, 30), .7), ((40, 20, 120), .3)], tmp, "nearblack")
            self.assert_readable(palette.resolve(art=near_black), "near-black art")
            self.assertEqual(palette.resolve({"accent": "#2e7d32"}, art=red)["source"], "theme")  # theme beats art
            self.assertEqual(palette.resolve(art=os.path.join(tmp, "missing.png"))["source"], "neutral")
            self.assertIsNone(palette.art_file("file://" + os.path.join(tmp, "nope.jpg").replace("\\", "/"), os.path.join(tmp, "cache")))
            self.assert_readable(palette.resolve(), "neutral")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def args(**kw):
    a = argparse.Namespace(mode="showcase", style=None, images="cdn", viewer=None, show=None, hide=None, title=None, subtitle=None, out=None)
    a.__dict__.update(kw)
    return a


class Privacy(unittest.TestCase):
    """Offline (deck_check mocked): shared pages leave out DECISIONS.md lines and PROJECT.md text; --include-notes adds them."""

    def fake_deck_check(self, path, tmp, project, cheapest=False, cards_only=False):
        if cards_only:
            return {"cards": [], "checks": [], "unavailable": [], "data": {"verification": "fresh"}}
        brew = load(path)
        cards = [{"name": brew["commander"]["cards"][0]["name"], "qty": 1, "commander": True, "printing_id": "c0", "set": "tst",
                  "collector_number": "1", "type_line": "Legendary Creature — Goblin", "cmc": 4, "color_identity": ["R"], "game_changer": False,
                  "price_usd": 1, "image": "https://cards.scryfall.io/c0.jpg", "back_image": None, "status": "legal", "roles": {}}]
        cards += [dict(cards[0], name=c["name"], qty=c["qty"], commander=False, printing_id=f"d{i}", type_line="Instant") for i, c in enumerate(brew["deck"])]
        stats = {"price_usd": 1, "average_mv": 1, "lands": 0, "game_changers": [], "curve": {}, "types": {"Instant": 99}}
        return {"cards": cards, "checks": [], "stats": stats, "deck_hash": brew["deck_hash"], "checked": "2026-11-04", "unavailable": [], "data": {}}

    def page(self, *projects, multi=False, **kw):
        """page-data.json (or summary.md text with mode="summary") for the projects (default krenko)."""
        tmp = tempfile.mkdtemp()
        try:
            site = site_data.Site(args(out=os.path.join(tmp, "page-data.json"), **kw), multi=multi)
            site.D["look"] = site_data.look_for([])
            with mock.patch.object(site_data, "deck_check", side_effect=self.fake_deck_check), contextlib.redirect_stdout(io.StringIO()):
                for ws in projects or (KRENKO,):
                    site_data.add_project(site, ws)
                site_data.finish(site, tmp)
            if kw.get("mode") == "summary":
                with open(os.path.join(tmp, "summary.md"), encoding="utf-8") as h:
                    return h.read()
            return load(os.path.join(tmp, "page-data.json"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_recommendation_times_link_their_video(self):
        """A time after a named creator in a recommendation's reason links that video at that moment."""
        tmp = tempfile.mkdtemp()
        try:
            ws = os.path.join(tmp, "krenko")
            shutil.copytree(KRENKO, ws)
            b = load(os.path.join(ws, "brew-b3.json"))
            b["recommendations"][0]["reason"] = "MTG Bear plays it as a combat trick (1:13)."
            with open(os.path.join(ws, "brew-b3.json"), "w", encoding="utf-8") as h:
                json.dump(b, h)
            D = self.page(ws)
            rec = next(x for g in D["groups"] for c in g["commanders"] for d in c["decks"] if d["id"] == "b3"
                       for x in d["recs_view"]["proposed"] if x["id"] == "rec-001")
            urls = [a["url"] for c in rec["cites"] for a in c.get("at", [])]
            self.assertTrue(any(u.endswith("t=73s") for u in urls), urls)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_quoted_private_notes_are_hidden(self):
        """Research and audit text that quotes STATE.md or DECISIONS.md is hidden unless --include-notes; the notice
        counts it; card names and brew.json's own words are never hidden."""
        tmp = tempfile.mkdtemp()
        try:
            ws = os.path.join(tmp, "krenko")
            shutil.copytree(KRENKO, ws)
            with open(os.path.join(ws, "STATE.md"), "w", encoding="utf-8") as h:
                h.write("# State\n- 2026-11-04: b3 audit = FAIL (unpinned printings). Fixed in b4 by pinning every line.\n")
            r = load(os.path.join(ws, "research.json"))
            r["findings"][0]["explanation"] = ("STATE.md says 'b3 audit = FAIL (unpinned printings). Fixed in b4 by pinning every line' and "
                                               "DECISIONS.md keeps 'Rejected Cyclonic Rift (rec-002): off-color' for Coat of Arms.")
            with open(os.path.join(ws, "research.json"), "w", encoding="utf-8") as h:
                json.dump(r, h)
            shared = json.dumps(self.page(ws), ensure_ascii=False)
            self.assertNotIn("Rejected Cyclonic Rift", shared)
            # STATE.md restates the audit: its overlap with research/audit text is a public fact, not a leak
            self.assertIn("STATE.md says 'b3 audit = FAIL (unpinned printings). Fixed in b4 by pinning every line' and DECISIONS.md keeps [private note]", shared)
            n = re.search(r"(\d+) quoted private notes? (?:were|was) hidden", shared)
            self.assertTrue(n and int(n.group(1)) >= 1, "the privacy notice gives the count")
            self.assertIn("Goblin creatures and cards that make Goblins", shared)  # brew.json's theme rule = PROJECT.md text, shown anyway
            own = json.dumps(self.page(ws, include_notes=True), ensure_ascii=False)
            self.assertTrue(all(q in own for q in ("b3 audit = FAIL", "Rejected Cyclonic Rift")) and "[private note]" not in own)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        R = views.Redactor(["- Never add Hellkite Charger, Aggravated Assault or Underworld Breach"], names=["Hellkite Charger", "Aggravated Assault", "Underworld Breach"])
        self.assertEqual(R("Near-misses: Hellkite Charger, Aggravated Assault or Underworld Breach."), "Near-misses: Hellkite Charger, Aggravated Assault or Underworld Breach.")
        self.assertEqual(R.count, 0)  # card names alone are not a private note

    def test_theme_rule0_and_summary(self):
        D = self.page()
        b3 = next(d for c in D["groups"][0]["commanders"] for d in c["decks"] if d["id"] == "b3")
        brew = load(os.path.join(KRENKO, "brew-b3.json"))
        qty = lambda t: sum(c["qty"] for c in brew["deck"] if c.get("theme") == t)
        ts = b3["theme_stats"]
        self.assertEqual(ts, {"on": qty("on_theme"), "exception": qty("exception"), "off": qty("off_theme"), "exempt": qty("n/a"),
                              "total": qty("on_theme") + qty("exception") + qty("off_theme")})
        self.assertEqual(b3["theme"]["on_theme_pct"], round(100 * ts["on"] / ts["total"], 1))
        self.assertEqual(b3["rule0_items"][1], {"label": "Game Changers", "value": "None"})  # the bare "no Game Changers" is dropped
        self.assertNotIn("rule0", b3)
        rows = lambda r, gcs: {x["label"]: x["value"] for x in site_data.rule0_rows(dict({"bracket": 3}, restrictions=r), gcs)}
        self.assertEqual(rows(["no extra turns", "max 3 Game Changers"], ["Fierce Guardianship", "Mystical Tutor"]),
                         {"Bracket": "3 (Upgraded)", "Game Changers": "Fierce Guardianship, Mystical Tutor (max 3)", "Restrictions": "no extra turns"})
        self.assertEqual(rows(["Game Changers allowed"], ["Rhystic Study"])["Game Changers"], "Rhystic Study (allowed)")
        self.assertEqual(rows(["no Game Changers"], ["Rhystic Study"])["Game Changers"], "Rhystic Study (no Game Changers)")  # never dropped silently
        md = self.page(mode="summary")
        rule0 = next(l for l in md.splitlines() if l.startswith("**Rule 0.**") and "Bracket: 3" in l)
        self.assertEqual(rule0, "**Rule 0.** Bracket: 3 (Upgraded); Game Changers: None; Restrictions: no extra turns, no mass land denial; Win turn: 7-9")
        for part in ("**Why this commander.**", "**Theme exceptions.**", "**Theme rules.**", f"Theme: {ts['on']} of {ts['total']} cards on theme",
                     "**Scope.** Theme: Goblins · depth: quick", "### How it was researched", "- Tools used: Scryfall API",
                     "- Failed: Commander Spellbook: not queried in this quick pass"):
            self.assertIn(part, md)
        self.assertNotIn("Player decisions", md)
        self.assertIn("**Player decisions (DECISIONS.md).**", self.page(mode="summary", include_notes=True))

    def test_showcase_subtitle_and_methodology(self):
        D = self.page(KRENKO, os.path.join(FIX, "showcase", "projects", "talrand"), multi=True)
        self.assertNotIn("Goblin tokens", D["subtitle"])  # the first project's archetype doesn't speak for the page
        t = D["research_tab"][0]
        self.assertEqual((t["scope"], sorted(t["methodology"])), ({"theme": "Goblins", "depth": "quick"}, ["approach", "tools_failed", "tools_used"]))

    def test_notes_only_on_request(self):
        with open(os.path.join(KRENKO, "DECISIONS.md"), encoding="utf-8") as h:
            lines = [l.strip()[2:] for l in h if l.strip().startswith(("- ", "* "))]
        self.assertTrue(lines)
        shared = self.page()
        blob = json.dumps(shared, ensure_ascii=False)
        self.assertFalse([l for l in lines if l in blob])
        self.assertTrue(any("--include-notes" in n["text"] for n in shared["notices"]))
        titles = {s["title"] for c in shared["groups"][0]["commanders"] for d in c["decks"] for s in d["summary"]["sections"]}
        self.assertNotIn("Theme (PROJECT.md)", titles)
        own = self.page(include_notes=True)
        blob = json.dumps(own, ensure_ascii=False)
        self.assertTrue(all(l in blob for l in lines))
        self.assertFalse(any("--include-notes" in n["text"] for n in own["notices"]))
        # views and old fields side by side
        d = own["groups"][0]["commanders"][0]["decks"][0]
        self.assertEqual(d["stats"]["type_counts"], {"Commander": 1, "Instant": 99})
        self.assertIn(d["audit_view"]["verdict_label"], ("Pass with warnings", "Audit out of date", "Not audited", "Pass"))
        self.assertTrue(own["findings_view"] and own["sources_view"] and own["research_tab"])
        self.assertEqual(own["groups"][0]["commanders"][0]["hero"]["art"], "c0_f")


@LIVE
class RealPipeline(unittest.TestCase):
    """site_data.py on a temp copy of EDHC_REAL_PROJECT (skipped when unset): every research item reaches the page,
    page type counts equal deck_check's, private notes stay out, old fields stay."""

    @classmethod
    def setUpClass(cls):
        if not (REAL and os.path.isdir(REAL)):
            raise unittest.SkipTest("EDHC_REAL_PROJECT not set")
        cls.tmp = tempfile.mkdtemp()
        cls.ws = os.path.join(cls.tmp, os.path.basename(REAL.rstrip("/\\")))
        shutil.copytree(REAL, cls.ws, ignore=shutil.ignore_patterns("reports"))
        out = os.path.join(cls.tmp, "page-data.json")
        p = subprocess.run([shutil.which("uv"), "run", "--quiet", "--script", os.path.join(HERE, "site_data.py"), "from-workspace", cls.ws, "--out", out,
                            "--images", "cdn"], capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        assert p.returncode == 0, p.stderr
        cls.D = load(out)
        cls.research = load(os.path.join(cls.ws, "research.json")) if os.path.exists(os.path.join(cls.ws, "research.json")) else None

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_research_complete(self):
        r, D = self.research, self.D
        if not r:
            self.skipTest("no research.json")
        self.assertEqual(sorted(i["id"] for g in D["findings_view"] for i in g["items"]), sorted(f["id"] for f in r["findings"]))
        self.assertEqual(sorted(i["id"] for g in D["sources_view"] for i in g["items"]), sorted(s["id"] for s in r["sources"]))
        self.assertEqual([d["topic"] for d in D["disagreements_view"]], [d["topic"] for d in r.get("disagreements", [])])
        self.assertEqual(D["research_tab"][0]["gaps"], r.get("gaps", []))
        self.assertEqual(len(D["research_tab"][0]["candidates"]), len(r.get("card_candidates", [])))

    def test_types_old_fields_privacy(self):
        for k in ("groups", "rankings", "research", "accuracy", "look", "data_dates"):
            self.assertIn(k, self.D)
        for c in (c for g in self.D["groups"] for c in g["commanders"]):
            for d in c["decks"]:
                self.assertEqual(sum(d["stats"]["type_counts"].values()), sum(x["qty"] for x in d["cards"]))
                self.assertEqual(d["stats"]["lands"], d["stats"]["type_counts"].get("Land", 0))
        dec = os.path.join(self.ws, "DECISIONS.md")
        if os.path.exists(dec):
            with open(dec, encoding="utf-8") as h:
                lines = [l.strip()[2:] for l in h if l.strip().startswith(("- ", "* ")) and len(l) > 30]
            blob = json.dumps(self.D, ensure_ascii=False)
            self.assertFalse([l for l in lines if l in blob])


if __name__ == "__main__":
    unittest.main()
