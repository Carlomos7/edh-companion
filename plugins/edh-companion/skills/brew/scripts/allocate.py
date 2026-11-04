#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi"]
# ///
"""Divide a card pool (a Secret Lair, a box, a trade binder) between decks or players without handing out more
copies than exist.

Usage:
  allocate.py POOL --target NAME=DECK_OR_COMMANDER [--target ...] [--want NAME:CARD ...] [--json OUT]

POOL      a list of cards with quantities (any import format)
--target  NAME=path/to/decklist.txt   a deck that already lists the cards it needs
          NAME=Commander Name         a player or deck known only by its commander: fits = within color identity
--want    NAME:Card                   a stated wish ("Sam wants Doctor Strange"); wins over needs and fits

Priority per copy: stated wish > a deck that lists the card > a commander whose colors allow it.
When more targets want a card than there are copies at the same priority, it is NOT decided here:
it's listed under "choose" for the player(s). Nothing is assigned twice.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "audit", "scripts"))
import deck_check  # noqa: E402  (shared parser and Scryfall lookup)


def load_list(path):
    cards, cmd = deck_check.parse_text(open(path, encoding="utf-8").read())
    out = {}
    for c in cmd + cards:
        out[c["name"]] = out.get(c["name"], 0) + c["qty"]
    return out


def allocate(pool, needs, identities, card_colors, wants):
    """Pure allocation. pool {card: copies}; needs {target: {card: qty}}; identities {target: set(colors)} for
    commander-only targets; card_colors {card: set(colors)}; wants [(target, card)].
    Returns {"assigned": {target: {card: n}}, "choose": [...], "unused": {card: n}, "unmet": {target: [cards]}}."""
    left = dict(pool)
    assigned = {t: {} for t in set(needs) | set(identities)}
    choose = []

    def give(t, card, n=1):
        assigned.setdefault(t, {})[card] = assigned.get(t, {}).get(card, 0) + n
        left[card] -= n

    tiers = []
    for card in pool:
        tiers.append((card, [t for t, c in wants if c == card],
                      [t for t, deck in needs.items() if card in deck],
                      [t for t, ident in identities.items() if card in card_colors and card_colors[card] <= ident]))
    for card, wish, need, fit in tiers:
        for group, label in ((wish, "wanted"), (need, "listed in their deck"), (fit, "fits their commander's colors")):
            group = [t for t in dict.fromkeys(group) if assigned.get(t, {}).get(card, 0) == 0]
            if not group or left[card] <= 0:
                continue
            if len(group) <= left[card]:
                for t in group:
                    give(t, card)
            else:
                choose.append({"card": card, "copies": left[card], "candidates": group, "reason": label})
                left[card] = 0
            break
    unmet = {}
    for t, deck in needs.items():
        miss = [c for c in deck if c in pool and assigned.get(t, {}).get(c, 0) == 0 and not any(c == x["card"] and t in x["candidates"] for x in choose)]
        if miss:
            unmet[t] = miss
    return {"assigned": {t: v for t, v in assigned.items() if v}, "choose": choose,
            "unused": {c: n for c, n in left.items() if n > 0}, "unmet": unmet}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pool")
    ap.add_argument("--target", action="append", default=[], required=True)
    ap.add_argument("--want", action="append", default=[])
    ap.add_argument("--json")
    a = ap.parse_args()
    pool = load_list(a.pool)
    needs, commanders = {}, {}
    for t in a.target:
        name, _, ref = t.partition("=")
        if os.path.exists(ref):
            needs[name] = load_list(ref)
        else:
            commanders[name] = ref
    names = list(pool) + list(commanders.values())
    found, missing = deck_check.fetch([{"name": n} for n in names])
    if missing:
        print("not found on Scryfall: " + "; ".join(missing), file=sys.stderr)
    colors = {names[i]: set(c.get("color_identity", [])) for i, c in found.items()}
    for name, cmd in commanders.items():
        c = found.get(names.index(cmd))
        if c is None or not deck_check.can_be_commander(c):
            sys.exit(f"{name}: '{cmd}' isn't a legal commander or a decklist path")
    identities = {n: colors.get(cmd, set()) for n, cmd in commanders.items()}
    wants = [tuple(w.split(":", 1)) for w in a.want]
    res = allocate(pool, needs, identities, colors, wants)
    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), indent=1)
    for t, cards in res["assigned"].items():
        print(f"{t}: " + ", ".join(f"{n}x {c}" if n > 1 else c for c, n in cards.items()))
    for x in res["choose"]:
        print(f"CHOOSE: {x['card']} ({x['copies']} cop{'y' if x['copies'] == 1 else 'ies'}) - {', '.join(x['candidates'])} ({x['reason']})")
    if res["unused"]:
        print("fits no target: " + ", ".join(res["unused"]))
    for t, m in res["unmet"].items():
        print(f"{t} still needs from the pool: " + ", ".join(m))


if __name__ == "__main__":
    main()
