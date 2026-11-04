"""One network probe for every live test: skip them when Scryfall can't be reached (or EDHC_OFFLINE=1)."""
import functools, os, ssl, urllib.request


@functools.lru_cache(maxsize=None)
def online():
    if os.environ.get("EDHC_OFFLINE") == "1":
        return False
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = None
    try:
        req = urllib.request.Request("https://api.scryfall.com/sets/spm", headers={"User-Agent": "edh-companion-tests/1.0", "Accept": "application/json"})
        urllib.request.urlopen(req, timeout=10, context=ctx).close()
        return True
    except Exception:  # noqa: BLE001
        return False
