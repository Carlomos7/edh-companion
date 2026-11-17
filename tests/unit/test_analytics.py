"""Offline tests: role rules, mana sources vs pips, seeded simulation, and pool allocation.

Run: uv run --with certifi python -m unittest discover -s tests/unit
"""
import importlib.util, os, sys, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AUDIT = os.path.join(ROOT, "plugins", "edh-companion", "skills", "audit", "scripts")
BREW = os.path.join(ROOT, "plugins", "edh-companion", "skills", "brew", "scripts")
sys.path.insert(0, AUDIT)
import analytics  # noqa: E402

spec = importlib.util.spec_from_file_location("allocate", os.path.join(BREW, "allocate.py"))
alloc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alloc)


def c(name, type_line, text="", cost="", cmc=0, produced=None):
    return {"name": name, "type_line": type_line, "oracle_text": text, "mana_cost": cost, "cmc": cmc, "produced_mana": produced}


class Roles(unittest.TestCase):
    def r(self, *a, **k):
        return set(analytics.roles(c(*a, **k)))

    def test_ramp_rock_and_land_search(self):
        self.assertEqual(self.r("Sol Ring", "Artifact", "{T}: Add {C}{C}."), {"ramp"})
        self.assertEqual(self.r("Cultivate", "Sorcery", "Search your library for up to two basic land cards, reveal those cards, put one onto the battlefield tapped and the other into your hand, then shuffle."), {"ramp"})

    def test_spell_land_double_faced_card_counts_once(self):
        awakening = {"name": "Valakut Awakening // Valakut Stoneforge", "type_line": "Instant // Land", "cmc": 3, "produced_mana": ["R"],
                     "card_faces": [{"type_line": "Instant", "mana_cost": "{2}{R}", "oracle_text": "Put any number of cards from your hand on the bottom of your library, then draw that many cards plus one."},
                                    {"type_line": "Land", "mana_cost": "", "oracle_text": "As Valakut Stoneforge enters, you may pay 3 life. If you don't, it enters tapped.\n{T}: Add {R}."}]}
        counts, per = analytics.role_counts([(1, awakening)])
        self.assertEqual(counts, {"draw": 1})  # one card, one role; its land face isn't a second card or a land
        self.assertNotIn("land", per[awakening["name"]])

    def test_lands_are_only_lands(self):
        self.assertEqual(self.r("Command Tower", "Land", "{T}: Add one mana of any color in your commander's color identity."), {"land"})

    def test_removal_variants(self):
        for text in ("Destroy target creature.", "Lightning Bolt deals 3 damage to any target.", "Target creature gets -3/-3 until end of turn.",
                     "The owner of target permanent shuffles it into their library, then reveals the top card of their library.",
                     "Return target nonland permanent to its owner's hand."):
            self.assertIn("removal", self.r("X", "Instant", text), text)

    def test_blinking_your_own_creature_is_not_removal(self):
        self.assertNotIn("removal", self.r("Ephemerate", "Instant", "Exile target creature you control, then return it to the battlefield under its owner's control."))
        self.assertIn("removal", self.r("Swords to Plowshares", "Instant", "Exile target creature. Its controller gains life equal to its power."))

    def test_wipe_is_not_targeted_removal(self):
        self.assertEqual(self.r("Wrath", "Sorcery", "Destroy all creatures. They can't be regenerated."), {"wipe"})

    def test_multiple_roles(self):
        self.assertEqual(self.r("Mind Stone", "Artifact", "{T}: Add {C}.\n{1}, {T}, Sacrifice Mind Stone: Draw a card."), {"ramp", "draw"})

    def test_tutor_but_not_land_search(self):
        self.assertIn("tutor", self.r("Goblin Matron", "Creature — Goblin", "When Goblin Matron enters, you may search your library for a Goblin card, reveal that card, put it into your hand, then shuffle."))
        self.assertNotIn("tutor", self.r("Rampant Growth", "Sorcery", "Search your library for a basic land card, put that card onto the battlefield tapped, then shuffle."))

    def test_reminder_text_ignored(self):
        self.assertEqual(self.r("Bear", "Creature — Bear", "Partner (You can draw a card when...)"), set())

    def test_counts_multi_role(self):
        counts, _ = analytics.role_counts([(1, c("Mind Stone", "Artifact", "{T}: Add {C}.\n{1}, {T}: Draw a card.")), (35, c("Forest", "Basic Land — Forest"))])
        self.assertEqual(counts, {"ramp": 1, "draw": 1, "land": 35})


