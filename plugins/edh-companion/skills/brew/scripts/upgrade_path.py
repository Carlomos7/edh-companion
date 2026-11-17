#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi", "truststore"]
# ///
"""Ordered upgrade steps for an existing deck: one add and one cut per step, best value per dollar first.

  upgrade_path.py <project> [--budget USD] [--steps 15] [--collection <workspace>/collection.json] [--out FILE]
                  [--fresh|--offline]

Value of a swap = role gain + synergy gain. Role gain: +1 when the add fills a role below its floor
(references/roles.json), -1 when the cut takes a role to below its floor. Synergy gain: the add's lift lower bound
minus the cut's (candidates.py score; 1 = no association, also for cards without numbers). Spells swap for spells,
lands for lands; among equal swaps the least-played card is cut (EDHREC inclusion lower bound; unknown counts as
50%, then Scryfall's overall EDHREC rank decides); Game Changers aren't added past the bracket's limit. Price: $0 when the collection has the card
(any printing), else its cheapest paper printing. Owned swaps come first ("swaps you can make today"); the rest are
ordered by value per dollar and recomputed after every step, so later steps see the deck the earlier ones made.
--budget is a true running total: a step that would pass it is skipped. Candidates must come from candidates.json
(run candidates.py first). With a strict or prefer theme, only on-theme or approved-exception candidates are added. Proposals only: apply what
the player accepts with plan.py.
"""
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "audit", "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))
import analytics  # noqa: E402
from edhcore.cards import front_type  # noqa: E402

ROLES_FILE = os.path.join(HERE, "..", "references", "roles.json")


def load(p):
    with open(p, encoding="utf-8") as h:
        return json.load(h)


