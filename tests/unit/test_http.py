"""deck_check.http: bounded retries for 429 / 5xx / network errors, Retry-After honoured and capped, other 4xx fail fast.
Offline: urlopen is mocked and sleeps are recorded, not slept.

Run: uv run --with certifi python -m unittest discover -s tests/unit
"""
import importlib.util, io, json, os, unittest, urllib.error
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
spec = importlib.util.spec_from_file_location("deck_check", os.path.join(ROOT, "plugins", "edh-companion", "skills", "audit", "scripts", "deck_check.py"))
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)


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
        with mock.patch.object(dc.urllib.request, "urlopen", side_effect=effects):
            try:
                return dc.http("https://api.scryfall.com/x", tries=tries, sleep=waits.append), waits
            except Exception as e:  # noqa: BLE001
                return e, waits

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
        self.assertIsInstance(res, RuntimeError)
        self.assertIn("HTTP 502", str(res))
        self.assertEqual(len(waits), 2)                 # no wait after the last attempt

    def test_404_fails_at_once(self):
        res, waits = self.run_with([err(404)])
        self.assertIsInstance(res, urllib.error.HTTPError)
        self.assertEqual(waits, [])

    def test_network_error_retries(self):
        res, waits = self.run_with([urllib.error.URLError("reset"), Ok({"ok": 1})])
        self.assertEqual(res, {"ok": 1})
        self.assertEqual(waits, [2])


class Batching(unittest.TestCase):
    def test_collection_batches_of_75(self):
        names = [{"name": f"Card {i}"} for i in range(160)]
        calls = []

        def fake(url, body=None, **k):
            calls.append(len(body["identifiers"]))
            return {"data": [{"name": x["name"]} for x in body["identifiers"]]}

        with mock.patch.object(dc, "http", side_effect=fake), mock.patch.object(dc.time, "sleep"):
            found, missing = dc.fetch(names)
        self.assertEqual(calls, [75, 75, 10])            # 3 requests for 160 cards, not 160
        self.assertEqual(len(found), 160)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