class Mana(unittest.TestCase):
    def test_pips_and_sources(self):
        rows = [(1, c("Counterspell", "Instant", "", "{U}{U}", 2)), (1, c("Boros Charm", "Instant", "", "{R}{W}", 2)),
                (1, c("Kitchen Finks", "Creature", "", "{1}{G/W}{G/W}", 3)), (10, c("Island", "Basic Land — Island", produced=["U"])),
                (1, c("Arcane Signet", "Artifact", "{T}: Add one mana of any color in your commander's color identity.", "{2}", 2, ["W", "U", "B", "R", "G"]))]
        m = analytics.mana(rows, identity={"U", "W"})
        self.assertEqual(m["pips"], {"W": 3, "U": 2, "R": 1, "G": 2})
        self.assertEqual(m["sources"]["U"], 11)
        self.assertEqual(m["sources"]["W"], 1)


class Simulation(unittest.TestCase):
    def test_seeded_and_sane(self):
        rows = [(36, c("Mountain", "Basic Land — Mountain", produced=["R"])), (63, c("Bear", "Creature", "", "{1}{R}", 2))]
        a = analytics.simulate(rows, 4, runs=3000)
        b = analytics.simulate(rows, 4, runs=3000)
        self.assertEqual(a, b)                                   # reproducible
        self.assertEqual(a["by_turn"][3], 0.0)                   # 4-drop can't come down on turn 3 with lands only
        self.assertTrue(0.3 < a["by_turn"][4] < 0.9)
        self.assertTrue(all(a["by_turn"][t] <= a["by_turn"][t + 1] for t in range(1, 8)))

    def test_rocks_help(self):
        lands = [(36, c("Mountain", "Basic Land — Mountain", produced=["R"]))]
        filler = [(63, c("Bear", "Creature", "", "{1}{R}", 2))]
        rocks = [(10, c("Mind Stone", "Artifact", "{T}: Add {C}.", "{2}", 2, ["C"])), (53, c("Bear", "Creature", "", "{1}{R}", 2))]
        self.assertGreater(analytics.simulate(lands + rocks, 4, runs=3000)["by_turn"][3], analytics.simulate(lands + filler, 4, runs=3000)["by_turn"][3])


