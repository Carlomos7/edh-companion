"""edhcore: the shared data core. Offline except where noted (a local stub HTTP server, never the internet).

Regression tests for the Azula run's failures: Scryfall 429s, 502s from one endpoint, duplicate requests, parallel
processes sharing rate limits; plus cache freshness per data category, stale/unavailable reporting, provider
exclusions and fenced cache recovery.
"""
import http.server, io, json, os, shutil, subprocess, sys, tempfile, textwrap, threading, time, unittest, urllib.error
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS = os.path.join(ROOT, "plugins", "edh-companion", "scripts")
sys.path.insert(0, SCRIPTS)
from edhcore import cache as cache_mod, http as h, policy as pol  # noqa: E402
from edhcore.cache import Cache  # noqa: E402
from edhcore.session import Session, DAY  # noqa: E402

SF = "https://api.scryfall.com"


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t, self.slept = t, []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(round(s, 3))
        self.t += s


def err(code, retry_after=None):
    hdr = {"Retry-After": str(retry_after)} if retry_after is not None else {}
    return urllib.error.HTTPError(SF + "/x", code, "x", hdr, io.BytesIO(b""))


class Ok:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return io.BytesIO(json.dumps(self.payload).encode())

    def __exit__(self, *a):
        return False


def client(clock, cache=None, policy=None):
    return h.Client(cache or Cache(mode="off", now=clock.now), policy, sleep=clock.sleep, now=clock.now, jitter=lambda: 0)


class FailureClasses(unittest.TestCase):
    """429 = rate limit, 5xx/timeouts = transient, other 4xx = request error, repeated exhaustion = endpoint failing."""

    def setUp(self):
        self.clock = Clock()
        self.c = client(self.clock)

    def call(self, effects, url="https://example.test/a"):
        with mock.patch.object(h.urllib.request, "urlopen", side_effect=effects) as m:
            try:
                return json.loads(self.c.request(url)), m.call_count
            except Exception as e:  # noqa: BLE001
                return e, m.call_count

    def test_429_retry_after_seconds(self):
        res, n = self.call([err(429, 7), Ok({"ok": 1})])
        self.assertEqual(res, {"ok": 1})
        self.assertEqual(self.clock.slept, [7])

    def test_429_retry_after_http_date(self):
        when = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(self.clock.t + 12))
        res, n = self.call([err(429, when), Ok({"ok": 1})])
        self.assertEqual(res, {"ok": 1})
        self.assertAlmostEqual(self.clock.slept[0], 12, delta=1)

    def test_429_default_and_cap(self):
        self.call([err(429), Ok({})])
        self.call([err(429, 900), Ok({})])
        self.assertEqual(self.clock.slept, [30, h.MAX_WAIT])

    def test_429_on_scryfall_holds_the_shared_bucket(self):
        res, n = self.call([err(429, 5), Ok({"ok": 1})], SF + "/cards/search?q=x")
        self.assertEqual(res, {"ok": 1})
        self.assertGreaterEqual(sum(self.clock.slept), 5)          # waited out the hold before retrying
        self.assertGreaterEqual(self.c.cache.reserve("scryfall-slow", 0.5), 0.0)

    def test_429_every_try_is_not_an_endpoint_failure(self):
        res, n = self.call([err(429, 1)] * 3)
        self.assertIsInstance(res, h.Unavailable)
        self.assertIn("rate-limited", str(res))
        self.assertEqual(self.c.cache.breaker("example.test/a")["fails"], 0)

    def test_read_timeout_is_retried(self):
        res, n = self.call([TimeoutError("read timed out"), Ok({"ok": 1})])
        self.assertEqual(res, {"ok": 1})
        self.assertEqual(self.clock.slept, [1])

    def test_5xx_backoff_is_bounded(self):
        res, n = self.call([err(502)] * 3)
        self.assertIsInstance(res, h.Unavailable)
        self.assertEqual((n, self.clock.slept), (3, [1, 2]))     # no wait after the last try

    def test_404_is_a_request_error_and_not_counted(self):
        res, n = self.call([err(404)])
        self.assertIsInstance(res, h.RequestError)
        self.assertEqual((n, self.clock.slept), (1, []))
        self.assertEqual(self.c.cache.breaker("example.test/a")["fails"], 0)


