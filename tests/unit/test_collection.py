"""collection.py: CSV/text collection exports -> collection.json, offline with a fake Scryfall."""
import os, shutil, sys, tempfile, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "plugins", "edh-companion", "scripts"))
import collection as col  # noqa: E402

CARDS = {"sol ring": {"id": "p-sol-c21", "oracle_id": "o-sol", "name": "Sol Ring", "set": "c21", "collector_number": "263"},
         "arcane signet": {"id": "p-sig-m3c", "oracle_id": "o-sig", "name": "Arcane Signet", "set": "m3c", "collector_number": "283"},
         "valakut awakening": {"id": "p-val", "oracle_id": "o-val", "name": "Valakut Awakening // Valakut Stoneforge", "set": "znr", "collector_number": "174"}}
BY_PRINT = {(c["set"], c["collector_number"]): c for c in CARDS.values()}
BY_ID = {c["id"]: c for c in CARDS.values()}


class FakeScryfall:
    def __init__(self, down=()):
        self.down, self.calls = set(down), 0

    def collection(self, idents, need="legality"):
        self.calls += 1
        out, nf, un = [], [], []
        for i, x in enumerate(idents):
            c = BY_ID.get(x.get("id")) or BY_PRINT.get((x.get("set"), x.get("collector_number"))) or CARDS.get(x.get("name", "").lower())
            if c and c["name"] in self.down:
                c, _ = None, un.append(i)
            elif not c:
                nf.append(i)
            out.append(c)
        return out, nf, un


class FakeSession:
    def __init__(self, **kw):
        self.scryfall = FakeScryfall(**kw)

    def data_block(self):
        return {"as_of": "2026-11-17 10:00", "verification": "fresh", "endpoints_unavailable": [], "requests": 1}


MANABOX = "Name,Set code,Set name,Collector number,Foil,Rarity,Quantity,ManaBox ID,Scryfall ID\n" \
          "Sol Ring,c21,Commander 2021,263,normal,uncommon,2,1,p-sol-c21\n" \
          "Sol Ring,c21,Commander 2021,263,foil,uncommon,1,2,p-sol-c21\n" \
          "Arcane Signet,m3c,Modern Horizons 3 Commander,283,normal,common,1,3,\n"
MOXFIELD = "\"Count\",\"Tradelist Count\",\"Name\",\"Edition\",\"Condition\",\"Language\",\"Foil\",\"Tags\",\"Last Modified\",\"Collector Number\"\n" \
           "\"1\",\"0\",\"Sol Ring\",\"c21\",\"Near Mint\",\"English\",\"etched\",\"\",\"2026-01-01\",\"263\"\n" \
           "\"x\",\"0\",\"Arcane Signet\",\"m3c\",\"Near Mint\",\"English\",\"\",\"\",\"2026-01-01\",\"283\"\n"
DECKBOX = "Count,Tradelist Count,Name,Edition,Card Number,Condition,Language,Foil\n" \
          "1,0,Valakut Awakening // Valakut Stoneforge,Zendikar Rising,174,Near Mint,English,\n" \
          "1,0,Not A Real Card,Nowhere,1,Near Mint,English,\n"
TEXT = "1 Sol Ring (C21) 263 *F*\n2 Arcane Signet\n"


class Collection(unittest.TestCase):
    def run_files(self, *texts, **kw):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        files = []
        for i, t in enumerate(texts):
            files.append(os.path.join(d, f"f{i}.csv"))
            with open(files[-1], "w", encoding="utf-8") as h:
                h.write(t)
        self.s = FakeSession(**kw)
        return col.build(files, self.s, today="2026-11-17")

    def test_manabox_keeps_printing_and_adds_up(self):
        doc = self.run_files(MANABOX)
        by = {(c["name"], c["finish"]): c for c in doc["cards"]}
        self.assertEqual(by[("Sol Ring", "nonfoil")]["qty"], 2)
        self.assertEqual(by[("Sol Ring", "foil")]["printing_id"], "p-sol-c21")
        self.assertEqual(by[("Arcane Signet", "nonfoil")]["printing_id"], "p-sig-m3c")  # set + number, no Scryfall ID
        self.assertEqual(doc["counts"], {"rows": 3, "cards": 4, "unique": 2, "unmatched": 0})
        self.assertEqual(self.s.scryfall.calls, 1)  # one batched lookup

    def test_moxfield_bad_quantity_is_reported(self):
        doc = self.run_files(MOXFIELD)
        self.assertEqual([(c["name"], c["finish"]) for c in doc["cards"]], [("Sol Ring", "etched")])
        self.assertEqual(doc["unmatched"], [{"row": "f0.csv:3", "text": "Arcane Signet", "reason": "quantity 'x' is not a number"}])

    def test_deckbox_set_names_fall_back_to_names(self):
        doc = self.run_files(DECKBOX)
        self.assertEqual([c["name"] for c in doc["cards"]], ["Valakut Awakening // Valakut Stoneforge"])
        self.assertIsNone(doc["cards"][0]["printing_id"])  # "Zendikar Rising" isn't a set code: any printing
        self.assertEqual(doc["unmatched"][0]["reason"], "not found on Scryfall")

    def test_text_list_and_unavailable(self):
        doc = self.run_files(TEXT, down=["Arcane Signet"])
        self.assertEqual([(c["name"], c["finish"], c["qty"]) for c in doc["cards"]], [("Sol Ring", "foil", 1)])
        self.assertEqual(doc["unmatched"][0]["reason"], "card data unavailable (try again online)")

    def test_set_code_column_wins_and_name_retry(self):
        deckbox = "Count,Tradelist Count,Name,Edition,Edition Code,Card Number\n1,0,Sol Ring,Mirage,c21,263\n1,0,Arcane Signet,Exodus,zzz,999\n"
        doc = self.run_files(deckbox)
        by = {c["name"]: c for c in doc["cards"]}
        self.assertEqual(by["Sol Ring"]["printing_id"], "p-sol-c21")               # "Edition Code", not "Edition"
        self.assertIsNone(by["Arcane Signet"]["printing_id"])                     # wrong printing: found by name instead
        self.assertEqual(doc["unmatched"], [])

    def test_states(self):
        have = col.owned({"cards": [{"oracle_id": "o-sol", "printing_id": "p-sol-c21", "qty": 1}, {"oracle_id": "o-sig", "printing_id": None, "qty": 1}]})
        self.assertEqual(col.state({"oracle_id": "o-sol", "printing_id": "p-sol-c21"}, have), "owned")
        self.assertEqual(col.state({"oracle_id": "o-sol", "printing_id": "p-other"}, have), "other_printing")
        self.assertEqual(col.state({"oracle_id": "o-sig", "printing_id": "p-any"}, have), "owned")  # owned in an unknown printing
        self.assertEqual(col.state({"oracle_id": "o-val"}, have), "missing")


if __name__ == "__main__":
    unittest.main()
