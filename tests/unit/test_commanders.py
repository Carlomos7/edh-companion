"""Commander eligibility and pairings (CR 903.3 and 702.124, rules effective 2026-09-25).

Offline tests use minimal card records; live tests run deck_check.py against Scryfall with real cards.
Run: uv run --with certifi python -m unittest discover -s tests/unit
"""
import importlib.util, json, os, subprocess, sys, tempfile, unittest, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(ROOT, "plugins", "edh-companion", "skills", "audit", "scripts", "deck_check.py")
spec = importlib.util.spec_from_file_location("deck_check", SCRIPT)
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)


def card(name, type_line, text="", power=None):
    return {"name": name, "type_line": type_line, "oracle_text": text, "power": power}


PARTNER = "Partner (You can have two commanders if both have partner.)"


class Eligibility(unittest.TestCase):
    def test_legendary_creature(self):
        self.assertTrue(dc.can_be_commander(card("A", "Legendary Creature — Elf")))

    def test_nonlegendary_creature(self):
        self.assertFalse(dc.can_be_commander(card("Llanowar Elves", "Creature — Elf Druid")))

    def test_legendary_noncreature_needs_text(self):
        self.assertFalse(dc.can_be_commander(card("X", "Legendary Planeswalker — X")))
        self.assertTrue(dc.can_be_commander(card("Grist", "Legendary Planeswalker — Grist", "Grist can be your commander.")))
        self.assertTrue(dc.can_be_commander(card("Bond", "Legendary Sorcery", "Bond can be your commander.")))

    def test_vehicle_and_spacecraft(self):
        self.assertTrue(dc.can_be_commander(card("Adrestia", "Legendary Artifact — Vehicle", power="4")))
        self.assertTrue(dc.can_be_commander(card("Ship", "Legendary Artifact — Spacecraft", power="3")))
        self.assertFalse(dc.can_be_commander(card("Station", "Legendary Artifact — Spacecraft")))  # no power/toughness

    def test_background_alone_is_not_a_commander(self):
        self.assertFalse(dc.can_be_commander(card("Sage", "Legendary Enchantment — Background")))
        self.assertTrue(dc.is_background(card("Sage", "Legendary Enchantment — Background")))

    def test_double_faced_uses_front(self):
        c = {"name": "Front // Back", "type_line": "Legendary Creature — Human // Legendary Planeswalker — X",
             "card_faces": [{"type_line": "Legendary Creature — Human", "oracle_text": ""}, {"type_line": "Legendary Planeswalker — X", "oracle_text": ""}]}
        self.assertTrue(dc.can_be_commander(c))


