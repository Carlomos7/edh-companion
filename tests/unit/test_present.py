"""present skill pipeline test: fixture project -> site_data.py -> build_site.py. Live classes need uv and network
(Scryfall) and are skipped offline; the Data and Atlas classes run offline.

Run: python tests/unit/test_present.py
"""
import argparse, collections, importlib.util, io, json, os, re, shutil, subprocess, sys, tempfile, unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # _net, also when run as tests.unit.test_present
from _net import online  # noqa: E402

LIVE = unittest.skipUnless(online(), "needs Scryfall")

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(ROOT, "plugins", "edh-companion", "skills", "present", "scripts")
WS = os.path.join(ROOT, "tests", "fixtures", "krenko")
SC_ROOT = os.path.join(ROOT, "tests", "fixtures", "showcase")
SHOWCASE = os.path.join(SC_ROOT, "showcases", "test-showcase")
PARTNERS = os.path.join(ROOT, "tests", "fixtures", "partners")
RESEARCH_ONLY = os.path.join(SC_ROOT, "projects", "spider-research")
TALRAND = os.path.join(SC_ROOT, "projects", "talrand")
BENCH = os.path.join(ROOT, "tests", "bench")  # its sitecustomize.py logs every urlopen of every subprocess
spec = importlib.util.spec_from_file_location("site_data", os.path.join(HERE, "site_data.py"))
site_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site_data)
sys.path.insert(0, os.path.join(ROOT, "plugins", "edh-companion", "scripts"))
from edhcore.cards import record  # noqa: E402


