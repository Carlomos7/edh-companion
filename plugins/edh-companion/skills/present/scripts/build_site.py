#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "certifi", "truststore"]
# ///
"""Validate site-data.json, pack images into WebP atlases, and render the fixed template into a site folder.

  build_site.py PROJECT/reports/page-data.json [--out DIR] [--separate-data] [--no-images] [--raw-cache DIR]

Output (default: the data file's folder): index.html (+ img/atlas_*.webp, + site-data.json with --separate-data or
when data > 3 MB). Publish index.html as an artifact with `supporting_files` as supporting files, or open it locally.
Exit 1 on schema errors or size-limit breaches.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "template")  # index.html + page.css + page.js; --template swaps the folder
SLOTS_IN_INDEX = ("__TITLE__", "/*__CSS__*/", "/*__JS__*/", "/*__DATA__*/")
LIMITS = {"page_mb": 16, "file_mb": 15, "files": 511, "total_mb": 256}
THREE_URL = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"
SLOTS = ["var(--s1)", "var(--s2)", "var(--s3)", "var(--s5)", "var(--s6)", "var(--s7)", "var(--s8)"]  # s4 = off-theme


def validate(D):
    errs, warns = [], []
    req = lambda o, keys, where: [errs.append(f"{where}: missing {k}") for k in keys if k not in o]
    req(D, ["title", "groups"], "site")
    if (D.get("page") or {}).get("images", "atlas") not in ("atlas", "cdn", "none"):
        errs.append(f"page images must be atlas, cdn or none, not {D['page'].get('images')!r}")
    if D.get("viewer", "simple") not in ("simple", "three"):
        errs.append(f"viewer must be simple or three, not {D.get('viewer')!r}")
    if not any(D.get(k) for k in ("groups", "rankings", "research")):
        errs.append("site has no decks, rankings or research")
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
            if (c.get("hero") or {}).get("art") and c["hero"]["art"] not in imgs:
                errs.append(f"{c['slug']}: hero image key {c['hero']['art']} not in images")
            ids = [d.get("id") or f"b{d.get('bracket')}" for d in c.get("decks", [])]
            if len(ids) != len(set(ids)):
                errs.append(f"{c['slug']}: duplicate build ids {ids}")
            for d, did in zip(c.get("decks", []), ids):
                w = f"{c['slug']}/{did}"
                if d.get("bracket") not in (1, 2, 3, 4, 5):
                    errs.append(f"{w}: bracket must be 1 to 5")
                n = sum(x["qty"] for x in d.get("cards", []))
                if n != 100:
                    errs.append(f"{w}: {n} cards, must be 100")
                state = (d.get("audit_view") or {}).get("verdict")
                if state not in ("not audited", "audit out of date", "pass", "pass_with_warnings", "fail", "incomplete"):
                    errs.append(f"{w}: audit state {state!r} is not a derived state")
                elif state != "pass":
                    warns.append(f"{w}: shown as {(d.get('audit_view') or {}).get('verdict_label') or state}")
                for x in [r for k in ("proposed", "applied", "rejected") for r in (d.get("recs_view") or {}).get(k, [])]:
                    if x.get("img") and x["img"] not in imgs:
                        errs.append(f"{w}: change {x.get('add')}: image key {x['img']} not in images")
                for x in d.get("cards", []):
                    if x.get("img") and x["img"] not in imgs:
                        errs.append(f"{w}: image key {x['img']} not in images")
                    if D.get("theme") and x.get("theme") and x["theme"] not in labels:
                        errs.append(f"{w}: {x['name']} has unknown theme label {x['theme']}")
    for r in D.get("rankings", []):
        req(r, ["id", "title", "method", "cards"], f"ranking {r.get('title')}")
        for c in r.get("cards", []):
            if c.get("img") and c["img"] not in imgs:
                errs.append(f"ranking {r['id']}: image key {c['img']} not in images")
    if not D.get("data_dates"):
        warns.append("no data_dates: the accuracy tab will be empty")
    return errs, warns


def hero_art(D, out_dir, mode, raw_dir=None):
    """Commander art crops for the hero: a WebP next to the atlases (atlas), Scryfall's URL (cdn, local pages only)
    or nothing. A crop that can't be fetched is dropped with a warning; the hero still shows the card."""
    warns = []
    for g in D.get("groups", []):
        for c in g.get("commanders", []):
            h = c.get("hero") or {}
            if not h.get("art_crop") or mode == "cdn":
                continue
            src = None
            if mode == "atlas":
                sys.path.insert(0, HERE)
                import palette
                src = palette.art_file(h["art_crop"], raw_dir)
            if not src:
                h["art_crop"] = None
                if mode == "atlas":
                    warns.append(f"{c['slug']}: commander art crop could not be downloaded; the hero shows the card only")
                continue
            from PIL import Image
            name = "img/" + os.path.splitext(os.path.basename(src))[0] + ".webp"
            os.makedirs(os.path.join(out_dir, "img"), exist_ok=True)
            with Image.open(src) as im:
                im.convert("RGB").save(os.path.join(out_dir, name), "WEBP", quality=80, method=6)
            h["art_crop"] = name
    return warns


