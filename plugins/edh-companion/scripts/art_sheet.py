#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi", "truststore", "pillow"]
# ///
"""Contact sheets for looking at many cards at once, only for the ones not checked yet.

  art_sheet.py <project> --footer [--status pending] [--per 40]
      the bottom strip of each pool card without footer evidence: read the © line, then record it with
      `pool.py footer <project> --marvel ID ... --not ID ...`
  art_sheet.py <project> [--status accepted] [--per 24]
      the art crop of each pool illustration with no art note (or a stale one): record what it shows with
      `pool.py art <project> ID --characters ...`

Sheets go to <project>/sources/sheets/ with an index (sheet → cell → set:number), each cell labelled with set:number.
Images come from cards.scryfall.io (no rate limit) and are not stored beyond the sheets.
"""
import argparse, io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edhcore.http import Client, RequestError, Unavailable  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

CDN = "https://cards.scryfall.io"


def image_url(sid, kind):
    # Scryfall's CDN path: /<kind>/front/<a>/<b>/<id>.jpg
    return f"{CDN}/{kind}/front/{sid[0]}/{sid[1]}/{sid}.jpg"


def todo(lock, notes, footer, status):
    rows, seen = [], set()
    for sid, e in lock["cards"].items():
        if status and e["status"] != status:
            continue
        if footer:
            if not any(x.split(":", 1)[0] in ("footer", "footer_absent") for x in e["evidence"]):
                rows.append((sid, e))
        else:
            ill = e.get("illustration_id")
            note = notes.get(ill) or {}
            if ill and ill not in seen and (not note or note.get("stale") or note.get("verified_by", "").startswith("scryfall-tagger")):
                seen.add(ill)
                rows.append((sid, e))
    return rows


def sheet(client, rows, footer, out, per):
    os.makedirs(out, exist_ok=True)
    index, cols = {}, 4 if footer else 6
    cw, ch = (488, 70) if footer else (240, 176)
    for n in range(0, len(rows), per):
        chunk = rows[n:n + per]
        img = Image.new("RGB", (cols * cw, ((len(chunk) + cols - 1) // cols) * (ch + 18)), "white")
        d = ImageDraw.Draw(img)
        name = f"{'footer' if footer else 'art'}-{n // per + 1:02d}.png"
        for i, (sid, e) in enumerate(chunk):
            x, y = (i % cols) * cw, (i // cols) * (ch + 18)
            tag = f"{e['set']}:{e['number']}"
            try:
                raw = client.request(image_url(sid, "normal" if footer else "art_crop"), accept="image/*")
                im = Image.open(io.BytesIO(raw)).convert("RGB")
                if footer:  # the copyright line sits in the bottom ~6% of a 488 x 680 card
                    im = im.crop((0, int(im.height * 0.9), im.width, im.height))
                im.thumbnail((cw, ch))
                img.paste(im, (x, y + 18))
            except (RequestError, Unavailable, OSError) as err:
                d.text((x + 4, y + 30), f"no image: {err}"[:60], fill="red")
            d.text((x + 4, y + 3), f"{i + 1}. {tag} {e['name']}"[:70], fill="black")
            index.setdefault(name, {})[i + 1] = tag
        img.save(os.path.join(out, name))
        print(f"{os.path.join(out, name)}: {len(chunk)} cards")
    with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as h:
        json.dump(index, h, indent=1)
    return index


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--footer", action="store_true")
    ap.add_argument("--status")
    ap.add_argument("--per", type=int)
    a = ap.parse_args()
    src = os.path.join(a.project, "sources")
    lock = json.load(open(os.path.join(src, "pool.lock.json"), encoding="utf-8"))
    notes = json.load(open(os.path.join(src, "art_notes.json"), encoding="utf-8")) if os.path.exists(os.path.join(src, "art_notes.json")) else {}
    rows = todo(lock, notes, a.footer, a.status if a.status else ("pending" if a.footer else "accepted"))
    if not rows:
        print("nothing to check")
        return
    sheet(Client(), rows, a.footer, os.path.join(src, "sheets"), a.per or (40 if a.footer else 24))


if __name__ == "__main__":
    main()
