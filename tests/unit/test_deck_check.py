"""deck_check.py: parsing and hashing offline; the real checks against Scryfall/Spellbook (skipped offline).

Run: uv run --with certifi python -m unittest discover -s tests/unit
"""
import importlib.util, json, os, re, subprocess, sys, tempfile, unittest, urllib.parse
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # _net, also when run as tests.unit.test_deck_check
from _net import online  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(ROOT, "plugins", "edh-companion", "skills", "audit", "scripts", "deck_check.py")
spec = importlib.util.spec_from_file_location("deck_check", SCRIPT)
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)
from edhcore.cache import Cache  # noqa: E402  (deck_check put plugin/scripts on sys.path)
from edhcore.http import Client  # noqa: E402
from edhcore.policy import Policy  # noqa: E402
from edhcore.session import DAY, Session  # noqa: E402


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
        self.assertEqual(cards[0], {"qty": 1, "name": "Sol Ring", "set": "c21", "cn": "263", "finish": "foil"})
        self.assertEqual(cards[1]["qty"], 2)
        self.assertNotIn("Black Lotus", [c["name"] for c in cards])  # sideboard ignored

    def test_hash_ignores_order_and_case_but_not_printings(self):
        a = [{"qty": 1, "name": "Sol Ring", "set": "c21", "cn": "263"}, {"qty": 2, "name": "Island", "set": None, "cn": None}]
        b = [{"qty": 2, "name": "island", "set": None, "cn": None}, {"qty": 1, "name": "Sol Ring", "set": "lea", "cn": "270"}]
        self.assertEqual(dc.deck_hash(a), dc.deck_hash(b))
        self.assertNotEqual(dc.deck_hash(a, True), dc.deck_hash(b, True))

    def test_finish_and_archidekt_tags(self):
        cards, cmd = dc.parse_text("1x Krenko, Mob Boss (rvr) 120 *F* [Commander]\n1x Sol Ring (c21) 263 *E* [Ramp]\n1 Mountain\n")
        self.assertEqual(cmd[0]["name"], "Krenko, Mob Boss")
        self.assertEqual(cmd[0]["finish"], "foil")
        self.assertEqual(cards[0]["finish"], "etched")
        self.assertEqual(cards[1]["finish"], "nonfoil")

    def test_brew_json_input(self):
        brew = {"commander": {"cards": [{"name": "Krenko, Mob Boss"}]}, "deck": [{"name": "Mountain", "qty": 99, "role": "land"}]}
        cards, cmd = dc.parse_brew(brew)
        self.assertEqual(cmd[0]["name"], "Krenko, Mob Boss")
        self.assertEqual(cards[0]["qty"], 99)


T = 1_800_000_000.0
KRENKO = {"id": "k1", "name": "Krenko, Mob Boss", "set": "rvr", "collector_number": "120", "type_line": "Legendary Creature \u2014 Goblin Warrior",
          "oracle_text": "{T}: Create X 1/1 red Goblin creature tokens, where X is the number of Goblins you control.", "cmc": 4,
          "mana_cost": "{2}{R}{R}", "color_identity": ["R"], "legalities": {"commander": "legal"}, "prices": {"usd": "1.00"}}
MOUNTAIN = {"id": "m1", "name": "Mountain", "set": "fdn", "collector_number": "279", "type_line": "Basic Land \u2014 Mountain",
            "oracle_text": "({T}: Add {R}.)", "cmc": 0, "color_identity": [], "legalities": {"commander": "legal"}, "prices": {"usd": "0.10"},
            "produced_mana": ["R"]}
DECK = "Commander\n1 Krenko, Mob Boss\nDeck\n99 Mountain\n"


