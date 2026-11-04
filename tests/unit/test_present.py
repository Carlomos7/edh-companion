"""present skill pipeline test: fixture project -> site_data.py -> build_site.py. Needs uv and network (Scryfall).

Run: python tests/unit/test_present.py
"""
import importlib.util, json, os, re, shutil, subprocess, tempfile, unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(ROOT, "plugins", "edh-companion", "skills", "present", "scripts")
WS = os.path.join(ROOT, "tests", "fixtures", "krenko")
spec = importlib.util.spec_from_file_location("site_data", os.path.join(HERE, "site_data.py"))
site_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site_data)


def run(*args):
    return subprocess.run([shutil.which("uv"), "run", "--quiet", "--script", *args], capture_output=True, text=True, encoding="utf-8",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))


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
            self.assertEqual(d["errors"], [])

    def test_audit_states_derived_never_upgraded(self):
        self.assertEqual(self.decks["b3"]["validation"]["state"], "pass_with_warnings")
        self.assertEqual(self.decks["b4"]["validation"]["state"], "audit out of date")
        self.assertNotIn("checks", self.decks["b4"]["validation"])  # an out-of-date audit's checks are never shown
        kinds = {c["kind"] for c in self.decks["b3"]["validation"]["checks"]}
        self.assertEqual(kinds, {"deterministic", "judgment"})
        self.assertIn('"state":"audit out of date"', self.html)
        states = {i["file"]: i["audit_state"] for i in self.report["inputs"] if "audit_state" in i}
        self.assertEqual(states, {"brew-b3.json": "pass_with_warnings", "brew-b4.json": "audit out of date"})
        self.assertIn("| brew-b4.json | 2 | a7499368e991 | audit out of date |", self.checks_md)
        self.assertIn("| cast-by-turn simulation | no |", self.checks_md)

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
        src = self.D["sources"]
        self.assertEqual(len(src), 6)
        self.assertTrue(all(re.match(r"https?://", s["url"]) for s in src))
        video = next(s for s in src if s["links"])
        self.assertEqual([l["url"].rsplit("t=", 1)[1] for l in video["links"]], ["25s", "73s", "89s"])
        self.assertTrue(all(c["url"].startswith("http") for c in self.decks["b3"]["summary"]["community"]))
        self.assertTrue(self.D["groups"][0]["commanders"][0]["youtube"])

    def test_no_invented_numbers(self):
        blob = json.dumps(self.D)
        for key in ('"sim"', '"price_styles"', '"printings"', '"pips"', '"cost_to_buy"'):
            self.assertNotIn(key, blob)
        for d in self.decks.values():
            s, cards = d["stats"], d["cards"]
            self.assertEqual(s["lands"], sum(c["qty"] for c in cards if c["land"] and not c["commander"]))
            self.assertAlmostEqual(s["price"], sum(c["price"] * c["qty"] for c in cards if c["price"] is not None), places=1)
            self.assertEqual(s["unpriced"], [c["name"] for c in cards if c["price"] is None])
        hidden = {x["name"] for x in self.report["sections"] if not x["included"]}
        self.assertIn("cast-by-turn simulation", hidden)
        self.assertTrue(all(x["why_not"] for x in self.report["sections"] if not x["included"]))

    def test_sections_and_swaps(self):
        sw = {s["card"]: s for s in self.D["groups"][0]["swaps"]}
        self.assertEqual(set(sw), {"Goblin Surprise", "Jeska's Will"})  # the rejected rec is left out
        self.assertEqual({f["deck"].split("/")[1] for f in sw["Goblin Surprise"]["fits"]}, {"b3", "b4"})
        titles = [x["title"] for x in self.decks["b3"]["summary"]["sections"]]
        self.assertIn("Proposed cuts", titles)
        self.assertEqual(self.D["theme"]["labels"][0]["label"], "On theme")
        self.assertIn("Player decisions (DECISIONS.md)", titles)
        self.assertIn("Theme (PROJECT.md)", titles)
        self.assertEqual(self.D["title"], "Krenko Goblins")
        dfc = next(c for c in self.decks["b3"]["cards"] if c["name"].startswith("Valakut Awakening"))
        self.assertTrue(dfc["back"] and dfc["back"].endswith("_b"))

    def test_no_theme_no_pills(self):
        brew = {"deck": [{"name": "Sol Ring", "qty": 1, "role": "ramp"}], "theme_policy": None}
        self.assertEqual(site_data.theme_setup([brew]), (None, {}))


if __name__ == "__main__":
    unittest.main()
