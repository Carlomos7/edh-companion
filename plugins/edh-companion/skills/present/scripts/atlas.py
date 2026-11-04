"""Pack card images into WebP atlases (needs Pillow). Imported by build_site.py; build() is the entry point.

Images come from *.scryfall.io (no rate limit). Keys: <printing id>_f (front), <printing id>_b (real back of a
double-faced card), back_<card_back_id> (standard card back).
"""
import os, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

try:  # certifi's CA bundle: Windows certificate stores can hold an outdated root that breaks newer Let's Encrypt chains
    import certifi, ssl
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = None

UA = {"User-Agent": "edh-companion-atlas/1.0", "Accept": "*/*"}


def http_get(url):
    req = urllib.request.Request(url, headers=UA)
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(31)
                continue
            raise
    raise RuntimeError(url)


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
        if os.path.exists(dst):
            return k, None
        try:
            if url.startswith("file://"):
                data = open(url[7:], "rb").read()
            else:
                data = http_get(url)
            open(dst, "wb").write(data)
            return k, None
        except Exception as e:
            return k, str(e)

    with ThreadPoolExecutor(8) as ex:
        failed = [(k, e) for k, e in ex.map(fetch, jobs.items()) if e]
    keys = sorted(k for k in jobs if os.path.exists(os.path.join(raw_dir, k + ".jpg")))
    W, H, per = width, int(width * 680 / 488), cols * rows
    man = {"cell": [W, H], "cols": cols, "rows": rows, "atlases": [], "cards": {}}
    for i in range(0, len(keys), per):
        sheet = Image.new("RGB", (W * cols, H * rows), (0, 0, 0))
        for j, k in enumerate(keys[i:i + per]):
            im = Image.open(os.path.join(raw_dir, k + ".jpg")).convert("RGB").resize((W, H), Image.LANCZOS)
            x, y = (j % cols) * W, (j // cols) * H
            sheet.paste(im, (x, y))
            man["cards"][k] = [len(man["atlases"]), x, y]
        name = f"atlas_{len(man['atlases']):03d}.webp"
        sheet.save(os.path.join(out_dir, name), "WEBP", quality=quality, method=6)
        man["atlases"].append(name)
    return man, failed
