"""PROJECT.md Rules/Guidance ids, per-rule staleness, DECISIONS ids, and plan.py (offline: card lookups are stubbed)."""
import importlib.util, json, os, shutil, sys, tempfile, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS = os.path.join(ROOT, "plugins", "edh-companion", "scripts")
sys.path.insert(0, SCRIPTS)


def mod(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SCRIPTS, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


co, plan = mod("companion"), mod("plan")
PROJECT = """# Test
## Rules
- R1 Strict Marvel: only Marvel printings.
- R2 [b2] Bracket 2: no Game Changers.
- R3 [main] Bracket 3.
## Guidance
- G1 Spider-Verse creatures first.
"""


def put(p, x):
    with open(p, "w", encoding="utf-8") as h:
        h.write(x if isinstance(x, str) else json.dumps(x))


class Rules(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        put(os.path.join(self.d, "PROJECT.md"), PROJECT)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_rules_per_variant_and_guidance_not_hashed(self):
        self.assertEqual(set(co.rule_hashes(self.d, "main")), {"R1", "R3"})
        self.assertEqual(set(co.rule_hashes(self.d, "b2")), {"R1", "R2"})
        before = co.goals_hash(self.d)
        put(os.path.join(self.d, "PROJECT.md"), PROJECT.replace("Spider-Verse creatures first", "Any Marvel creature"))
        self.assertEqual(co.goals_hash(self.d), before)  # guidance edits never stale an audit

    def test_changed_rule_stales_only_checks_citing_it(self):
        audit = {"subject": {"rule_hashes": co.rule_hashes(self.d)},
                 "checks": [{"id": "chk-theme-1", "rules": ["R1"]}, {"id": "chk-bracket-1", "rules": ["R3"]}]}
        self.assertEqual(co.rule_drift(self.d, audit)[0], False)
        put(os.path.join(self.d, "PROJECT.md"), PROJECT.replace("only Marvel printings", "Marvel printings, basics exempt"))
        stale, why, ids = co.rule_drift(self.d, audit)
        self.assertTrue(stale)
        self.assertEqual(ids, ["chk-theme-1"])
        put(os.path.join(self.d, "PROJECT.md"), PROJECT.replace("- R2 [b2]", "- R2"))  # R2 now applies to main too
        stale, why, ids = co.rule_drift(self.d, audit)
        self.assertIn("no check covers R2", why)

    def test_rule_leaving_rules_needs_a_decision_and_decision_ids(self):
        put(os.path.join(self.d, "audit.json"), {"subject": {"rule_hashes": {"R1": "x", "R9": "y"}}, "checks": []})
        put(os.path.join(self.d, "DECISIONS.md"), "- D-1 2026-11-16 something\n- D-1 2026-11-16 dup (superseded by D-7)\n")
        errs = " | ".join(co.validate(self.d)[0])
        self.assertIn("R9 left PROJECT.md Rules", errs)
        self.assertIn("duplicate id D-1", errs)
        self.assertIn("superseded by D-7", errs)
        put(os.path.join(self.d, "DECISIONS.md"), "- D-1 2026-11-16 R9 moved to Guidance as G2\n")
        self.assertNotIn("R9", " | ".join(co.validate(self.d)[0]))


def brew(bracket, deck, version=1):
    b = {"version": version, "target_bracket": {"bracket": bracket}, "commander": {"cards": [{"name": "Cosmic Spider-Man"}]},
         "deck": [{"name": n, "qty": q, "role": "x"} for n, q in deck]}
    b["deck_hash"] = plan.hash_of(b)
    return b


CARDS = {"Cosmic Spider-Man": {"color_identity": list("WUBRG")}, "Rhystic Study": {"color_identity": ["U"], "game_changer": True},
         "Nature's Lore": {"color_identity": ["G"]}, "Sol Ring": {"color_identity": []}}


class Plan(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        put(os.path.join(self.d, "brew.json"), brew(3, [("Forest", 30), ("Sol Ring", 1)]))
        put(os.path.join(self.d, "brew-b2.json"), brew(2, [("Forest", 30), ("Sol Ring", 1)]))
        self.lookup = lambda names: {n: CARDS.get(n) for n in names}

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def b(self, f):
        return json.load(open(os.path.join(self.d, f), encoding="utf-8"))

    def test_apply_per_variant_refuses_game_changer_in_b2_and_reverts(self):
        plan.new(self.d, ["main:+Rhystic Study@draw", "main:-Forest", "b2:+Rhystic Study", "b2:-Forest"])
        self.assertEqual(plan.apply(self.d, self.lookup), 1)
        main, b2 = self.b("brew.json"), self.b("brew-b2.json")
        self.assertEqual(main["version"], 2)
        self.assertEqual(main["deck_hash"], plan.hash_of(main))
        self.assertIn({"name": "Rhystic Study", "qty": 1, "role": "draw"}, main["deck"])
        self.assertTrue(os.path.exists(os.path.join(self.d, "decklists", "main-v2.txt")))
        self.assertEqual(b2["version"], 1)  # refused, untouched
        res = self.b("PLAN.json")["result"]
        self.assertIn("Game Changer", res["b2"]["why"][0])
        self.assertEqual(plan.apply(self.d, self.lookup), 2)  # applied plans don't apply twice
        self.assertEqual(plan.revert(self.d), 0)
        self.assertEqual(self.b("brew.json")["version"], 1)

    def test_changed_deck_refuses_and_printing_swap_works(self):
        plan.new(self.d, ["main:-Sol Ring", "main:+Sol Ring (SLD) 908 *F*@ramp"])
        b = self.b("brew.json")
        b["deck"][0]["qty"] = 29
        b["deck_hash"] = plan.hash_of(b)
        put(os.path.join(self.d, "brew.json"), b)
        self.assertEqual(plan.apply(self.d, self.lookup), 1)
        self.assertIn("deck changed since the plan", self.b("PLAN.json")["result"]["main"]["why"][0])
        plan.new(self.d, ["main:-Sol Ring", "main:+Sol Ring (SLD) 908 *F*@ramp"])
        self.assertEqual(plan.apply(self.d, self.lookup), 0)
        ring = [c for c in self.b("brew.json")["deck"] if c["name"] == "Sol Ring"]
        self.assertEqual(ring, [{"name": "Sol Ring", "qty": 1, "role": "ramp", "set": "sld", "collector_number": "908", "finish": "foil"}])


if __name__ == "__main__":
    unittest.main()