class Offline(unittest.TestCase):
    """main() in-process against a temp cache with no network (offline policy, fixed clock)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cache = Cache(path=os.path.join(self.tmp, "c", "cache.sqlite"), now=lambda: T)
        pol = Policy(offline=True, config=os.path.join(self.tmp, "none.yaml"))
        self.s = Session(cache=self.cache, policy=pol, client=Client(self.cache, pol, sleep=lambda x: None, now=lambda: T), now=lambda: T)

    def tearDown(self):
        self.cache.db.close()
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def put(self, card, age):
        self.cache.put("card:name:" + card["name"].lower(), "card", card, fetched_at=T - age)
        if card is KRENKO or card["name"] == KRENKO["name"]:  # deck_check's second opinion on commander eligibility
            self.cache.put('search:cards:(!"Krenko, Mob Boss") is:commander', "search", [card], fetched_at=T - age)

    def main(self, *argv, deck=DECK):
        p, out = os.path.join(self.tmp, "deck.txt"), os.path.join(self.tmp, "out.json")
        if deck:
            open(p, "w", encoding="utf-8").write(deck)
        args = ([p] if deck else []) + list(argv) + ["--json", out]
        with mock.patch.object(dc, "Session", return_value=self.s), mock.patch.object(sys, "argv", ["deck_check.py", *args]), \
                mock.patch("sys.stdout", new_callable=lambda: open(os.devnull, "w", encoding="utf-8")):
            with self.assertRaises(SystemExit) as ex:
                dc.main()
        res = json.load(open(out, encoding="utf-8"))
        return ex.exception.code, res, {c["id"]: c for c in res["checks"]}

    def test_cached_data_passes(self):
        self.put(KRENKO, 3600)
        self.put(MOUNTAIN, 3600)
        code, res, ch = self.main("--bracket", "3", "--no-combos")
        self.assertEqual(res["data"]["verification"], "cached")
        self.assertEqual(res["data"]["requests"], 0)
        self.assertEqual({k: v["status"] for k, v in ch.items() if k.startswith("chk-legality")}, {"chk-legality-1": "pass", "chk-legality-2": "pass"})
        self.assertIn("back_image", res["cards"][0])

    def test_stale_data_is_unverified_never_pass(self):
        self.put(KRENKO, 3 * DAY)  # legality max age is 1 day; still within the 30-day stale limit
        self.put(MOUNTAIN, 3 * DAY)
        code, res, ch = self.main("--bracket", "3", "--no-combos", "--budget", "500")
        self.assertEqual(res["data"]["verification"], "stale")
        for cid in ("chk-legality-1", "chk-legality-2", "chk-game-changers-1", "chk-budget-1"):
            self.assertEqual(ch[cid]["status"], "unverified", cid)
            self.assertIn("data stale (as of", ch[cid]["detail"])
        self.assertEqual(ch["chk-count-1"]["status"], "pass")  # counting needs no card data
        self.assertEqual(code, 2)

    def test_stale_fail_stays_fail(self):
        self.put(KRENKO, 3 * DAY)
        self.put(dict(MOUNTAIN, legalities={"commander": "banned"}), 3 * DAY)
        _, _, ch = self.main("--no-combos")
        self.assertEqual(ch["chk-legality-1"]["status"], "fail")

    def test_unavailable_cards_are_reported_not_missing(self):
        self.put(KRENKO, 3600)  # Mountain: not cached and no network
        code, res, ch = self.main("--bracket", "3", "--no-combos")
        self.assertEqual(ch["chk-cards-1"]["status"], "unverified")
        self.assertIn("Mountain", ch["chk-cards-1"]["detail"])
        self.assertNotIn("not found", ch["chk-cards-1"]["detail"])
        self.assertTrue(any("Mountain" in u for u in res["unavailable"]))
        self.assertTrue(all(c["status"] != "pass" for k, c in ch.items() if k != "chk-count-1"))
        self.assertEqual(code, 2)

    def test_commander_only_has_no_count_check_and_no_spellbook(self):
        self.put(KRENKO, 3600)
        with mock.patch.object(self.s.spellbook, "find_my_combos") as sb:
            code, res, ch = self.main("--commander", "Krenko, Mob Boss", deck=None)
        sb.assert_not_called()
        self.assertNotIn("chk-count-1", ch)
        self.assertEqual(ch["chk-legality-2"]["status"], "pass")
        self.assertEqual(code, 0)

    def test_stale_combos_are_unverified(self):
        self.put(KRENKO, 3600)
        self.put(MOUNTAIN, 3600)  # card data merely cached: only the Spellbook answer is stale
        self.cache.put("combos:old", "combos", {"results": {"included": [], "almostIncluded": []}}, fetched_at=T - 3 * DAY)
        with mock.patch.object(self.s.spellbook, "find_my_combos", side_effect=lambda *a: self.s.fallback("combos:old")):
            code, res, ch = self.main("--bracket", "3")
        self.assertEqual(ch["chk-combos-1"]["status"], "unverified")
        self.assertIn("data stale (as of", ch["chk-combos-1"]["detail"])
        self.assertEqual(ch["chk-legality-1"]["status"], "pass")  # degraded on the combo call's own status, not the cards'
        self.assertEqual(res["data"]["verification"], "stale")
        self.assertEqual(code, 2)

    def test_non_json_answer_is_unverified_not_a_crash(self):
        html = json.JSONDecodeError("Expecting value", "<html>captive portal</html>", 0)  # an HTML page answered 200
        with mock.patch.object(self.s.client, "post_json", side_effect=html):
            code, res, ch = self.main("--bracket", "3", "--no-combos")
        self.assertEqual(ch["chk-legality-1"]["status"], "unverified")
        self.assertIn("JSONDecodeError", ch["chk-legality-1"]["detail"])
        self.assertEqual(res["data"]["verification"], "unavailable")
        self.assertEqual(code, 2)

    def test_cards_only_has_status_and_release_date(self):
        future = dict(MOUNTAIN, id="f1", name="Future Card", type_line="Creature", legalities={"commander": "not_legal"}, released_at="2099-01-01")
        banned = dict(MOUNTAIN, id="b1", name="Banned Card", type_line="Artifact", legalities={"commander": "banned"})
        for c in (KRENKO, future, banned):
            self.put(c, 3600)
        _, res, _ = self.main("--cards-only", deck="Commander\n1 Krenko, Mob Boss\nDeck\n1 Future Card\n1 Banned Card\n")
        cards = {c["name"]: c for c in res["cards"]}
        self.assertEqual({n: c["status"] for n, c in cards.items()},
                         {"Krenko, Mob Boss": "legal", "Future Card": "upcoming", "Banned Card": "banned"})
        self.assertEqual(cards["Future Card"]["releases"], "2099-01-01")

    def test_cheapest_reuses_names_across_variants(self):
        fx = os.path.join(ROOT, "tests", "fixtures", "krenko")
        b3, b4 = ({c["name"] for c in json.load(open(os.path.join(fx, f), encoding="utf-8"))["deck"]} - {"Mountain"}
                  for f in ("brew-b3.json", "brew-b4.json"))
        asked = []

        def search(url):
            names = re.findall(r'!"([^"]+)"', urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["q"][0])
            asked.append(names)
            return {"data": [{"id": n, "name": n, "set": "tst", "collector_number": "1", "prices": {"usd": "1.00"}} for n in names], "has_more": False}

        with mock.patch.object(dc, "_SESSION", self.s), mock.patch.object(self.s.client, "get_json", side_effect=search):
            first = dc.cheapest(sorted(b3))
            n3, asked[:] = len(asked), []
            second = dc.cheapest(sorted(b4))
        self.assertEqual((set(first), set(second)), (b3, b4))
        self.assertEqual(n3, -(-len(b3) // 15))                       # 15 names per query
        self.assertEqual([set(q) for q in asked], [b4 - b3])           # the variant only searches for the cards it doesn't share


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

    def test_finishes_and_budgets(self):
        deck = "Commander\n1 Spider-Gwen, Free Spirit (SPM) 90\nDeck\n1 Sol Ring (C21) 263 *F*\n1 Shock (SPM) 1\n97 Mountain\n"
        code, out = run(deck, "--no-combos", "--cheapest", "--budget", "1", "--per-card-max", "0.5")
        s = self.status(out)
        self.assertEqual(s["chk-printing-3"], "fail")       # Commander 2021 Sol Ring has no foil
        self.assertEqual(s["chk-printing-2"], "fail")       # SPM 1 isn't Shock
        self.assertEqual(s["chk-identity-1"], "pass")       # ...but Shock itself is checked, not the wrong card
        self.assertIn("price_cheapest_usd", out["stats"])
        self.assertIn("chk-budget-1", s)
        sol = next(c for c in out["cards"] if c["name"] == "Sol Ring")
        self.assertEqual(sol["finish"], "foil")
        self.assertIsNone(sol["price_usd"])                 # no foil price for a printing with no foil

    def test_flexible_vs_hard_budget(self):
        deck = "Commander\n1 Atraxa, Praetors' Voice\nDeck\n1 Rhystic Study\n98 Forest\n"
        _, soft = run(deck, "--no-combos", "--budget", "5", "--per-card-max", "5")
        _, hard = run(deck, "--no-combos", "--budget", "5", "--per-card-max", "5", "--hard-budget")
        self.assertEqual(self.status(soft)["chk-budget-1"], "warning")   # a target: over is flagged with the amount
        self.assertEqual(self.status(hard)["chk-budget-1"], "fail")      # a hard limit: over fails
        self.assertEqual(self.status(soft)["chk-budget-3"], "warning")
        self.assertEqual(self.status(hard)["chk-budget-3"], "fail")

    def test_commander_plus_two_combo(self):
        code, out = run("Commander\n1 Fire Lord Azula\nDeck\n1 Frantic Search\n1 Narset's Reversal\n97 Island\n", "--bracket", "3")
        two = [c for c in out["combos"]["included"] if c["two_card"]]
        self.assertTrue(any({"Frantic Search", "Narset's Reversal"} <= set(c["cards"]) for c in two))
        self.assertEqual(self.status(out)["chk-combos-1"], "warning")


if __name__ == "__main__":
    unittest.main()