class Pairings(unittest.TestCase):
    def ok(self, a, b):
        return dc.pairing(a, b)[0]

    def test_partner(self):
        self.assertTrue(self.ok(card("A", "Legendary Creature — X", PARTNER), card("B", "Legendary Creature — Y", PARTNER)))

    def test_partner_needs_both(self):
        self.assertFalse(self.ok(card("A", "Legendary Creature — X", PARTNER), card("B", "Legendary Creature — Y")))

    def test_partner_text_must_match(self):
        s = "Partner—Survivors (You can have two commanders if both have this ability.)"
        f = "Partner—Father & son (You can have two commanders if both have this ability.)"
        self.assertTrue(self.ok(card("A", "Legendary Creature — X", s), card("B", "Legendary Creature — Y", s)))
        self.assertFalse(self.ok(card("A", "Legendary Creature — X", s), card("B", "Legendary Creature — Y", f)))
        self.assertTrue(self.ok(card("A", "Legendary Creature — X", "Partner—Character select"), card("B", "Legendary Creature — Y", "Partner—Character select (You can...)")))

    def test_old_friends_forever_wording_still_pairs(self):
        old = "Friends forever (You can have two commanders if both have friends forever.)"
        new = "Partner—Friends forever (You can have two commanders if both have this ability.)"
        self.assertTrue(self.ok(card("A", "Legendary Creature — X", old), card("B", "Legendary Creature — Y", new)))

    def test_different_partner_abilities_dont_mix(self):  # CR 702.124f
        s = "Partner—Survivors (You can have two commanders if both have this ability.)"
        self.assertFalse(self.ok(card("A", "Legendary Creature — X", PARTNER), card("B", "Legendary Creature — Y", s)))
        self.assertFalse(self.ok(card("Pir", "Legendary Creature — X", "Partner with Toothy"), card("B", "Legendary Creature — Y", PARTNER)))

    def test_partner_with_must_name_each_other(self):
        pir = card("Pir, Imaginative Rascal", "Legendary Creature — Human", "Partner with Toothy, Imaginary Friend (When this creature enters, ...)")
        toothy = card("Toothy, Imaginary Friend", "Legendary Creature — Illusion", "Partner with Pir, Imaginative Rascal (When this creature enters, ...)")
        other = card("Rory Williams", "Legendary Creature — Human", "Partner with Amy Pond")
        self.assertTrue(self.ok(pir, toothy))
        self.assertFalse(self.ok(pir, other))

    def test_background(self):
        chooser = card("Abdel", "Legendary Creature — Human Warrior", "Choose a Background (You can have a Background as a second commander.)")
        bg = card("Sage", "Legendary Enchantment — Background")
        self.assertTrue(self.ok(chooser, bg))
        self.assertTrue(self.ok(bg, chooser))
        self.assertFalse(self.ok(card("Tymna", "Legendary Creature — Human", PARTNER), bg))
        self.assertFalse(self.ok(chooser, card("Tymna", "Legendary Creature — Human", PARTNER)))

    def test_doctors_companion(self):
        comp = card("Barbara Wright", "Legendary Creature — Human Advisor", "Doctor's companion (You can have two commanders if the other is the Doctor.)")
        doctor = card("The Eleventh Doctor", "Legendary Creature — Time Lord Doctor")
        not_only_doctor = card("Doctor X", "Legendary Creature — Time Lord Doctor Rogue")
        self.assertTrue(self.ok(comp, doctor))
        self.assertFalse(self.ok(comp, not_only_doctor))
        self.assertFalse(self.ok(comp, card("Tymna", "Legendary Creature — Human", PARTNER)))

    def test_card_with_two_abilities_can_use_either(self):  # CR 702.124g
        amy = card("Amy Pond", "Legendary Creature — Human", "Partner with Rory Williams (...)\nDoctor's companion (...)")
        rory = card("Rory Williams", "Legendary Creature — Human", "Partner with Amy Pond (...)\nDoctor's companion (...)")
        self.assertTrue(self.ok(amy, rory))
        self.assertTrue(self.ok(amy, card("The Eleventh Doctor", "Legendary Creature — Time Lord Doctor")))


def online():
    try:
        urllib.request.urlopen(urllib.request.Request("https://api.scryfall.com/sets/spm", headers=dc.UA), timeout=10, context=dc.CTX)
        return True
    except Exception:
        return False


@unittest.skipUnless(online(), "needs Scryfall")
class Live(unittest.TestCase):
    def run_cmd(self, *names):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.json")
            args = [sys.executable, SCRIPT, "--no-combos", "--json", out]
            for n in names:
                args += ["--commander", n]
            subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
            return {c["id"]: c["status"] for c in json.load(open(out, encoding="utf-8"))["checks"]}

    def test_valid(self):
        for pair in [("Tymna the Weaver", "Kraum, Ludevic's Opus"), ("Pir, Imaginative Rascal", "Toothy, Imaginary Friend"),
                     ("Abdel Adrian, Gorion's Ward", "Candlekeep Sage"), ("Barbara Wright", "The Eleventh Doctor"),
                     ("Ellie, Vengeful Hunter", "Joel, Resolute Survivor"), ("Kratos, Stoic Father", "Atreus, Impulsive Son"),
                     ("Bjorna, Nightfall Alchemist", "Cecily, Haunted Mage"), ("Aminatou, the Fateshifter",), ("Adrestia",)]:
            s = self.run_cmd(*pair)
            self.assertEqual(s["chk-legality-2"], "pass", pair)
            if len(pair) == 2:
                self.assertEqual(s["chk-legality-3"], "pass", pair)

    def test_invalid(self):
        for pair, check in [(("Pir, Imaginative Rascal", "Tymna the Weaver"), "chk-legality-3"), (("Ellie, Vengeful Hunter", "Tymna the Weaver"), "chk-legality-3"),
                            (("Candlekeep Sage",), "chk-legality-2"), (("Llanowar Elves",), "chk-legality-2"), (("Griselbrand",), "chk-legality-2"),
                            (("Deep Space 9",), "chk-legality-2"), (("Tymna the Weaver", "Kraum, Ludevic's Opus", "Thrasios, Triton Hero"), "chk-legality-2")]:
            self.assertEqual(self.run_cmd(*pair)[check], "fail", pair)


if __name__ == "__main__":
    unittest.main()
