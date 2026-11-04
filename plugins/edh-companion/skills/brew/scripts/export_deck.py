#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi"]  # deck_check.py (shared parser) imports it
# ///
"""Export a deck to import formats, keeping exact printings and finishes where the format supports them.

Usage:
  export_deck.py DECK [--format moxfield|archidekt|text|csv|all] [--out DIR]

DECK is a brew.json (preferred: carries set, collector number and finish per card) or a decklist text file.
Formats:
  moxfield   1 Sol Ring (C21) 263 *F*      commander first, then a blank line, then the deck
  archidekt  1x Sol Ring (c21) 263 *F* [Commander]   commander tagged so Archidekt sets it
  text       1 Sol Ring                    names only, for anything (and Arena-style tools); printings dropped
  csv        quantity,name,set,collector_number,finish,section,scryfall_id
--format all writes deck.moxfield.txt, deck.archidekt.txt, deck.txt and deck.csv into --out (default: stdout for one format).
"""
import argparse, csv, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIN = {"foil": " *F*", "etched": " *E*"}


def load(path):
    if path.endswith(".json"):
        d = json.load(open(path, encoding="utf-8"))
        cmd = [dict(c, qty=1, section="commander") for c in d["commander"]["cards"]]
        deck = [dict(c, section="deck") for c in d["deck"]]
        return cmd + deck
    sys.path.insert(0, os.path.join(HERE, "..", "..", "audit", "scripts"))
    from deck_check import parse_text  # same parser the checks use
    cards, cmd = parse_text(open(path, encoding="utf-8").read())
    rows = [dict(c, section="commander") for c in cmd] + [dict(c, section="deck") for c in cards]
    return [{"name": r["name"], "qty": r["qty"], "set": r.get("set"), "collector_number": r.get("cn"), "finish": r.get("finish"), "section": r["section"]} for r in rows]


def line(c, style):
    qty, name = c["qty"], c["name"]
    if style == "text":
        return f"{qty} {name}"
    pr = ""
    if c.get("set") and c.get("collector_number"):
        s = c["set"].upper() if style == "moxfield" else c["set"].lower()
        pr = f" ({s}) {c['collector_number']}"
    fin = FIN.get(c.get("finish") or "", "") if pr else ""
    if style == "moxfield":
        return f"{qty} {name}{pr}{fin}"
    return f"{qty}x {name}{pr}{fin}" + (" [Commander]" if c["section"] == "commander" else "")


def render(cards, fmt):
    cmd = [c for c in cards if c["section"] == "commander"]
    deck = [c for c in cards if c["section"] != "commander"]
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["quantity", "name", "set", "collector_number", "finish", "section", "scryfall_id"])
        for c in cmd + deck:
            w.writerow([c["qty"], c["name"], c.get("set") or "", c.get("collector_number") or "", c.get("finish") or "nonfoil", c["section"], c.get("printing_id") or ""])
        return buf.getvalue()
    style = {"moxfield": "moxfield", "archidekt": "archidekt", "text": "text"}[fmt]
    head = [line(c, style) for c in cmd]
    body = [line(c, style) for c in deck]
    return "\n".join(head + ([""] if head and fmt != "archidekt" else []) + body) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck")
    ap.add_argument("--format", default="moxfield", choices=["moxfield", "archidekt", "text", "csv", "all"])
    ap.add_argument("--out")
    a = ap.parse_args()
    cards = load(a.deck)
    if a.format != "all" and not a.out:
        sys.stdout.write(render(cards, a.format))
        return
    out = a.out or "."
    os.makedirs(out, exist_ok=True)
    names = {"moxfield": "deck.moxfield.txt", "archidekt": "deck.archidekt.txt", "text": "deck.txt", "csv": "deck.csv"}
    for fmt in (names if a.format == "all" else [a.format]):
        p = os.path.join(out, names[fmt])
        open(p, "w", encoding="utf-8", newline="\n").write(render(cards, fmt))
        print(p)
    missing = [c["name"] for c in cards if not (c.get("set") and c.get("collector_number")) and "basic" not in (c.get("role") or "")]
    if missing:
        print(f"note: {len(missing)} cards have no exact printing; importers will pick one (e.g. {', '.join(missing[:3])})", file=sys.stderr)


if __name__ == "__main__":
    main()
