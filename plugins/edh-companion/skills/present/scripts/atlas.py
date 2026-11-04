"""Pack card images into WebP atlases (needs Pillow). Imported by build_site.py; build() is the entry point.

Images come from *.scryfall.io (no rate limit). Keys: <printing id>_f (front), <printing id>_b (real back of a
double-faced card), back_<card_back_id> (standard card back). Downloads go through the shared client
(scripts/edhcore: retries on 429, 5xx and network errors) and are written atomically; an empty or undecodable cached
file counts as missing and is fetched again.
"""
import os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
from edhcore.http import Client  # noqa: E402
from edhcore.policy import Policy  # noqa: E402

_client = None


def http_get(url):
    global _client
    _client = _client or Client(policy=Policy())
    return _client.request(url, accept="*/*")


def valid(path):
    """A cached image is usable: non-empty and Pillow can decode all of it (verify() passes truncated JPEGs)."""
    from PIL import Image
    try:
        if os.path.getsize(path) == 0:
            return False
        with Image.open(path) as im:
            im.load()
        return True
    except Exception:  # noqa: BLE001  missing, truncated or not an image
        return False


def build(jobs, out_dir, raw_dir=None, width=488, cols=10, rows=10, quality=72):
    """jobs: {key: url}. Downloads (cached in raw_dir, never inside out_dir) and packs WebP atlases.
    Returns the atlas manifest dict and the list of failed keys."""
    from PIL import Image
    raw_dir = raw_dir or os.path.expanduser("~/.cache/edh-companion/img")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    def fetch(item):
        k, url = item
        dst = os.path.join(raw_dir, k + ".jpg")
        if valid(dst):
            return k, None
        tmp = f"{dst}.{os.getpid()}.tmp"
        try:
            if url.startswith("file://"):
                data = open(url[7:], "rb").read()
            else:
                data = http_get(url)
            with open(tmp, "wb") as h:
                h.write(data)
            if not valid(tmp):
                raise ValueError(f"not an image ({len(data)} bytes)")
            os.replace(tmp, dst)  # readers never see a half-written file
            return k, None
        except Exception as e:  # noqa: BLE001
            if os.path.exists(tmp):
                os.remove(tmp)
            return k, str(e)

    with ThreadPoolExecutor(8) as ex:
        failed = [(k, e) for k, e in ex.map(fetch, jobs.items()) if e]
    bad = {k for k, _ in failed}
    keys = sorted(k for k in jobs if k not in bad and os.path.exists(os.path.join(raw_dir, k + ".jpg")))
    W, H, per = width, int(width * 680 / 488), cols * rows
    man = {"cell": [W, H], "cols": cols, "rows": rows, "atlases": [], "cards": {}}
    for i in range(0, len(keys), per):
        sheet = Image.new("RGB", (W * cols, H * rows), (0, 0, 0))
        for j, k in enumerate(keys[i:i + per]):
            try:
                with Image.open(os.path.join(raw_dir, k + ".jpg")) as src:
                    im = src.convert("RGB").resize((W, H), Image.LANCZOS)
            except Exception as e:  # noqa: BLE001  one bad image leaves an empty cell, never aborts the build
                failed.append((k, str(e)))
                continue
            x, y = (j % cols) * W, (j // cols) * H
            sheet.paste(im, (x, y))
            man["cards"][k] = [len(man["atlases"]), x, y]
        name = f"atlas_{len(man['atlases']):03d}.webp"
        sheet.save(os.path.join(out_dir, name), "WEBP", quality=quality, method=6)
        man["atlases"].append(name)
    return man, failed
