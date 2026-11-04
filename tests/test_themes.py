"""Theme mode and edge-case tests. Run: python3 -m unittest discover -s tests"""
import json, os, sqlite3, subprocess, sys, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_mtgdb as base
MtgdbTest, SCRIPT = None, base.SCRIPT


class ThemeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.MtgdbTest.setUpClass()
        cls.T = base.MtgdbTest
        cls.vader = cls.T.sid("Darth Vader", "swt")
        cls.sol_sld = cls.T.sid("Sol Ring", "sld")

    def tmap(self, printings, **spec):
        path = os.path.join(self.T.tmp, f"map{time.time_ns()}.json")
        built = spec.pop("built", time.strftime("%Y-%m-%d"))
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"built": built, "spec": spec, "printings": printings}, f)
        return path

    def val(self, deck, tmap=None, *extra, bracket="4"):
        args = (["--themes", tmap] if tmap else []) + ["validate", deck, "--bracket", bracket] + list(extra)
        p = subprocess.run([sys.executable, SCRIPT, "--db", self.T.db] + args, capture_output=True, text=True, env=self.T.env)
        return p.returncode, json.loads(p.stdout)

    def deck(self, lines):
        return base.MtgdbTest.deck(self.T, lines)

    BASE = ["1 Darth Vader (SWT) 12", "1 Sol Ring (C21) 263", "1 Demonic Tutor (CMM) 1", "97 Swamp (SWT) 300"]

    def test_no_theme_file_means_no_theme_checks(self):
        code, rep = self.val(self.deck(self.BASE))
        self.assertNotIn("theme", rep)
        self.assertEqual(code, 0, rep)

    def test_mode_none_skips_everything(self):
        m = self.tmap({"set:swt": "Sith"}, mode="none", labels=["Sith"])
        code, rep = self.val(self.deck(self.BASE), m)
        self.assertNotIn("theme", rep)
        self.assertFalse([w for w in rep["warnings"] if "themed" in w])

    def test_strict_off_theme_is_error_but_commander_and_basics_exempt(self):
        m = self.tmap({"set:swt": "Sith", "sld#999": "Sith"}, mode="strict", labels=["Sith"])
        code, rep = self.val(self.deck(self.BASE), m)
        errs = " ".join(rep["errors"])
        self.assertIn("strict theme", errs)
        self.assertIn("Demonic Tutor", errs)
        self.assertIn("Sol Ring", errs)
        # commander off-theme but exempt by default: no commander error
        m2 = self.tmap({"set:swt": "Sith"}, mode="strict", labels=["Sith"])
        code, rep = self.val(self.deck(["1 Darth Vader (SWT) 12", "99 Swamp (SWT) 300"]), m2)
        self.assertEqual(code, 0, rep)

    def test_commander_must_match(self):
        m = self.tmap({"sld#999": "Sith"}, mode="prefer", labels=["Sith"], commander_must_match=True)
        code, rep = self.val(self.deck(["1 Darth Vader (SWT) 12", "99 Swamp (SWT) 300"]), m)
        self.assertIn("commander Darth Vader is off-theme", " ".join(rep["errors"]))

    def test_basics_not_counted_unless_asked(self):
        m = self.tmap({f"oracle:o-Darth Vader": "Sith"}, mode="strict", labels=["Sith"])  # swamps off-theme
        code, rep = self.val(self.deck(["1 Darth Vader (SWT) 12", "99 Swamp (SWT) 300"]), m)
        self.assertEqual(code, 0, rep)
        m2 = self.tmap({f"oracle:o-Darth Vader": "Sith"}, mode="strict", labels=["Sith"], count_basics=True)
        code, rep = self.val(self.deck(["1 Darth Vader (SWT) 12", "99 Swamp (SWT) 300"]), m2)
        self.assertIn("Swamp", " ".join(rep["errors"]))

    def test_limits_off_theme_and_franchise(self):
        m = self.tmap({"set:swt": "Sith", "sld#999": "Star Wars"}, mode="prefer", labels=["Sith", "Star Wars"],
                      franchise_label="Star Wars", max_off_theme=0, max_franchise=0)
        d = self.deck(["1 Darth Vader (SWT) 12", "1 Sol Ring (SLD) 999", "1 Demonic Tutor (CMM) 1", "97 Swamp (SWT) 300"])
        code, rep = self.val(d, m)
        errs = " ".join(rep["errors"])
        self.assertIn("1 off-theme cards, limit 0", errs)
        self.assertIn("'Star Wars' cards, limit 0", errs)
        code, rep = self.val(d, m, "--max-off-theme", "1", "--max-franchise", "1")  # CLI overrides
        self.assertEqual(code, 0, rep)

    def test_prefer_needs_reasons(self):
        m = self.tmap({"set:swt": "Sith", "sld#999": "Sith"}, mode="prefer", labels=["Sith"])
        d = self.deck(self.BASE)
        code, rep = self.val(d, m)
        self.assertIn("without a reason", " ".join(rep["warnings"]))
        rp = os.path.join(self.T.tmp, "reasons.json")
        with open(rp, "w", encoding="utf-8") as f:
            json.dump({"Demonic Tutor": "no themed printing", "Sol Ring": "budget"}, f)
        code, rep = self.val(d, m, "--reasons", rp)
        self.assertNotIn("without a reason", " ".join(rep["warnings"]))

    def test_power_mode_no_errors_but_free_printing_swaps_flagged(self):
        m = self.tmap({"set:swt": "Sith", "sld#999": "Sith"}, mode="power", labels=["Sith"])
        code, rep = self.val(self.deck(self.BASE), m)
        self.assertEqual(code, 0, rep)
        self.assertIn("themed_printing_available", " ".join(rep["warnings"]))

    def test_label_priority(self):
        m = self.tmap({"sld#999": "Marvel", self.sol_sld: "Spider-Man"}, mode="prefer", labels=["Spider-Man", "Marvel"])
        d = self.deck(["1 Darth Vader (SWT) 12", "1 Sol Ring (SLD) 999", "98 Swamp (SWT) 300"])
        code, rep = self.val(d, m)
        self.assertEqual(rep["theme"]["counts"].get("Spider-Man"), 1)
        self.assertNotIn("Marvel", rep["theme"]["counts"])

    def test_theme_premium(self):
        m = self.tmap({"sld#999": "Sith", "set:swt": "Sith"}, mode="prefer", labels=["Sith"], max_premium_per_card=10)
        d = self.deck(["1 Darth Vader (SWT) 12", "1 Sol Ring (SLD) 999", "98 Swamp (SWT) 300"])
        code, rep = self.val(d, m)
        self.assertEqual(rep["theme"]["theme_premium_usd"], 29.0)
        self.assertIn("costs $29.0 more", " ".join(rep["warnings"]))

    def test_stale_map_warns(self):
        m = self.tmap({"set:swt": "Sith"}, mode="prefer", labels=["Sith"], built="2025-01-01")
        code, rep = self.val(self.deck(["1 Darth Vader (SWT) 12", "99 Swamp (SWT) 300"]), m)
        self.assertIn("theme map is", " ".join(rep["warnings"]))

    def test_unplayable_themed_printing_not_suggested(self):
        x = sqlite3.connect(self.T.db)
        x.execute("UPDATE printings SET oversized=1 WHERE set_code='sld' AND cn='999'")
        x.commit()
        m = self.tmap({"sld#999": "Sith", "set:swt": "Sith"}, mode="prefer", labels=["Sith"])
        code, rep = self.val(self.deck(["1 Darth Vader (SWT) 12", "1 Sol Ring (C21) 263", "98 Swamp (SWT) 300"]), m)
        self.assertNotIn("themed_printing_available", " ".join(rep["warnings"]))
        x.execute("UPDATE printings SET oversized=0 WHERE set_code='sld' AND cn='999'")
        x.commit(); x.close()

    def test_theme_build_from_queries(self):
        cache = os.path.join(self.T.tmp, "cache")
        os.makedirs(cache, exist_ok=True)
        x = sqlite3.connect(os.path.join(cache, "extra.sqlite"))
        x.execute("CREATE TABLE IF NOT EXISTS search_cache(query TEXT PRIMARY KEY, fetched REAL, body TEXT)")
        x.execute("INSERT OR REPLACE INTO search_cache VALUES(?,?,?)", ("prints|e:swt", time.time(), json.dumps([{"id": self.vader}])))
        x.execute("INSERT OR REPLACE INTO search_cache VALUES(?,?,?)", ("prints|e:sld art:saber", time.time(), json.dumps([{"id": self.sol_sld}])))
        x.commit(); x.close()
        spec = os.path.join(self.T.tmp, "spec.json")
        json.dump({"mode": "prefer", "franchise_label": "Star Wars", "labels": [
            {"label": "Sith", "queries": ["e:swt"], "include": ["name:Swamp"]},
            {"label": "Star Wars", "queries": ["e:sld art:saber"], "include": ["name:Not A Card"]}]}, open(spec, "w"))
        outp = os.path.join(self.T.tmp, "built.json")
        p = subprocess.run([sys.executable, SCRIPT, "--db", self.T.db, "theme-build", spec, "--out", outp],
                           capture_output=True, text=True, env=self.T.env)
        rep = json.loads(p.stdout)
        self.assertIn("include name not found", " ".join(rep["problems"]))
        built = json.load(open(outp))
        self.assertEqual(built["printings"][self.vader], "Sith")
        self.assertEqual(built["printings"][self.sol_sld], "Star Wars")
        self.assertEqual(built["spec"]["labels"], ["Sith", "Star Wars"])
        code, rep = self.val(self.deck(["1 Darth Vader (SWT) 12", "1 Sol Ring (SLD) 999", "98 Swamp (SWT) 300"]), outp)
        self.assertEqual(rep["theme"]["counts"], {"Sith": 99, "Star Wars": 1})

    def test_theme_pool(self):
        m = self.tmap({"set:swt": "Sith", "sld#999": "Star Wars"}, mode="strict", labels=["Sith", "Star Wars"], franchise_label="Star Wars")
        p = subprocess.run([sys.executable, SCRIPT, "--db", self.T.db, "--themes", m, "theme-pool", "Darth Vader"],
                           capture_output=True, text=True, env=self.T.env)
        rep = json.loads(p.stdout)
        self.assertEqual(rep["identity"], "B")
        self.assertIn("not realistic", rep["verdict"])
        self.assertEqual(rep["pool"]["Star Wars"]["nonland"], 1)

    def test_help_works(self):
        p = subprocess.run([sys.executable, SCRIPT, "--help"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        for sub in ("validate", "--help", "simulate", "theme-build"):
            p = subprocess.run([sys.executable, SCRIPT, sub, "--help"] if sub != "--help" else [sys.executable, SCRIPT, "-h"],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()


class JourneyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.MtgdbTest.setUpClass()
        cls.T = base.MtgdbTest

    def run_(self, *args):
        p = subprocess.run([sys.executable, SCRIPT, "--db", self.T.db] + list(args), capture_output=True, text=True, env=self.T.env)
        return json.loads(p.stdout)

    def test_profile_detects_printing_lean_and_problems(self):
        d = base.MtgdbTest.deck(self.T, ["1 Darth Vader (SWT) 12", "1 Mana Crypt (WC97) 1", "1 Rhystic Study (PCY) 45", "1 Demonic Tutor (CMM) 1", "96 Swamp (SWT) 300"])
        rep = self.run_("profile", d)
        self.assertEqual(rep["identity"], "B")
        self.assertTrue(any("banned" in e for e in rep["legal_problems"]))
        self.assertTrue(any("identity" in e for e in rep["legal_problems"]))
        self.assertIn("B3", rep["bracket_signal"])
        self.assertTrue(rep["printing_sets_top"])

    def test_diff(self):
        a = base.MtgdbTest.deck(self.T, ["1 Darth Vader", "1 Sol Ring (C21) 263", "98 Swamp"])
        b = base.MtgdbTest.deck(self.T, ["1 Darth Vader", "1 Sol Ring (SLD) 999", "1 Demonic Tutor", "97 Swamp"])
        rep = self.run_("diff", a, b)
        self.assertEqual(rep["adds"], ["Demonic Tutor"])
        self.assertEqual(rep["cuts"], [])
        self.assertIn("Swamp: 98 -> 97", rep["quantity_changes"])
        self.assertTrue(rep["printing_swaps"][0].startswith("Sol Ring: c21#263 -> sld#999"))
        self.assertEqual(rep["cost_of_adds_usd"], 20.0)
