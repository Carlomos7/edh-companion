"""export_deck.py: Moxfield, Archidekt, text and CSV output keep printings and finishes (offline).

Run: uv run --with certifi python -m unittest discover -s tests/unit
"""
import csv, io, json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXPORT = os.path.join(ROOT, "plugins", "edh-companion", "skills", "brew", "scripts", "export_deck.py")
BREW = {"commander": {"cards": [{"name": "Spider-Gwen, Free Spirit", "set": "spm", "collector_number": "90", "finish": "foil"}]},
        "deck": [{"name": "Sol Ring", "qty": 1, "role": "ramp", "set": "c21", "collector_number": "263", "finish": "nonfoil", "printing_id": "abc"},
                 {"name": "Lightning Greaves", "qty": 1, "role": "protection", "set": "drc", "collector_number": "55", "finish": "etched"},
                 {"name": "Mountain", "qty": 98, "role": "land"}]}


def export(fmt, src):
    r = subprocess.run([sys.executable, EXPORT, src, "--format", fmt], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return r.stdout


class Export(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.brew = os.path.join(self.d, "brew.json")
        json.dump(BREW, open(self.brew, "w", encoding="utf-8"))

    def test_moxfield(self):
        lines = export("moxfield", self.brew).splitlines()
        self.assertEqual(lines[0], "1 Spider-Gwen, Free Spirit (SPM) 90 *F*")
        self.assertEqual(lines[1], "")
        self.assertIn("1 Sol Ring (C21) 263", lines)
        self.assertIn("1 Lightning Greaves (DRC) 55 *E*", lines)
        self.assertIn("98 Mountain", lines)

    def test_archidekt_marks_commander(self):
        out = export("archidekt", self.brew)
        self.assertIn("1x Spider-Gwen, Free Spirit (spm) 90 *F* [Commander]", out)
        self.assertIn("1x Sol Ring (c21) 263\n", out)

    def test_text_drops_printings(self):
        self.assertEqual(export("text", self.brew).splitlines()[2], "1 Sol Ring")

    def test_csv_columns(self):
        rows = list(csv.DictReader(io.StringIO(export("csv", self.brew))))
        self.assertEqual(rows[0]["section"], "commander")
        sol = next(r for r in rows if r["name"] == "Sol Ring")
        self.assertEqual((sol["set"], sol["collector_number"], sol["finish"], sol["scryfall_id"]), ("c21", "263", "nonfoil", "abc"))

    def test_round_trip_from_text(self):
        txt = os.path.join(self.d, "deck.txt")
        open(txt, "w", encoding="utf-8").write(export("archidekt", self.brew))
        again = export("moxfield", txt)
        self.assertEqual(again, export("moxfield", self.brew))


if __name__ == "__main__":
    unittest.main()
