"""Unit tests for mtgdb.py on a tiny synthetic bulk file. Run: python3 -m unittest evals/tests/test_mtgdb.py"""
import json, os, subprocess, sys, tempfile, unittest, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.normpath(os.path.join(HERE, "../plugins/mtg/scripts/mtgdb.py"))


def card(name, ci, type_, set_, cn, usd, gc=False, border="black", digital=False, legal="legal", text="",
         cost="{1}", cmc=1, produced=None, faces=None):
    c = {"id": str(uuid.uuid4()), "oracle_id": "o-" + name, "name": name, "lang": "en", "color_identity": list(ci),
         "type_line": type_, "oracle_text": text, "cmc": cmc, "mana_cost": cost, "set": set_, "collector_number": cn,
         "set_name": set_.upper(), "border_color": border, "digital": digital, "prices": {"usd": usd},
         "legalities": {"commander": legal}, "game_changer": gc, "layout": "normal",
         "image_uris": {"normal": "https://cards.scryfall.io/n.jpg", "small": "https://cards.scryfall.io/s.jpg"},
         "card_back_id": "0aeebaf5-8c7d-4636-9e82-8c27447861f7"}
    if produced:
        c["produced_mana"] = produced
    if faces:
        c["card_faces"], c["image_uris"] = faces, None
    return c


class MtgdbTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cards = [
            card("Darth Vader", "B", "Legendary Creature — Human Sith", "swt", "12", "5", cost="{3}{B}{B}", cmc=5),
            card("Sol Ring", "", "Artifact", "c21", "263", "1", produced=["C"], text="{T}: Add {C}{C}."),
            card("Sol Ring", "", "Artifact", "sld", "999", "30", produced=["C"], text="{T}: Add {C}{C}."),
            card("Rhystic Study", "U", "Enchantment", "pcy", "45", "40", gc=True),
            card("Demonic Tutor", "B", "Sorcery", "cmm", "1", "20", gc=True, text="Search your library for a card"),
            card("Vampiric Tutor", "B", "Instant", "cmm", "2", "30", gc=True),
            card("Imperial Seal", "B", "Sorcery", "me1", "3", "100", gc=True),
            card("Necropotence", "B", "Enchantment", "ice", "4", "50", gc=True),
            card("Armageddon", "W", "Sorcery", "lea", "5", "5", text="Destroy all lands."),
            card("Time Warp", "U", "Sorcery", "m10", "6", "5", text="Target player takes an extra turn after this one."),
            card("Swamp", "B", "Basic Land — Swamp", "swt", "300", "0.1", produced=["B"]),
            card("Mana Crypt", "", "Artifact", "wc97", "1", "0.5", border="gold", legal="banned"),
            card("Relentless Rats", "B", "Creature — Rat", "m11", "7", "0.2", text="A deck can have any number of cards named Relentless Rats."),
            card("Bonecrusher Giant // Stomp", "R", "Creature — Giant // Instant — Adventure", "eld", "115", "1",
                 faces=[{"name": "Bonecrusher Giant", "oracle_text": "", "image_uris": {"normal": "f"}},
                        {"name": "Stomp", "oracle_text": "", "image_uris": None}]),
            card("Black Lotus", "", "Artifact", "lea", "232", "9999", digital=True),
            card("Big Furnace", "R", "Artifact", "pcmd", "1", "3"),
            card("Volcanic Island", "UR", "Land — Island Mountain", "lea", "283", None, produced=["U", "R"]),
        ]
        bulk = os.path.join(cls.tmp, "bulk.json")
        open(bulk, "w").write("[\n" + ",\n".join(json.dumps(c) for c in cards) + "\n]\n")
        cls.db = os.path.join(cls.tmp, "c.sqlite")
        cls.themes = os.path.join(cls.tmp, "themes.json")
        json.dump({"printings": {"set:swt": "Sith", "sld#999": "franchise"}}, open(cls.themes, "w"))
        cls.cards = cards
        cls.env = dict(os.environ, MTG_CACHE=os.path.join(cls.tmp, "cache"))
        cls.run_cmd(["index", "--bulk-file", bulk])
        import sqlite3
        x = sqlite3.connect(cls.db)  # mark one printing oversized, as Scryfall bulk would
        x.execute("UPDATE printings SET oversized=1 WHERE set_code='pcmd'")
        x.commit(); x.close()

    @classmethod
    def run_cmd(cls, args, themes=False, stdin=None, raw=False):
        base = [sys.executable, SCRIPT, "--db", cls.db] + (["--themes", cls.themes] if themes else [])
        p = subprocess.run(base + args, capture_output=True, text=True, input=stdin, env=cls.env)
        if raw:
            return p
        try:
            return p.returncode, json.loads(p.stdout)
        except json.JSONDecodeError:
            return p.returncode, p.stdout

    @classmethod
    def sid(self, name, set_):
        return next(c["id"] for c in self.cards if c["name"] == name and c["set"] == set_)

    def test_collection_csv_and_cost_to_buy(self):
        csvp = os.path.join(self.tmp, "col.csv")
        with open(csvp, "w") as f:
            f.write('Count,Name,Edition,Collector Number\n1,Sol Ring,c21,263\n1,Darth Vader,swt,12\n40,Swamp,swt,300\n1,Rhystc Stdy,x,1\n')
        code, rep = self.run_cmd(["collection", "import", csvp])
        self.assertEqual(rep["unique_cards"], 3)
        self.assertEqual(len(rep["unresolved"]), 1)
        d = self.deck(["1 Darth Vader", "1 Demonic Tutor (CMM) 1", "98 Swamp"])
        code, rep = self.run_cmd(["validate", d, "--bracket", "4"])
        self.assertEqual(rep["collection"]["owned"], 2)  # Vader + Swamp (basics count if owned)
        self.assertEqual(rep["collection"]["cost_to_buy_usd"], 20.0)
        code, rep = self.run_cmd(["printings", "Sol Ring"])
        self.assertEqual(rep["owned_total"], 1)
        self.assertEqual(next(p for p in rep["printings"] if p["set_code"] == "c21")["owned_qty"], 1)
        os.remove(os.path.join(self.tmp, "cache", "collection.json"))

    def test_hook_blocks_bad_deck_and_ignores_other_files(self):
        vault = os.path.join(self.tmp, "run", "vault")
        os.makedirs(os.path.join(vault, "vader"), exist_ok=True)
        json.dump({"budget": None, "since": "2026-02-09", "commanders": {}}, open(os.path.join(vault, "config.json"), "w"))
        bad = os.path.join(vault, "vader", "b3.txt")
        with open(bad, "w") as f:
            f.write("1 Darth Vader\n1 Demonic Tutor\n1 Vampiric Tutor\n1 Imperial Seal\n1 Necropotence\n95 Swamp\n")
        p = self.run_cmd(["hook"], stdin=json.dumps({"tool_name": "Write", "tool_input": {"file_path": bad}}), raw=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn("4 Game Changers", p.stderr)
        with open(bad, "w") as f:
            f.write("1 Darth Vader\n99 Swamp\n")
        p = self.run_cmd(["hook"], stdin=json.dumps({"tool_name": "Write", "tool_input": {"file_path": bad}}), raw=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        p = self.run_cmd(["hook"], stdin=json.dumps({"tool_name": "Write", "tool_input": {"file_path": "/x/notes.md"}}), raw=True)
        self.assertEqual(p.returncode, 0)
        led = os.path.join(vault, "vader", "claims.jsonl")
        with open(led, "w") as f:
            f.write(json.dumps({"id": "x", "type": "combo", "claim": "c", "confidence": "low",
                                "sources": [{"url": "https://a.com", "date": "2026-03-01"}]}) + "\n")
        p = self.run_cmd(["hook"], stdin=json.dumps({"tool_name": "Write", "tool_input": {"file_path": led}}), raw=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn("independent", p.stderr)

    def test_prices_sync_from_mtgjson_files(self):
        import gzip
        ids = os.path.join(self.tmp, "ids.json.gz")
        prices = os.path.join(self.tmp, "prices.json.gz")
        sol = self.sid("Sol Ring", "c21")
        with gzip.open(ids, "wt") as f:
            json.dump({"meta": {}, "data": {"u1": {"identifiers": {"scryfallId": sol}}, "u2": {"identifiers": {}}}}, f)
        with gzip.open(prices, "wt") as f:
            json.dump({"meta": {}, "data": {"u1": {"paper": {
                "tcgplayer": {"currency": "USD", "retail": {"normal": {"2026-11-01": 1.1, "2026-11-02": 1.2}}},
                "cardkingdom": {"currency": "USD", "retail": {"normal": {"2026-11-02": 1.5}}, "buylist": {"normal": {"2026-11-02": 0.6}}}}}}}, f)
        code, rep = self.run_cmd(["prices-sync", "--identifiers", ids, "--prices-file", prices])
        self.assertEqual(code, 0, rep)
        self.assertEqual(rep["rows"], 4)
        code, rep = self.run_cmd(["printings", "Sol Ring"])
        v = next(p for p in rep["printings"] if p["set_code"] == "c21")["vendors"]
        self.assertEqual(v["tcgplayer"]["retail_normal"], 1.2)
        self.assertEqual(v["cardkingdom"]["buylist_normal"], 0.6)
        code, rep = self.run_cmd(["price-history", "Sol Ring", "--set", "c21", "--cn", "263"])
        self.assertEqual(len(rep["printings"][0]["series"]), 3)

    def test_tags_drive_roles(self):
        import sqlite3
        cache = os.path.join(self.tmp, "cache")
        os.makedirs(cache, exist_ok=True)
        x = sqlite3.connect(os.path.join(cache, "extra.sqlite"))
        x.executescript("""CREATE TABLE IF NOT EXISTS tags(oracle_id TEXT, name TEXT, tag TEXT, synced TEXT);
            CREATE TABLE IF NOT EXISTS tag_sync(tag TEXT PRIMARY KEY, synced TEXT, count INTEGER);""")
        x.execute("INSERT INTO tags VALUES('o-Sol Ring','Sol Ring','mana-rock','2026-11-03')")
        x.execute("INSERT INTO tags VALUES('o-Demonic Tutor','Demonic Tutor','tutor','2026-11-03')")
        x.execute("INSERT OR REPLACE INTO tag_sync VALUES('mana-rock','2026-11-03',1)")
        x.commit(); x.close()
        d = self.deck(["1 Darth Vader", "1 Sol Ring", "1 Demonic Tutor", "97 Swamp"])
        code, st = self.run_cmd(["stats", d])
        self.assertIn("Tagger", st["roles_source"])
        self.assertEqual(st["roles"]["ramp"]["cards"], ["Sol Ring"])
        self.assertEqual(st["roles"]["tutor"]["cards"], ["Demonic Tutor"])
        os.remove(os.path.join(cache, "extra.sqlite"))

    def test_search_uses_cache(self):
        import sqlite3, time as t
        cache = os.path.join(self.tmp, "cache")
        os.makedirs(cache, exist_ok=True)
        x = sqlite3.connect(os.path.join(cache, "extra.sqlite"))
        x.execute("CREATE TABLE IF NOT EXISTS search_cache(query TEXT PRIMARY KEY, fetched REAL, body TEXT)")
        x.execute("INSERT OR REPLACE INTO search_cache VALUES(?,?,?)", ("prints|e:sld art:lightsaber", t.time(),
                  json.dumps([{"id": "1", "name": "Sol Ring", "set": "sld", "cn": "999"}])))
        x.commit(); x.close()
        code, rep = self.run_cmd(["search", "e:sld art:lightsaber", "--unique", "prints"])
        self.assertEqual(rep["count"], 1)

    def test_picker_page(self):
        cand = os.path.join(self.tmp, "cand.json")
        json.dump({"title": "T", "slots": [{"slot": "Draw", "options": [{"name": "A <b>", "why": "x", "price": 1}]}]}, open(cand, "w"))
        outp = os.path.join(self.tmp, "p.html")
        picker = os.path.normpath(os.path.join(HERE, "../plugins/mtg/skills/commander-deckbuilding/scripts/picker.py"))
        subprocess.run([sys.executable, picker, cand, "--out", outp], check=True, capture_output=True)
        page = open(outp, encoding="utf-8").read()
        self.assertIn("A &lt;b&gt;", page)
        self.assertIn("Copy my picks", page)

    def deck(self, lines):
        path = os.path.join(self.tmp, f"{uuid.uuid4()}.txt")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        return path

    def test_clean_deck_passes(self):
        d = self.deck(["1 Darth Vader (SWT) 12", "1 Sol Ring (SLD) 999", "98 Swamp (SWT) 300"])
        code, rep = self.run_cmd(["validate", d, "--bracket", "2"], themes=True)
        self.assertEqual(code, 0, rep)
        self.assertEqual(rep["theme_counts"], {"Sith": 99, "franchise": 1})

    def test_count_identity_ban_gold(self):
        d = self.deck(["1 Darth Vader (SWT) 12", "1 Rhystic Study", "1 Mana Crypt (WC97) 1", "96 Swamp (SWT) 300"])
        code, rep = self.run_cmd(["validate", d, "--bracket", "4"])
        self.assertEqual(code, 1)
        txt = " ".join(rep["errors"])
        for needle in ("count is 99", "outside color identity", "banned", "not playable"):
            self.assertIn(needle, txt)

    def test_game_changer_limit_b3(self):
        d = self.deck(["1 Darth Vader", "1 Demonic Tutor", "1 Vampiric Tutor", "1 Imperial Seal", "1 Necropotence", "95 Swamp"])
        code, rep = self.run_cmd(["validate", d, "--bracket", "3"])
        self.assertEqual(code, 1)
        self.assertIn("4 Game Changers", " ".join(rep["errors"]))
        code, rep = self.run_cmd(["validate", d, "--bracket", "4"])
        self.assertEqual(code, 0, rep)

    def test_singleton_and_exceptions(self):
        d = self.deck(["1 Darth Vader", "2 Sol Ring", "20 Relentless Rats", "77 Swamp"])
        code, rep = self.run_cmd(["validate", d, "--bracket", "4"])
        errs = " ".join(rep["errors"])
        self.assertIn("Sol Ring x2", errs)
        self.assertNotIn("Relentless Rats x", errs)
        self.assertNotIn("Swamp x", errs)

    def test_mld_flagged_below_b4(self):
        d = self.deck(["1 Darth Vader", "1 Armageddon", "98 Swamp"])
        code, rep = self.run_cmd(["validate", d, "--bracket", "3"])
        self.assertIn("mass land denial", " ".join(rep["errors"]))

    def test_themed_printing_warning(self):
        d = self.deck(["1 Darth Vader (SWT) 12", "1 Sol Ring (C21) 263", "98 Swamp (SWT) 300"])
        code, rep = self.run_cmd(["validate", d, "--bracket", "2"], themes=True)
        self.assertIn("themed_printing_available", " ".join(rep["warnings"]))

    def test_normalize_transcript_names(self):
        code, res = self.run_cmd(["normalize", "rhystic studdy", "Sol Ring", "stomp", "totally fake card"])
        by = {r["input"]: r for r in res}
        self.assertEqual(by["rhystic studdy"]["name"], "Rhystic Study")
        self.assertEqual(by["Sol Ring"]["match"], "exact")
        self.assertEqual(by["stomp"]["name"], "Bonecrusher Giant // Stomp")
        self.assertEqual(by["totally fake card"]["match"], "none")
        self.assertEqual(code, 1)

    def test_unknown_card_suggests(self):
        d = self.deck(["1 Darth Vader", "1 Rhystic Studdy", "98 Swamp"])
        code, rep = self.run_cmd(["validate", d, "--bracket", "4"])
        self.assertIn("did you mean: Rhystic Study", " ".join(rep["errors"]))

    def test_swaptest(self):
        d = self.deck(["1 Darth Vader", "1 Sol Ring", "98 Swamp"])
        code, rep = self.run_cmd(["swaptest", d, "--bracket", "2", "--swap", "-Sol Ring +Demonic Tutor"])
        self.assertEqual(code, 1)
        self.assertIn("Game Changers", " ".join(rep["errors"]))
        code, rep = self.run_cmd(["swaptest", d, "--bracket", "2", "--swap", "-Not In Deck +Sol Ring"])
        self.assertIn("swap_out not in deck", " ".join(rep["errors"]))

    def test_digital_printing_rejected(self):
        d = self.deck(["1 Darth Vader", "1 Black Lotus (LEA) 232", "98 Swamp"])
        code, rep = self.run_cmd(["validate", d, "--bracket", "4"])
        self.assertIn("digital-only", " ".join(rep["errors"]))

    def test_audit_claims(self):
        led = os.path.join(self.tmp, "claims.jsonl")
        good = {"id": "c1", "type": "must-play", "claim": "Sol Ring is a must-play", "cards": ["Sol Ring"], "confidence": "high",
                "sources": [{"url": "https://youtube.com/watch?v=a", "kind": "video", "author": "Channel A", "date": "2026-06-01", "locator": "12:30"},
                            {"url": "https://edhrec.com/commanders/x", "kind": "edhrec", "date": "2026-11-01"}]}
        weak = {"id": "c2", "type": "combo", "claim": "x", "cards": ["Rhystic Studdy"], "confidence": "low",
                "sources": [{"url": "https://youtube.com/watch?v=b", "kind": "video", "date": "2023-01-01"}]}
        stat = {"id": "c3", "type": "stat", "claim": "62% inclusion", "confidence": "medium",
                "sources": [{"url": "https://edhrec.com/x", "date": "2026-11-01"}]}
        open(led, "w").write("\n".join(json.dumps(x) for x in (good, weak, stat)) + "\n")
        code, rep = self.run_cmd(["audit-claims", led, "--since", "2026-02-09"])
        probs = {(p["id"], p["problem"].split(" ")[0]) for p in rep["problems"]}
        self.assertFalse(any(p[0] == "c1" for p in probs), rep)
        msgs = " ".join(p["problem"] for p in rep["problems"])
        for needle in ("needs 2 independent", "older than", "without timestamp", "unknown card", "sample size"):
            self.assertIn(needle, msgs)

    def test_stats(self):
        d = self.deck(["1 Darth Vader", "1 Sol Ring", "1 Demonic Tutor", "97 Swamp"])
        code, st = self.run_cmd(["stats", d])
        self.assertEqual(st["lands"], 97)
        self.assertEqual(st["sources"]["B"], 97)
        self.assertEqual(st["sources"]["C"], 1)
        self.assertIn("tutor", st["roles"])
        self.assertIn("regex", st["roles_source"])


    def test_oversized_printing_rejected(self):
        d = self.deck(["1 Darth Vader", "1 Big Furnace (PCMD) 1", "98 Swamp"])
        code, rep = self.run_cmd(["validate", d, "--bracket", "4"])
        self.assertIn("not playable", " ".join(rep["errors"]))

    def test_unpriced_warning(self):
        d = self.deck(["1 Darth Vader", "1 Volcanic Island", "98 Swamp"])
        code, rep = self.run_cmd(["validate", d, "--bracket", "4"])
        self.assertIn("no price", " ".join(rep["warnings"]))

    def test_simulate_more_lands_and_ramp_cast_sooner(self):
        few = self.deck(["1 Darth Vader", "30 Swamp", "69 Demonic Tutor"])
        many = self.deck(["1 Darth Vader", "40 Swamp", "59 Demonic Tutor"])
        ramp = self.deck(["1 Darth Vader", "30 Swamp", "10 Sol Ring", "59 Demonic Tutor"])
        allland = self.deck(["1 Darth Vader", "99 Swamp"])
        r = {k: self.run_cmd(["simulate", d, "--runs", "4000"])[1]["pct_commander_cast_by"]["turn_5"]
             for k, d in (("few", few), ("many", many), ("ramp", ramp), ("all", allland))}
        self.assertEqual(r["all"], 100.0)
        self.assertGreater(r["many"], r["few"])
        self.assertGreater(r["ramp"], r["few"])

    def test_contact_sheet(self):
        from PIL import Image
        img = os.path.join(self.tmp, "x.jpg")
        Image.new("RGB", (488, 680), (10, 120, 200)).save(img)
        items = os.path.join(self.tmp, "items.json")
        json.dump([{"label": "sld#1", "img": "file://" + img}] * 3, open(items, "w"))
        outp = os.path.join(self.tmp, "sheet.jpg")
        p = self.run_cmd(["contact-sheet", items, "--out", outp, "--cols", "2"], raw=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(Image.open(outp).size, (488, 2 * 368))


if __name__ == "__main__":
    unittest.main()


class LogicTest(unittest.TestCase):
    """In-process tests for parsing and matching logic that has no CLI-only behavior."""
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.dirname(SCRIPT))
        import mtgdb
        cls.m = mtgdb

    def test_commander_plus_two_is_a_two_card_combo(self):
        combo = lambda cards, req=(): {"id": "x", "cards": cards, "also_requires": list(req), "produces": ["Infinite looting"]}
        got = self.m.short_combos([combo(["Fire Lord Azula", "Narset's Reversal", "Frantic Search"]),
                                   combo(["Twinning Staff", "Narset's Reversal"]),
                                   combo(["A", "B", "C"]), combo(["A", "B"], ["a creature with power 3"])], ["Fire Lord Azula"])
        self.assertEqual([g["deck_pieces"] for g in got], [["Narset's Reversal", "Frantic Search"], ["Twinning Staff", "Narset's Reversal"]])
        self.assertEqual([g["commander_enabled"] for g in got], [True, False])

    def test_research_log_and_coverage(self):
        d = tempfile.mkdtemp()
        entries = [{"kind": "video", "title": "Deck tech", "url": "https://youtu.be/x", "used_for": "traps", "locator": "1:23"},
                   {"kind": "video", "title": "Deck tech", "url": "https://youtu.be/x", "used_for": "plan"},
                   {"kind": "decklist", "title": "List", "url": "https://archidekt.com/decks/1"}]
        p = subprocess.run([sys.executable, SCRIPT, "research", "log", d, "--entries", json.dumps(entries), "--bracket", "4"],
                           capture_output=True, text=True)
        res = json.loads(p.stdout)
        self.assertEqual(res["claims"], 3)
        self.assertEqual({g["kind"]: (g["sources"], g["citations"]) for g in res["groups"]}, {"video": (1, 2), "decklist": (1, 1)})
        self.assertEqual(res["shortfalls"]["decklist"], "1 of 6")
        self.assertIn("cedh", res["shortfalls"])  # bracket 4 needs cEDH results
        self.assertIn("used for: plan; traps", open(os.path.join(d, "sources.md"), encoding="utf-8").read())
        bad = subprocess.run([sys.executable, SCRIPT, "research", "log", d, "--entries", json.dumps([{"kind": "rumor", "url": "u"}])],
                             capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)

    def test_web_cache_falls_back_when_offline(self):
        m, d = self.m, tempfile.mkdtemp()
        old_cache, old_get = m.CACHE, m.http_get
        try:
            m.CACHE = d
            m.http_get = lambda *a, **k: b'{"v": 1}'
            self.assertEqual(m.cached_web_json("k", "https://x", 24), {"v": 1})
            os.utime(os.path.join(d, "web", "k.json"), (0, 0))  # make the cache old
            def down(*a, **k):
                raise OSError("offline")
            m.http_get = down
            got = m.cached_web_json("k", "https://x", 24)
            self.assertEqual(got["v"], 1)
            self.assertIn("_stale_cache", got)
            with self.assertRaises(OSError):  # nothing cached: the error surfaces
                m.cached_web_json("never", "https://x", 24)
        finally:
            m.CACHE, m.http_get = old_cache, old_get

    def test_research_log_accepts_jsonl_and_rejects_garbage(self):
        d = tempfile.mkdtemp()
        f = os.path.join(d, "e.jsonl")
        with open(f, "w", encoding="utf-8") as h:
            h.write(json.dumps({"kind": "article", "url": "https://a"}) + "\n" + json.dumps({"kind": "community", "url": "https://b"}) + "\n")
        ok = subprocess.run([sys.executable, SCRIPT, "research", "log", os.path.join(d, "r"), "--entries", f], capture_output=True, text=True)
        self.assertEqual(json.loads(ok.stdout)["claims"], 2)
        again = subprocess.run([sys.executable, SCRIPT, "research", "log", os.path.join(d, "r2"), "--entries",
                                os.path.join(d, "r", "claims.jsonl")], capture_output=True, text=True)
        self.assertEqual(json.loads(again.stdout)["claims"], 2)  # its own ledger format is accepted too
        bad = subprocess.run([sys.executable, SCRIPT, "research", "log", d, "--entries", "{nope"], capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("valid JSON", json.loads(bad.stdout)["error"])

    def _run_with_web(self, fake, argv):
        """Run a research command in-process with cached_web_json faked (no network)."""
        import contextlib, io
        m, old = self.m, self.m.cached_web_json
        m.cached_web_json = fake
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                try:
                    m.main(argv)
                except SystemExit:
                    pass
        finally:
            m.cached_web_json = old
        return json.loads(buf.getvalue())

    def test_edhrec_parsing_and_partner_slug(self):
        seen = []
        def fake(key, url, *a, **k):
            seen.append(url)
            return {"bracket_counts": {"3": 10}, "container": {"json_dict": {"card": {"num_decks": 200}, "cardlists": [
                {"header": "Top Cards", "cardviews": [{"name": "Sol Ring", "num_decks": 150, "potential_decks": 200, "synergy": 0.05},
                                                      {"name": "Frantic Search", "num_decks": 140, "potential_decks": 180, "synergy": 0.49}]}]}}}
        deck = self.write("1 Darth Vader\n1 Sol Ring\n")
        res = self._run_with_web(fake, ["edhrec", "Tymna the Weaver", "--partner", "Kraum, Ludevic's Opus", "--deck", deck])
        self.assertTrue(seen[0].endswith("/kraum-ludevics-opus-tymna-the-weaver.json"), seen)
        self.assertEqual(res["decks"], 200)
        self.assertEqual(res["lists"][0]["cards"][0]["inclusion_pct"], 75.0)
        self.assertEqual([x["name"] for x in res["popular_missing"]], ["Frantic Search"])  # Sol Ring is in the deck
        self.assertEqual(res["log_entry"]["kind"], "stats")

    def test_decklists_keeps_finished_lists_only(self):
        def card(n, q=1, cats=None):
            return {"quantity": q, "categories": cats or [], "card": {"oracleCard": {"name": n}}}
        lists = {"results": [{"id": 1}, {"id": 2}, {"id": 3}]}
        full = {"name": "Real list", "owner": {"username": "a"}, "createdAt": "2026-01-02T00:00:00Z", "updatedAt": "2026-11-04T00:00:00Z",
                "categories": [{"name": "Maybeboard", "includedInDeck": False}],
                "cards": [card("Sol Ring"), card("Island", 97), card("Brainstorm"), card("Lotus Petal", 1, ["Maybeboard"])]}
        def fake(key, url, *a, **k):
            if "v3" in url:
                return lists
            if "/1/" in url:
                return full
            if "/2/" in url:
                return dict(full, name="Half a brew", cards=[card("Sol Ring"), card("Island", 40)])
            return dict(full, name="Copy of Real list")
        res = self._run_with_web(fake, ["decklists", "Darth Vader"])
        self.assertEqual([x["name"] for x in res["lists"]], ["Real list"])  # unfinished and copies dropped
        self.assertEqual((res["lists"][0]["size"], res["lists"][0]["created"]), (99, "2026-01-02"))  # maybeboard excluded
        self.assertNotIn("Lotus Petal", [n for n, _ in res["most_played"]])
        self.assertEqual(res["log_entries"][0]["kind"], "decklist")

    def test_web_slug(self):
        self.assertEqual(self.m.web_slug("Narset's Reversal"), "narsets-reversal")
        self.assertEqual(self.m.web_slug("Brazen Borrower // Petty Theft"), "brazen-borrower")
        self.assertEqual(self.m.web_slug("Lim-Dûl the Necromancer"), "lim-dul-the-necromancer")

    def write(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
        f.write(text); f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_moxfield_sections(self):
        path = self.write("Deck\n1 Sol Ring\n\nCommander\n1 Tymna the Weaver\n1 Kraum, Ludevic's Opus\n\n"
                          "Sideboard\n1 Black Lotus\n\nMaybeboard\n1 Mana Crypt\n")
        rows, n = self.m.parse_deck_sections(path)
        self.assertEqual(n, 2)
        self.assertEqual([r["name"] for r in rows], ["Tymna the Weaver", "Kraum, Ludevic's Opus", "Sol Ring"])

    def test_plain_list_unchanged(self):
        rows, n = self.m.parse_deck_sections(self.write("1 Darth Vader (SWT) 12\n1 Sol Ring *F*\n"))
        self.assertEqual((n, rows[0]["set"], rows[0]["cn"]), (0, "swt", "12"))

    def test_pastes_from_other_sites(self):
        # Arena header, Archidekt categories (commander by category), finish marks, a bare name, a BOM
        path = self.write("\ufeffAbout\nName My Deck\n\n1x Krenko, Mob Boss (rvr) 109 [Commander{top}]\n1x Sol Ring (cmm) 410 *F* [Ramp]\n1 Sol Ring (cmm) 703 *E*\nArcane Signet\n")
        rows, n = self.m.parse_deck_sections(path)
        self.assertEqual(n, 1)
        self.assertEqual([(r["name"], r["qty"], r["finish"]) for r in rows],
                         [("Krenko, Mob Boss", 1, ""), ("Sol Ring", 1, "foil"), ("Sol Ring", 1, "etched"), ("Arcane Signet", 1, "")])
        self.assertFalse(any("error" in r for r in rows))

    def test_land_rule(self):
        self.assertTrue(self.m.is_land_type("Land // Land"))  # Pathways
        self.assertFalse(self.m.is_land_type("Sorcery // Land"))  # modal spells count as spells
        self.assertTrue(self.m.is_land_type("Basic Land — Swamp"))

    def test_collection_csv_values(self):
        self.assertEqual([self.m.csv_qty(v) for v in ("2", "2.0", "3x", "", "x", "two")], [2, 2, 3, 1, None, None])
        self.assertEqual([self.m.csv_finish(v) for v in ("foil", "Etched", "normal", "", "TRUE")],
                         ["foil", "etched", "", "", "foil"])

    def test_identity_names(self):
        self.assertEqual(self.m.parse_identity("Esper"), set("WUB"))
        self.assertEqual(self.m.parse_identity("rg"), set("RG"))
        self.assertEqual(self.m.parse_identity("C"), set())

    def test_tag_key(self):
        self.assertEqual(self.m.tag_key("board-wipe"), self.m.tag_key("Board Wipe"))
        self.assertEqual(self.m.tag_key("mana rock"), "manarock")

    def test_parse_rules(self):
        text = ("Magic: The Gathering Comprehensive Rules\n\nThese rules are effective as of September 25, 2026.\n\n"
                "Contents\n\nGlossary\n\n" + "\n" * 100 +
                "702.19. Trample\n\n702.19a Trample is a static ability.\n\n903.8. A commander costs {2} more.\n\n"
                "Glossary\n\nCommander Tax\nInformal term. See rule 903.8.\n\nTrample\nA keyword ability.\n\nCredits\n")
        eff, rows = self.m.parse_rules(text)
        self.assertEqual(eff, "September 25, 2026")
        self.assertEqual(rows["702.19a"], "Trample is a static ability.")
        self.assertEqual(rows["glossary:Commander Tax"], "Informal term. See rule 903.8.")
        self.assertNotIn("glossary:Contents", rows)

    def test_drippy_and_finish(self):
        p = {"finishes": "nonfoil,foil", "usd": 1.0, "usd_foil": 4.0, "usd_etched": None, "border": "borderless",
             "frame_effects": "", "promo_types": "", "set_code": "sld", "full_art": 0}
        self.assertEqual(self.m.finish_prices(p), [("nonfoil", 1.0), ("foil", 4.0)])
        self.assertGreater(self.m.drippy_score(p, "foil"), self.m.drippy_score(p, "nonfoil"))
        self.assertEqual(self.m.drippy_score(dict(p, promo_types="serialized"), "foil"), -1)

    def test_direct_link(self):
        aff = "https://partner.tcgplayer.com/c/1/2/3?subId1=api&u=https%3A%2F%2Fwww.tcgplayer.com%2Fproduct%2F671258%3Fpage%3D1"
        self.assertEqual(self.m.direct_link(aff), "https://www.tcgplayer.com/product/671258?page=1")


class NameCollisionTest(unittest.TestCase):
    run_cmd = MtgdbTest.__dict__["run_cmd"]
    """A paper card and a digital-only Alchemy card share a name: lookups must return the paper card."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        alchemy = card("Heroic Sacrifice", "W", "Instant", "amsh", "31", None, digital=True, legal="not_legal")
        alchemy["oracle_id"], alchemy["name"] = "o-alchemy", "Heroic Sacrifice // Heroic Sacrifice"
        alchemy["card_faces"] = [{"name": "Heroic Sacrifice", "oracle_text": ""}, {"name": "Heroic Sacrifice", "oracle_text": ""}]
        paper = card("Heroic Sacrifice", "W", "Instant", "msc", "18", "0.5")
        bulk = os.path.join(cls.tmp, "bulk.json")
        open(bulk, "w", encoding="utf-8").write("[\n" + ",\n".join(json.dumps(c) for c in (alchemy, paper)) + "\n]\n")
        cls.db = os.path.join(cls.tmp, "c.sqlite")
        cls.themes = None
        cls.env = dict(os.environ, MTG_CACHE=os.path.join(cls.tmp, "cache"))
        cls.run_cmd(["index", "--bulk-file", bulk])

    def test_paper_card_wins(self):
        code, res = self.run_cmd(["card", "Heroic Sacrifice"])
        self.assertEqual((code, res["name"], res["commander_legal"]), (0, "Heroic Sacrifice", "legal"))