class Breaker(unittest.TestCase):
    """One broken endpoint (the Azula 502s) never locks out the provider, and recovers on its own."""

    def setUp(self):
        self.clock = Clock()
        self.c = client(self.clock)

    def fail(self, url, times=1):
        for _ in range(times):
            with mock.patch.object(h.urllib.request, "urlopen", side_effect=[err(502)] * 3):
                with self.assertRaises(h.Unavailable):
                    self.c.request(url)

    def test_opens_after_three_exhausted_calls_for_that_endpoint_only(self):
        self.fail(SF + "/cards/search?q=a", 3)
        with mock.patch.object(h.urllib.request, "urlopen") as m:
            with self.assertRaises(h.Unavailable) as cm:
                self.c.request(SF + "/cards/search?q=b")
            self.assertEqual(m.call_count, 0)                       # fails fast: no network
        self.assertIn("retry after", str(cm.exception))
        with mock.patch.object(h.urllib.request, "urlopen", side_effect=[Ok({"data": []})]) as m:
            self.c.request(SF + "/cards/collection")                # same host, other endpoint: still works
            self.assertEqual(m.call_count, 1)

    def test_cooldown_probe_success_closes(self):
        self.fail(SF + "/cards/search?q=a", 3)
        self.clock.t += 61
        with mock.patch.object(h.urllib.request, "urlopen", side_effect=[Ok({})]):
            self.c.request(SF + "/cards/search?q=a")
        self.assertEqual(self.c.cache.breaker("api.scryfall.com/cards/search")["fails"], 0)

    def test_failed_probe_doubles_cooldown(self):
        self.fail(SF + "/cards/search?q=a", 3)
        self.clock.t += 61
        self.fail(SF + "/cards/search?q=a")
        st = self.c.cache.breaker("api.scryfall.com/cards/search")
        self.assertEqual(st["cooldown"], 120)
        self.assertGreater(st["open_until"], self.clock.t + 100)

    def test_card_ids_share_one_endpoint(self):
        self.assertEqual(h.endpoint(SF + "/cards/228e551e-023a-4c9a-8f32-58dae6ffdf7f"), "api.scryfall.com/cards/:id")


class Policy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cfg(self, text):
        p = os.path.join(self.tmp, "config.yaml")
        open(p, "w", encoding="utf-8").write(textwrap.dedent(text))
        return p

    def test_excluded_provider_gets_no_requests(self):
        p = pol.Policy(config=self.cfg("""
            research:
              approved: {card_data: MTG MCP}
              excluded: [Scryfall API]
            """))
        clock = Clock()
        c = client(clock, policy=p)
        with mock.patch.object(h.urllib.request, "urlopen") as m:
            with self.assertRaises(h.Unavailable):
                c.request(SF + "/cards/collection")
            self.assertEqual(m.call_count, 0)
            self.assertIsNone(p.blocked("backend.commanderspellbook.com"))

    def test_block_list_and_project_override(self):
        cfg = self.cfg("""
            research:
              excluded:
                - Commander Spellbook
            """)
        self.assertIn("excluded", pol.Policy(config=cfg).blocked("backend.commanderspellbook.com"))
        proj = os.path.join(self.tmp, "p")
        os.makedirs(proj)
        open(os.path.join(proj, "PROJECT.md"), "w").write("# P\n\n## Research preferences\n- Exclude: direct APIs\n")
        self.assertIsNotNone(pol.Policy(project=proj, config=os.path.join(self.tmp, "none")).blocked("api.scryfall.com"))

    def test_not_onboarded_allows_and_offline_blocks(self):
        none = os.path.join(self.tmp, "none")
        self.assertIsNone(pol.Policy(config=none).blocked("api.scryfall.com"))
        self.assertEqual(pol.Policy(config=none, offline=True).blocked("api.scryfall.com"), "offline mode")