def plan(deck, cands, cfg, bracket=None, owned=lambda c: False, price=lambda c: None, budget=None, steps=15):
    """deck: [{card, lift_lb}] (commanders excluded). cands: [{card, lift_lb, evidence}] not in the deck.
    Returns {"steps": [...], "total_usd", "skipped": [...]}."""
    roles_cfg = cfg["roles"]
    gc_max = cfg["game_changers"].get(str(bracket), 99) if bracket else 99
    deck, pool = list(deck), list(cands)
    roles = lambda e: set(analytics.roles(e["card"]))
    is_land = lambda e: "Land" in front_type(e["card"])
    out, total, skipped = [], 0.0, []

    def gain(a, c, counts):
        g, why = (a.get("lift_lb") or 1.0) - (c.get("lift_lb") or 1.0), []
        for r, lim in roles_cfg.items():
            if r in roles(a) and r not in roles(c) and counts[r] < lim["min"]:
                g += 1
                why.append(f"fills {r} ({counts[r]} of {lim['min']})")
            if r in roles(c) and r not in roles(a) and counts[r] <= lim["min"]:
                g -= 1
                why.append(f"drops {r} below {lim['min']}")
        if (a.get("lift_lb") or 1.0) != (c.get("lift_lb") or 1.0):
            why.append(f"lift {a.get('lift_lb') or 1.0:g} vs {c.get('lift_lb') or 1.0:g}")
        why.append(f"cut in {c['inclusion_lb']:g}% of decks" if c.get("inclusion_lb") is not None else
                   f"cut is #{c['card']['edhrec_rank']} on EDHREC overall" if c["card"].get("edhrec_rank") else "cut has no EDHREC numbers: check it")
        return g, why

    while len(out) < steps:
        counts = {r: sum(r in roles(e) for e in deck) for r in roles_cfg}
        gcs = sum(bool(e["card"].get("game_changer")) for e in deck)
        best = None
        for a in pool:
            own = owned(a["card"])
            cost = 0.0 if own else price(a["card"])
            if cost is None:
                continue
            if a["card"].get("game_changer") and gcs >= gc_max:
                continue
            for c in deck:
                if is_land(a) != is_land(c) or c.get("locked"):
                    continue
                g, why = gain(a, c, counts)
                if g <= 0:
                    continue
                played = c["inclusion_lb"] if c.get("inclusion_lb") is not None else 50.0  # unknown: assume mid-pack
                overall = c["card"].get("edhrec_rank") or 10 ** 6  # Scryfall's EDHREC rank across all decks: 1 = most played
                key = (own, g / max(cost, 0.01), g, -played, overall)  # owned first, value per dollar; cut the least-played card
                if best is None or key > best[0]:
                    best = (key, a, c, cost, g, why, own)
        if best is None:
            break
        _, a, c, cost, g, why, own = best
        if budget is not None and total + cost > budget + 1e-9:
            skipped.append({"add": a["card"]["name"], "price_usd": cost, "why": f"would pass the ${budget:g} budget"})
            pool.remove(a)
            continue
        total += cost
        deck[deck.index(c)] = a
        pool.remove(a)
        out.append({"step": len(out) + 1, "add": a["card"]["name"], "cut": c["card"]["name"], "owned": own,
                    "price_usd": round(cost, 2), "total_usd": round(total, 2), "value": round(g, 2), "why": "; ".join(why),
                    "evidence": a.get("evidence") or []})
    return {"steps": out, "total_usd": round(total, 2), "skipped": skipped,
            "swaps_today": sum(s["owned"] for s in out)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--budget", type=float)
    ap.add_argument("--steps", type=int, default=15)
    ap.add_argument("--collection", help="collection.json from collection.py (default: the workspace's, if any)")
    ap.add_argument("--out")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fresh", action="store_true")
    g.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    from edhcore.session import Session
    import collection as col
    import deck_check
    brew, cand = load(os.path.join(a.project, "brew.json")), load(os.path.join(a.project, "candidates.json"))
    cp = a.collection or os.path.join(a.project, "..", "..", "collection.json")  # <workspace>/projects/<name>
    have = col.owned(load(cp)) if os.path.exists(cp) else {}
    s = Session(fresh=a.fresh, offline=a.offline, project=a.project)
    deck_check._SESSION = s
    lift = {c["name"].lower(): (c.get("score") or {}).get("lift_lb") for c in cand["cards"]}
    played = {c["name"].lower(): (c.get("score") or {}).get("inclusion_lb", (c.get("edhrec") or {}).get("inclusion_pct")) for c in cand["cards"]}
    in_deck = {d["name"].lower() for d in brew["deck"]}
    themed = ((brew.get("theme_policy") or {}).get("mode")) in ("strict", "prefer")  # a theme deck only adds on-theme cards
    adds = [c for c in cand["cards"] if c["verdict"] == "eligible" and c["name"].lower() not in in_deck
            and (not themed or c["theme"]["fit"] in ("on_theme", "exception"))]
    names = [d["name"] for d in brew["deck"] if "basic" not in (d.get("role") or "").lower()] + [c["name"] for c in adds]
    found, _, _ = s.scryfall.collection([{"name": n.split(" // ")[0]} for n in names])
    nd = len(names) - len(adds)
    deck = [{"card": found[i], "lift_lb": lift.get(names[i].lower()), "inclusion_lb": played.get(names[i].lower())} for i in range(nd) if found[i] and "Basic" not in found[i].get("type_line", "")]
    pool = [{"card": found[nd + i], "lift_lb": (c.get("score") or {}).get("lift_lb"), "evidence": c["evidence"]} for i, c in enumerate(adds) if found[nd + i]]
    prices = deck_check.cheapest([p["card"]["name"] for p in pool])
    doc = plan(deck, pool, load(ROLES_FILE), bracket=(brew.get("target_bracket") or {}).get("bracket"),
               owned=lambda c: col.state({"oracle_id": c.get("oracle_id")}, have) != "missing",
               price=lambda c: (prices.get(c["name"]) or {}).get("usd"), budget=a.budget, steps=a.steps)
    doc = {"schema_version": "1.0", "generated": time.strftime("%Y-%m-%d"), "deck_version": brew.get("version"), "budget_usd": a.budget,
           "collection": os.path.basename(cp) if have else None, "prices": "cheapest paper printing, Scryfall daily prices", "data": s.data_block(), **doc}
    out = a.out or os.path.join(a.project, "upgrade_path.json")
    with open(out + ".tmp", "w", encoding="utf-8") as h:
        json.dump(doc, h, ensure_ascii=False, indent=1)
    os.replace(out + ".tmp", out)
    print(f"{len(doc['steps'])} swaps, about ${doc['total_usd']:.2f}" + (f" of ${a.budget:g}" if a.budget is not None else "")
          + f"; {doc['swaps_today']} you can make today ($0, owned); prices as of {doc['data'].get('as_of')}")
    for st in doc["steps"]:
        print(f"{st['step']}. +{st['add']} -{st['cut']}  {'owned' if st['owned'] else '$%.2f' % st['price_usd']} (total ${st['total_usd']:.2f}): {st['why']}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
