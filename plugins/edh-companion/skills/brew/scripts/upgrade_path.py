#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi", "truststore"]
# ///
"""Ordered upgrade steps for an existing deck: one add and one cut per step, best value per dollar first.

  upgrade_path.py <project> [--budget USD] [--steps 15] [--collection <workspace>/collection.json] [--out FILE]
                  [--fresh|--offline]

Value of a swap = role gain + synergy gain. Role gain: +1 when the add fills a role below its floor
(brew.json role_targets, else references/roles.json), -1 when the cut takes a role to below its floor. Synergy gain: the add's lift lower bound
minus the cut's (candidates.py score; 1 = no association, also for cards without numbers). Spells swap for spells,
lands for lands; among equal swaps the least-played card is cut (EDHREC inclusion lower bound; unknown counts as
50%, then Scryfall's overall EDHREC rank decides); Game Changers aren't added past the bracket's limit. Price: $0 when the collection has the card
(any printing), else its cheapest paper printing. Owned swaps come first ("swaps you can make today"); the rest are
ordered by value per dollar and recomputed after every step, so later steps see the deck the earlier ones made.
Commander Spellbook combos: a piece of a combo the deck has is never cut, an add that completes one gains 1, and
2+ missing pieces are one package step (two-card combos aren't promoted at brackets 1-3). --budget is a true running total: a step that would pass it is skipped. Candidates must come from candidates.json
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


def plan(deck, cands, cfg, bracket=None, owned=lambda c: False, price=lambda c: None, budget=None, steps=15, combos=(), commanders=(),
         commander_gc=0, ident=()):
    """deck: [{card, lift_lb, inclusion_lb}] (commanders excluded). cands: [{card, lift_lb, evidence}] not in the deck.
    combos: [{cards, id, result}] from Commander Spellbook over the deck plus the candidates. A card in a combo the deck
    already has is never cut; an add that completes a combo gains 1; a combo missing 2+ candidates is one package step
    (bought together or not at all). Returns {"steps": [...], "total_usd", "skipped": [...], "swaps_today"}."""
    roles_cfg = cfg["roles"]
    gc_max = cfg["game_changers"].get(str(bracket), 99) if bracket else 99
    deck, pool = list(deck), list(cands)
    roles = lambda e: set(analytics.roles(e["card"]))
    is_land = lambda e: "Land" in front_type(e["card"])
    name = lambda e: e["card"]["name"].lower()
    cmd = {n.lower() for n in commanders}
    combos = [dict(x, pieces={p.lower() for p in x["cards"]}) for x in combos]
    out, total, skipped, blocked = [], 0.0, [], set()

    def gain(a, c, counts):
        # lift: the add's numbers against the cut's (a cut without numbers counts as 1, no association); an add without
        # numbers makes no lift claim, so a staple with lift under 1 is never cut for a card nobody has measured
        both = a.get("lift_lb") is not None
        g, why = ((a["lift_lb"] - (c.get("lift_lb") or 1.0)) if both else 0.0), []
        if is_land(a) and is_land(c) and ident:  # fixing: a land that makes more of the deck's colors than the one it replaces
            more = len(analytics.made_colors(a["card"], ident) & set(ident)) - len(analytics.made_colors(c["card"], ident) & set(ident))
            if more > 0:
                g += 0.5 * more
                why.append(f"makes {more} more of your colors")
        for r, lim in roles_cfg.items():
            if r in roles(a) and r not in roles(c) and counts[r] < lim["min"]:
                g += 1
                why.append(f"fills {r} ({counts[r]} of {lim['min']})")
            if r in roles(c) and r not in roles(a) and counts[r] <= lim["min"]:
                g -= 1
                why.append(f"drops {r} below {lim['min']}")
        if both and a["lift_lb"] != (c.get("lift_lb") or 1.0):
            why.append(f"lift {a.get('lift_lb') or 1.0:g} vs {c.get('lift_lb') or 1.0:g}")
        why.append(f"cut in {c['inclusion_lb']:g}% of decks" if c.get("inclusion_lb") is not None else
                   f"cut is #{c['card']['edhrec_rank']} on EDHREC overall" if c["card"].get("edhrec_rank") else "cut has no EDHREC numbers: check it")
        return g, why

    played = lambda c: c["inclusion_lb"] if c.get("inclusion_lb") is not None else 50.0  # unknown: assume mid-pack
    overall = lambda c: c["card"].get("edhrec_rank") or 10 ** 6  # Scryfall's EDHREC rank across all decks: 1 = most played

    while len(out) < steps:
        counts = {r: sum(r in roles(e) for e in deck) for r in roles_cfg}
        gcs = commander_gc + sum(bool(e["card"].get("game_changer")) for e in deck)
        have = {name(e) for e in deck} | cmd
        protected = set().union(*[x["pieces"] for x in combos if x["pieces"] <= have])
        by_name = {name(a): a for a in pool}
        moves = [([a], None) for a in pool]
        for x in combos:
            missing = x["pieces"] - have
            if len(missing) >= 2 and missing <= set(by_name):
                moves.append(([by_name[m] for m in sorted(missing)], x))
        best = None
        for adds, combo in moves:
            key_adds = frozenset(name(a) for a in adds)
            if key_adds in blocked:
                continue
            costs = [0.0 if owned(a["card"]) else price(a["card"]) for a in adds]
            if None in costs or gcs + sum(bool(a["card"].get("game_changer")) for a in adds) > gc_max:
                continue
            done = [x for x in combos if (x["pieces"] - have) and (x["pieces"] - have) <= key_adds]
            keep = protected.union(*[x["pieces"] for x in done])  # never cut a piece of the combo this move completes
            cuts, value, why = [], 0.0, []
            for a in adds:
                opts = [(gain(a, c, counts), c) for c in deck
                        if c not in cuts and is_land(a) == is_land(c) and not c.get("locked") and name(c) not in keep]
                if not opts:
                    break
                (g, w), c = max(opts, key=lambda o: (o[0][0], -played(o[1]), overall(o[1])))
                cuts.append(c)
                value += g
                why += w
            if len(cuts) < len(adds):
                continue
            if done:
                value += 1
                why.append("completes a combo: " + "; ".join(f"{' + '.join(sorted(x['cards']))}" + (f" ({x['result']})" if x.get("result") else "") for x in done[:2]))
            if value <= 0:
                continue
            cost, own = sum(costs), all(owned(a["card"]) for a in adds)
            key = (own, value / max(cost, 0.01), value, -sum(played(c) for c in cuts), sum(overall(c) for c in cuts))
            if best is None or key > best[0]:
                best = (key, adds, cuts, cost, value, why, own, combo)
        if best is None:
            break
        _, adds, cuts, cost, value, why, own, combo = best
        label = " + ".join(a["card"]["name"] for a in adds)
        if budget is not None and total + cost > budget + 1e-9:
            skipped.append({"add": label, "price_usd": round(cost, 2), "why": f"would pass the ${budget:g} budget"})
            blocked.add(frozenset(name(a) for a in adds))
            continue
        total += cost
        for a, c in zip(adds, cuts):
            deck[deck.index(c)] = a
            pool.remove(a)
        out.append({"step": len(out) + 1, "add": label, "cut": " + ".join(c["card"]["name"] for c in cuts), "owned": own,
                    "package": len(adds) > 1, "price_usd": round(cost, 2), "total_usd": round(total, 2), "value": round(value, 2),
                    "why": "; ".join(why), "evidence": [e for a in adds for e in a.get("evidence") or []]})
    return {"steps": out, "total_usd": round(total, 2), "skipped": skipped,
            "swaps_today": sum(s["owned"] for s in out)}


def combos_for(s, commanders, names, bracket):
    """(combos, note): Commander Spellbook combos within the deck plus candidates. Two-card combos aren't promoted at
    brackets 1-3 (deck_check flags them there). Spellbook unreachable: no combos, and the note says so."""
    from edhcore.http import RequestError, Unavailable
    try:
        res = s.spellbook.find_my_combos(commanders, [(n, 1) for n in names])
    except (Unavailable, RequestError) as e:
        return [], f"Commander Spellbook unreachable ({e}): combos not considered"
    out, cmd = [], {n.lower() for n in commanders}
    for v in (res.get("results", res) or {}).get("included", []):
        pieces = [u["card"]["name"] for u in v.get("uses", [])]
        if bracket and bracket <= 3 and len([p for p in pieces if p.lower() not in cmd]) <= 2:
            continue
        out.append({"cards": pieces, "id": v.get("id"), "result": "; ".join(f["feature"]["name"] for f in v.get("produces", [])[:2])})
    return out, f"{len(out)} Commander Spellbook combos considered"


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
    commanders = [c["name"] for c in brew["commander"]["cards"]]
    names = [d["name"] for d in brew["deck"] for _ in range(d.get("qty") or 1)] + [c["name"] for c in adds] + commanders  # basics once per copy
    found, _, _ = s.scryfall.collection([{"name": n.split(" // ")[0]} for n in names])
    nd, nc = len(names) - len(adds) - len(commanders), len(commanders)
    cmd_cards = [c for c in found[len(names) - nc:] if c]
    found = found[:len(names) - nc]
    deck = [{"card": found[i], "lift_lb": lift.get(names[i].lower()), "inclusion_lb": played.get(names[i].lower())} for i in range(nd) if found[i]]
    pool = [{"card": found[nd + i], "lift_lb": (c.get("score") or {}).get("lift_lb"), "evidence": c["evidence"]} for i, c in enumerate(adds) if found[nd + i]]
    prices = deck_check.cheapest([p["card"]["name"] for p in pool])
    bracket = (brew.get("target_bracket") or {}).get("bracket")
    combos, combo_note = combos_for(s, commanders, [e["card"]["name"] for e in deck + pool], bracket)
    from autobuild import with_targets
    doc = plan(deck, pool, with_targets(load(ROLES_FILE), brew.get("role_targets")), bracket=bracket, combos=combos, commanders=commanders,
               commander_gc=sum(bool(c.get("game_changer")) for c in cmd_cards),
               ident=sorted({x for c in cmd_cards for x in c.get("color_identity", [])}),
               owned=lambda c: col.state({"oracle_id": c.get("oracle_id")}, have) != "missing",
               price=lambda c: (prices.get(c["name"]) or {}).get("usd"), budget=a.budget, steps=a.steps)
    doc = {"schema_version": "1.0", "generated": time.strftime("%Y-%m-%d"), "deck_version": brew.get("version"), "budget_usd": a.budget,
           "collection": os.path.basename(cp) if have else None, "prices": "cheapest paper printing, Scryfall daily prices", "combos": combo_note, "data": s.data_block(), **doc}
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
