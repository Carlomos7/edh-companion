"""deck_check's HTTP path (now the shared edhcore client): 429 honours Retry-After (capped), 5xx and network errors
back off and are bounded, other 4xx fail at once; card lookups are batched and cached. Offline: urlopen is mocked
and sleeps are recorded, not slept. The Azula session's 429/502 failures are covered here and in test_core.py.

Run: uv run --with certifi python -m unittest discover -s tests/unit
"""
import importlib.util, io, json, os, socket, tempfile, unittest, urllib.error
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
spec = importlib.util.spec_from_file_location("deck_check", os.path.join(ROOT, "plugins", "edh-companion", "skills", "audit", "scripts", "deck_check.py"))
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)
from edhcore.cache import Cache  # noqa: E402  (deck_check put plugin/scripts on sys.path)
from edhcore.http import Client  # noqa: E402
from edhcore.session import Session  # noqa: E402


def err(code, retry_after=None):
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else {}
    return urllib.error.HTTPError("https://api.scryfall.com/x", code, "x", headers, io.BytesIO(b""))


class Ok:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return io.BytesIO(json.dumps(self.payload).encode())

    def __exit__(self, *a):
        return False


class Http(unittest.TestCase):
    def run_with(self, effects, tries=3):
        waits = []
        with mock.patch("urllib.request.urlopen", side_effect=effects):
            try:
                res = dc.http("https://api.scryfall.com/x", tries=tries, sleep=waits.append)
            except Exception as e:  # noqa: BLE001
                res = e
        return res, [round(w) for w in waits if w >= 0.5]  # ignore the 100 ms pacing gaps

    def test_429_then_ok_uses_retry_after(self):
        res, waits = self.run_with([err(429, retry_after=7), Ok({"ok": 1})])
        self.assertEqual(res, {"ok": 1})
        self.assertEqual(waits, [7])

    def test_429_without_header_waits_the_scryfall_lockout(self):
        res, waits = self.run_with([err(429), Ok({"ok": 1})])
        self.assertEqual(waits, [30])

    def test_wait_is_capped(self):
        res, waits = self.run_with([err(429, retry_after=900), Ok({"ok": 1})])
        self.assertEqual(waits, [dc.MAX_WAIT])

    def test_502_retries_are_bounded(self):
        res, waits = self.run_with([err(502), err(502), err(502)])
        self.assertIsInstance(res, dc.Unavailable)
        self.assertIsInstance(res, RuntimeError)
        self.assertIn("HTTP 502", str(res))
        self.assertEqual(len(waits), 2)                 # no wait after the last attempt
        self.assertEqual(waits, sorted(waits))          # backing off, not hammering

    def test_404_fails_at_once(self):
        res, waits = self.run_with([err(404)])
        self.assertIsInstance(res, dc.RequestError)
        self.assertEqual(res.code, 404)
        self.assertEqual(waits, [])

    def test_network_error_and_read_timeout_retry(self):
        res, waits = self.run_with([urllib.error.URLError("reset"), socket.timeout("read"), Ok({"ok": 1})])
        self.assertEqual(res, {"ok": 1})
        self.assertEqual(len(waits), 2)


class Batching(unittest.TestCase):
    def test_collection_batches_of_75_then_cache(self):
        names = [{"name": f"Card {i}"} for i in range(160)]
        calls = []

        def fake(req, *a, **k):
            ids = json.loads(req.data)["identifiers"]
            calls.append(len(ids))
            return Ok({"data": [{"id": f"id-{x['name']}", "name": x["name"], "set": "tst", "collector_number": "1"} for x in ids]})

        with tempfile.TemporaryDirectory() as d:
            cache = Cache(path=os.path.join(d, "cache.sqlite"))
            s = Session(cache=cache, client=Client(cache, sleep=lambda s: None))
            with mock.patch.object(dc, "_SESSION", s), mock.patch("urllib.request.urlopen", side_effect=fake):
                found, missing = dc.fetch(names)
                again, _ = dc.fetch(names)
            cache.db.close()
        self.assertEqual(calls, [75, 75, 10])            # 3 requests for 160 cards, not 160; the second lookup is cached
        self.assertEqual((len(found), len(again), missing), (160, 160, []))


if __name__ == "__main__":
    unittest.main()