def card(name, cid, legal="legal", gc=False):
    return {"id": cid, "name": name, "set": "tst", "collector_number": "1", "legalities": {"commander": legal}, "game_changer": gc,
            "type_line": "Artifact", "prices": {"usd": "1.00"}, "color_identity": []}


class Freshness(unittest.TestCase):
    """Per-category freshness, --fresh for final audits, stale-if-error and unavailable, duplicate requests avoided."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.clock = Clock()
        self.path = os.path.join(self.tmp, "c", "cache.sqlite")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def session(self, fresh=False):
        cache = Cache(path=self.path, now=self.clock.now)
        c = h.Client(cache, pol.Policy(config=os.path.join(self.tmp, "none")), sleep=self.clock.sleep, now=self.clock.now, jitter=lambda: 0)
        return Session(fresh=fresh, cache=cache, client=c, policy=c.policy, now=self.clock.now)

    def lookup(self, s, names, need="legality", effects=None):
        effects = effects if effects is not None else [Ok({"data": [card(n, f"id-{n}") for n in names]})]
        with mock.patch.object(h.urllib.request, "urlopen", side_effect=effects) as m:
            res = s.scryfall.collection([{"name": n} for n in names], need)
        return res, m.call_count

    def test_second_lookup_is_free_even_across_processes(self):
        (_, _, _), n1 = self.lookup(self.session(), ["Sol Ring", "Arcane Signet"])
        s2 = self.session()                                  # a new session = what a second process sees
        (cards, miss, un), n2 = self.lookup(s2, ["Sol Ring", "Arcane Signet"], effects=[])
        self.assertEqual((n1, n2), (1, 0))
        self.assertEqual([c["name"] for c in cards], ["Sol Ring", "Arcane Signet"])
        self.assertEqual(s2.data_block()["verification"], "cached")

    def test_policy_table(self):
        self.lookup(self.session(), ["Sol Ring"])
        for hours, need, refetch in ((23, "legality", False), (25, "legality", True), (25, "price", True),
                                     (6 * 24, "oracle", False), (8 * 24, "oracle", True)):
            clock_t = self.clock.t
            self.clock.t += hours * 3600
            (_, _, _), n = self.lookup(self.session(), ["Sol Ring"], need)
            self.assertEqual(n, int(refetch), (hours, need))
            self.clock.t = clock_t
            Cache(path=self.path).put("card:name:sol ring", "card", card("Sol Ring", "id-Sol Ring"), fetched_at=clock_t)

    def test_fresh_refetches_legality_and_game_changer(self):
        self.lookup(self.session(), ["Mana Vault"])
        s = self.session(fresh=True)
        updated = card("Mana Vault", "id-Mana Vault", legal="banned", gc=True)
        (cards, _, _), n = self.lookup(s, ["Mana Vault"], effects=[Ok({"data": [updated]})])
        self.assertEqual((n, cards[0]["legalities"]["commander"], cards[0]["game_changer"]), (1, "banned", True))
        self.assertEqual(s.data_block()["verification"], "fresh")

    def test_stale_if_error_then_unavailable(self):
        self.lookup(self.session(), ["Sol Ring"])
        self.clock.t += 10 * DAY
        s = self.session()
        (cards, _, un), _ = self.lookup(s, ["Sol Ring"], effects=[err(502)] * 3)
        self.assertEqual((cards[0]["name"], un), ("Sol Ring", []))
        self.assertEqual(s.data_block()["verification"], "stale")
        self.assertEqual(s.scryfall.stale_ids, {"id-Sol Ring"})      # callers can flag exactly the stale cards
        self.clock.t += 30 * DAY
        s = self.session()
        (cards, _, un), _ = self.lookup(s, ["Sol Ring"], effects=[err(502)] * 3)
        self.assertEqual((cards[0], un), (None, [0]))
        d = s.data_block()
        self.assertEqual(d["verification"], "unavailable")
        self.assertTrue(d["endpoints_unavailable"])

    def test_batches_of_75_and_only_misses(self):
        self.lookup(self.session(), ["Card 0", "Card 1"])
        names = [f"Card {i}" for i in range(160)]
        bodies = []

        def fake(req, **k):
            ids = json.loads(req.data)["identifiers"]
            bodies.append(len(ids))
            return Ok({"data": [card(x["name"], "id-" + x["name"]) for x in ids]})

        with mock.patch.object(h.urllib.request, "urlopen", side_effect=fake):
            cards, miss, un = self.session().scryfall.collection([{"name": n} for n in names])
        self.assertEqual(bodies, [75, 75, 8])                # 158 misses; the 2 cached cards aren't asked for
        self.assertEqual((len([c for c in cards if c]), miss, un), (160, [], []))

    def test_search_404_is_empty_and_cached(self):
        s = self.session()
        with mock.patch.object(h.urllib.request, "urlopen", side_effect=[err(404)]):
            self.assertEqual(s.scryfall.search("t:goblin is:nothing"), [])


class CardTypes(unittest.TestCase):
    """One classifier for deck_check stats and pages: layout decides double-faced vs split handling."""

    def test_layout_cases(self):
        from edhcore.types import card_types
        split = {"name": "Commit // Memory", "layout": "split", "type_line": "Instant // Sorcery",
                 "card_faces": [{"type_line": "Instant"}, {"type_line": "Sorcery"}]}
        azcanta = {"name": "Search for Azcanta // Azcanta, the Sunken Ruin", "layout": "transform",
                   "type_line": "Legendary Enchantment // Legendary Land",
                   "card_faces": [{"type_line": "Legendary Enchantment"}, {"type_line": "Legendary Land"}]}
        mdfc = {"name": "Sink into Stupor // Soporific Springs", "layout": "modal_dfc", "type_line": "Instant // Land",
                "card_faces": [{"type_line": "Instant"}, {"type_line": "Land"}]}
        self.assertEqual((card_types(split)["type_group"], card_types(split)["types"]), ("Instant", ["Instant", "Sorcery"]))
        self.assertEqual((card_types(azcanta)["type_group"], card_types(azcanta)["mdfc_land"]), ("Enchantment", False))
        self.assertEqual((card_types(mdfc)["type_group"], card_types(mdfc)["mdfc_land"]), ("Instant", True))


class CacheSafety(unittest.TestCase):
    """A corrupt cache is rebuilt, but recovery never deletes anything in a project, workspace or repo."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_corrupt_cache_rebuilt(self):
        d = os.path.join(self.tmp, "cache")
        os.makedirs(d)
        open(os.path.join(d, "cache.sqlite"), "wb").write(b"not a database" * 100)
        open(os.path.join(d, "keep.txt"), "w").write("other file")
        c = Cache(path=os.path.join(d, "cache.sqlite"))
        self.assertIn("rebuilt", c.note)
        c.put("k", "t", {"v": 1})
        self.assertEqual(c.get("k")[0], {"v": 1})
        self.assertTrue(os.path.exists(os.path.join(d, "keep.txt")))

    def test_cache_inside_a_project_is_never_wiped(self):
        proj = os.path.join(self.tmp, "EDHCompanion", "projects", "azula")
        d = os.path.join(proj, "cache")
        os.makedirs(d)
        open(os.path.join(proj, "PROJECT.md"), "w").write("# Azula\n")
        bad = os.path.join(d, "cache.sqlite")
        open(bad, "wb").write(b"garbage")
        c = Cache(path=bad)
        self.assertIsNone(c.db)
        self.assertIn("cache off", c.note)
        self.assertTrue(os.path.exists(bad) and os.path.exists(os.path.join(proj, "PROJECT.md")))
        self.assertEqual(c.reserve("b", 1.0), 0.0)           # still works, in memory

    def test_safe_dir_rules(self):
        self.assertFalse(cache_mod.safe_dir(os.path.expanduser("~")))
        self.assertFalse(cache_mod.safe_dir(ROOT))           # the repo (.git)
        self.assertTrue(cache_mod.safe_dir(os.path.join(self.tmp, "x")))


