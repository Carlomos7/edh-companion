#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""Pack card images for resolved decks into WebP atlases + atlas.json (needs Pillow).

Usage: atlas.py vault/data/*.json --out vault/site/img
Images come from *.scryfall.io (no rate limit). Card backs use card_back_id.
Keys in atlas.json: <printing id>_f (front), <printing id>_b (real back of DFC), back_<card_back_id>.
"""
import argparse, json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "mtgdb-atlas/1.0", "Accept": "*/*"}


def http_get(url):
    req = urllib.request.Request(url, headers=UA)
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(31)
                continue
            raise
    raise RuntimeError(url)


def cmd_images(a):
    """Legacy CLI: resolved deck JSON files -> atlases."""
    from PIL import Image
    import io
    jobs = {}
    for path in a.resolved:
        for x in json.load(open(path, encoding="utf-8"))["cards"]:
            if "printing" not in x:
                continue
            p = x["printing"]
            jobs[p["id"] + "_f"] = p["img_front"]
            if p["img_back"]:
                jobs[p["id"] + "_b"] = p["img_back"]
            elif p["back_id"]:
                b = p["back_id"]  # verify this URL pattern once before a big run
                jobs["back_" + b] = f"https://backs.scryfall.io/normal/{b[0]}/{b[1]}/{b}.jpg"
    jobs = {k: v for k, v in jobs.items() if v}
    raw_dir = os.path.join(a.out, "raw")
    os.makedirs(raw_dir, exist_ok=True)

    def fetch(item):
        k, url = item
        dst = os.path.join(raw_dir, k + ".jpg")
        if not os.path.exists(dst):
            try:
                open(dst, "wb").write(http_get(url))
            except Exception as e:  # keep going, report at the end
                return k, str(e)
        return k, None

    with ThreadPoolExecutor(8) as ex:
        failed = [(k, e) for k, e in ex.map(fetch, jobs.items()) if e]
    keys = sorted(k for k in jobs if os.path.exists(os.path.join(raw_dir, k + ".jpg")))
    W, H, per = a.width, int(a.width * 680 / 488), a.cols * a.rows
    manifest = {"cell": [W, H], "atlases": [], "cards": {}}
    for i in range(0, len(keys), per):
        sheet = Image.new("RGB", (W * a.cols, H * a.rows), (0, 0, 0))
        for j, k in enumerate(keys[i:i + per]):
            im = Image.open(os.path.join(raw_dir, k + ".jpg")).convert("RGB").resize((W, H), Image.LANCZOS)
            x, y = (j % a.cols) * W, (j // a.cols) * H
            sheet.paste(im, (x, y))
            manifest["cards"][k] = [len(manifest["atlases"]), x, y]
        name = f"atlas_{len(manifest['atlases']):03d}.webp"
        sheet.save(os.path.join(a.out, name), "WEBP", quality=a.quality, method=6)
        manifest["atlases"].append(name)
    json.dump(manifest, open(os.path.join(a.out, "atlas.json"), "w", encoding="utf-8"))
    sizes = sum(os.path.getsize(os.path.join(a.out, n)) for n in manifest["atlases"])
    print(json.dumps({"images": len(keys), "atlases": len(manifest["atlases"]), "total_mb": round(sizes / 1e6, 1),
                      "failed": failed}, indent=1))



def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("resolved", nargs="+"); ap.add_argument("--out", default="vault/site/img")
    ap.add_argument("--width", type=int, default=488); ap.add_argument("--cols", type=int, default=10)
    ap.add_argument("--rows", type=int, default=10); ap.add_argument("--quality", type=int, default=72)
    cmd_images(ap.parse_args())


if __name__ == "__main__":
    main()


def build(jobs, out_dir, raw_dir=None, width=488, cols=10, rows=10, quality=72):
    """jobs: {key: url}. Downloads (cached in raw_dir, never inside out_dir) and packs WebP atlases.
    Returns the atlas manifest dict and the list of failed keys."""
    from PIL import Image
    raw_dir = raw_dir or os.path.expanduser("~/.cache/mtg/img")
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
