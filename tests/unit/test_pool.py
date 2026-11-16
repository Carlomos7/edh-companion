"""pool.py: theme pool lockfile, evidence rules, footer and player calls, migrations, art notes, conditional downloads.

Offline except LivePool (EDHC_LIVE=1: downloads Scryfall's default_cards bulk, ~80 MB, and MTGJSON SLD).
"""
import importlib.util, json, os, shutil, sys, tempfile, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS = os.path.join(ROOT, "plugins", "edh-companion", "scripts")
sys.path.insert(0, SCRIPTS)
spec = importlib.util.spec_from_file_location("pool", os.path.join(SCRIPTS, "pool.py"))
pool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pool)


def card(i, name, set_, set_name, num, **kw):
    return {"id": i, "name": name, "oracle_id": "o" + i, "illustration_id": "ill-" + i, "set": set_, "set_name": set_name,
            "collector_number": num, "released_at": "2026-01-01", "image_status": "highres_scan", **kw}


CARDS = [card("a1", "Spider-Bite", "spm", "Marvel's Spider-Man", "1"),
         card("a2", "Spider Token", "tspm", "Marvel's Spider-Man Tokens", "1", set_type="token"),
         card("s1", "Fact or Fiction", "sld", "Secret Lair Drop", "1995"),
         card("s2", "Masterwork of Ingenuity", "sld", "Secret Lair Drop", "863"),
         card("s3", "Smothering Tithe", "sld", "Secret Lair Drop", "7009"),
         card("s4", "Sol Ring", "sld", "Secret Lair Drop", "100"),
         card("x1", "Sol Ring", "c21", "Commander 2021", "263")]
DROPS = {"s1": ["Marvel's Spider-Man: Daily Bugle Breaking News"], "s2": [], "s3": [], "s4": ["The Walking Dead"]}
MDD = [card("m1", "Darkhold Card", "mdd", "Marvel: Darkhold Destiny", "1", released_at="2027-04-09")]


class Pool(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def sweep(self, cards=CARDS, extra=MDD):
        return pool.sweep(self.d, client=object(), cards=list(cards), drop_map=DROPS, extra=list(extra), sources={})

    def status(self):
        return {s: e["status"] for s, e in pool.load(pool.P(self.d, "pool.lock.json"))["cards"].items()}

    def test_channels_decide_status(self):
        lock, diff = self.sweep()
        st = self.status()
        self.assertEqual(st, {"a1": "accepted", "s1": "accepted", "s2": "pending", "s3": "pending", "m1": "accepted"})  # s4: another franchise's drop, never listed
        self.assertNotIn("a2", st)  # tokens aren't deck cards
        self.assertIn("mdd", lock["theme_sets"])  # upcoming set found by the date>now channel
        self.assertTrue(os.path.exists(pool.P(self.d, "theme-rule.json")))  # the rule is a data file
        self.assertIn("## New, pending (2)", open(pool.P(self.d, "pool.diff.md"), encoding="utf-8").read())

    def test_footer_and_player_win_and_survive_a_resweep(self):
        self.sweep()
        pool.add_evidence(self.d, ["sld:863"], "footer", ("footer",))
        pool.add_evidence(self.d, ["s3"], "footer_absent", ("footer",))
        pool.add_evidence(self.d, ["spm:1"], "player:reject", ("player",))
        self.sweep()
        st = self.status()
        self.assertEqual((st["s2"], st["s3"], st["a1"]), ("accepted", "rejected", "rejected"))
        diff = open(pool.P(self.d, "pool.diff.md"), encoding="utf-8").read()
        self.assertIn("No changes.", diff)

    def test_card_not_found_again_is_dropped_unless_a_person_spoke_for_it(self):
        self.sweep()
        pool.add_evidence(self.d, ["s2"], "footer", ("footer",))
        _, diff = self.sweep(cards=[c for c in CARDS if c["id"] not in ("s2", "s3")])
        st = self.status()
        self.assertIn("s2", st)
        self.assertNotIn("s3", st)
        self.assertEqual([s for s, _ in diff["gone"]], ["s3"])

    def test_migrations_merge_and_delete(self):
        self.sweep()
        done = pool.apply_migrations(self.d, [
            {"migration_strategy": "merge", "old_scryfall_id": "s1", "new_scryfall_id": "s1-new"},
            {"migration_strategy": "delete", "old_scryfall_id": "s2"}])
        lock = pool.load(pool.P(self.d, "pool.lock.json"))
        self.assertEqual(len(done), 2)
        self.assertEqual(lock["cards"]["s1-new"]["migrated_from"], "s1")
        self.assertEqual(lock["cards"]["s2"]["status"], "removed")

    def test_art_notes_seed_record_and_go_stale_on_better_image(self):
        self.sweep()
        tags = [{"type": "illustration", "id": "t1", "label": "spider-man", "taggings": [{"illustration_id": "ill-a1"}]},
                {"type": "illustration", "id": "t2", "label": "zombie", "taggings": [{"illustration_id": "ill-s4"}]}]
        self.assertEqual(pool.art_seed(self.d, tags=tags), 1)
        pool.art(self.d, "s1", ["Spider-Man", "J. Jonah Jameson"], "test")
        notes = pool.load(pool.P(self.d, "art_notes.json"))
        self.assertEqual(notes["ill-a1"]["verified_by"], "scryfall-tagger (community, unverified)")
        self.assertEqual(notes["ill-s1"]["characters"], ["Spider-Man", "J. Jonah Jameson"])
        notes["ill-s1"]["image_status"] = "lowres"
        pool.save(pool.P(self.d, "art_notes.json"), notes)
        self.assertEqual(pool.stale_art(self.d), 1)


class Snapshot(unittest.TestCase):
    def test_304_keeps_file_and_key_skips_request(self):
        from edhcore.http import Client, RequestError
        d = tempfile.mkdtemp()
        try:
            calls = []

            class C(Client):
                def request(self, url, data=None, headers=None, accept="application/json", with_headers=False):
                    calls.append(dict(headers or {}))
                    if len(calls) == 1:
                        return b"v1", {"ETag": '"e1"', "Last-Modified": None}
                    raise RequestError(url, 304)
            c, p = C(), os.path.join(d, "f.bin")
            self.assertTrue(c.snapshot("u", p, key="k1")["changed"])
            self.assertFalse(c.snapshot("u", p)["changed"])
            self.assertEqual(calls[1]["If-None-Match"], '"e1"')
            self.assertFalse(c.snapshot("u", p, key="k1")["changed"])
            self.assertEqual(len(calls), 2)  # same key: no request
            self.assertEqual(open(p, "rb").read(), b"v1")
        finally:
            shutil.rmtree(d, ignore_errors=True)


BONUS = (["863", "864", "865", "866", "867", "868", "869", "870", "908"] + [str(n) for n in range(7013, 7022)]
         + [str(n) for n in range(7117, 7126)] + ["7127", "7129"])


@unittest.skipUnless(os.environ.get("EDHC_LIVE") == "1", "live: set EDHC_LIVE=1 (downloads ~80 MB)")
class LivePool(unittest.TestCase):
    def test_bonus_sld_cards_and_mdd_are_in_the_pool(self):
        d = tempfile.mkdtemp()
        try:
            lock, _ = pool.sweep(d)
            found = {f"{e['set']}:{e['number']}": e["status"] for e in lock["cards"].values()}
            missing = [n for n in BONUS if found.get("sld:" + n) not in ("accepted", "pending")]
            self.assertEqual(len(BONUS), 29)
            self.assertEqual(missing, [])
            self.assertTrue(any(k.startswith("mdd:") for k in found))
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
