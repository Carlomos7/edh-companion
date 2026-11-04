"""companion.py: workspace resolution, schema validation, citation IDs and stale-audit detection (offline).

Run: uv run --with jsonschema --with pyyaml --with certifi python -m unittest discover -s tests/unit
"""
import json, os, re, shutil, subprocess, sys, tempfile, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COMPANION = os.path.join(ROOT, "plugins", "edh-companion", "scripts", "companion.py")
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "spider-gwen")  # same project the eval scaffolds create


def sh(*args, cwd=None):
    r = subprocess.run([sys.executable, COMPANION, *args], capture_output=True, text=True, encoding="utf-8", cwd=cwd)
    return r.returncode, r.stdout


class Companion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = os.path.join(self.tmp, "EDHCompanion", "projects", "spider-gwen")
        shutil.copytree(FIXTURE, self.p)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def edit(self, name, fn):
        path = os.path.join(self.p, name)
        d = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
        fn(d)
        json.dump(d, open(path, "w", encoding="utf-8"))

    def test_local_folder_needs_marker(self):
        code, out = sh("where", cwd=self.tmp)
        self.assertNotIn("marked folder", out)            # a stray EDHCompanion folder isn't used
        self.assertIn("isn't the workspace", out)
        open(os.path.join(self.tmp, "EDHCompanion", "workspace.yaml"), "w").close()
        code, out = sh("where", cwd=self.tmp)
        self.assertEqual(code, 0)
        self.assertIn("marked folder in the current directory", out)

    def test_started_inside_a_project(self):
        code, out = sh("where", cwd=os.path.join(self.p, "decklists"))
        self.assertIn("project    spider-gwen", out)
        code, out = sh("where", cwd=self.tmp)
        self.assertNotIn("Claude Code started inside it", out)

    def test_research_prefs_and_project_override(self):
        home = os.path.join(self.tmp, "home")
        cfg = os.path.join(home, ".config", "edh-companion")
        os.makedirs(cfg)
        env = dict(os.environ, HOME=home, USERPROFILE=home)
        run = lambda *a: subprocess.run([sys.executable, COMPANION, *a], capture_output=True, text=True, encoding="utf-8", env=env).stdout
        out = run("research", self.p)
        self.assertIn("not set up yet", out)
        with open(os.path.join(cfg, "config.yaml"), "w", encoding="utf-8") as h:
            h.write("research:\n  approved: {card_data: MTG MCP, transcripts: YouTube Transcript}\n  excluded: [MTGGoldfish]\n"
                    "  approval: every_time\n  depth: quick\n  status: {transcripts: failed}\n")
        with open(os.path.join(self.p, "PROJECT.md"), "a", encoding="utf-8") as h:
            h.write("\n## Research preferences\nNo videos for this deck.\n")
        out = run("research", self.p)
        self.assertIn("card_data=MTG MCP", out)
        self.assertIn("transcripts=YouTube Transcript [failed]", out)
        self.assertIn("excluded:       MTGGoldfish", out)
        self.assertIn("ask before research: every_time", out)
        self.assertIn("depth:          quick", out)
        self.assertIn("No videos for this deck.", out)
        self.assertIn("permission prompts are separate", out)

    def test_projects_lists_for_resume(self):
        open(os.path.join(self.tmp, "EDHCompanion", "workspace.yaml"), "w").close()
        code, out = sh("projects", cwd=self.tmp)
        self.assertIn("project spider-gwen", out)
        self.assertIn("A fast Spider-Gwen aggro deck.", out)  # the goal, not the heading
        self.assertIn("brew.json", out)

    def test_valid_project_not_audited(self):
        code, out = sh("validate", self.p)
        self.assertEqual(code, 0, out)
        self.assertIn("not audited", out)

    def audit(self, version, deck_hash, verdict="pass", status="pass"):
        return {"schema_version": "1.0", "created": "2026-11-04", "subject": {"kind": "deck", "brew_file": "brew.json", "deck": {"version": version, "deck_hash": deck_hash}},
                "auditor": {"independent": True}, "checks": [{"id": "chk-count-1", "area": "count", "requirement": "100 cards", "kind": "deterministic", "status": status}],
                "required_fixes": [], "verdict": {"status": verdict, "summary": "ok"}}

    def test_current_and_stale_audit(self):
        json.dump(self.audit(3, "31e00e29a1f3"), open(os.path.join(self.p, "audit.json"), "w"))
        code, out = sh("validate", self.p)
        self.assertEqual(code, 0, out)
        self.assertIn("current, verdict pass", out)
        self.edit("brew.json", lambda d: d.update(version=4, deck_hash="aaaaaaaaaaaa"))
        code, out = sh("validate", self.p)
        self.assertIn("STALE", out)

    def test_rule_change_makes_audit_stale(self):
        code, gh = sh("goals-hash", self.p)
        a = self.audit(3, "31e00e29a1f3")
        a["subject"]["goals_hash"] = gh.strip()
        json.dump(a, open(os.path.join(self.p, "audit.json"), "w"))
        self.assertIn("current", sh("validate", self.p)[1])
        with open(os.path.join(self.p, "PROJECT.md"), "a", encoding="utf-8") as h:
            h.write("\n## Theme\n- Mode: strict\n")
        self.assertIn("PROJECT.md rules changed", sh("validate", self.p)[1])

    def test_pass_with_unverified_check_is_an_error(self):
        json.dump(self.audit(3, "31e00e29a1f3", status="unverified"), open(os.path.join(self.p, "audit.json"), "w"))
        code, out = sh("validate", self.p)
        self.assertEqual(code, 1)
        self.assertIn("verdict is pass but a check is fail or unverified", out)

    def test_unknown_citation_and_schema_errors(self):
        research = {"schema_version": "1.0", "version": 1, "created": "2026-11-04", "scope": {"question": "q"}, "methodology": {"approach": "a", "coverage": {}},
                    "sources": [{"id": "src-001", "title": "t", "url": "https://example.com", "type": "article", "accessed": "2026-11-04"}],
                    "findings": [{"id": "fnd-001", "claim": "c", "class": "community_opinion", "confidence": "low", "evidence": ["src-009"]}], "gaps": []}
        json.dump(research, open(os.path.join(self.p, "research.json"), "w"))
        self.edit("brew.json", lambda d: d.pop("deck"))
        code, out = sh("validate", self.p)
        self.assertEqual(code, 1)
        self.assertIn("src-009 is not a defined source", out)
        self.assertIn("'deck' is a required property", out)

    def put(self, name, doc):
        with open(os.path.join(self.p, name), "w", encoding="utf-8") as h:
            json.dump(doc, h)

    def research(self, **extra):
        r = {"schema_version": "1.0", "version": 1, "created": "2026-11-04", "scope": {"question": "q"}, "methodology": {"approach": "a", "coverage": {}},
             "sources": [{"id": "src-001", "title": "t", "url": "https://example.com/a", "type": "stats", "accessed": "2026-11-01"},
                         {"id": "src-w1-001", "title": "t2", "url": "https://example.com/b", "type": "article", "accessed": "2026-11-01"}],
             "findings": [{"id": "fnd-w1-001", "claim": "c", "class": "community_opinion", "confidence": "low", "evidence": ["src-w1-001"]}], "gaps": []}
        r.update(extra)
        self.put("research.json", r)
        return sh("validate", self.p)

    def test_research_new_rules(self):
        code, out = self.research()
        self.assertEqual(code, 0, out)                              # worker-prefixed IDs are valid
        card = lambda **k: {"card": {"name": "Sol Ring"}, "rank": 1, "why": "w", "evidence": ["src-001"], **k}
        src = lambda i, url, **k: {"id": i, "title": "t", "url": url, "type": "stats", "accessed": "2026-11-01", **k}
        cases = {
            "rankings: evidence src-404": dict(rankings=[{"group": "G", "method": "m", "cards": [card(evidence=["src-404"])]}]),
            "disagreements: evidence src-404": dict(disagreements=[{"topic": "t", "positions": [{"position": "p", "evidence": ["src-404"]}]}]),
            "feasibility: evidence fnd-404": dict(feasibility={"question": "q", "verdict": "feasible", "evidence": ["fnd-404"], "commanders": ["Krenko, Mob Boss"]}),
            "total_decks 0 must be > 0": dict(rankings=[{"group": "G", "method": "m", "cards": [card(total_decks=0)]}]),
            "decks 50 > total_decks 40": dict(rankings=[{"group": "G", "method": "m", "cards": [card(decks=50, total_decks=40)]}]),
            "inclusion_pct 50 != 25.0": dict(rankings=[{"group": "G", "method": "m", "cards": [card(inclusion_pct=50, decks=10, total_decks=40)]}]),
            "src-002 has the same URL as src-001": dict(sources=[src("src-001", "https://Example.com/a"), src("src-002", "https://example.com/a/?utm_source=x")], findings=[]),
            "accessed 2999-01-01 is in the future": dict(sources=[src("src-001", "https://example.com/a", accessed="2999-01-01")], findings=[]),
            "published 2999-02 is in the future": dict(sources=[src("src-001", "https://example.com/a", published="2999-02")], findings=[]),
            "locator source src-404 is not a defined source": dict(sources=[src("src-001", "https://example.com/a")], findings=[
                {"id": "fnd-w1-001", "claim": "c", "class": "community_opinion", "confidence": "low", "evidence": ["src-001"],
                 "locators": [{"source": "src-404", "at": ["1:00"]}]}]),
            "locator source src-002 is not in its evidence": dict(sources=[src("src-001", "https://example.com/a"), src("src-002", "https://example.com/b")], findings=[
                {"id": "fnd-w1-001", "claim": "c", "class": "community_opinion", "confidence": "low", "evidence": ["src-001"],
                 "locators": [{"source": "src-002", "at": ["1:00-2:00"]}]}]),
        }
        for msg, extra in cases.items():   # checks newer than 7.8 warn on research.json so existing projects stay valid
            with self.subTest(msg):
                code, out = self.research(**extra)
                self.assertEqual(code, 0, out)
                self.assertRegex(out, r"WARN .*" + re.escape(msg))
        for msg, extra in {"findings: evidence src-404": dict(findings=[{"id": "fnd-w1-001", "claim": "c", "class": "community_opinion", "confidence": "low", "evidence": ["src-404"]}]),
                           "duplicate source or finding id": dict(findings=[{"id": "fnd-w1-001", "claim": "c", "class": "community_opinion", "confidence": "low", "evidence": []}] * 2)}.items():
            with self.subTest(msg):    # 7.8's checks stay errors
                code, out = self.research(**extra)
                self.assertEqual(code, 1, out)
                self.assertRegex(out, r"ERROR .*" + re.escape(msg))
        self.put("research-part-old.json", {})   # pre-merge-research hyphenated part files are just old notes
        self.assertEqual(self.research()[0], 0)
        code, out = self.research(rankings=[{"group": "G", "method": "m", "cards": [card(inclusion_pct=26.5, decks=10, total_decks=40)]}])
        self.assertEqual(code, 0, out)                              # within 2 points

    def test_research_incomplete_and_stale_candidates(self):
        self.research()
        plan = {"schema_version": "1.0", "created": "2026-11-04", "workers": [
            {"slug": "w1", "role": "r", "subjects": [], "id_prefix": "w1", "status": "merged", "part_hash": "a" * 64},
            {"slug": "w2", "role": "r", "subjects": [], "id_prefix": "w2", "status": "pending", "part_hash": None}]}
        self.put("research.plan.json", plan)
        code, out = sh("validate", self.p)
        self.assertEqual(code, 1)
        self.assertIn("research incomplete: worker(s) not merged: w2", out)
        plan["workers"][1].update(status="merged", part_hash="b" * 64)
        self.put("research.plan.json", plan)
        self.assertEqual(sh("validate", self.p)[0], 0)
        self.put("research.part-w3.json", {})
        code, out = sh("validate", self.p)
        self.assertEqual(code, 1)
        self.assertIn("research incomplete: unmerged research.part-w3.json", out)
        os.remove(os.path.join(self.p, "research.part-w3.json"))
        self.put("candidates.json", {})
        os.utime(os.path.join(self.p, "candidates.json"), (1, 1))
        code, out = sh("validate", self.p)
        self.assertEqual(code, 0, out)
        self.assertIn("NOTE  candidates.json stale", out)

    def test_missing_decklist_file(self):
        self.edit("brew.json", lambda d: d.update(decklist="decklists/main-v9.txt"))
        code, out = sh("validate", self.p)
        self.assertIn("decklists/main-v9.txt not found", out)


if __name__ == "__main__":
    unittest.main()
