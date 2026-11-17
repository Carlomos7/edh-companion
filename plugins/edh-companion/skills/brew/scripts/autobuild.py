#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi", "truststore"]
# ///
"""A first-draft 100-card deck from candidates.json: greedy picks under hard limits, then a mana check.

  autobuild.py <project> [--bracket N] [--budget USD] [--lock NAME ...] [--ban NAME ...] [--out <project>/autobuild.json]
               [--fresh|--offline]

Reads candidates.json (run candidates.py first) and brew.json for the commanders, bracket and the current deck.
Hard limits are filters, never scores: verdict not ineligible, not upcoming, singleton, Game Changers within the
bracket, the budget as a true total from each card's cheapest printing (a card with no price can't be bought within
a budget, so it's left out). Order: locked cards, then each role's floor from references/roles.json (ramp first,
best-ranked cards with that role), then the rest by candidates.py's rank without passing any role's cap. Lands:
Karsten's formula from the chosen spells (never below 33), the best-ranked candidate lands, then basics split by the
spells' pips. Mana check: the seeded cast-by-turn simulation; when the commander isn't castable by the turn after
its mana value in half the games and a color is the bottleneck, a basic of that color replaces one of the most
plentiful color (or the lowest-ranked filler), at most 3 times. Writes autobuild.json: every pick with why, its
roles, evidence and price; binding limits; weak spots; the simulation; and the plan.py changes from the current
deck. A draft for the player to edit, not a finished deck: deck_check and the audit still apply.
"""
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "audit", "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))
import analytics  # noqa: E402
from edhcore.cards import front_type  # noqa: E402