WORKER = r"""
import json, sys, time
sys.path.insert(0, sys.argv[1])
from edhcore import http as h
from edhcore.cache import Cache
h.PACE.insert(0, ("127.0.0.1", "stub", float(sys.argv[4])))
c = h.Client(Cache(path=sys.argv[2]))
for i in range(int(sys.argv[5])):
    c.get_json(sys.argv[3] + f"/x?i={i}")
"""


class Stub(http.server.BaseHTTPRequestHandler):
    hits, plan = [], []

    def do_GET(self):
        Stub.hits.append(time.time())
        code, headers = Stub.plan.pop(0) if Stub.plan else (200, {})
        self.send_response(code)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b'{"ok": 1}')

    def log_message(self, *a):
        pass


class CrossProcess(unittest.TestCase):
    """Real concurrent processes share one rate limit through the cache DB (the parallel-worker case)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        Stub.hits, Stub.plan = [], []
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        self.script = os.path.join(self.tmp, "worker.py")
        open(self.script, "w").write(WORKER)
        self.db = os.path.join(self.tmp, "c", "cache.sqlite")
        Cache(path=self.db)  # create the schema before the race

    def tearDown(self):
        self.srv.shutdown()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_workers(self, n, interval, each):
        ps = [subprocess.Popen([sys.executable, self.script, SCRIPTS, self.db, self.url, str(interval), str(each)]) for _ in range(n)]
        for p in ps:
            self.assertEqual(p.wait(timeout=60), 0)

    def test_pacing_holds_across_processes(self):
        self.run_workers(3, 0.3, 3)
        t = sorted(Stub.hits)
        self.assertEqual(len(t), 9)
        gaps = [b - a for a, b in zip(t, t[1:])]
        # 3 processes share one 0.3 s slot: 9 requests span >= 8 slots (unpaced they'd all land within ~0.1 s);
        # single gaps vary by network/process jitter, so only gross overlap is checked per gap.
        self.assertGreaterEqual(t[-1] - t[0], 8 * 0.3 * 0.9, gaps)
        self.assertGreaterEqual(min(gaps), 0.1, gaps)

    def test_a_429_makes_every_process_wait(self):
        Stub.plan = [(429, {"Retry-After": "2"})]
        self.run_workers(2, 0.05, 2)
        t = sorted(Stub.hits)
        self.assertEqual(len(t), 5)                          # 4 requests + 1 retry
        # only a request whose slot was already reserved before the 429 arrived may go during the 2 s hold
        self.assertLessEqual(sum(1 for x in t[1:] if x - t[0] < 1.8), 1, [round(x - t[0], 2) for x in t])

    def test_concurrent_failures_all_count(self):
        """Review #4: every process's exhausted call increments the shared breaker (none lost to a read-then-write)."""
        Stub.plan = [(502, {})] * 20
        script = os.path.join(self.tmp, "fail.py")
        open(script, "w").write(FAIL_WORKER)
        t0 = str(time.time() + 1.5)
        ps = [subprocess.Popen([sys.executable, script, SCRIPTS, self.db, self.url, t0]) for _ in range(6)]
        for p in ps:
            self.assertEqual(p.wait(timeout=60), 0)
        st = Cache(path=self.db).breaker(f"127.0.0.1:{self.srv.server_address[1]}/x")
        self.assertGreaterEqual(len(Stub.hits), 3)
        self.assertEqual(st["fails"], len(Stub.hits))      # one count per call that reached the server
        self.assertGreater(st["open_until"], time.time())


