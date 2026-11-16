"""companion.py prose lint, sections and audit-scope; deck_check's Scryfall-tag second opinion (offline).

Run: uv run --with jsonschema --with pyyaml --with certifi python -m unittest discover -s tests/unit
"""
import importlib.util, json, os, shutil, sys, tempfile, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
spec = importlib.util.spec_from_file_location("companion", os.path.join(ROOT, "plugins", "edh-companion", "scripts", "companion.py"))
co = importlib.util.module_from_spec(spec)
spec.loader.exec_module(co)


def put(path, obj):
    with open(path, "w", encoding="utf-8") as h:
        h.write(obj if isinstance(obj, str) else json.dumps(obj))

BREW = {"version": 2, "deck_hash": "abc", "deck": [{"name": "Forest", "qty": 36}, {"name": "Raise the Palisade", "qty": 1}],
        "recommendations": [{"id": "rec-001", "add": "Raise the Palisade", "cut": "Savage Beating", "status": "accepted", "reason": "x"}],
        "strategy": {"game_plan": "Cast the commander by turn 5 in about 52% of games."},
        "limitations": ["Mana: 36 lands + 11 ramp (the video's guide is 38 + 10).", "Community lists run 34 to 36 lands.",
                        "No Savage Beating any more, so no extra combats.", "Drippy: $100.00 as listed."]}
DC = {"deck_hash": "abc", "stats": {"lands": 36, "price_usd": 100.0, "cast_by_turn": {"by_turn": {"5": 0.524}}}}


class Lint(unittest.TestCase):
    def test_clean_prose_has_no_warnings(self):
        self.assertEqual(co.lint_prose(BREW, DC), [])

    def test_stale_numbers_and_cut_cards_are_caught(self):
        b = json.loads(json.dumps(BREW))
        b["strategy"]["game_plan"] = "Cast the commander by turn 5 in about 47% of games; Savage Beating wins."
        b["limitations"][0] = "Mana: 35 lands + 11 ramp (the video's guide is 38 + 10)."
        b["limitations"][3] = "Drippy: $90.00 as listed."
        w = " | ".join(co.lint_prose(b, DC))
        for frag in ("47% by turn 5", "35 lands", "Savage Beating", "$90.00"):
            self.assertIn(frag, w)
        self.assertNotIn("34 to 36", w)  # a number about other decks isn't this deck's


