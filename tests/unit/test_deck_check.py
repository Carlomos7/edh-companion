"""deck_check.py: parsing and hashing offline; the real checks against Scryfall/Spellbook (skipped offline).

Run: uv run --with certifi python -m unittest discover -s tests/unit
"""
import importlib.util, json, os, subprocess, sys, tempfile, unittest, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(ROOT, "plugins", "edh-companion", "skills", "audit", "scripts", "deck_check.py")
spec = importlib.util.spec_from_file_location("deck_check", SCRIPT)
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)


def online():
    try:
        urllib.request.urlopen(urllib.request.Request("https://api.scryfall.com/sets/spm", headers=dc.UA), timeout=10, context=dc.CTX)
        return True
    except Exception:
        return False


def run(deck_text, *args):
    with tempfile.TemporaryDirectory() as d:
        p, out = os.path.join(d, "deck.txt"), os.path.join(d, "out.json")
        open(p, "w", encoding="utf-8").write(deck_text)
        r = subprocess.run([sys.executable, SCRIPT, p, "--json", out, *args], capture_output=True, text=True, encoding="utf-8")
        return r.returncode, json.load(open(out, encoding="utf-8"))


class Parse(unittest.TestCase):
    def test_moxfield_sections_and_printings(self):
        cards, cmd = dc.parse_text("Commander\n1 Tymna the Weaver\n1 Kraum, Ludevic's Opus\n\nDeck\n1 Sol Ring (C21) 263 *F*\n2x Island\n\nSideboard\n1 Black Lotus\n")
        self.assertEqual([c["name"] for c in cmd], ["Tymna the Weaver", "Kraum, Ludevic's Opus"])
        self.assertEqual(cards[0], {"qty": 1, "name": "Sol Ring", "set": "c21", "cn": "263"})
        self.assertEqual(cards[1]["qty"], 2)
        self.assertNotIn("Black Lotus", [c["name"] for c in cards])  # sideboard ignored

    def test_hash_ignores_order_and_case_but_not_printings(self):
        a = [{"qty": 1, "name": "Sol Ring", "set": "c21", "cn": "263"}, {"qty": 2, "name": "Island", "set": None, "cn": None}]
        b = [{"qty": 2, "name": "island", "set": None, "cn": None}, {"qty": 1, "name": "Sol Ring", "set": "lea", "cn": "270"}]
        self.assertEqual(dc.deck_hash(a), dc.deck_hash(b))
        self.assertNotEqual(dc.deck_hash(a, True), dc.deck_hash(b, True))

    def test_brew_json_input(self):
        brew = {"commander": {"cards": [{"name": "Krenko, Mob Boss"}]}, "deck": [{"name": "Mountain", "qty": 99, "role": "land"}]}
        cards, cmd = dc.parse_brew(brew)
        self.assertEqual(cmd[0]["name"], "Krenko, Mob Boss")
        self.assertEqual(cards[0]["qty"], 99)


@unittest.skipUnless(online(), "needs Scryfall and Commander Spellbook")
class Live(unittest.TestCase):
    def status(self, out):
        return {c["id"]: c["status"] for c in out["checks"]}

    def test_planted_errors(self):
        deck = "1 Atraxa, Praetors' Voice\n1 Sol Ring\n1 Mana Crypt\n1 Rhystic Study\n1 Smothering Tithe\n1 Demonic Tutor\n1 Vampiric Tutor\n1 Lightning Bolt\n1 Black Lotus (LEA) 232\n92 Forest\n"
        code, out = run(deck, "--commander", "Atraxa, Praetors' Voice", "--bracket", "3", "--no-combos")
        s = self.status(out)
        self.assertEqual(code, 1)
        self.assertEqual(s["chk-count-1"], "fail")            # 101 cards
        self.assertEqual(s["chk-identity-1"], "fail")         # Lightning Bolt
        self.assertEqual(s["chk-legality-1"], "fail")         # Mana Crypt, Black Lotus banned
        self.assertEqual(s["chk-game-changers-1"], "fail")    # 4 Game Changers at bracket 3
        self.assertIn("Lightning Bolt", next(c for c in out["checks"] if c["id"] == "chk-identity-1")["cards"])

    def test_wrong_printing_number_fails(self):
        code, out = run("Commander\n1 Krenko, Mob Boss\nDeck\n1 Lightning Greaves (M19) 239\n98 Mountain\n", "--no-combos")
        self.assertEqual(self.status(out).get("chk-printing-2"), "fail")  # M19 239 is Manalith

    def test_commander_plus_two_combo(self):
        code, out = run("Commander\n1 Fire Lord Azula\nDeck\n1 Frantic Search\n1 Narset's Reversal\n97 Island\n", "--bracket", "3")
        two = [c for c in out["combos"]["included"] if c["two_card"]]
        self.assertTrue(any({"Frantic Search", "Narset's Reversal"} <= set(c["cards"]) for c in two))
        self.assertEqual(self.status(out)["chk-combos-1"], "warning")


if __name__ == "__main__":
    unittest.main()
