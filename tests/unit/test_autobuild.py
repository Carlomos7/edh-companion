"""autobuild.py: greedy first-draft deck under hard limits, role floors and the mana check. Offline, synthetic cards."""
import json, os, sys, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BREW = os.path.join(ROOT, "plugins", "edh-companion", "skills", "brew", "scripts")
sys.path.insert(0, BREW)
import autobuild as ab  # noqa: E402

CFG = json.load(open(os.path.join(BREW, "..", "references", "roles.json"), encoding="utf-8"))


def card(name, text="", cost="{1}{R}", cmc=2, type_line="Creature", ci=("R",), gc=False, produced=None):
    return {"name": name, "oracle_text": text, "mana_cost": cost, "cmc": cmc, "type_line": type_line, "color_identity": list(ci),
            "game_changer": gc, "produced_mana": produced}


def pool():
    out, rank = [], 0

    def add(c, status="legal"):
        nonlocal rank
        rank += 1
        out.append({"card": c, "rank": rank, "evidence": [f"src-{rank:03d}"], "status": status})
    add(card("Big Gamble", "Draw seven cards.", gc=True))
    add(card("Next Year Goblin"), status="upcoming")
    for i in range(70):
        add(card(f"Goblin {i}"))
    for i in range(16):
        add(card(f"Rock {i}", "{T}: Add {C}{C}.", "{2}", 2, "Artifact", (), produced=["C"]))
    for i in range(14):
        add(card(f"Insight {i}", "Draw two cards.", "{2}{R}", 3, "Sorcery"))
    for i in range(12):
        add(card(f"Bolt {i}", "Bolt deals 3 damage to any target.", "{R}", 1, "Instant"))
    for i in range(5):
        add(card(f"Wrath {i}", "Destroy all creatures.", "{3}{R}{R}", 5, "Sorcery"))
    add(card("Red Utility Land", "{T}: Add {R}.", "", 0, "Land", (), produced=["R"]))
    return out


KRENKO = card("Krenko, Mob Boss", "", "{2}{R}{R}", 4, "Legendary Creature")


class Autobuild(unittest.TestCase):
    def test_hard_limits_floors_and_size(self):
        doc = ab.build([KRENKO], pool(), CFG, bracket=2, locks=["Goblin 69"], bans=["Goblin 0"], runs=1000)
        names = [d["name"] for d in doc["deck"] if d["why"] != "basic land, split by the spells' pips and the mana check"]
        self.assertEqual(doc["cards"], 100)
        self.assertEqual(len(names), len(set(names)))                   # singleton
        self.assertNotIn("Big Gamble", names)                           # bracket 2: no Game Changers
        self.assertNotIn("Next Year Goblin", names)
        self.assertNotIn("Goblin 0", names)
        self.assertIn("Goblin 69", names)                               # locked, though ranked last of the goblins
        self.assertGreaterEqual(doc["role_counts"]["ramp"], 12)         # a 4-drop commander raises the ramp floor
        for role in ("draw", "removal", "wipe"):
            self.assertGreaterEqual(doc["role_counts"][role], CFG["roles"][role]["min"], role)
        self.assertLessEqual(doc["role_counts"]["wipe"], CFG["roles"]["wipe"]["max"])
        self.assertTrue(33 <= doc["lands"] <= 40)
        self.assertIn("Red Utility Land", names)
        self.assertGreater(doc["mana_check"][-1]["probability"], 0.5)
        self.assertTrue(all(d["why"] for d in doc["deck"]))              # every pick says why

    def test_budget_is_a_true_total(self):
        doc = ab.build([KRENKO], pool(), CFG, budget=40, price=lambda c: 1.0 if c["name"] != "Goblin 3" else None, runs=500)
        self.assertLessEqual(doc["total_usd"], 40)
        self.assertTrue(any(b.startswith("budget") for b in doc["binding"]), doc["binding"])
        pricey = ab.build([KRENKO], pool(), CFG, budget=60, price=lambda c: 30.0 if c["name"] == "Goblin 1" else 0.5, runs=300)
        self.assertNotIn("Goblin 1", [d["name"] for d in pricey["deck"]])  # one card can't take half the budget
        self.assertIn({"name": "Goblin 3", "why": "no price (can't be counted against the budget)"}, doc["left_out"])
        self.assertTrue(doc["weak_spots"])                               # 40 dollars can't fill the spells: said, not hidden

    def test_mana_check_moves_basics_to_the_bottleneck(self):
        esper = card("Esper Boss", "", "{W}{W}{U}", 3, "Legendary Creature", ("W", "U"))
        p = [dict(e, card=dict(e["card"], mana_cost="{1}{U}{U}", color_identity=["U"])) if e["card"]["type_line"] != "Land" else e for e in pool()]
        doc = ab.build([esper], p, CFG, runs=1000)
        first, last = doc["mana_check"][0], doc["mana_check"][-1]
        self.assertEqual(first["bottleneck"], "W")                       # spells are all blue, so basics start mostly Islands
        self.assertGreater(last["basics"].get("W", 0), first["basics"].get("W", 0))
        self.assertGreaterEqual(last["probability"], first["probability"])
        self.assertEqual(doc["cards"], 100)


if __name__ == "__main__":
    unittest.main()
