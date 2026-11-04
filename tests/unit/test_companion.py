"""companion.py: workspace resolution, schema validation, citation IDs and stale-audit detection (offline).

Run: uv run --with jsonschema --with pyyaml --with certifi python -m unittest discover -s tests/unit
"""
import json, os, shutil, subprocess, sys, tempfile, unittest

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

    def test_where_prefers_local_folder(self):
        code, out = sh("where", cwd=self.tmp)
        self.assertEqual(code, 0)
        self.assertIn("current folder", out)

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

    def test_missing_decklist_file(self):
        self.edit("brew.json", lambda d: d.update(decklist="decklists/main-v9.txt"))
        code, out = sh("validate", self.p)
        self.assertIn("decklists/main-v9.txt not found", out)


if __name__ == "__main__":
    unittest.main()