ATTRIBUTION = ("Card data and images from Scryfall (scryfall.com); popularity numbers from EDHREC and combos from Commander "
               "Spellbook where cited. Magic: The Gathering card names and art are © Wizards of the Coast; unofficial Fan Content "
               "permitted under the Fan Content Policy, not approved or endorsed by Wizards.")


def extras(D, out):
    """llms.txt and one export-<project>-<build>.json per build next to the page; returns the head tags and file names."""
    esc = lambda t: re.sub(r"[<>&\"]", "", str(t or ""))
    dated = max((v for v in (D.get("data_dates") or {}).values() if v), default=None)
    lines, files = [f"# {D['title']}", "", f"> {D.get('subtitle') or 'Commander deck notes'}", "", "## Builds"], []
    for g in D.get("groups", []):
        for c in g.get("commanders", []):
            for d in c.get("decks", []):
                f = f"export-{d.get('project') or 'deck'}-{d['id']}.json".lower()
                verdict = (d.get("audit_view") or {}).get("verdict")
                doc = {"name": f"{c['name']}: {d['label']}", "commander": c["name"], "build": d["label"], "bracket": d.get("bracket"),
                       "version": d.get("version"), "dateModified": dated, "audit": verdict, "decklist": d.get("moxfield"),
                       "isBasedOn": ["https://scryfall.com", "https://edhrec.com", "https://commanderspellbook.com"], "attribution": ATTRIBUTION}
                with open(os.path.join(out, f), "w", encoding="utf-8") as h:
                    json.dump(doc, h, ensure_ascii=False, indent=1)
                files.append(f)
                lines.append(f"- [{c['name']}, {d['label']}]({f}): bracket {d.get('bracket')}, version {d.get('version')}, audit: {(verdict or 'none').replace('_', ' ')}")
    if os.path.exists(os.path.join(out, "summary.md")):
        lines += ["", "## Optional", "- [Summary](summary.md): the same report as Markdown"]
    lines += ["", ATTRIBUTION, ""]
    with open(os.path.join(out, "llms.txt"), "w", encoding="utf-8") as h:
        h.write("\n".join(lines))
    head = (f'<meta property="og:title" content="{esc(D["title"])}">\n<meta property="og:description" content="{esc(D.get("subtitle"))}">\n'
            '<meta property="og:type" content="website">\n<link rel="alternate" type="text/plain" href="llms.txt" title="Summary for tools">\n')
    return head, files + ["llms.txt"]