class ColorAware(unittest.TestCase):
    def test_missing_color_is_the_bottleneck(self):
        five = {c: 1 for c in "WUBRG"}
        mono = [(36, c("Mountain", "Basic Land — Mountain", produced=["R"])), (63, c("Bear", "Creature", "", "{1}{R}", 2))]
        rainbow = [(36, c("Command Tower", "Land", produced=list("WUBRG"))), (63, c("Bear", "Creature", "", "{1}{R}", 2))]
        bad = analytics.simulate(mono + [(1, c("Island", "Basic Land — Island", produced=["U"]))], 5, runs=2000, cost=five)
        good = analytics.simulate(rainbow, 5, runs=2000, cost=five)
        self.assertEqual(bad["by_turn"][8], 0.0)  # no W, B or G source at all
        self.assertIn(bad["bottleneck"], {"W", "B", "G"})
        self.assertGreater(good["by_turn"][5], 0.5)
        self.assertIsNone(good["bottleneck"])
        self.assertGreater(good["mulligans_per_game"], 0)

    def test_fetch_lands_find_only_their_types(self):
        mire = c("Bloodstained Mire", "Land", "{T}, Pay 1 life, Sacrifice Bloodstained Mire: Search your library for a Swamp or Mountain card, put it onto the battlefield, then shuffle.")
        passage = c("Fabled Passage", "Land", "{T}, Sacrifice Fabled Passage: Search your library for a basic land card, put it onto the battlefield tapped, then shuffle.")
        verge = c("Krosan Verge", "Land", "{T}: Add {C}.\n{2}, {T}, Sacrifice Krosan Verge: Search your library for a Forest card and a Plains card, put them onto the battlefield tapped, then shuffle.", produced=["C"])
        self.assertEqual(analytics.made_colors(mire), {"B", "R"})
        self.assertEqual(analytics.made_colors(passage, "WU"), {"W", "U"})
        self.assertEqual(analytics.made_colors(verge), {"G", "W"})  # its {C} is not a color
        panorama = c("Jungle Panorama", "Land", "{T}: Add {C}.\n{1}, {T}, Sacrifice it: Search your library for a basic Forest, Island, or Mountain card, put it onto the battlefield tapped, then shuffle.", produced=["C"])
        self.assertEqual(analytics.made_colors(panorama), {"G", "U", "R"})
        bear = c("Bear", "Creature", "", "{1}{W}", 2)
        chk = analytics.source_check([(36, mire), (63, bear)])
        self.assertEqual(chk["W"]["sources"], 0)                 # a Mire can't find a Plains
        sim = analytics.simulate([(36, mire), (63, bear)], 2, runs=500, cost={"W": 1})
        self.assertEqual((sim["by_turn"][8], sim["bottleneck"]), (0.0, "W"))
        self.assertEqual(analytics.mana([(36, mire), (63, bear)], "WBR")["sources"], {"W": 0, "B": 36, "R": 36})

    def test_karsten_needs_and_land_formula(self):
        self.assertEqual(analytics.karsten_need(c("Wrath of God", "Sorcery", "", "{2}{W}{W}", 4)), {"W": 26})
        self.assertEqual(analytics.karsten_need(c("Boros Charm", "Instant", "", "{R}{W}", 2)), {"R": 20, "W": 20})  # gold +1
        rows = [(36, c("Forest", "Basic Land — Forest", produced=["G"])), (63, c("Bear", "Creature", "", "{1}{G}", 2))]
        lc = analytics.land_count(rows)
        self.assertEqual(lc["recommended"], round(31.42 + 3.13 * 2, 1))
        self.assertIsNone(lc["warning"])  # 36 vs 37.7: within 2
        chk = analytics.source_check(rows)
        self.assertEqual(chk["G"], {"sources": 36, "needed": 19, "for": "Bear", "short": 0})


class Allocation(unittest.TestCase):
    colors = {"Doctor Strange": {"U"}, "Spider-Man": {"R"}, "Sol Ring": set(), "Counterspell": {"U"}, "Lightning Bolt": {"R"}, "Llanowar Elves": {"G"}}

    def test_no_double_allocation_and_wishes_win(self):
        res = alloc.allocate({"Sol Ring": 1, "Doctor Strange": 1, "Lightning Bolt": 1, "Llanowar Elves": 1},
                             needs={"Me": {"Sol Ring": 1, "Lightning Bolt": 1}}, identities={"Sam": {"U", "R"}},
                             card_colors=self.colors, wants=[("Sam", "Doctor Strange")])
        self.assertEqual(res["assigned"]["Sam"], {"Doctor Strange": 1})
        self.assertEqual(res["assigned"]["Me"], {"Sol Ring": 1, "Lightning Bolt": 1})
        self.assertEqual(res["unused"], {"Llanowar Elves": 1})   # fits nobody's colors

    def test_conflict_goes_to_the_player(self):
        res = alloc.allocate({"Sol Ring": 1}, needs={"Me": {"Sol Ring": 1}, "Sam": {"Sol Ring": 1}}, identities={}, card_colors=self.colors, wants=[])
        self.assertEqual(res["choose"][0]["candidates"], ["Me", "Sam"])
        self.assertEqual(res["assigned"], {})

    def test_enough_copies_for_everyone(self):
        res = alloc.allocate({"Sol Ring": 2}, needs={"Me": {"Sol Ring": 1}, "Sam": {"Sol Ring": 1}}, identities={}, card_colors=self.colors, wants=[])
        self.assertEqual(res["assigned"], {"Me": {"Sol Ring": 1}, "Sam": {"Sol Ring": 1}})


if __name__ == "__main__":
    unittest.main()
