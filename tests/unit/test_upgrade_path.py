"""upgrade_path.py: ordered swaps by value per dollar, owned first, true budget total. Offline, synthetic cards."""
import json, os, sys, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BREW = os.path.join(ROOT, "plugins", "edh-companion", "skills", "brew", "scripts")
sys.path.insert(0, BREW)
import upgrade_path as up  # noqa: E402

CFG = json.load(open(os.path.join(BREW, "..", "references", "roles.json"), encoding="utf-8"))


def e(name, text="", lift=None, type_line="Creature", gc=False):
    return {"card": {"name": name, "oracle_text": text, "type_line": type_line, "cmc": 2, "game_changer": gc}, "lift_lb": lift, "evidence": ["src-001"]}


DECK = [e(f"Bear {i}") for i in range(60)] + [e(f"Rock {i}", "{T}: Add {C}.") for i in range(10)] + \
       [e(f"Divination {i}", "Draw two cards.") for i in range(8)] + [e(f"Wrath {i}", "Destroy all creatures.") for i in range(2)] + \
       [e(f"Bolt {i}", "Bolt deals 3 damage to any target.") for i in range(8)] + [e(f"Mountain {i}", type_line="Basic Land — Mountain") for i in range(10)]
POOL = [e("Harmonize", "Draw three cards."), e("Phyrexian Arena", "At the beginning of your upkeep, you draw a card.", lift=2.0),
        e("Goblin Synergist", lift=3.0), e("Owned Goblin", lift=1.5), e("Fancy Land", "{T}: Add {R}.", lift=4.0, type_line="Land"),
        e("Big Gamble", "Draw seven cards.", gc=True), e("Unpriced Thing", lift=5.0)]
PRICES = {"Harmonize": 1.0, "Phyrexian Arena": 4.0, "Goblin Synergist": 2.0, "Owned Goblin": 9.0, "Fancy Land": 10.0, "Big Gamble": 1.0}


class Upgrade(unittest.TestCase):
    def run_plan(self, **kw):
        return up.plan(DECK, POOL, CFG, owned=lambda c: c["name"] == "Owned Goblin", price=lambda c: PRICES.get(c["name"]), **kw)

    def test_owned_first_then_value_per_dollar(self):
        doc = self.run_plan(bracket=2)
        steps = [(s["add"], s["owned"]) for s in doc["steps"]]
        self.assertEqual(steps[0], ("Owned Goblin", True))                 # a $0 swap you can make today
        self.assertEqual(doc["swaps_today"], 1)
        adds = [s["add"] for s in doc["steps"]]
        self.assertLess(adds.index("Harmonize"), adds.index("Phyrexian Arena"))  # both fill draw; Harmonize is cheaper per point
        self.assertNotIn("Big Gamble", adds)                               # bracket 2: no Game Changers
        self.assertNotIn("Unpriced Thing", adds)                           # no price, no step
        fancy = next(s for s in doc["steps"] if s["add"] == "Fancy Land")
        self.assertTrue(fancy["cut"].startswith("Mountain"))               # lands swap for lands
        self.assertFalse(any(s["cut"].startswith(("Rock", "Bolt", "Wrath")) for s in doc["steps"]))  # never breaks a floor
        self.assertEqual(doc["total_usd"], round(sum(PRICES[a] for a in adds if a != "Owned Goblin"), 2))

    def test_cuts_the_least_played_card(self):
        deck = [dict(x, inclusion_lb=90.0) if x["card"]["name"] == "Bear 0" else dict(x, inclusion_lb=5.0) if x["card"]["name"] == "Bear 7" else x for x in DECK]
        doc = up.plan(deck, [e("Goblin Synergist", lift=3.0)], CFG, price=lambda c: 1.0)
        self.assertEqual(doc["steps"][0]["cut"], "Bear 7")
        ranked = [dict(x, card=dict(x["card"], edhrec_rank=1 if x["card"]["name"] == "Bear 3" else 5000 if x["card"]["name"] == "Bear 4" else 100)) for x in DECK]
        doc = up.plan(ranked, [e("Goblin Synergist", lift=3.0)], CFG, price=lambda c: 1.0)
        self.assertEqual(doc["steps"][0]["cut"], "Bear 4")              # no deck numbers: the least played overall goes

    def test_budget_is_a_running_total(self):
        doc = self.run_plan(budget=5)
        self.assertLessEqual(doc["total_usd"], 5)
        self.assertTrue(all(s["total_usd"] <= 5 for s in doc["steps"]))
        self.assertIn("Fancy Land", [s["add"] for s in doc["skipped"]])

    def test_steps_recompute(self):
        doc = self.run_plan(steps=2)
        self.assertEqual(len(doc["steps"]), 2)
        draw_fills = [s for s in self.run_plan()["steps"] if "fills draw" in s["why"]]
        self.assertEqual(len(draw_fills), 2)                               # 8 -> 10: the floor is met after two draw adds


if __name__ == "__main__":
    unittest.main()