class Scope(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        open(os.path.join(self.d, "PROJECT.md"), "w").write("# rules\n")
        put(os.path.join(self.d, "brew.json"), BREW)
        self.audit = {"created": "2026-11-14", "subject": {"deck": {"version": 2, "deck_hash": "abc"}, "goals_hash": co.goals_hash(self.d),
                                                           "sections": co.sections(BREW)},
                      "checks": [{"id": "chk-count-1", "area": "count", "status": "pass", "requirement": "100 cards"},
                                 {"id": "chk-rec-001", "area": "recommendation", "status": "pass", "requirement": "rec-001 supported"},
                                 {"id": "chk-theme-1", "area": "theme", "status": "warning", "requirement": "theme"},
                                 {"id": "chk-art-1", "area": "printing", "status": "pass", "requirement": "art", "cards": ["Raise the Palisade"]},
                                 {"id": "chk-art-2", "area": "printing", "status": "pass", "requirement": "art", "cards": ["Forest"]}]}

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def plan(self, brew=None):
        put(os.path.join(self.d, "audit.json"), self.audit)
        if brew:
            put(os.path.join(self.d, "brew.json"), brew)
        return co.audit_scope(self.d)

    def test_no_sections_means_full(self):
        del self.audit["subject"]["sections"]
        self.assertEqual(self.plan()[0], "full")

    def test_rule_change_means_full(self):
        self.audit["subject"]["goals_hash"] = "000000000000"
        self.assertEqual(self.plan()[0], "full")

    def test_changed_recommendation_and_deck_wide_rerun_rest_carries(self):
        b = json.loads(json.dumps(BREW))
        b["recommendations"][0]["reason"] = "reworded"
        mode, lines = self.plan(b)
        text = "\n".join(lines)
        self.assertEqual(mode, "scoped")
        self.assertIn("re-check chk-count-1: deck-wide", text)
        self.assertIn("re-check chk-rec-001: recommendation changed", text)
        self.assertIn("re-check chk-theme-1: was warning", text)
        self.assertNotIn("re-check chk-art-1", text)  # its card didn't change
        self.assertIn("rec:rec-001", text)

    def test_changed_card_reruns_its_checks(self):
        b = json.loads(json.dumps(BREW))
        b["deck"][1]["note"] = "new printing"
        text = "\n".join(self.plan(b)[1])
        self.assertIn("re-check chk-art-1: card changed", text)
        self.assertNotIn("re-check chk-art-2", text)

    def test_write_carry_records_new_subject_and_oldest_carried_date(self):
        self.audit["checks"][4]["carried_from"] = "2026-11-01"  # carried before: keep the oldest date
        self.audit["checks"] += [{"id": f"chk-art-{i}", "area": "printing", "status": "pass", "requirement": "art", "cards": ["Forest"]} for i in (3, 4)]
        b = json.loads(json.dumps(BREW))
        b.update(version=3, deck_hash="def")
        b["deck"][1]["note"] = "new printing"
        self.plan(b)
        out = co.write_carry(self.d)
        doc = json.load(open(out, encoding="utf-8"))
        sub = doc["subject"]
        self.assertEqual((sub["deck"]["version"], sub["deck"]["deck_hash"]), (3, "def"))
        self.assertEqual((sub["mode"], sub["based_on"], sub["goals_hash"]), ("scoped", "2026-11-14", co.goals_hash(self.d)))
        self.assertEqual(sub["sections"], co.sections(b))
        carried = {c["id"]: c["carried_from"] for c in doc["checks"]}
        self.assertEqual(len(carried), 2)  # 4 unchanged pass checks minus 2 spot checks
        self.assertLessEqual(set(carried), {"chk-rec-001", "chk-art-2", "chk-art-3", "chk-art-4"})
        for i, date in carried.items():
            self.assertEqual(date, "2026-11-01" if i == "chk-art-2" else "2026-11-14")


class Tags(unittest.TestCase):
    def test_unavailable_tags_never_change_data_status(self):
        sys.path.insert(0, os.path.join(ROOT, "tests", "unit"))
        from test_deck_check import Offline, dc  # temp cache, offline policy
        t = Offline("test_cached_data_passes")
        t.setUp()
        try:
            dc._SESSION = t.s
            before = (t.s.status, t.s.used, dict(t.s.client.unavailable))
            self.assertIsNone(dc.tag_roles(["Swords to Plowshares"]))
            self.assertEqual(before, (t.s.status, t.s.used, dict(t.s.client.unavailable)))
        finally:
            dc._SESSION = None
            t.tearDown()

    def test_cached_tags_map_to_roles_and_sweepers_are_not_removal(self):
        sys.path.insert(0, os.path.join(ROOT, "tests", "unit"))
        from test_deck_check import Offline, dc, T
        t = Offline("test_cached_data_passes")
        t.setUp()
        try:
            dc._SESSION = t.s
            names = ["Kindred Dominance", "Spider-Man No More"]
            q = lambda tag: f'otag:{tag} (!"Kindred Dominance" or !"Spider-Man No More")'
            hits = {"removal": names, "sweeper": ["Kindred Dominance"]}
            for tag in dc.TAG_ROLES:
                t.cache.put(f"search:cards:{q(tag)}", "search", [{"name": n} for n in hits.get(tag, [])], fetched_at=T - 60)
            roles = dc.tag_roles(names)
            self.assertEqual(roles["Spider-Man No More"], {"removal": ["Scryfall tag otag:removal"]})
            self.assertEqual(roles["Kindred Dominance"], {"wipe": ["Scryfall tag otag:sweeper"]})
        finally:
            dc._SESSION = None
            t.tearDown()


if __name__ == "__main__":
    unittest.main()