def assemble(folder, title, head=""):
    """One self-contained HTML page from a template folder: index.html with the placeholders in SLOTS_IN_INDEX, plus
    page.css and page.js. Any folder with the same files and placeholders can replace the default (--template).
    The page data goes in afterwards (/*__DATA__*/), so nothing in the CSS or JS can be taken for a placeholder."""
    read = lambda n: open(os.path.join(folder, n), encoding="utf-8").read()
    try:
        index, css, js = read("index.html"), read("page.css"), read("page.js")
    except FileNotFoundError as e:
        sys.exit(f"template {folder}: {os.path.basename(e.filename)} missing (a template is index.html, page.css and page.js)")
    missing = [p for p in SLOTS_IN_INDEX if p not in index]
    if missing:
        sys.exit(f"template {folder}: index.html lacks {', '.join(missing)}")
    index = index.replace("__TITLE__", re.sub(r"[<>&\"]", "", title)).replace("</title>\n", "</title>\n" + head, 1)
    index = index.replace("<style>/*__CSS__*/</style>", "<style>\n" + css + "</style>", 1).replace("/*__CSS__*/", css, 1)
    return index.replace("<script>/*__JS__*/</script>", "<script>\n" + js + "</script>", 1).replace("/*__JS__*/", js, 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("site"); ap.add_argument("--out", help="default: the folder holding the data file")
    ap.add_argument("--separate-data", action="store_true"); ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--raw-cache"); ap.add_argument("--width", type=int, default=488)
    ap.add_argument("--template", default=TEMPLATE, help="template folder (index.html, page.css, page.js); default: the plugin's")
    a = ap.parse_args()
    D = json.load(open(a.site, encoding="utf-8"))
    a.out = a.out or os.path.dirname(os.path.abspath(a.site))
    errs, warns = validate(D)
    if errs:
        print(json.dumps({"pass": False, "errors": errs[:50], "warnings": warns[:50]}, indent=1))
        sys.exit(1)
    os.makedirs(a.out, exist_ok=True)
    img_dir = os.path.join(a.out, "img")
    failed = []
    mode = "none" if a.no_images else (D.get("page") or {}).get("images", "atlas")
    if mode == "cdn":  # local page: images load from Scryfall's CDN (it allows any origin); no download
        D["image_urls"] = D.get("images", {})
        warns.append("card images load from Scryfall's servers: open this page locally; to publish it as an artifact, "
                      "rebuild with images downloaded (--images atlas) because artifact pages block outside images")
    if mode == "atlas" and D.get("images"):
        sys.path.insert(0, HERE)
        import atlas
        man, failed = atlas.build(D["images"], img_dir, raw_dir=a.raw_cache, width=a.width)
        D["atlas"] = man
        missing = [k for k in D["images"] if k not in man["cards"]]
        if missing:
            warns.append(f"{len(missing)} image(s) failed to download; those cards show blank art")
    warns += hero_art(D, a.out, mode, a.raw_cache)
    if D.get("theme"):
        for i, l in enumerate(D["theme"]["labels"]):
            l.setdefault("color", SLOTS[i % len(SLOTS)])
            if i >= 3:
                warns.append("more than 3 theme labels: colors beyond 3 are hard to tell apart, rely on pill text")
    D.pop("images", None)  # urls are build inputs, not page data
    data = json.dumps(D, ensure_ascii=False, separators=(",", ":"))
    # Windows paths (JSON-escaped or forward slashes) or a Unix home folder not inside a URL
    leak = re.search(r'[A-Za-z]:(?:\\\\|/)(?:Users|Documents and Settings)(?:\\\\|/)[^\\"/]+|(?<![\w.:/])/(?:Users|home)/[^/"]+/', data)
    if leak:  # a username or home folder would ship inside a shareable page
        print(json.dumps({"pass": False, "errors": [f"local path in page data: {leak.group(0)[:40]}... (remove it from the project files)"]}, indent=1))
        sys.exit(1)
    head, extra_files = extras(D, a.out)
    html = assemble(a.template, D["title"], head)
    if D.get("viewer") != "three" or not (D.get("page") or {}).get("show", {}).get("viewer", True):
        html = html.replace(THREE_URL, "")  # interactive/basic pages never load three.js
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
            files.append(os.path.relpath(p, a.out).replace(os.sep, "/"))
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
              "supporting_files": sorted(f for f in files if f.startswith("img/") or (separate and f == "site-data.json") or f in extra_files), "files": len(files),
              "total_mb": round(total / 1e6, 2), "data": "site-data.json" if separate else "inline",
              "image_failures": failed[:20], "errors": errs, "warnings": warns[:30]}
    print(json.dumps(report, indent=1))
    sys.exit(0 if not errs else 1)


if __name__ == "__main__":
    main()
