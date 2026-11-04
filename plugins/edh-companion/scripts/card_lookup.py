#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi"]
# ///
"""Compact, cached Scryfall lookups for research and brewing: one line per card instead of raw JSON.

  card_lookup.py names "Sol Ring" "Arcane Signet" ...   [--file names.txt] [--json OUT] [--fresh|--offline]
  card_lookup.py search 'QUERY' [--unique cards|prints|art] [--limit 40] [--json OUT] [--fresh|--offline]

Line format: name | mana cost | type | color identity | Commander legality (+ GC) | USD. Full card data goes to --json
only. Uses the shared cache and rate limits (edhcore), so repeating a lookup costs no request. Use this instead of
curl or ad-hoc Python against Scryfall. Respects excluded providers in the player's research preferences.
Exit 0 ok, 1 some names not found, 2 data unavailable (network or excluded provider) for some cards.
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edhcore.cards import brief  # noqa: E402
from edhcore.http import Unavailable, RequestError  # noqa: E402
from edhcore.session import Session  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["names", "search"])
    ap.add_argument("terms", nargs="*")
    ap.add_argument("--file")
    ap.add_argument("--unique", default="cards", choices=["cards", "prints", "art"])
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--json", metavar="OUT")
    ap.add_argument("--project", help="project folder (its research preferences are respected)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fresh", action="store_true", help="ignore cached data (final checks)")
    g.add_argument("--offline", action="store_true", help="cache only, no network")
    a = ap.parse_args()
    s = Session(fresh=a.fresh, offline=a.offline, project=a.project)
    code, cards = 0, []
    if a.mode == "names":
        names = list(a.terms) + ([x.strip() for x in open(a.file, encoding="utf-8") if x.strip()] if a.file else [])
        found, missing, unavail = s.scryfall.collection([{"name": n.split(" // ")[0]} for n in names])
        cards = [c for c in found if c]
        for c in cards:
            print(brief(c))
        if missing:
            print("NOT FOUND: " + "; ".join(names[i] for i in missing))
            code = 1
        if unavail:
            print("UNAVAILABLE: " + "; ".join(names[i] for i in unavail))
            code = 2
    else:
        q = " ".join(a.terms)
        try:
            cards = s.scryfall.search(q, unique=a.unique, limit=a.limit)
        except (Unavailable, RequestError) as e:
            print(f"UNAVAILABLE: {e}")
            code = 2
        for c in cards:
            print(brief(c))
        print(f"{len(cards)} card(s){' (limit reached)' if len(cards) >= a.limit else ''}")
    d = s.data_block()
    print(f"data: {d['verification']}" + (f", as of {d['as_of']}" if d["as_of"] else "") + (f"; {'; '.join(d['endpoints_unavailable'])}" if d["endpoints_unavailable"] else ""))
    if a.json:
        json.dump({"data": d, "cards": cards}, open(a.json, "w", encoding="utf-8"), ensure_ascii=False)
    sys.exit(code)


if __name__ == "__main__":
    main()