def browse(case, html, script, actions=None):
    """Load a built page in Chromium and return (uncaught JS errors, the value of `script`). Skips without a browser."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        case.skipTest("playwright not installed")
    errors = []
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception:
                browser = p.chromium.launch(channel="chrome")
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto("file:///" + html.replace(os.sep, "/"))
            page.wait_for_timeout(1500)
            if actions:
                actions(page)
            value = page.evaluate(script)
            browser.close()
    except Exception as e:
        case.skipTest(f"no browser: {e}")
    return errors, value


def build_pipeline(tmp, cmd, path, *flags, site=True):
    """site_data.py (+ build_site.py) into tmp; returns (report, data or None, html or None)."""
    data = os.path.join(tmp, "page-data.json")
    p = run(os.path.join(HERE, "site_data.py"), cmd, path, "--out", data, "--images", "cdn", *flags)
    assert p.returncode == 0, p.stderr
    report = json.loads(p.stdout)
    if not site:
        return report, None, None
    with open(data, encoding="utf-8") as h:
        D = json.load(h)
    b = run(os.path.join(HERE, "build_site.py"), data, "--out", os.path.join(tmp, "site"))
    assert json.loads(b.stdout)["pass"], b.stdout
    with open(os.path.join(tmp, "site", "index.html"), encoding="utf-8") as h:
        return report, D, h.read()


def run(*args):
    return subprocess.run([shutil.which("uv"), "run", "--quiet", "--script", *args], capture_output=True, text=True, encoding="utf-8",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))


@LIVE
class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        data = os.path.join(cls.tmp, "page-data.json")
        p = run(os.path.join(HERE, "site_data.py"), "from-workspace", WS, "--out", data, "--images", "cdn")
        assert p.returncode == 0, p.stderr
        cls.report = json.loads(p.stdout)
        with open(data, encoding="utf-8") as h:
            cls.D = json.load(h)
        b = run(os.path.join(HERE, "build_site.py"), data, "--out", os.path.join(cls.tmp, "site"))
        cls.build = json.loads(b.stdout)
        with open(os.path.join(cls.tmp, "site", "index.html"), encoding="utf-8") as h:
            cls.html = h.read()
        with open(os.path.join(cls.tmp, "presentation-checks.md"), encoding="utf-8") as h:
            cls.checks_md = h.read()
        cls.decks = {d["id"]: d for c in cls.D["groups"][0]["commanders"] for d in c["decks"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_builds_without_errors(self):
        self.assertTrue(self.build["pass"], self.build["errors"])
        self.assertEqual(sorted(self.decks), ["b3", "b4"])
        for d in self.decks.values():
            self.assertEqual(sum(c["qty"] for c in d["cards"]), 100)
            self.assertNotIn("errors", d)  # internal deck_check failures go to presentation-checks.md, not the page
        self.assertTrue(any(c.get("artist") for d in self.decks.values() for c in d["cards"]))  # artist credit next to the art
        self.assertIn("Illustrated by", self.html)
        for t in ("Copy shown", "Copy for Moxfield", "gcopy"):  # per-section, filtered and single-card copy
            self.assertIn(t, self.html)

    def test_machine_readable_exports(self):
        site = os.path.join(self.tmp, "site")
        llms = open(os.path.join(site, "llms.txt"), encoding="utf-8").read()
        self.assertTrue(llms.startswith("# " + self.D["title"]))
        self.assertIn('<meta property="og:title"', self.html)
        self.assertIn('<link rel="alternate" type="text/plain" href="llms.txt"', self.html)
        self.assertIn("Fan Content Policy", self.html)
        for d in self.decks.values():
            f = f"export-{d['project'] or 'deck'}-{d['id']}.json".lower()
            self.assertIn(f"]({f})", llms)
            x = json.load(open(os.path.join(site, f), encoding="utf-8"))
            self.assertEqual((x["version"], x["decklist"], x["audit"]), (d["version"], d["moxfield"], (d["audit_view"] or {}).get("verdict")))
            self.assertIn("Scryfall", x["attribution"])                  # attribution travels with the data
            self.assertIn(f, self.build["supporting_files"])

    def test_page_runs_without_js_errors(self):
        """The built page in a real browser: any uncaught JS error (a broken template edit) fails here."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("playwright not installed")
        errors = []
        try:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch()
                except Exception:
                    browser = p.chromium.launch(channel="chrome")
                page = browser.new_page()
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto("file:///" + os.path.join(self.tmp, "site", "index.html").replace(os.sep, "/"))
                page.wait_for_timeout(1500)
                tabs = page.locator("#tabs button, #tabs a").count()
                browser.close()
        except Exception as e:  # no browser available on this machine
            self.skipTest(f"no browser: {e}")
        self.assertEqual(errors, [])
        self.assertGreater(tabs, 0)

    def test_template_js_parses(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        p = subprocess.run([node, "--check", os.path.join(HERE, "..", "assets", "template", "page.js")], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_audit_states_derived_never_upgraded(self):
        b3, b4 = self.decks["b3"]["audit_view"], self.decks["b4"]["audit_view"]
        self.assertEqual((b3["verdict"], b3["verdict_label"]), ("pass_with_warnings", "Pass with warnings"))
        self.assertEqual(b4["verdict"], "audit out of date")
        self.assertFalse([c for g in b4.get("groups", []) for c in g["checks"]])  # an out-of-date audit's checks are never shown
        self.assertTrue([c for g in b3["groups"] for c in g["checks"]])
        self.assertIn('"verdict":"audit out of date"', self.html)
        states = {i["file"]: i["audit_state"] for i in self.report["inputs"] if "audit_state" in i}
        self.assertEqual(states, {"brew-b3.json": "pass_with_warnings", "brew-b4.json": "audit out of date"})
        self.assertIn("| brew-b4.json | 2 | a7499368e991 | audit out of date |", self.checks_md)
        self.assertIn("| cast-by-turn chart | yes |", self.checks_md)
        self.assertIn("## Theme", self.checks_md)

    def test_derivation_rules(self):
        brew = {"version": 2, "deck_hash": "aaaaaaaaaaaa"}
        audit = {"subject": {"deck": {"version": 2, "deck_hash": "bbbbbbbbbbbb"}}, "checks": [], "verdict": {"status": "pass"}, "auditor": {}}
        shown = lambda a, h="aaaaaaaaaaaa": site_data.shown_validation(brew, a, h)["state"]
        self.assertEqual(shown(None), "not audited")
        self.assertEqual(shown(audit), "audit out of date")  # audit of another list
        audit["subject"]["deck"].update(deck_hash="aaaaaaaaaaaa", version=1)
        self.assertEqual(shown(audit), "audit out of date")  # audit of another version
        audit["subject"]["deck"]["version"] = 2
        self.assertEqual(shown(audit, "cccccccccccc"), "audit out of date")  # list changed since
        self.assertEqual(shown(audit), "pass")

    def test_sources_link_out(self):
        src = [s for g in self.D["sources_view"] for s in g["items"]]
        self.assertEqual(len(src), 6)
        self.assertTrue(all(re.match(r"https?://", s["url"]) for s in src))
        self.assertEqual([s["n"] for s in sorted(src, key=lambda s: s["n"])], list(range(1, 7)))  # numbered like the markers
        moments = [m for s in src for m in s["moments"]]
        self.assertEqual([m["url"].rsplit("t=", 1)[1] for m in moments], ["25s", "73s", "89s"])  # every moment links to its time
        cites = [c for g in self.D["findings_view"] for i in g["items"] for c in i["cites"]]
        self.assertTrue(cites and all(c["n"] in {s["n"] for s in src} for c in cites))

    def test_no_invented_numbers(self):
        blob = json.dumps(self.D)
        for key in ('"sim"', '"price_styles"', '"printings"', '"cost_to_buy"'):
            self.assertNotIn(key, blob)
        for d in self.decks.values():
            s, cards = d["stats"], d["cards"]
            self.assertEqual(s["lands"], sum(c["qty"] for c in cards if c["type_group"] == "Land"))
            self.assertAlmostEqual(s["price"], sum(c["price"] * c["qty"] for c in cards if c["price"] is not None), places=1)
            self.assertEqual(s["unpriced"], [c["name"] for c in cards if c["price"] is None])
            # one type rule (edhcore.types, shared with deck_check): groups cover every card
            self.assertEqual(sum(s["type_counts"].values()), 100)
        hidden = {x["name"] for x in self.report["sections"] if not x["included"]}
        self.assertIn("research tab (commanders compared, disagreements)", hidden)  # krenko's research sits next to builds
        self.assertTrue(all(x["why_not"] for x in self.report["sections"] if not x["included"]))

    def test_sections_and_swaps(self):
        rv = {d: self.decks[d]["recs_view"] for d in ("b3", "b4")}
        prop = {d: {x["add"]: x for x in rv[d]["proposed"] if x.get("add")} for d in rv}
        self.assertEqual(set(prop["b3"]) | set(prop["b4"]), {"Goblin Surprise"})
        self.assertEqual([x["add"] for x in rv["b4"]["applied"]], ["Jeska's Will"])  # already in b4: applied, not "to consider"
        self.assertEqual([x["add"] for x in rv["b3"]["rejected"]], ["Cyclonic Rift"])  # rejected listed apart
        self.assertTrue(all(x.get("img") in self.D["images"] for p in prop.values() for x in p.values()))  # proposals show their card
        titles = [x["title"] for x in self.decks["b3"]["summary"]["sections"]]
        self.assertIn("Proposed cuts", titles)
        self.assertEqual(self.D["theme"]["labels"][0]["label"], "On theme")
        self.assertNotIn("Player decisions (DECISIONS.md)", titles)  # private notes need --include-notes (test_views.Privacy)
        self.assertNotIn("Theme (PROJECT.md)", titles)
        self.assertIn("Theme rules", titles)
        self.assertEqual(self.D["title"], "Krenko Goblins")
        dfc = next(c for c in self.decks["b3"]["cards"] if c["name"].startswith("Valakut Awakening"))
        self.assertTrue(dfc["back"] and dfc["back"].endswith("_b"))

    def test_no_theme_no_pills(self):
        brew = {"deck": [{"name": "Sol Ring", "qty": 1, "role": "ramp"}], "theme_policy": None}
        self.assertEqual(site_data.theme_setup([brew]), (None, {}))

    def test_roles_from_deck_check_not_brew_labels(self):
        for d in self.decks.values():
            s = d["stats"]
            counted = {}
            for c in d["cards"]:
                self.assertNotIn("role", c)  # the brew label lives in "label"; stats use the Oracle-text rules
                if not c["commander"]:
                    for r in c["roles"]:
                        counted[r] = counted.get(r, 0) + c["qty"]
            self.assertEqual(s["roles"], counted)
            self.assertIn("Oracle-text rules", s["roles_note"])
            self.assertEqual({r: v[0] for r, v in s["template"].items() if r != "lands"}, {r: s["roles"].get(r, 0) for r in ("ramp", "draw", "removal", "wipe")})
            for x in s["label_diff"]:
                self.assertNotIn(x["label"], x["rules"])
            self.assertTrue(all(isinstance(v, list) and v for c in d["cards"] for v in c["roles"].values()))  # every role names its rule

    def test_analytics_from_deck_check(self):
        s = self.decks["b3"]["stats"]
        self.assertEqual(set(s["price_ladder"]), {"affordable_usd", "as_listed_usd", "premium_usd", "note", "as_of"})
        self.assertGreater(s["cast_by_turn"]["runs"], 0)
        self.assertTrue(s["cast_by_turn"]["assumptions"])
        self.assertEqual(set(s["mana"]), {"pips", "sources"})
        self.assertTrue(any(c.get("cheapest") for c in self.decks["b3"]["cards"]))


class Units(unittest.TestCase):
    """Offline: theming, status, hidden analytics."""

    def test_identity_palette(self):
        hues = site_data.identity_hues
        self.assertEqual(hues(["R"]), (site_data.HUES["R"],) * 2)
        self.assertEqual(hues(["R", "U"]), (site_data.HUES["U"], site_data.HUES["R"]))  # WUBRG order: Izzet = blue, red
        self.assertEqual(hues(["W", "U", "B"]), (site_data.GOLD, site_data.GOLD))  # 3+ colors: one muted gold, no rainbow
        self.assertEqual(hues([]), (site_data.NEUTRAL, site_data.NEUTRAL))  # colorless
        self.assertEqual(site_data.resolve_look([], [])["source"], "commander color identity (colorless)")
        self.assertEqual(site_data.resolve_look([])["source"], "neutral")

    def test_accent_contrast(self):
        for hexc in list(site_data.HUES.values()) + [site_data.GOLD, site_data.NEUTRAL, "#ffff00", "#101010", "#c8102e"]:
            look = site_data.palette(hexc)
            for mode, bgs in (("l", site_data.LIGHT_BG), ("d", site_data.DARK_BG)):
                for key in ("a", "a2"):
                    for bg in bgs:
                        self.assertGreaterEqual(site_data.contrast(look[mode][key], bg), 4.5, (hexc, mode, bg))
        self.assertAlmostEqual(site_data.contrast("#000000", "#ffffff"), 21, places=1)

    def test_theme_precedence(self):
        t = lambda c: {"accent": c}
        cands = [("--theme", None), ("showcase.yaml projects[x] theme", t("#112233")), ("showcase.yaml theme", t("#445566")), ("x/report-theme.yaml", t("#778899"))]
        self.assertEqual(site_data.resolve_look(cands, ["R"])["source"], "showcase.yaml projects[x] theme")
        cands[0] = ("--theme", t("#aa0000"))
        self.assertEqual(site_data.resolve_look(cands, ["R"])["source"], "--theme")
        cands[0], cands[1] = ("--theme", None), ("p", None)
        self.assertEqual(site_data.resolve_look(cands, ["R"])["source"], "showcase.yaml theme")
        only_file = [("--theme", None), ("p", None), ("g", None), ("x/report-theme.yaml", {"accent": "#778899", "style": "comic", "label": "L"})]
        look = site_data.resolve_look(only_file, ["R"])
        self.assertEqual((look["source"], look["style"], look["label"]), ("x/report-theme.yaml", "comic", "L"))
        self.assertEqual(site_data.resolve_look([("p", None)], ["G"])["source"], "commander color identity (G)")
        with self.assertRaises(SystemExit):
            site_data.resolve_look([("bad", {"accent": "red"})])
        with self.assertRaises(SystemExit):
            site_data.resolve_look([("bad", {"accent": "#ff0000", "style": "rainbow"})])

    def test_status(self):
        self.assertEqual(site_data.status_of({"status": "upcoming", "releases": "2027-01-15"}), ("upcoming", "2027-01-15"))
        self.assertEqual(site_data.status_of({"status": "legal"}), (None, None))
        self.assertEqual(site_data.status_of({"status": "legal"}, {"status": "banned"}), ("banned", None))

    def test_analytics_hidden_when_absent(self):
        deck = {"stats": {"price": 1}, "cards": [], "validation": {"state": "not audited"}, "summary": {"community": []}}
        D = {"page": {"show": dict.fromkeys(site_data.SECTIONS, True)}, "research": [], "rankings": [], "groups": []}
        names = ("cast-by-turn chart", "price ladder", "mana sources vs color requirements")
        rows = {x["name"]: x for x in site_data.sections(D, [deck])}
        for name in names:
            self.assertFalse(rows[name]["included"])
            self.assertIn("deck_check", rows[name]["why_not"])
        deck["stats"].update(cast_by_turn={"by_turn": {}}, price_ladder={"x": 1}, mana={"pips": {}})
        rows = {x["name"]: x for x in site_data.sections(D, [deck])}
        self.assertTrue(all(rows[n]["included"] for n in names))


@LIVE
class Showcase(unittest.TestCase):
    """from-showcase: krenko (Villains, b3/b4), spider-gwen + talrand (Heroes: commander picker), spider-research (research only)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.report, cls.D, cls.html = build_pipeline(cls.tmp, "from-showcase", SHOWCASE)
        with open(os.path.join(cls.tmp, "presentation-checks.md"), encoding="utf-8") as h:
            cls.checks_md = h.read()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_one_page_build_bar(self):
        """Every build in one picker (bracket chip, name, audit tag; grouped), at most four views, ranking pages behind one switch."""
        errors, v = browse(self, os.path.join(self.tmp, "site", "index.html"), """({
            views: [...document.querySelectorAll('#tabs button')].map(b => b.dataset.view),
            groups: [...document.querySelectorAll('#bsel-lb .pk-g')].map(g => g.textContent),
            chips: [...document.querySelectorAll('#bsel-lb .pk-opt')].map(o => (o.querySelector('.bchip') || {}).textContent),
            tags: document.querySelectorAll('#bsel-lb .pk-opt .tag').length,
            selected: document.querySelectorAll('#bsel-lb [aria-selected="true"]').length})""")
        self.assertEqual(errors, [])
        self.assertLessEqual(len(v["views"]), 4)
        self.assertEqual(v["views"][0], "decks")
        self.assertEqual(v["groups"], [g["title"] for g in self.D["groups"]])
        n = sum(len(c["decks"]) for g in self.D["groups"] for c in g["commanders"])
        self.assertEqual(len(v["chips"]), n)
        self.assertTrue(all(c and c.startswith("B") for c in v["chips"]), v["chips"])  # every option leads with its bracket chip
        self.assertEqual(v["tags"], n)                                                  # and carries its audit tag
        self.assertEqual(v["selected"], 1)

    def test_build_picker_keyboard(self):
        """Arrow keys open the picker, End moves to the last build, Enter picks it: the page redraws and the link follows."""
        def keys(page):
            page.focus("#bsel")
            page.keyboard.press("ArrowDown")
            page.keyboard.press("End")
            page.keyboard.press("Enter")
            page.wait_for_timeout(500)
        errors, v = browse(self, os.path.join(self.tmp, "site", "index.html"), """({
            hash: decodeURIComponent(location.hash), open: document.getElementById('bsel').getAttribute('aria-expanded'),
            focus: document.activeElement.id})""", keys)
        last = [(c["slug"], d["id"] or "b" + str(d["bracket"])) for g in self.D["groups"] for c in g["commanders"] for d in c["decks"]][-1]
        self.assertEqual(errors, [])
        self.assertEqual(v["hash"], f"#build={last[0]}/{last[1]}")
        self.assertEqual((v["open"], v["focus"]), ("false", "bsel"))

    def test_groups_and_picker(self):
        g = {x["title"]: x for x in self.D["groups"]}
        self.assertEqual(list(g), ["Villains", "Heroes"])
        self.assertEqual([c["project"] for c in g["Heroes"]["commanders"]], ["spider-gwen", "talrand"])  # 2 commanders: picker
        self.assertEqual([d["id"] for d in g["Villains"]["commanders"][0]["decks"]], ["b3", "b4"])  # variant switch
        self.assertTrue(all(d["project"] for x in g.values() for c in x["commanders"] for d in c["decks"]))
        self.assertEqual(self.D["title"], "Test Showcase")
        self.assertNotIn("Goblin tokens", self.D["subtitle"])  # krenko's archetype doesn't speak for a showcase
        self.assertEqual({r["project"] for r in self.D["overview"]}, {"krenko", "spider-gwen", "talrand"})
        self.assertEqual([a["name"] for a in g["Villains"]["alts"]], ["Krenko, Mob Boss"])
        self.assertTrue(g["Villains"]["alts"][0]["built"])

    def test_audits_stay_separate(self):
        states = {i["file"]: i.get("audit_state") for i in self.report["inputs"]}
        self.assertEqual(states["krenko/brew-b4.json"], "audit out of date")
        self.assertEqual(states["talrand/brew.json"], "not audited")
        self.assertIn("| krenko/brew-b3.json | 1 |", self.checks_md)

    def test_rankings_tabs(self):
        R = {r["title"]: r for r in self.D["rankings"]}
        self.assertEqual(list(R), ["Spider-Man heroes", "Spider-Man villains"])
        h = R["Spider-Man heroes"]
        self.assertTrue(h["method"].startswith("EDHREC inclusion") and h["as_of"] == "2026-11-04")
        bolt = h["cards"][1]
        self.assertEqual((bolt["rank"], bolt["tier"], bolt["pct"], bolt["decks"], bolt["n"]), (2, "A", 61.2, 252, 412))
        self.assertEqual((bolt["status"], bolt["releases"]), ("upcoming", "2026-12-05"))
        self.assertTrue(bolt["img"] and bolt["evidence"][0]["url"].startswith("https://"))
        v = R["Spider-Man villains"]["cards"]
        self.assertEqual([c["rank"] for c in v], [1, 2, 3])
        self.assertTrue(all(c["tier"] is None and c["pct"] is None for c in v))  # never computed
        self.assertEqual(v[1]["status"], "banned")
        self.assertEqual(len(self.D["research"]), 1)
        self.assertEqual(self.D["research"][0]["commanders"][0]["legal_check"], "deck_check.py --commander 2026-11-04")

    def test_looks(self):
        looks = {c["project"]: c["look"] for g in self.D["groups"] for c in g["commanders"]}
        self.assertEqual(looks["krenko"]["source"], "showcase.yaml projects[../../krenko] theme")
        self.assertEqual(looks["krenko"]["style"], "gothic")
        self.assertEqual(looks["talrand"]["source"], "commander color identity (U)")
        self.assertNotEqual(looks["talrand"]["palette"]["l"]["accent"], looks["spider-gwen"]["palette"]["l"]["accent"])
        self.assertNotIn("l", looks["talrand"])  # the old accent pair isn't published; palette roles replace it
        self.assertEqual(self.D["look"]["source"], "neutral")
        self.assertIn("| Talrand, Sky Summoner (talrand) | commander color identity (U) |", self.checks_md)

    def test_page_has_views_and_no_legacy_fields(self):
        """The page carries the views the template reads, per page, commander and build (each build its own counts);
        legacy fields (tiers, the old sources dump, per-deck validation/errors, swaps, video lists) aren't published."""
        for k in ("groups", "rankings", "research", "accuracy", "look", "data_dates", "fan",
                  "findings_view", "disagreements_view", "sources_view", "research_tab", "notices"):
            self.assertIn(k, self.D)
        for k in ("tiers", "sources", "schema"):
            self.assertNotIn(k, self.D)
        self.assertEqual(set(self.D["accuracy"]), {"unverified"})
        looks = {c["project"]: c["look"]["palette"]["source"] for g in self.D["groups"] for c in g["commanders"]}
        self.assertEqual(looks["krenko"], "theme")  # an explicit showcase theme beats the artwork
        self.assertIn(looks["talrand"], ("artwork", "identity"))
        for g in self.D["groups"]:
            for c in g["commanders"]:
                self.assertEqual(c["hero"]["name"], c["name"])
                self.assertNotIn("youtube", c)
                self.assertFalse(any("swaps" in g for g in self.D["groups"]))
                for d in c["decks"]:
                    for k in ("summary", "moxfield", "rule0_items", "stats", "cards", "audit_view", "recs_view", "hero"):
                        self.assertIn(k, d)
                    for k in ("validation", "errors", "archetype", "rule0"):  # rule0 is summary.md's one-line form
                        self.assertNotIn(k, d)
                    self.assertEqual(d["hero"]["stats"][2]["value"].split()[0], str(d["stats"]["lands"]))  # each build's own hero stats
                    self.assertEqual(sum(d["stats"]["type_counts"].values()), sum(x["qty"] for x in d["cards"]))
                    self.assertEqual(d["stats"]["lands"], d["stats"]["type_counts"].get("Land", 0))

    def test_anchors_unique_across_projects(self):
        """krenko and spider-research both have fnd-001 and src-001: every anchor is unique and cited_by stays in its project."""
        items = [(g["project"], i) for g in self.D["findings_view"] for i in g["items"]]
        srcs = [s for g in self.D["sources_view"] for s in g["items"]]
        anchors = [i["anchor"] for _, i in items] + [s["anchor"] for s in srcs]
        self.assertEqual(len(anchors), len(set(anchors)))
        self.assertIn("f-spider-research-fnd-001", anchors)
        heads = {(p, i["id"]): i["headline"] for p, i in items}
        for s in srcs:
            for c in s["cited_by"]:
                self.assertEqual((c["project"], c["anchor"], c["headline"]), (s["project"], f"f-{s['project']}-{c['id']}", heads[(s["project"], c["id"])]))
        self.assertIn('"anchor":"s-krenko-src-001"', self.html.replace(" ", ""))

    def test_future_and_showcase_mode(self):
        tal = next(d for g in self.D["groups"] for c in g["commanders"] for d in c["decks"] if d["project"] == "talrand")
        self.assertEqual(tal["future"]["waits_for"][0]["releases"], "2027-01-15")
        self.assertEqual(self.D["page"]["mode"], "showcase")
        self.assertIn("three.min.js", self.html)
        self.assertTrue(self.D["page"]["show"]["fan"])


@LIVE
class ResearchOnly(unittest.TestCase):
    def test_research_only_report(self):
        tmp = tempfile.mkdtemp()
        try:
            report, D, html = build_pipeline(tmp, "from-workspace", RESEARCH_ONLY)
            self.assertEqual(D["groups"], [])
            self.assertEqual(len(D["rankings"]), 2)
            r = D["research"][0]
            self.assertEqual([c["name"] for c in r["commanders"]], ["Spider-Gwen, Free Spirit", "Electro, Assaulting Battery"])
            self.assertTrue(r["commanders"][0]["disadvantages"] and r["disagreements"])
            self.assertEqual(sum(len(g["items"]) for g in D["sources_view"]), 2)
            self.assertIn('"rankings"', html)
            hidden = {x["name"] for x in report["sections"] if not x["included"]}
            self.assertIn("overview and decklist", hidden)
            build_pipeline(tmp, "from-workspace", RESEARCH_ONLY, "--mode", "summary", site=False)
            with open(os.path.join(tmp, "summary.md"), encoding="utf-8") as h:
                md = h.read()
            self.assertIn("## Ranking: Spider-Man heroes", md)
            self.assertIn("| 2 | A | Electro's Bolt | 61.2% (252 of 412 decks) |", md)
            self.assertIn("popularity", md)
            self.assertIn("### Commanders compared", md)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


@LIVE
class Modes(unittest.TestCase):
    def test_interactive_and_summary(self):
        tmp = tempfile.mkdtemp()
        try:
            _, D, html = build_pipeline(tmp, "from-workspace", TALRAND, "--mode", "interactive")
            self.assertEqual((D["viewer"], D["page"]["show"]["fan"], D["page"]["calm"]), ("simple", False, True))
            self.assertNotIn("three.min.js", html)  # no three.js reference at all
            self.assertTrue(D["page"]["show"]["charts"] and D["page"]["show"]["prices"])
            os.remove(os.path.join(tmp, "page-data.json"))
            build_pipeline(tmp, "from-workspace", TALRAND, "--mode", "summary", site=False)
            self.assertFalse(os.path.exists(os.path.join(tmp, "page-data.json")))  # summary mode writes Markdown only
            with open(os.path.join(tmp, "summary.md"), encoding="utf-8") as h:
                md = h.read()
            for part in ("# Talrand spells", "**Plan.**", "**Rule 0.** Bracket: 2 (Core); Game Changers: None\n", "**Audit.** Not audited",
                         "Roles (from fixed Oracle-text rules", "### Decklist", "1 Talrand, Sky Summoner", "**Planned for release.**", "Price ladder"):
                self.assertIn(part, md)
            self.assertNotIn("weak", md.lower())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def args(**kw):
    a = argparse.Namespace(mode="showcase", style=None, images="cdn", viewer=None, show=None, hide=None, title=None, subtitle=None, out=None)
    a.__dict__.update(kw)
    return a


def rec(name, pid, commander=False, back=None, type_line="Creature \u2014 Goblin"):
    """A deck_check card record (the fields site_data reads)."""
    return {"name": name, "qty": 1, "commander": commander, "printing_id": pid, "set": "tst", "collector_number": "1", "type_line": type_line,
            "cmc": 1, "mana_cost": "{R}", "color_identity": ["R"], "game_changer": False, "price_usd": 0.5, "image": f"https://cards.scryfall.io/{pid}.jpg",
            "back_image": back, "status": "legal", "roles": {}}


def sf(layout, name, pid, faces, top=False):
    """Minimal Scryfall card in its real shape (checked against api.scryfall.com, Nov 2026): transform and modal DFCs carry
    image_uris per face and none on the card; split, adventure and flip cards have one top-level image for both halves."""
    img = lambda side: {"normal": f"https://cards.scryfall.io/normal/{side}/{pid[0]}/{pid[1]}/{pid}.jpg", "art_crop": "x"}
    return {"object": "card", "id": pid, "name": name, "layout": layout, "set": "tst", "collector_number": "1", "type_line": "Creature",
            **({"image_uris": img("front")} if top else {}),
            "card_faces": [dict({"object": "card_face", "name": n}, **({} if top else {"image_uris": img(side)}))
                           for n, side in zip(faces, ("front", "back"))]}


LAYOUTS = {  # layout -> (card, has a separate back image)
    "transform": (sf("transform", "Delver of Secrets // Insectile Aberration", "6904ea20-e504-47da-95a0-08739fdde260",
                     ["Delver of Secrets", "Insectile Aberration"]), True),
    "modal_dfc": (sf("modal_dfc", "Valakut Awakening // Valakut Stoneforge", "228e551e-023a-4c9a-8f32-58dae6ffdf7f",
                     ["Valakut Awakening", "Valakut Stoneforge"]), True),
    "split": (sf("split", "Fire // Ice", "18303862-4726-4136-814f-157aa7006579", ["Fire", "Ice"], top=True), False),
    "adventure": (sf("adventure", "Bonecrusher Giant // Stomp", "b5b71cd2-de35-451f-b16e-2e3936169407", ["Bonecrusher Giant", "Stomp"], top=True), False),
    "flip": (sf("flip", "Akki Lavarunner // Tok-Tok, Volcano Born", "6ee6cd34-c117-4d7e-97d1-8f8464bfaac8",
                ["Akki Lavarunner", "Tok-Tok, Volcano Born"], top=True), False),
}


class Data(unittest.TestCase):
    """Offline: card data comes only from deck_check's JSON; missing data never aborts a build."""

    def test_back_face_from_card_record(self):
        site = site_data.Site(args(), multi=False)
        for layout, (card, two_images) in LAYOUTS.items():
            with self.subTest(layout):
                r, pid = record(card), card["id"]
                self.assertTrue(r["image"].endswith(f"/front/{pid[0]}/{pid[1]}/{pid}.jpg"))
                if two_images:
                    self.assertTrue(r["back_image"].endswith(f"/back/{pid[0]}/{pid[1]}/{pid}.jpg"))
                    self.assertEqual(site.add_img(r), (pid + "_f", pid + "_b"))
                    self.assertEqual(site.D["images"][pid + "_b"], r["back_image"])
                else:
                    self.assertIsNone(r["back_image"])
                    self.assertEqual(site.add_img(r), (pid + "_f", None))
                    self.assertNotIn(pid + "_b", site.D["images"])

    def test_deck_check_gets_the_project(self):
        tmp = tempfile.mkdtemp()
        argv = []

        def fake_run(cmd, **kw):
            argv.extend(cmd)
            open(cmd[cmd.index("--json") + 1], "w", encoding="utf-8").write("{}")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        try:
            with mock.patch.object(site_data.subprocess, "run", side_effect=fake_run):
                site_data.deck_check("deck.txt", tmp, WS, cards_only=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(argv[argv.index("--project") + 1], WS)  # its research preferences decide the providers

    def fake_deck_check(self, path, tmp, project, cheapest=False, cards_only=False):
        """deck_check with Scryfall half down: the commander and two cards have data, the rest are unavailable."""
        self.projects.append(project)
        if cards_only:
            return {"cards": [], "checks": [], "unavailable": ["Scryfall: no card data for 3 cards"], "data": {"verification": "unavailable", "as_of": None}}
        brew = json.load(open(path, encoding="utf-8"))
        cmd = brew["commander"]["cards"][0]["name"]
        cards = [rec(cmd, "c0", commander=True)] + [rec(c["name"], f"d{i}") for i, c in enumerate(brew["deck"][:2])]
        stats = {"price_usd": 1.5, "average_mv": 1, "lands": 0, "game_changers": [], "curve": {"1": 2}, "types": {"Creature": 2}}
        return {"cards": cards, "checks": [{"id": "chk-cards-1", "status": "unverified", "requirement": "x", "detail": "", "cards": []}],
                "stats": stats, "deck_hash": brew["deck_hash"], "checked": "2026-11-04",
                "unavailable": ["Scryfall: no card data for 97 cards: ..."], "data": {"verification": "stale", "as_of": "2026-10-30 10:00"}}

    def add(self, fake=None):
        self.projects = []
        site = site_data.Site(args(), multi=False)
        site.D["look"] = site_data.resolve_look([])
        with mock.patch.object(site_data, "deck_check", side_effect=fake or self.fake_deck_check), \
                mock.patch("urllib.request.urlopen", side_effect=AssertionError("no network")):
            site_data.add_project(site, WS)
        return site, [d for g in site.D["groups"] for c in g["commanders"] for d in c["decks"]]

    def test_unavailable_cards_do_not_abort_a_page(self):
        site, decks = self.add()
        self.assertEqual(sorted(d["id"] for d in decks), ["b3", "b4"])
        texts = [u["text"] for u in site.D["accuracy"]["unverified"]]
        self.assertTrue(any("no card data for 97 cards" in t for t in texts))
        self.assertTrue(any("card data stale" in t for t in texts))
        self.assertTrue(any("no card data for 3 cards" in t for t in texts))  # research lookups too
        self.assertEqual(set(self.projects), {os.path.abspath(WS)})           # builds, research and swap lookups

    def test_build_without_card_data_is_left_out(self):
        def fake(path, tmp, project, cheapest=False, cards_only=False):
            if path.endswith("brew-b3.json"):
                return {"cards": [], "checks": [], "unavailable": ["Scryfall: unreachable"], "data": {"verification": "unavailable", "as_of": None}}
            return self.fake_deck_check(path, tmp, project, cheapest, cards_only)

        site, decks = self.add(fake)
        self.assertEqual([d["id"] for d in decks], ["b4"])
        self.assertTrue(any(u["text"] == "build b3 not shown: no card data" for u in site.D["accuracy"]["unverified"]))

    def test_nothing_to_show_exits(self):
        site = site_data.Site(args(out=os.path.join(tempfile.gettempdir(), "never-written.json")), multi=False)
        site.D["look"] = site_data.resolve_look([])
        with self.assertRaises(SystemExit):
            site_data.finish(site, tempfile.gettempdir())


@unittest.skipUnless(importlib.util.find_spec("PIL"), "needs Pillow")
class Atlas(unittest.TestCase):
    """Offline: atomic image cache, corrupt files refetched, 5xx retried."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, HERE)
        import atlas
        cls.atlas = atlas

    def setUp(self):
        from PIL import Image
        self.tmp = tempfile.mkdtemp()
        self.raw, self.out = os.path.join(self.tmp, "raw"), os.path.join(self.tmp, "out")
        os.makedirs(self.raw)
        self.src = os.path.join(self.tmp, "src.jpg")
        Image.new("RGB", (488, 680), (200, 30, 30)).save(self.src, "JPEG")
        buf = io.BytesIO()
        Image.new("RGB", (488, 680), (30, 30, 200)).save(buf, "JPEG")
        self.jpeg = buf.getvalue()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_corrupt_or_empty_cache_is_refetched(self):
        open(os.path.join(self.raw, "a_f.jpg"), "wb").close()                      # zero bytes
        open(os.path.join(self.raw, "b_f.jpg"), "wb").write(b"<html>oops</html>")  # not an image
        url = "file://" + self.src.replace("\\", "/")
        man, failed = self.atlas.build({"a_f": url, "b_f": url}, self.out, raw_dir=self.raw, width=48)
        self.assertEqual(failed, [])
        self.assertEqual(set(man["cards"]), {"a_f", "b_f"})
        self.assertTrue(all(self.atlas.valid(os.path.join(self.raw, k + ".jpg")) for k in ("a_f", "b_f")))
        self.assertEqual([f for f in os.listdir(self.raw) if f.endswith(".tmp")], [])

    def test_truncated_jpeg_is_refetched_or_skipped(self):
        cut = self.jpeg[: len(self.jpeg) // 2]  # header intact, so Image.verify() would accept it
        open(os.path.join(self.raw, "t_f.jpg"), "wb").write(cut)
        self.assertFalse(self.atlas.valid(os.path.join(self.raw, "t_f.jpg")))
        url = "file://" + self.src.replace("\\", "/")
        man, failed = self.atlas.build({"t_f": url}, self.out, raw_dir=self.raw, width=48)
        self.assertEqual((failed, set(man["cards"])), ([], {"t_f"}))  # refetched
        # one image that still can't be decoded at packing time is a failure, never a crashed build
        open(os.path.join(self.raw, "t_f.jpg"), "wb").write(cut)
        open(os.path.join(self.raw, "u_f.jpg"), "wb").write(self.jpeg)
        with mock.patch.object(self.atlas, "valid", return_value=True):
            man, failed = self.atlas.build({"t_f": url, "u_f": url}, self.out, raw_dir=self.raw, width=48)
        self.assertEqual([k for k, _ in failed], ["t_f"])
        self.assertEqual(set(man["cards"]), {"u_f"})

    def test_bad_download_never_lands_in_the_cache(self):
        with mock.patch.object(self.atlas, "http_get", return_value=b"not an image"):
            man, failed = self.atlas.build({"x_f": "https://cards.scryfall.io/x.jpg"}, self.out, raw_dir=self.raw, width=48)
        self.assertEqual([k for k, _ in failed], ["x_f"])
        self.assertEqual(os.listdir(self.raw), [])  # no partial or bogus file left behind
        self.assertEqual(man["cards"], {})

    def test_5xx_is_retried(self):
        import urllib.error
        from edhcore.http import Client
        calls = []

        class Ok:
            def __init__(s, b): s.b = b
            def __enter__(s): return io.BytesIO(s.b)
            def __exit__(s, *x): return False

        def fake(req, *a, **k):
            calls.append(req.headers.get("Accept"))
            if len(calls) == 1:
                raise urllib.error.HTTPError(req.full_url, 502, "bad gateway", {}, io.BytesIO(b""))
            return Ok(self.jpeg)

        with mock.patch.object(self.atlas, "_client", Client(sleep=lambda s: None)), mock.patch("urllib.request.urlopen", side_effect=fake):
            man, failed = self.atlas.build({"y_f": "https://cards.scryfall.io/y.jpg"}, self.out, raw_dir=self.raw, width=48)
        self.assertEqual(failed, [])
        self.assertEqual(calls, ["*/*", "*/*"])
        self.assertIn("y_f", man["cards"])


@LIVE
class CacheReuse(unittest.TestCase):
    """A 2-variant page built twice in one cache: each card is looked up once, and the rebuild needs no card lookups."""

    def test_collection_only_in_the_private_copy(self):
        tmp = tempfile.mkdtemp()
        try:
            cf = os.path.join(tmp, "collection.json")
            with open(cf, "w", encoding="utf-8") as h:
                json.dump({"cards": [{"name": "Nothing Owned", "oracle_id": "none", "printing_id": None, "qty": 1}]}, h)
            _, D, html = build_pipeline(tmp, "from-workspace", WS, "--include-notes", "--collection", cf)
            d = D["groups"][0]["commanders"][0]["decks"][0]
            self.assertEqual(d["missing"]["cards"], sum(c["qty"] for c in d["cards"] if not c["commander"]))
            self.assertTrue(all(c["owned"] == "missing" for c in d["cards"]))
            self.assertIn("Not in your collection", html)
            self.assertIn("Missing cards", [x["label"] for x in d["hero"]["stats"]])
            shared = os.path.join(tmp, "shared")
            os.makedirs(shared)
            _, D, _ = build_pipeline(shared, "from-workspace", WS, "--collection", cf)
            d = D["groups"][0]["commanders"][0]["decks"][0]
            self.assertIsNone(d["missing"])                              # a shared page never shows ownership
            self.assertTrue(all(c["owned"] is None for c in d["cards"]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_two_commanders_side_by_side(self):
        tmp = tempfile.mkdtemp()
        try:
            _, D, _ = build_pipeline(tmp, "from-workspace", PARTNERS)
            errors, v = browse(self, os.path.join(tmp, "site", "index.html"), """({
                cards: [...document.querySelectorAll('.hero-art.duo .hero-card')].map(b => b.getAttribute('aria-label')),
                text: document.querySelector('.hero').innerText})""")
            self.assertEqual(errors, [])
            self.assertEqual(v["cards"], ["Tymna the Weaver, open card", "Thrasios, Triton Hero, open card"])
            self.assertIn("Tymna the Weaver + Thrasios, Triton Hero", v["text"])
            self.assertEqual(sum(c["qty"] for c in D["groups"][0]["commanders"][0]["decks"][0]["cards"]), 100)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_template_folder_is_swappable(self):
        tmp = tempfile.mkdtemp()
        try:
            tpl = os.path.join(tmp, "tpl")
            shutil.copytree(os.path.join(HERE, "..", "assets", "template"), tpl)
            with open(os.path.join(tpl, "page.css"), "a", encoding="utf-8") as h:
                h.write("/* my-house-style */\n")
            _, D, _ = build_pipeline(tmp, "from-workspace", WS, site=False)
            b = run(os.path.join(HERE, "build_site.py"), os.path.join(tmp, "page-data.json"), "--out", os.path.join(tmp, "site"), "--template", tpl)
            self.assertTrue(json.loads(b.stdout)["pass"], b.stdout)
            self.assertIn("/* my-house-style */", open(os.path.join(tmp, "site", "index.html"), encoding="utf-8").read())
            with open(os.path.join(tpl, "index.html"), encoding="utf-8") as h:
                broken = h.read().replace("/*__JS__*/", "")
            with open(os.path.join(tpl, "index.html"), "w", encoding="utf-8") as h:
                h.write(broken)
            b = run(os.path.join(HERE, "build_site.py"), os.path.join(tmp, "page-data.json"), "--out", os.path.join(tmp, "site2"), "--template", tpl)
            self.assertNotEqual(b.returncode, 0)
            self.assertIn("lacks /*__JS__*/", b.stderr)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_project_conventions_on_the_page(self):
        tmp = tempfile.mkdtemp()
        try:
            ws = os.path.join(tmp, "ws")
            shutil.copytree(WS, ws)
            f = next(os.path.join(ws, n) for n in sorted(os.listdir(ws)) if n.startswith("brew"))
            with open(f, encoding="utf-8") as h:
                b = json.load(h)
            b["role_targets"] = {"lands": {"min": 36, "max": 37}, "roles": {"ramp": {"min": 10, "max": 12}, "protection": {"min": 7, "max": None}},
                                 "note": "PROJECT.md role targets"}
            b["theme_policy"] = dict(b.get("theme_policy") or {"mode": "prefer"}, tiers=[{"id": "goblin", "label": "Goblins"}, {"id": "red", "label": "Other red"}])
            themed = [c for c in b["deck"] if c.get("theme") == "on_theme"]
            themed[0]["theme_tier"], themed[1]["theme_tier"] = "goblin", "red"
            with open(f, "w", encoding="utf-8") as h:
                json.dump(b, h)
            _, D, html = build_pipeline(tmp, "from-workspace", ws)
            d = next(x for c in D["groups"][0]["commanders"] for x in c["decks"] if x["id"] in os.path.basename(f))
            self.assertEqual(d["stats"]["template_kind"], "yours")
            self.assertEqual(d["stats"]["template"]["lands"][1:], [36, 37])
            self.assertEqual(d["stats"]["template"]["protection"][1:], [7, None])   # open-ended "7+"
            self.assertIn("your target 36–37", [x.get("context") for x in d["hero"]["stats"]])
            by = {c["name"]: c for c in d["cards"]}
            self.assertEqual((by[themed[0]["name"]]["tier"], by[themed[1]["name"]]["tier"]), ("Goblins", "Other red"))
            self.assertEqual([t["label"] for t in d["theme"]["tiers"]], ["Goblins", "Other red"])
            self.assertIn("Against your targets", html)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_build_label_overrides_variant_id(self):
        tmp = tempfile.mkdtemp()
        try:
            ws = os.path.join(tmp, "ws")
            shutil.copytree(WS, ws)
            f = next(os.path.join(ws, n) for n in sorted(os.listdir(ws)) if n.startswith("brew"))
            with open(f, encoding="utf-8") as h:
                b = json.load(h)
            b["label"] = "B3 Upgraded"
            foil = b["deck"][0]
            foil["finish"] = "foil"
            with open(f, "w", encoding="utf-8") as h:
                json.dump(b, h)
            _, D, _ = build_pipeline(tmp, "from-workspace", ws)
            decks = [d for c in D["groups"][0]["commanders"] for d in c["decks"]]
            labels = sorted(d["label"] for d in decks)
            self.assertIn("B3 Upgraded", labels)
            self.assertEqual(len(labels), 2)  # the other build keeps its default
            d = next(d for d in decks if d["label"] == "B3 Upgraded")
            card = next(c for c in d["cards"] if c["name"] == foil["name"])
            self.assertEqual(card["finish"], "foil")
            self.assertIn(f"{card['qty']} {card['name']} ({card['set'].upper()}) {card['cn']} *F*", d["moxfield"])  # Moxfield's foil marker
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_two_variants_share_one_lookup(self):
        tmp = tempfile.mkdtemp()
        try:
            env = dict(os.environ, PYTHONPATH=BENCH, EDHC_CACHE_DIR=os.path.join(tmp, "cache"), PYTHONIOENCODING="utf-8")
            rows = {}
            for phase in ("cold", "warm"):
                log = os.path.join(tmp, phase + ".jsonl")
                p = subprocess.run([shutil.which("uv"), "run", "--quiet", "--script", os.path.join(HERE, "site_data.py"), "from-workspace", WS,
                                    "--out", os.path.join(tmp, phase, "page-data.json"), "--images", "cdn"],
                                   capture_output=True, text=True, encoding="utf-8", env=dict(env, EDHC_BENCH_LOG=log))
                self.assertEqual(p.returncode, 0, p.stderr)
                rows[phase] = [r for r in (json.loads(x) for x in open(log, encoding="utf-8")) if r.get("kind", "request") == "request"] if os.path.exists(log) else []
            coll = [r for r in rows["cold"] if "/cards/collection" in r["url"]]
            self.assertTrue(coll)
            dup = [k for k, n in collections.Counter((r["url"], r["body"]) for r in rows["cold"]).items() if n > 1]
            self.assertEqual(dup, [])                                                    # nothing asked twice
            self.assertFalse([r for r in rows["cold"] if re.search(r"/cards/[0-9a-f-]{36}", r["url"])])  # no per-card back-face calls
            self.assertEqual([r["url"] for r in rows["warm"] if "api.scryfall.com" in r["url"]], [])   # rebuild: all from cache
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
