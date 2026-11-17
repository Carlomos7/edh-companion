#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi", "truststore"]
# ///
"""The player's card collection -> collection.json, every row resolved to a Scryfall card (oracle_id + printing).

  collection.py FILE [FILE ...] [--out <workspace>/collection.json] [--fresh|--offline]

Reads CSV exports from ManaBox, Moxfield, Deckbox, Archidekt (and most others) by their header row, or a plain text
list ("1 Sol Ring (C21) 263 *F*"). Rows with a Scryfall ID or set + collector number keep that exact printing;
name-only rows match the card in any printing. Same printing and finish rows are added up. Rows that can't be
resolved go to `unmatched` with the row number and why; nothing is dropped silently. One batched lookup (75 per
request) through the shared cache. The file is the player's own data: keep it in the workspace, never publish it.
"""
import argparse, csv, io, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edhcore.decklist import parse_text  # noqa: E402
from edhcore.session import Session  # noqa: E402

COLUMNS = {  # lowercase header -> field
    "qty": ("count", "quantity", "qty", "amount"),
    "name": ("name", "card name", "card"),
    "set": ("set code", "edition code", "set", "edition", "set_code"),
    "cn": ("collector number", "card number", "collector_number", "number", "cn"),
    "finish": ("finish", "foil", "printing", "foil/etched"),
    "id": ("scryfall id", "scryfall_id", "scryfallid"),
}


def finish_of(v):
    v = (v or "").strip().lower()
    return "etched" if "etched" in v else "foil" if v in ("foil", "true", "yes", "1", "y") else "nonfoil"


def parse(text):
    """[{row, qty, name, set, cn, finish, id}], [{row, text, reason}] from CSV (by header) or a text list."""
    first = text.lstrip("﻿").splitlines()[0] if text.strip() else ""
    head = [h.strip().lower() for h in next(csv.reader([first]))] if "," in first else []
    if not any(h in COLUMNS["name"] for h in head):
        cards, cmd = parse_text(text)
        return [dict(e, row=i, id=None) for i, e in enumerate(cmd + cards, 1)], []
    col = {f: next((h for h in head if h in names), None) for f, names in COLUMNS.items()}
    rows, bad = [], []
    for i, r in enumerate(csv.DictReader(io.StringIO(text.lstrip("﻿")), fieldnames=head), 0):
        if i == 0:
            continue  # the header row
        get = lambda f: (r.get(col[f]) or "").strip() if col[f] else ""
        name = get("name")
        if not name:
            bad.append({"row": i + 1, "text": ",".join(v or "" for v in r.values() if isinstance(v, str))[:80], "reason": "no card name"})
            continue
        qty = get("qty") or "1"
        if not qty.isdigit():
            bad.append({"row": i + 1, "text": name, "reason": f"quantity {qty!r} is not a number"})
            continue
        st = get("set").lower()
        rows.append({"row": i + 1, "qty": int(qty), "name": name, "set": st if 2 <= len(st) <= 6 else None,  # Deckbox's Edition is a full set name
                     "cn": get("cn") or None, "finish": finish_of(get("finish")), "id": get("id") or None})
    return rows, bad


def ident(r):
    if r["id"]:
        return {"id": r["id"]}
    if r["set"] and r["cn"]:
        return {"set": r["set"], "collector_number": r["cn"]}
    return {"name": r["name"].split(" // ")[0]}


def resolve(rows, s):
    """(cards, unmatched): rows matched to Scryfall cards, added up per printing and finish."""
    found, _, unavail = s.scryfall.collection([ident(r) for r in rows], need="oracle") if rows else ([], [], [])
    cards, unmatched = {}, []
    for i, r in enumerate(rows):
        c = found[i]
        if c is None:
            unmatched.append({"row": r["row"], "text": r["name"], "reason": "card data unavailable (try again online)" if i in unavail else "not found on Scryfall"})
            continue
        exact = bool(r["id"] or (r["set"] and r["cn"]))
        key = (c["id"] if exact else c["oracle_id"], r["finish"])
        e = cards.setdefault(key, {"name": c["name"], "oracle_id": c.get("oracle_id"), "printing_id": c["id"] if exact else None,
                                   "set": c.get("set") if exact else None, "collector_number": c.get("collector_number") if exact else None,
                                   "finish": r["finish"], "qty": 0})
        e["qty"] += r["qty"]
    return sorted(cards.values(), key=lambda e: (e["name"], e["set"] or "")), unmatched


def owned(doc):
    """{oracle_id: {"qty": n, "printings": {printing_id, ...}}} from a collection.json."""
    out = {}
    for c in (doc or {}).get("cards", []):
        o = out.setdefault(c["oracle_id"], {"qty": 0, "printings": set()})
        o["qty"] += c["qty"]
        if c.get("printing_id"):
            o["printings"].add(c["printing_id"])
    return out


def state(card, have):
    """owned | other_printing | missing for one deck card ({oracle_id, printing_id?}) against owned()."""
    o = have.get(card.get("oracle_id"))
    if not o:
        return "missing"
    if not card.get("printing_id") or card["printing_id"] in o["printings"] or not o["printings"]:
        return "owned"
    return "other_printing"


def build(files, s, today=None):
    rows, bad = [], []
    for f in files:
        with open(f, encoding="utf-8-sig") as h:
            r, b = parse(h.read())
        tag = os.path.basename(f)
        rows += [dict(x, row=f"{tag}:{x['row']}") for x in r]
        bad += [dict(x, row=f"{tag}:{x['row']}") for x in b]
    cards, unmatched = resolve(rows, s)
    return {"schema_version": "1.0", "generated": today or time.strftime("%Y-%m-%d"), "sources": [os.path.basename(f) for f in files],
            "data": s.data_block(), "counts": {"rows": len(rows) + len(bad), "cards": sum(c["qty"] for c in cards), "unique": len({c["oracle_id"] for c in cards}),
                                               "unmatched": len(bad) + len(unmatched)},
            "cards": cards, "unmatched": bad + unmatched}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default="collection.json")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fresh", action="store_true")
    g.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    doc = build(a.files, Session(fresh=a.fresh, offline=a.offline))
    with open(a.out + ".tmp", "w", encoding="utf-8") as h:
        json.dump(doc, h, ensure_ascii=False, indent=1)
    os.replace(a.out + ".tmp", a.out)
    n = doc["counts"]
    print(f"{n['cards']} cards ({n['unique']} unique) from {n['rows']} rows; {n['unmatched']} unmatched; data {doc['data']['verification'] or 'none looked up'}")
    for u in doc["unmatched"][:20]:
        print(f"unmatched {u['row']}: {u['text']}: {u['reason']}")
    if len(doc["unmatched"]) > 20:
        print(f"+{len(doc['unmatched']) - 20} more in {a.out}")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