BASICS = {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest", "C": "Wastes"}
ROLES_FILE = os.path.join(HERE, "..", "references", "roles.json")
MIN_LANDS, MAX_LANDS = 33, 40


def load(p):
    with open(p, encoding="utf-8") as h:
        return json.load(h)


def basic(col):
    return {"name": BASICS[col], "type_line": f"Basic Land — {BASICS[col]}", "produced_mana": [col], "cmc": 0, "basic": True}


def build(commanders, pool, cfg, bracket=None, budget=None, locks=(), bans=(), price=lambda c: None, runs=4000, strict_theme=False):
    """commanders: Scryfall cards. pool: [{card, rank, evidence, status, theme_fit}] (eligible/needs_review candidates).
    strict_theme: only on_theme / exception cards (a strict or prefer theme). The budget includes the commanders.
    Returns the autobuild document (without file metadata)."""
    ident = sorted({x for c in commanders for x in c.get("color_identity", [])}) or ["C"]
    slots = 100 - len(commanders)
    names = lambda n: {n.lower(), n.split(" // ")[0].lower()}  # full name or front face
    locks, bans = {n.lower() for n in locks}, {n.lower() for n in bans}
    cmd_names = set().union(*[names(c["name"]) for c in commanders])
    gc_max = cfg["game_changers"].get(str(bracket), 99) if bracket else 99
    roles_cfg = {k: dict(v) for k, v in cfg["roles"].items()}
    cmd_mv = max(int(c.get("cmc") or 0) for c in commanders)
    if cmd_mv >= 4:
        roles_cfg["ramp"]["min"] = cfg["ramp_high_cost"]
    picked, left_out, weak, binding = [], [], [], set()
    spent = sum(price(c) or 0.0 for c in commanders)  # the budget is the whole deck, commanders included
    gc = sum(bool(c.get("game_changer")) for c in commanders)
    if gc > gc_max:
        weak.append(f"the commander is a Game Changer: bracket {bracket} allows {gc_max}")

    usable = []
    for e in sorted(pool, key=lambda e: (e.get("rank") or 10 ** 6, e["card"]["name"])):
        c, n = e["card"], names(e["card"]["name"])
        why = ("banned by you" if n & bans else "a commander" if n & cmd_names else "not released yet" if e.get("status") == "upcoming" else
               "off theme or theme unchecked" if strict_theme and e.get("theme_fit") not in ("on_theme", "exception") else
               "no price (can't be counted against the budget)" if budget is not None and price(c) is None else None)
        if why:
            left_out.append({"name": c["name"], "why": why})
        else:
            usable.append(e)
    roles_of = {id(e): set(analytics.roles(e["card"])) for e in usable}

    def count(role):
        return sum(role in roles_of.get(id(p["e"]), ()) for p in picked if p["e"])

    def take(e, why, force=False):
        nonlocal spent, gc
        c = e["card"]
        if any(p["name"].lower() == c["name"].lower() for p in picked):
            return False
        cost = price(c) or 0.0
        if budget is not None and spent + cost > budget + 1e-9:
            binding.add("budget")
            return False
        open_slots = max(1, slots - lands_target - sum("Land" not in front_type(p["e"]["card"]) for p in picked))
        if budget is not None and not force and cost > 8 * (budget - spent) / open_slots:  # one card can't eat the budget
            binding.add("budget (per-card share)")
            return False
        if c.get("game_changer") and gc >= gc_max and not force:
            binding.add(f"Game Changers (bracket {bracket}: {gc_max})")
            return False
        if not force and any(count(r) >= roles_cfg[r]["max"] for r in roles_of[id(e)] if r in roles_cfg):
            return False
        spent += cost
        gc += bool(c.get("game_changer"))
        picked.append({"name": c["name"], "e": e, "why": why, "price": cost if price(c) is not None else None})
        return True

    lands_target = 37
    spells = [e for e in usable if "Land" not in front_type(e["card"])]
    for e in usable:
        if names(e["card"]["name"]) & locks:
            take(e, "locked by you", force=True)
    landed = set().union(*[names(p["name"]) for p in picked])
    for n in sorted(locks - landed):
        out = next((x["why"] for x in left_out if n in names(x["name"])), None)
        weak.append(f"lock {n} not used: " + (out or ("over the budget" if any(n in names(e["card"]["name"]) for e in usable) else "not in candidates.json")))
    if gc > gc_max:
        weak.append(f"{gc} Game Changers with your locks and commander: bracket {bracket} allows {gc_max}")
    locked_lands = sum("Land" in front_type(p["e"]["card"]) for p in picked)
    spell_slots = lambda: slots - max(lands_target, locked_lands)
    for role, lim in roles_cfg.items():
        for e in spells:
            if count(role) >= lim["min"]:
                break
            if role in roles_of[id(e)]:
                take(e, f"{role} floor ({count(role) + 1} of {lim['min']})" + (f", rank {e['rank']}" if e.get("rank") else ""))
        if count(role) < lim["min"]:
            weak.append(f"only {count(role)} {role} cards (floor {lim['min']}): the candidates don't have more")
    for _ in range(2):  # fill, then settle the land count from the chosen spells and refill
        nonland = [p for p in picked if "Land" not in front_type(p["e"]["card"])]
        for e in spells:
            if len(nonland) >= spell_slots():
                break
            if take(e, f"rank {e['rank']}" if e.get("rank") else "candidate without numbers"):
                nonland.append(picked[-1])
        rows = [(1, p["e"]["card"]) for p in nonland]
        lc = analytics.land_count(rows + [(lands_target, basic(ident[0]))])
        if lc:  # None when no spell could be picked
            lands_target = min(MAX_LANDS, max(MIN_LANDS, round(lc["recommended"])))
        extra = len(nonland) - spell_slots()
        for p in sorted((p for p in nonland if p["why"].startswith(("rank", "candidate"))), key=lambda p: -(p["e"].get("rank") or 10 ** 6))[:max(0, extra)]:
            picked.remove(p)
            spent -= p["price"] or 0
            gc -= bool(p["e"]["card"].get("game_changer"))
    nonland = [p for p in picked if "Land" not in front_type(p["e"]["card"])]
    if len(nonland) < spell_slots():
        off = sum(x["why"] == "off theme or theme unchecked" for x in left_out)
        weak.append(f"only {len(nonland)} spells for {spell_slots()} slots: add candidates (research) and rerun"
                    + (f"; {off} candidates left out as off theme or theme unchecked (rerun candidates.py with --theme-sets)" if off else ""))
    land_slots = slots - len(nonland)
    for e in usable:
        if sum("Land" in front_type(p["e"]["card"]) for p in picked) >= min(land_slots - 10, land_slots // 2):
            break
        if "Land" in front_type(e["card"]):  # candidates.py already dropped lands outside the identity
            take(e, f"land, rank {e['rank']}" if e.get("rank") else "land")
    pips = {k: v for k, v in analytics.mana([(1, p["e"]["card"]) for p in nonland], ident)["pips"].items() if k in ident} or {ident[0]: 1}
    n_basic = slots - len(picked)
    if n_basic < 0:
        weak.append(f"{-n_basic} card(s) over 100: your locks don't fit; unlock some")
        n_basic = 0
    split = {k: int(n_basic * v / max(1, sum(pips.values()))) for k, v in pips.items()}
    for k in sorted(pips, key=lambda k: -pips[k])[: n_basic - sum(split.values())]:
        split[k] += 1
    basics = dict(split)

    cost = {}
    for c in commanders:
        for k, v in analytics.pips(c).items():
            cost[k] = cost.get(k, 0) + v
    turn = min(8, cmd_mv + cfg["cast_target"]["turn_after_mv"])
    gate = []
    for attempt in range(4):
        rows = [(1, p["e"]["card"]) for p in picked] + [(n, basic(k)) for k, n in basics.items() if n]
        sim = analytics.simulate(rows, cmd_mv, cost=cost, runs=runs)
        p = sim["by_turn"][turn]
        gate.append({"attempt": attempt + 1, "castable_by_turn": turn, "probability": p, "bottleneck": sim["bottleneck"], "basics": dict(basics)})
        if p >= cfg["cast_target"]["probability"] or not sim["bottleneck"] or attempt == 3:
            break
        short = sim["bottleneck"]
        binding.add(f"mana check: {short} sources")
        used = {x["name"].lower() for x in picked}
        fixer = next((e for e in usable if e["card"]["name"].lower() not in used and "Land" in front_type(e["card"])
                      and short in analytics.made_colors(e["card"], ident)), None)  # usable is in rank order
        give = max((k for k in basics if k != short and basics[k] > 1), key=lambda k: basics[k], default=None)
        fix_cost = price(fixer["card"]) if fixer else None
        if fixer and give and (budget is None or (fix_cost is not None and spent + fix_cost <= budget)):
            basics[give] -= 1  # swap: a candidate land that makes the short color replaces a basic of the most plentiful one
            picked.append({"name": fixer["card"]["name"], "e": fixer, "why": f"land, mana check: makes {short} (replaces a {BASICS[give]})",
                           "price": fix_cost})
            spent += fix_cost or 0
            continue
        was_short = {g["bottleneck"] for g in gate}
        most = max((k for k in basics if k not in was_short and basics[k] > 1), key=lambda k: basics[k], default=None)
        if most:
            basics[most] -= 1
        else:  # nothing to trade: the lowest-ranked filler spell makes room
            filler = [x for x in picked if x["why"].startswith(("rank", "candidate"))]
            if not filler:
                break
            gone = max(filler, key=lambda x: x["e"].get("rank") or 10 ** 6)
            picked.remove(gone)
            spent -= gone["price"] or 0
            gc -= bool(gone["e"]["card"].get("game_changer"))
        basics[short] = basics.get(short, 0) + 1
    if gate[-1]["probability"] < cfg["cast_target"]["probability"]:
        weak.append(f"commander castable by turn {turn} in only {gate[-1]['probability']:.0%} of games"
                    + (f" (short of {gate[-1]['bottleneck']})" if gate[-1]["bottleneck"] else "") + ": add ramp or fixing")

    deck = [{"name": p["name"], "qty": 1, "why": p["why"], "roles": sorted(roles_of.get(id(p["e"]), ())), "rank": p["e"].get("rank"),
             "evidence": p["e"].get("evidence") or [], "price_usd": p["price"]} for p in picked]
    deck += [{"name": BASICS[k], "qty": n, "why": "basic land, split by the spells' pips and the mana check", "roles": ["land"], "rank": None,
              "evidence": [], "price_usd": None} for k, n in sorted(basics.items()) if n]
    counts = {r: count(r) for r in roles_cfg}
    cutoff = max((p["e"].get("rank") or 0 for p in picked if p["why"].startswith("rank")), default=None)
    for r in roles_cfg:  # a floor binds when it pulled in a card ranked below where filling stopped
        if cutoff and any(p["why"].startswith(f"{r} floor") and (p["e"].get("rank") or 10 ** 6) > cutoff for p in picked):
            binding.add(f"{r} floor {roles_cfg[r]['min']}")
    return {"commanders": [c["name"] for c in commanders], "color_identity": ident, "bracket": bracket, "budget_usd": budget,
            "total_usd": round(spent, 2), "cards": sum(d["qty"] for d in deck) + len(commanders), "lands": sum(d["qty"] for d in deck if "land" in d["roles"]),
            "role_counts": counts, "game_changers": gc, "rank_cutoff": cutoff, "pool_size": len(usable), "binding": sorted(binding), "weak_spots": weak, "mana_check": gate,
            "deck": deck, "left_out": left_out}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--bracket", type=int, choices=range(1, 6))
    ap.add_argument("--budget", type=float, help="whole-deck budget in USD, cheapest printings, a hard total")
    ap.add_argument("--lock", action="append", default=[], help="card that must be in (repeatable)")
    ap.add_argument("--ban", action="append", default=[], help="card that must stay out (repeatable)")
    ap.add_argument("--out")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fresh", action="store_true")
    g.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    from edhcore.session import Session
    import deck_check
    cp = os.path.join(a.project, "candidates.json")
    if not os.path.exists(cp):
        sys.exit("no candidates.json: run candidates.py first")
    cand = load(cp)
    bp = os.path.join(a.project, "brew.json")
    brew = load(bp) if os.path.exists(bp) else {}
    s = Session(fresh=a.fresh, offline=a.offline, project=a.project)
    deck_check._SESSION = s
    pool = [c for c in cand["cards"] if c["verdict"] != "ineligible"]
    found, _, _ = s.scryfall.collection([{"name": c["name"].split(" // ")[0]} for c in pool] + [{"name": n} for n in cand["commanders"]])
    commanders = [c for c in found[len(pool):] if c]
    if len(commanders) != len(cand["commanders"]):
        sys.exit("commander card data unavailable")
    entries = [{"card": found[i], "rank": c.get("rank"), "evidence": c["evidence"], "status": c["status"], "theme_fit": c["theme"]["fit"]}
               for i, c in enumerate(pool) if found[i]]
    prices = deck_check.cheapest([e["card"]["name"] for e in entries] + [c["name"] for c in commanders]) if a.budget is not None else {}
    doc = build(commanders, entries, load(ROLES_FILE), bracket=a.bracket or cand.get("bracket"), budget=a.budget, locks=a.lock, bans=a.ban,
                price=lambda c: (prices.get(c["name"]) or {}).get("usd"),
                strict_theme=(cand.get("theme_policy") or {}).get("mode") in ("strict", "prefer"))
    doc = {"schema_version": "1.0", "generated": time.strftime("%Y-%m-%d"), "candidates_generated": cand.get("generated"), "data": s.data_block(), **doc}
    now = {d["name"].lower() for d in brew.get("deck", [])}
    new = {d["name"].lower(): d["name"] for d in doc["deck"]}
    doc["changes"] = {"add": sorted(v for k, v in new.items() if k not in now), "cut": sorted(d["name"] for d in brew.get("deck", []) if d["name"].lower() not in new)}
    out = a.out or os.path.join(a.project, "autobuild.json")
    with open(out + ".tmp", "w", encoding="utf-8") as h:
        json.dump(doc, h, ensure_ascii=False, indent=1)
    os.replace(out + ".tmp", out)
    print(f"{doc['cards']} cards, {doc['lands']} lands, ${doc['total_usd']:.2f}" + (f" of ${a.budget:g}" if a.budget is not None else "")
          + f"; roles {', '.join(f'{k} {v}' for k, v in doc['role_counts'].items())}; Game Changers {doc['game_changers']}")
    g = doc["mana_check"][-1]
    print(f"mana check: castable by turn {g['castable_by_turn']} in {g['probability']:.0%} of games" + (f", short of {g['bottleneck']}" if g["bottleneck"] else ""))
    print("binding: " + (", ".join(doc["binding"]) or "none"))
    for w in doc["weak_spots"]:
        print("weak spot: " + w)
    if brew.get("deck"):
        print(f"vs brew.json: +{len(doc['changes']['add'])} / -{len(doc['changes']['cut'])} (plan them with plan.py new, then edit)")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
