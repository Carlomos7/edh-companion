#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""Validate site-data.json, pack images into WebP atlases, and render the fixed template into a site folder.

  build_site.py site-data.json --out site/ [--separate-data] [--no-images] [--raw-cache DIR]

Output: site/index.html (+ site/img/atlas_*.webp, + site/site-data.json with --separate-data or when data > 3 MB).
Publish site/index.html as an artifact with the other files as supporting files, or open it locally.
Exit 1 on schema errors or size-limit breaches.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "template.html")
LIMITS = {"page_mb": 16, "file_mb": 15, "files": 511, "total_mb": 256}
SLOTS = ["var(--s1)", "var(--s2)", "var(--s3)", "var(--s5)", "var(--s6)", "var(--s7)", "var(--s8)"]  # s4 = off-theme


def validate(D):
    errs, warns = [], []
    req = lambda o, keys, where: [errs.append(f"{where}: missing {k}") for k in keys if k not in o]
    req(D, ["title", "groups", "tiers"], "site")
    if not D.get("groups") and not D.get("tiers"):
        errs.append("site has no decks and no tier lists")
    imgs = D.get("images", {})
    labels = {l["label"] for l in (D.get("theme") or {}).get("labels", [])} | {"off-theme"}
    if json.dumps(D).find("data:image") >= 0:
        errs.append("base64 image data found: images must be atlas files, never embedded (fails the sharing review)")
    slugs = set()
    for g in D.get("groups", []):
        req(g, ["id", "title", "commanders"], f"group {g.get('title')}")
        for c in g.get("commanders", []):
            if c["slug"] in slugs:
                errs.append(f"duplicate commander slug {c['slug']}")
            slugs.add(c["slug"])
            for d in c.get("decks", []):
                w = f"{c['slug']}/b{d.get('bracket')}"
                if d.get("bracket") not in (1, 2, 3, 4, 5):
                    errs.append(f"{w}: bracket must be 1 to 5")
                n = sum(x["qty"] for x in d.get("cards", []))
                if n != 100:
                    errs.append(f"{w}: {n} cards, must be 100")
                if not d.get("checks", {}).get("validate"):
                    warns.append(f"{w}: deck did not pass mtgdb validate ({'; '.join(d.get('errors', [])[:3])})")
                for x in d.get("cards", []):
                    if x.get("img") and x["img"] not in imgs:
                        errs.append(f"{w}: image key {x['img']} not in images")
                    if D.get("theme") and x.get("theme") and x["theme"] not in labels:
                        errs.append(f"{w}: {x['name']} has unknown theme label {x['theme']}")
        decks = {f"{c['slug']}/b{d['bracket']}" for c in g.get("commanders", []) for d in c.get("decks", [])}
        for s in g.get("swaps", []):
            for f in s.get("fits", []):
                if f["deck"] not in decks:
                    errs.append(f"swap {s['card']} points at missing deck {f['deck']}")
    for t in D.get("tiers", []):
        req(t, ["id", "title", "cards"], f"tier {t.get('id')}")
        for c in t.get("cards", []):
            if c.get("pct") is None:
                errs.append(f"tier {t['id']}: {c['name']} has no pct")
    if not D.get("data_dates"):
        warns.append("no data_dates: the accuracy tab will be empty")
    return errs, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("site"); ap.add_argument("--out", default="site")
    ap.add_argument("--separate-data", action="store_true"); ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--raw-cache"); ap.add_argument("--width", type=int, default=488)
    a = ap.parse_args()
    D = json.load(open(a.site, encoding="utf-8"))
    errs, warns = validate(D)
    if errs:
        print(json.dumps({"pass": False, "errors": errs[:50], "warnings": warns[:50]}, indent=1))
        sys.exit(1)
    os.makedirs(a.out, exist_ok=True)
    img_dir = os.path.join(a.out, "img")
    failed = []
    if not a.no_images and D.get("images"):
        sys.path.insert(0, HERE)
        import atlas
        man, failed = atlas.build(D["images"], img_dir, raw_dir=a.raw_cache, width=a.width)
        D["atlas"] = man
        missing = [k for k in D["images"] if k not in man["cards"]]
        if missing:
            warns.append(f"{len(missing)} image(s) failed to download; those cards show blank art")
    if D.get("theme"):
        for i, l in enumerate(D["theme"]["labels"]):
            l.setdefault("color", SLOTS[i % len(SLOTS)])
            if i >= 3:
                warns.append("more than 3 theme labels: colors beyond 3 are hard to tell apart, rely on pill text")
    D.pop("themes_path", None)
    D.pop("images", None)  # urls are build inputs, not page data
    data = json.dumps(D, ensure_ascii=False, separators=(",", ":"))
    html = open(TEMPLATE, encoding="utf-8").read().replace("__TITLE__", re.sub(r"[<>&\"]", "", D["title"]))
    separate = a.separate_data or len(data) > 3_000_000
    if separate:
        open(os.path.join(a.out, "site-data.json"), "w", encoding="utf-8").write(data)
    else:
        html = html.replace("/*__DATA__*/", "window.SITE_DATA=" + data.replace("</", "<\\/") + ";")
    open(os.path.join(a.out, "index.html"), "w", encoding="utf-8").write(html)
    files, total, big = [], 0, []
    for root, _, fs in os.walk(a.out):
        for f in fs:
            p = os.path.join(root, f)
            sz = os.path.getsize(p)
            files.append(os.path.relpath(p, a.out))
            total += sz
            if sz > LIMITS["file_mb"] * 1e6:
                big.append(f"{f} is {sz / 1e6:.1f} MB")
    page = os.path.getsize(os.path.join(a.out, "index.html"))
    if page > LIMITS["page_mb"] * 1e6:
        errs.append(f"index.html is {page / 1e6:.1f} MB (limit {LIMITS['page_mb']}); rebuild with --separate-data")
    if len(files) > LIMITS["files"]:
        errs.append(f"{len(files)} files (limit {LIMITS['files']}); raise atlas cols/rows")
    if total > LIMITS["total_mb"] * 1e6:
        errs.append(f"{total / 1e6:.0f} MB total (limit {LIMITS['total_mb']}); lower --width or atlas quality")
    errs += big
    report = {"pass": not errs, "out": os.path.abspath(a.out), "page": "index.html",
              "supporting_files": sorted(f for f in files if f != "index.html"), "files": len(files),
              "total_mb": round(total / 1e6, 2), "data": "site-data.json" if separate else "inline",
              "image_failures": failed[:20], "errors": errs, "warnings": warns[:30]}
    print(json.dumps(report, indent=1))
    sys.exit(0 if not errs else 1)


if __name__ == "__main__":
    main()