FAIL_WORKER = r"""
import sys, time
sys.path.insert(0, sys.argv[1])
from edhcore import http as h
from edhcore.cache import Cache
c = h.Client(Cache(path=sys.argv[2]), tries=1)
while time.time() < float(sys.argv[4]):
    pass
try:
    c.get_json(sys.argv[3] + "/x")
except h.Unavailable:
    pass
"""


class ReviewFixes(unittest.TestCase):
    """Regression tests for the confirmed review findings on the data core."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.clock = Clock()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def session(self):
        cache = Cache(path=os.path.join(self.tmp, "c", "cache.sqlite"), now=self.clock.now)
        c = h.Client(cache, pol.Policy(config=os.path.join(self.tmp, "none")), sleep=self.clock.sleep, now=self.clock.now, jitter=lambda: 0)
        return Session(cache=cache, client=c, policy=c.policy, now=self.clock.now)

    # 2: collection pairs results by position; not_found says which requests failed
    def test_collection_punctuation_and_unicode_names_found(self):
        asked = ["Lim-Dul's Vault", "Kozilek’s Return", "Nope Not A Card", "Jace Vryn's Prodigy", "Fire"]
        res = {"not_found": [{"name": "Nope Not A Card"}],
               "data": [card("Lim-Dûl's Vault", "a"), card("Kozilek's Return", "b"), card("Jace, Vryn's Prodigy // Jace, Telepath Unbound", "c"),
                        dict(card("Fire // Ice", "d"), card_faces=[{"name": "Fire"}, {"name": "Ice"}])]}
        s = self.session()
        with mock.patch.object(h.urllib.request, "urlopen", side_effect=[Ok(res)]):
            cards, miss, un = s.scryfall.collection([{"name": n} for n in asked])
        self.assertEqual(([c and c["id"] for c in cards], miss, un), (["a", "b", None, "c", "d"], [2], []))
        with mock.patch.object(h.urllib.request, "urlopen") as m:   # cached under the requested name
            cards, miss, _ = self.session().scryfall.collection([{"name": "Kozilek’s Return"}])
            self.assertEqual((cards[0]["id"], m.call_count), ("b", 0))

    def test_collection_counts_off_falls_back_to_normalised_names(self):
        res = {"data": [card("Kozilek's Return", "b")]}               # no not_found, one card short: match by name
        with mock.patch.object(h.urllib.request, "urlopen", side_effect=[Ok(res)]):
            cards, miss, _ = self.session().scryfall.collection([{"name": "Ghost"}, {"name": "kozilek’s return"}])
        self.assertEqual((cards[0], cards[1]["id"], miss), (None, "b", [0]))

    # 3: provider exclusions in every common YAML and PROJECT.md form
    def test_policy_yaml_forms_with_and_without_pyyaml(self):
        forms = ["research:\n  excluded:\n  - Scryfall\n", "research:\n  excluded:\n    # direct\n    - Scryfall\n",
                 "research:\n  excluded: [Scryfall]\n", "research:\n  excluded: [\n    Scryfall]\n",
                 "research:\n  approval: x\n  excluded:\n  - Scryfall\n", "research:\r\n  excluded:\r\n    - Scryfall\r\n",
                 "research:\n    approval: x\n    excluded:\n        - Scryfall  # no\n"]
        p = os.path.join(self.tmp, "config.yaml")
        for no_yaml in (False, True):
            with mock.patch.dict(sys.modules, {"yaml": None} if no_yaml else {}):
                for text in forms:
                    open(p, "w", newline="").write(text)
                    self.assertIsNotNone(pol.Policy(config=p).blocked("api.scryfall.com"), (no_yaml, text))
                open(p, "w").write("research:\n  excluded: []\n  prefer: [Scryfall]\n")
                self.assertIsNone(pol.Policy(config=p).blocked("api.scryfall.com"), no_yaml)

    def test_policy_project_phrasings(self):
        proj = os.path.join(self.tmp, "p")
        os.makedirs(proj)
        none = os.path.join(self.tmp, "none")
        cases = {"- Excluded: none": None, "- Avoid Scryfall": "s", "- Do not use: Scryfall": "s", "- Sources to skip: Scryfall": "s",
                 "Excluded providers:\n- Scryfall\n- Spellbook": "sb", "- Excluded providers:\n  - Commander Spellbook\n- Approved: Scryfall MCP": "b",
                 "- Never use direct APIs": "sb", "- **Excluded:** Scryfall": "s", "- Approved: Scryfall MCP": None}
        for body, want in cases.items():
            open(os.path.join(proj, "PROJECT.md"), "w").write("# P\n\n## Research preferences\n" + body + "\n")
            p = pol.Policy(project=proj, config=none)
            got = ("s" if p.blocked("api.scryfall.com") else "") + ("b" if p.blocked("backend.commanderspellbook.com") else "")
            self.assertEqual(got or None, want, body)

    # 5: a 4xx answer to the half-open probe closes the breaker
    def test_probe_answered_with_404_closes_breaker(self):
        c = client(self.clock)
        for _ in range(3):
            with mock.patch.object(h.urllib.request, "urlopen", side_effect=[err(502)] * 3):
                with self.assertRaises(h.Unavailable):
                    c.request(SF + "/cards/search?q=a")
        self.clock.t += 61
        with mock.patch.object(h.urllib.request, "urlopen", side_effect=[err(404)]):
            with self.assertRaises(h.RequestError):
                c.request(SF + "/cards/search?q=nomatch")
        self.assertEqual(c.cache.breaker("api.scryfall.com/cards/search"), Cache.CLOSED)
        with mock.patch.object(h.urllib.request, "urlopen", side_effect=[Ok({"data": []})]) as m:
            c.request(SF + "/cards/search?q=b")
            self.assertEqual(m.call_count, 1)

    # 10: any operational error turns the cache off for the run instead of crashing the script
    def test_cache_operational_error_turns_cache_off(self):
        import sqlite3

        class Broken:
            in_transaction = False

            def execute(self, *a):
                raise sqlite3.OperationalError("disk I/O error")

            def close(self):
                pass

        c = Cache(path=os.path.join(self.tmp, "c", "cache.sqlite"), now=self.clock.now)
        c.db = Broken()
        c.put("k", "card", {"a": 1})
        self.assertIsNone(c.get("k"))
        self.assertIn("cache off: disk I/O error", c.note)
        self.assertEqual((c.reserve("b", 1.0), c.reserve("b", 1.0)), (0.0, 1.0))   # pacing continues in memory
        self.assertEqual(c.update_breaker("e", lambda st: dict(st, fails=st["fails"] + 1))["fails"], 1)

    def test_read_only_cache_is_not_wiped(self):
        import stat
        p = os.path.join(self.tmp, "c", "cache.sqlite")
        c = Cache(path=p)
        c.put("k", "card", {"a": 1})
        c._close()
        os.chmod(p, stat.S_IREAD)
        try:
            c = Cache(path=p)
            c.put("k2", "card", {"b": 2})                   # no exception
            c.reserve("x", 0.1)
            self.assertTrue(os.path.exists(p))
            c._close()
        finally:
            os.chmod(p, stat.S_IWRITE | stat.S_IREAD)

    # data block: nothing looked up = no verification claim
    def test_data_block_without_lookups_has_no_verification(self):
        s = self.session()
        self.assertIsNone(s.data_block()["verification"])
        with mock.patch.object(h.urllib.request, "urlopen", side_effect=[Ok({"data": [card("Sol Ring", "x")]})]):
            s.scryfall.collection([{"name": "Sol Ring"}])
        self.assertEqual(s.data_block()["verification"], "fresh")


if __name__ == "__main__":
    unittest.main()
