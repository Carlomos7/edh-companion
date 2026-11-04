"""companion.py research-plan / merge-research / research-find: deterministic, recoverable merging of parallel research parts (offline).

Run: uv run --with jsonschema --with pyyaml python -m unittest tests.unit.test_merge
"""
import contextlib, copy, glob, hashlib, importlib.util, io, json, os, shutil, subprocess, sys, tempfile, unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COMPANION = os.path.join(ROOT, "plugins", "edh-companion", "scripts", "companion.py")
FIX = os.path.join(ROOT, "tests", "fixtures")
AZULA = os.path.join(FIX, "azula")

spec = importlib.util.spec_from_file_location("companion", COMPANION)
companion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(companion)


def sh(*args):
    r = subprocess.run([sys.executable, COMPANION, *args], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def snapshot(d, skip=()):
    out = {}
    for f in glob.glob(os.path.join(d, "**", "*"), recursive=True):
        rel = os.path.relpath(f, d)
        if os.path.isfile(f) and not rel.startswith(skip):
            with open(f, "rb") as h:
                out[rel] = hashlib.sha256(h.read()).hexdigest()
    return out


def src(slug, n, url, **kw):
    return {"id": f"src-{slug}-{n:03d}", "title": f"{slug} source {n}", "url": url, "type": "article", "accessed": "2026-11-01", **kw}


def fnd(slug, n, ev, **kw):
    return {"id": f"fnd-{slug}-{n:03d}", "claim": f"claim {n} from {slug}", "class": "community_opinion", "confidence": "low", "evidence": ev, **kw}


def part(slug, sources=None, findings=None, status="complete", **extra):
    sources = sources if sources is not None else [src(slug, 1, f"https://example.com/{slug}/1")]
    findings = findings if findings is not None else [fnd(slug, 1, [sources[0]["id"]])]
    doc = {"schema_version": "1.0", "version": 1, "created": "2026-11-04", "scope": {"question": f"{slug} question"},
           "methodology": {"approach": f"{slug} approach", "coverage": {"article": len(sources)}, "tools_used": ["Exa search", f"tool {slug}"],
                           "sources_reviewed": 3, "workers": [{"role": slug, "subjects": [slug], "status": status}]},
           "sources": sources, "findings": findings, "gaps": []}
    doc.update(extra)
    return doc


class Merge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = os.path.join(self.tmp, "azula")
        shutil.copytree(AZULA, self.p)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path(self, *a):
        return os.path.join(self.p, *a)

    def read(self, name):
        with open(self.path(name), encoding="utf-8") as h:
            return json.load(h)

    def put(self, doc, slug=None):
        slug = slug or doc["methodology"]["workers"][0]["role"]
        with open(self.path(f"research.part-{slug}.json"), "w", encoding="utf-8") as h:
            json.dump(doc, h)

    def plan(self, *slugs):
        code, out = sh("research-plan", self.p, *sum((["--worker", f"{s}:{s} role:subject {s}"] for s in slugs), []))
        self.assertEqual(code, 0, out)

    # -- plan --------------------------------------------------------------
    def test_plan_create_and_extend(self):
        self.plan("cmd", "staples")
        plan = self.read("research.plan.json")
        self.assertEqual([w["slug"] for w in plan["workers"]], ["cmd", "staples"])
        self.assertEqual(plan["workers"][0], {"slug": "cmd", "role": "cmd role", "subjects": ["subject cmd"], "id_prefix": "cmd", "status": "pending", "part_hash": None})
        plan["workers"][0].update(status="merged", part_hash="0" * 64)
        with open(self.path("research.plan.json"), "w", encoding="utf-8") as h:
            json.dump(plan, h)
        code, out = sh("research-plan", self.p, "--worker", "cmd:other:x", "--worker", "videos:video worker:a,b")
        self.assertIn("kept   cmd", out)
        plan = self.read("research.plan.json")
        self.assertEqual(plan["workers"][0]["status"], "merged")       # never reset
        self.assertEqual(plan["workers"][2]["subjects"], ["a", "b"])
        self.assertNotEqual(sh("research-plan", self.p, "--worker", "Bad_Slug:r:s")[0], 0)

    def test_merge_needs_plan(self):
        code, out = sh("merge-research", self.p)
        self.assertEqual(code, 1)
        self.assertIn("run research-plan", out)

    # -- complete merge ----------------------------------------------------
    def test_complete_merge_keeps_ids_and_archives(self):
        before = self.read("research.json")
        with open(self.path("research.json"), "rb") as h:
            prev_bytes = h.read()
        self.plan("cmd", "staples")
        self.put(part("cmd"))
        self.put(part("staples"))
        code, out = sh("merge-research", self.p)
        self.assertEqual(code, 0, out)
        self.assertLessEqual(len(out.strip().splitlines()), 10)
        self.assertNotIn("{", out)
        r = self.read("research.json")
        self.assertEqual(r["version"], before["version"] + 1)
        self.assertEqual(r["sources"][:len(before["sources"])], before["sources"])      # existing IDs and content untouched
        self.assertEqual(r["findings"][:len(before["findings"])], before["findings"])
        self.assertEqual([s["id"] for s in r["sources"][-2:]], ["src-cmd-001", "src-staples-001"])
        self.assertEqual(r["methodology"]["coverage"]["article"], before["methodology"]["coverage"]["article"] + 2)
        self.assertEqual(r["methodology"]["sources_reviewed"], before["methodology"]["sources_reviewed"] + 6)
        self.assertEqual(r["methodology"]["tools_used"].count("Exa search"), 1)
        self.assertEqual(len(r["methodology"]["workers"]), 4)
        self.assertFalse(glob.glob(self.path("research.part-*.json")))
        v = f"v{r['version']}"
        self.assertTrue(os.path.exists(self.path("research.parts", v, "research.part-cmd.json")))
        with open(self.path("research.parts", v, "research.prev.json"), "rb") as h:
            self.assertEqual(h.read(), prev_bytes)
        plan = self.read("research.plan.json")
        self.assertTrue(all(w["status"] == "merged" and len(w["part_hash"]) == 64 for w in plan["workers"]))
        code, out = sh("validate", self.p)
        self.assertEqual(code, 0, out)

    def test_idempotent_and_deterministic(self):
        self.plan("cmd", "staples")
        self.put(part("cmd"))
        self.put(part("staples"))
        twin = os.path.join(self.tmp, "twin")
        shutil.copytree(self.p, twin)
        self.assertEqual(sh("merge-research", self.p)[0], 0)
        self.assertEqual(sh("merge-research", twin)[0], 0)
        with open(self.path("research.json"), "rb") as a, open(os.path.join(twin, "research.json"), "rb") as b:
            self.assertEqual(a.read(), b.read())
        snap = snapshot(self.p)
        code, out = sh("merge-research", self.p)
        self.assertEqual((code, out.strip()), (0, "nothing to merge"))
        self.assertEqual(snapshot(self.p), snap)

    # -- refusals ----------------------------------------------------------
    def test_missing_part_refused_nothing_written(self):
        self.plan("cmd", "staples")
        self.put(part("cmd"))
        snap = snapshot(self.p)
        code, out = sh("merge-research", self.p)
        self.assertEqual(code, 1)
        self.assertIn("nothing written", out)
        self.assertIn("- staples (staples role): missing", out)
        self.assertEqual(snapshot(self.p), snap)

    def test_invalid_parts_rejected(self):
        cases = {
            "bad url": part("cmd", sources=[src("cmd", 1, "not-a-url")]),
            "wrong prefix": part("cmd", sources=[src("other", 1, "https://example.com/x")]),
            "unprefixed": part("cmd", findings=[dict(fnd("cmd", 1, ["src-cmd-001"]), id="fnd-099")]),
            "future date": part("cmd", sources=[src("cmd", 1, "https://example.com/x", accessed="2999-01-01")]),
            "dangling ref": part("cmd", findings=[fnd("cmd", 1, ["src-cmd-404"])]),
            "bad edhrec": part("cmd", card_candidates=[{"card": {"name": "Sol Ring"}, "relevance": "r", "evidence": ["src-cmd-001"], "decks": 9, "total_decks": 3}]),
            "no worker status": part("cmd", methodology={"approach": "a", "coverage": {}}),
            "dup url": part("cmd", sources=[src("cmd", 1, "https://example.com/x"), src("cmd", 2, "http://www.example.com/x/")]),
            "dangling ranking ref": part("cmd", rankings=[{"group": "G", "method": "m", "cards": [{"card": {"name": "Sol Ring"}, "rank": 1, "why": "w", "evidence": ["src-cmd-404"]}]}]),
        }
        self.plan("cmd")
        snap = snapshot(self.p)
        for name, doc in cases.items():
            with self.subTest(name):
                self.put(doc, "cmd")
                code, out = sh("merge-research", self.p)
                self.assertEqual(code, 1, out)
                self.assertIn("invalid", out)
                os.remove(self.path("research.part-cmd.json"))
                self.assertEqual(snapshot(self.p), snap)

    def test_partial_then_rerun_merges_remainder(self):
        self.plan("cmd", "staples", "videos")
        self.put(part("cmd"))
        self.put(part("videos", status="partial: transcripts unavailable"))
        code, out = sh("merge-research", self.p, "--allow-partial")
        self.assertEqual(code, 0, out)
        r, plan = self.read("research.json"), self.read("research.plan.json")
        self.assertEqual({w["slug"]: w["status"] for w in plan["workers"]}, {"cmd": "merged", "staples": "pending", "videos": "partial"})
        self.assertIn("fnd-videos-001", [f["id"] for f in r["findings"]])      # the valid partial part is merged, not left behind
        self.assertTrue(os.path.exists(self.path("research.parts", f"v{r['version']}", "research.part-videos.json")))
        gaps = [g for g in r["gaps"] if g.startswith("research incomplete")]
        self.assertEqual(len(gaps), 2)
        self.assertIn("worker staples (staples role: subject staples) missing", gaps[0])
        self.assertIn("transcripts unavailable", gaps[1])
        code, out = sh("validate", self.p)
        self.assertEqual(code, 1)
        self.assertIn("research incomplete: worker(s) not merged: staples (", out)   # videos' gap is recorded, so only staples is owed
        snap = snapshot(self.p)
        self.assertEqual(sh("merge-research", self.p, "--allow-partial"), (0, "nothing to merge\n"))
        self.assertEqual(snapshot(self.p), snap)
        self.put(part("videos"))                                                # a merged partial worker can't be redone in place
        self.assertIn("plan a new worker instead", sh("merge-research", self.p)[1])
        os.remove(self.path("research.part-videos.json"))
        self.put(part("staples"))
        code, out = sh("merge-research", self.p)
        self.assertEqual(code, 0, out)
        r2 = self.read("research.json")
        self.assertEqual(r2["version"], r["version"] + 1)
        self.assertEqual([g for g in r2["gaps"] if g.startswith("research incomplete")], [gaps[1]])   # videos' gap stays
        self.assertIn("No tournament data for Azula.", r2["gaps"])
        self.assertEqual(sh("validate", self.p)[0], 0)

    def test_allow_partial_only_partial_worker_validates(self):
        self.plan("videos")
        self.put(part("videos", status="partial: no transcripts"))
        self.assertEqual(sh("merge-research", self.p)[0], 1)                  # without the flag nothing is written
        code, out = sh("merge-research", self.p, "--allow-partial")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read("research.plan.json")["workers"][0]["status"], "partial")
        self.assertFalse(glob.glob(self.path("research.part-*.json")))
        self.assertEqual(sh("validate", self.p)[0], 0)
        r = self.read("research.json")
        r["gaps"] = [g for g in r["gaps"] if "worker videos" not in g]          # a partial worker without its gap is still incomplete
        with open(self.path("research.json"), "w", encoding="utf-8") as h:
            json.dump(r, h)
        self.assertIn("not merged: videos", sh("validate", self.p)[1])

    def test_all_failed_into_empty_project_keeps_gaps(self):
        os.remove(self.path("research.json"))
        os.remove(self.path("brew.json"))
        self.plan("cmd", "staples")
        self.put(part("cmd", status="failed: no search tools"))
        code, out = sh("merge-research", self.p, "--allow-partial")
        self.assertEqual(code, 0, out)
        r = self.read("research.json")
        self.assertEqual((r["sources"], r["findings"]), ([], []))
        self.assertEqual(len([g for g in r["gaps"] if g.startswith("research incomplete")]), 2)
        self.assertEqual([w["status"] for w in r["methodology"]["workers"]], ["failed: no search tools", "failed: missing"])
        code, out = sh("validate", self.p)
        self.assertIn("not merged: staples", out)                              # still owed, but the record is valid
        self.assertNotIn("research.json: ", out.replace("research.json: research incomplete", ""))

    def test_part_redefining_a_base_id_is_rejected_not_filed(self):
        base = self.read("research.json")
        self.plan("cards")
        self.put(part("cards", sources=[dict(base["sources"][0]), src("cards", 1, "https://example.com/new")],
                      findings=[fnd("cards", 1, ["src-cards-001"])]))
        snap = snapshot(self.p)
        code, out = sh("merge-research", self.p)
        self.assertEqual(code, 1, out)
        self.assertIn("id src-001 must start with src-cards-", out)
        self.assertEqual(snapshot(self.p), snap)                               # nothing filed as "already merged"
        code, out = sh("merge-research", self.p, "--allow-partial")
        self.assertTrue(os.path.exists(self.path("research.part-cards.json")))  # left on disk, never lost
        self.assertEqual(self.read("research.plan.json")["workers"][0]["status"], "failed")
        self.assertEqual(sh("validate", self.p)[0], 1)

    # -- dedup and contradictions -----------------------------------------
    def test_url_dedup_rewrites_refs(self):
        dup = src("cmd", 1, "https://YouTube.com/watch?v=fixtureAzula1&t=30&utm_source=x", type="video", timestamps=["0:30", "2:15"])
        dup2 = src("cmd", 2, "https://EDHREC.com/commanders/azula-cunning-usurper/?utm_medium=y")
        new = src("cmd", 3, "https://example.com/new")
        refs = ["src-cmd-001", "src-cmd-002", "src-cmd-003"]
        doc = part("cmd", sources=[dup, dup2, new], findings=[fnd("cmd", 1, refs)],
                   card_candidates=[{"card": {"name": "Counterspell"}, "relevance": "r", "evidence": refs}],
                   rankings=[{"group": "Interaction", "method": "m", "cards": [{"card": {"name": "Counterspell"}, "rank": 1, "why": "w", "evidence": ["src-cmd-001"]}]}],
                   disagreements=[{"topic": "t", "positions": [{"position": "p", "evidence": ["src-cmd-002"]}]}],
                   alternatives=[{"option": "o", "why": "w", "evidence": ["src-cmd-001"]}],
                   recommendations=[{"text": "x", "evidence": ["src-cmd-002", "src-002"]}],
                   commanders=[{"card": {"name": "Azula, On the Hunt"}, "strategy": "s", "evidence": ["src-cmd-001"]}])
        self.plan("cmd")
        self.put(doc)
        code, out = sh("merge-research", self.p)
        self.assertEqual(code, 0, out)
        self.assertIn("duplicate URLs folded 2", out)
        r = self.read("research.json")
        ids = [s["id"] for s in r["sources"]]
        self.assertNotIn("src-cmd-001", ids)
        self.assertNotIn("src-cmd-002", ids)
        self.assertIn("src-cmd-003", ids)
        self.assertEqual(next(s for s in r["sources"] if s["id"] == "src-003")["timestamps"], ["0:30", "2:15", "11:40"])
        everywhere = [ev for _, ev in companion.evidence_lists(r)]
        self.assertFalse([e for e in everywhere if "src-cmd-001" in e or "src-cmd-002" in e])
        self.assertEqual(next(f for f in r["findings"] if f["id"] == "fnd-cmd-001")["evidence"], ["src-003", "src-002", "src-cmd-003"])
        self.assertEqual(r["recommendations"][-1]["evidence"], ["src-002"])   # rewritten and de-duplicated
        self.assertEqual(sh("validate", self.p)[0], 0)

    def test_norm_url(self):
        n = companion.norm_url
        self.assertEqual(n("HTTPS://Example.COM/a/?utm_source=x&b=1#frag"), n("https://example.com/a?b=1"))
        self.assertEqual(n("https://youtu.be/abc"), n("https://www.youtube.com/watch?v=abc&t=5"))
        for u in ("https://m.youtube.com/shorts/abc", "https://youtube.com/live/abc?si=x", "https://www.youtube.com/embed/abc/"):
            self.assertEqual(n(u), n("https://youtu.be/abc"), u)
        self.assertEqual(n("http://www.edhrec.com/commanders/azula"), n("https://edhrec.com/commanders/azula"))
        self.assertEqual(n("https://m.reddit.com/r/EDH/x"), n("https://reddit.com/r/EDH/x"))
        self.assertNotEqual(n("https://www.youtube.com/watch?v=abc"), n("https://www.youtube.com/watch?v=abd"))
        self.assertNotEqual(n("https://example.com/a"), n("https://example.com/b"))

    def test_contradictory_edhrec_becomes_disagreement(self):
        doc = part("cmd", rankings=[{"group": "dimir THEFT", "method": "m", "cards": [
            {"card": {"name": "thief of sanity"}, "rank": 1, "why": "w", "inclusion_pct": 70.0, "decks": 588, "total_decks": 840, "evidence": ["src-cmd-001"]},
            {"card": {"name": "Hostage Taker"}, "rank": 2, "why": "w", "inclusion_pct": 55.0, "decks": 462, "total_decks": 840, "evidence": ["src-cmd-001"]}]}],
            card_candidates=[{"card": {"name": "NOTION THIEF"}, "relevance": "r", "evidence": ["src-cmd-001"]}])
        self.plan("cmd")
        self.put(doc)
        before = self.read("research.json")
        code, out = sh("merge-research", self.p)
        self.assertEqual(code, 0, out)
        r = self.read("research.json")
        self.assertEqual(len(r["rankings"]), 1)
        thief = r["rankings"][0]["cards"][0]
        self.assertEqual((thief["inclusion_pct"], thief["decks"]), (61.9, 520))          # first kept, never averaged
        self.assertEqual(thief["evidence"], ["src-002", "src-cmd-001"])
        new = r["disagreements"][len(before["disagreements"]):]
        self.assertIn(f"disagreements {len(new)}", out)
        d = next(x for x in new if "Thief of Sanity" in x["topic"])
        self.assertIn("inclusion_pct", d["topic"])
        self.assertEqual([p["evidence"] for p in d["positions"]], [["src-002"], ["src-cmd-001"]])
        self.assertIn("70.0", d["positions"][1]["position"])
        self.assertEqual(len(r["card_candidates"]), len(before["card_candidates"]))     # merged by name, case-insensitive
        self.assertIn("src-cmd-001", r["card_candidates"][2]["evidence"])

    def test_differing_conclusions_become_disagreements(self):
        cand = lambda s, fit, rel: [{"card": {"name": "Sol Ring"}, "relevance": rel, "theme_fit": fit, "evidence": [f"fnd-{s}-001"]}]
        feas = lambda s, v: {"question": "q", "verdict": v, "evidence": [f"src-{s}-001"]}
        r0 = self.read("research.json")
        r0.pop("feasibility", None)
        with open(self.path("research.json"), "w", encoding="utf-8") as h:
            json.dump(r0, h)
        self.plan("a", "b")
        self.put(part("a", card_candidates=cand("a", "on_theme", "ramp"), feasibility=feas("a", "feasible")))
        self.put(part("b", card_candidates=cand("b", "off_theme", "ramp"), feasibility=feas("b", "infeasible")))
        code, out = sh("merge-research", self.p)
        self.assertEqual(code, 0, out)
        r = self.read("research.json")
        self.assertEqual((r["feasibility"]["verdict"], next(c for c in r["card_candidates"] if c["card"]["name"] == "Sol Ring")["theme_fit"]),
                         ("feasible", "on_theme"))                             # first kept ...
        new = {d["topic"]: d for d in r["disagreements"][len(r0.get("disagreements", [])):]}
        self.assertEqual(sorted(new), ["Workers differ on Sol Ring: theme_fit", "Workers differ on feasibility: verdict"])   # ... second recorded
        f = new["Workers differ on feasibility: verdict"]["positions"]
        self.assertEqual([(p["position"], p["evidence"]) for p in f], [("verdict feasible", ["src-a-001"]), ("verdict infeasible", ["src-b-001"])])
        self.assertEqual([p["evidence"] for p in new["Workers differ on Sol Ring: theme_fit"]["positions"]], [["fnd-a-001"], ["fnd-b-001"]])
        self.assertEqual(sh("validate", self.p)[0], 0)

    # -- recovery ----------------------------------------------------------
    def crash_on(self, n):
        real, calls = os.replace, []

        def fake(a, b):
            calls.append(a)
            if len(calls) == n:
                raise OSError("injected crash")
            return real(a, b)
        return mock.patch("os.replace", side_effect=fake)

    def run_inproc(self, *a):
        with contextlib.redirect_stdout(io.StringIO()):
            return companion.merge_research(self.p, *a)

    def test_crash_before_replace_leaves_everything_then_rerun_completes(self):
        self.plan("cmd", "staples")
        self.put(part("cmd"))
        self.put(part("staples"))
        snap = snapshot(self.p, skip=("research.parts",))
        with self.crash_on(1), self.assertRaises(OSError):   # 1st replace: research.json.tmp -> research.json
            self.run_inproc()
        self.assertEqual(snapshot(self.p, skip=("research.parts",)), snap)
        self.assertFalse(os.path.exists(self.path("research.json.tmp")))
        self.assertEqual(self.run_inproc(), 0)
        self.assertEqual(sh("validate", self.p)[0], 0)

    def test_crash_after_replace_before_plan_recovers_without_double_merge(self):
        self.plan("cmd", "staples")
        self.put(part("cmd"))
        self.put(part("staples"))
        with self.crash_on(2), self.assertRaises(OSError):   # 2nd replace: the plan
            self.run_inproc()
        merged = self.read("research.json")
        self.assertEqual(self.run_inproc(), 0)
        self.assertEqual(self.read("research.json"), merged)                 # not merged twice
        self.assertTrue(all(w["status"] == "merged" for w in self.read("research.plan.json")["workers"]))
        self.assertEqual(sh("validate", self.p)[0], 0)

    def test_merge_into_empty_project(self):
        os.remove(self.path("research.json"))
        os.remove(self.path("brew.json"))
        self.plan("cmd", "staples")
        self.put(part("cmd"))
        self.put(part("staples", sources=[src("staples", 1, "https://example.com/cmd/1/")]))
        code, out = sh("merge-research", self.p)
        self.assertEqual(code, 0, out)
        r = self.read("research.json")
        self.assertEqual((r["version"], [s["id"] for s in r["sources"]]), (1, ["src-cmd-001"]))
        self.assertEqual(r["findings"][1]["evidence"], ["src-cmd-001"])
        self.assertEqual(sh("validate", self.p)[0], 0)

    # -- find --------------------------------------------------------------
    def test_research_find(self):
        code, out = sh("research-find", self.p, "--card", "thief of")
        self.assertEqual(code, 0)
        self.assertIn("fnd-003 [popularity_metric/medium]", out)
        self.assertIn("src-004 EDHREC: Dimir theft theme", out)
        self.assertIn("candidate Thief of Sanity", out)
        self.assertIn("rank Dimir theft #1 Thief of Sanity (61.9% 520/840)", out)
        out = sh("research-find", self.p, "--class", "verified_fact")[1]
        self.assertIn("fnd-001", out)
        self.assertNotIn("candidate", out)
        self.assertIn("2 match(es)", out)
        out = sh("research-find", self.p, "--text", "SLOW ramp")[1]
        self.assertIn("fnd-004", out)
        out = sh("research-find", self.p, "--limit", "1")[1].strip().splitlines()
        self.assertEqual(len(out), 2)
        self.assertIn("more", out[1])


class Fixtures(unittest.TestCase):
    def test_fixtures_validate_and_stay_unchanged(self):
        dirs = [AZULA, os.path.join(FIX, "krenko"), os.path.join(FIX, "spider-gwen"),
                os.path.join(FIX, "showcase", "projects", "spider-research"), os.path.join(FIX, "showcase", "projects", "talrand")]
        before = snapshot(FIX)
        for d in dirs:
            code, out = sh("validate", d)
            self.assertEqual(code, 0, f"{d}: {out}")
            self.assertNotIn("ERROR", out)
        tmp = tempfile.mkdtemp()
        try:   # a full merge into a copy must not reach the original
            p = os.path.join(tmp, "azula")
            shutil.copytree(AZULA, p)
            sh("research-plan", p, "--worker", "cmd:c:s")
            with open(os.path.join(p, "research.part-cmd.json"), "w", encoding="utf-8") as h:
                json.dump(part("cmd"), h)
            self.assertEqual(sh("merge-research", p)[0], 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(snapshot(FIX), before)


if __name__ == "__main__":
    unittest.main()
