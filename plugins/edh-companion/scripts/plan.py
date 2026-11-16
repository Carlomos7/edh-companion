#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi", "truststore"]
# ///
"""One pending deck change, planned first and applied exactly (PLAN.json), across any number of variants.

  plan.py new <project> --change main:+Card --change b2:-Card [--change "v:+Card (SLD) 867 *F*@ramp"] [--note TEXT]
                                   write PLAN.json pinned to each variant's current version and deck_hash, then dry-run
  plan.py show <project>           dry-run: +card / -card per variant and whether each variant would apply
  plan.py apply <project>          apply exactly that plan; per variant: applied, or refused with the reason
                                   (deck changed since the plan, cut not in the deck, add already in it, a Game Changer
                                   in bracket 1-2, outside the color identity, banned)
  plan.py revert <project>         undo the last apply for every variant still at the applied hash

Apply bumps each variant's version once, writes decklists/<variant>-v<N>.txt and the new deck_hash (the same hash
deck_check computes), and marks the plan applied. Audit once afterwards, at the boundary (audit-scope per variant).
Refuses, per variant, rather than half-applying. Exit 0 all applied, 1 some refused, 2 nothing to do.
"""
import argparse, datetime, json, os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edhcore.decklist import deck_hash, parse_brew, parse_text  # noqa: E402

PLAN = "PLAN.json"


def load(p):
    with open(p, encoding="utf-8") as h:
        return json.load(h)


def save(p, doc):
    with open(p + ".tmp", "w", encoding="utf-8", newline="\n") as h:
        h.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    os.replace(p + ".tmp", p)


def brew_file(v):
    return "brew.json" if v == "main" else f"brew-{v}.json"


def hash_of(brew):
    cards, cmd = parse_brew(brew)
    return deck_hash(cmd + cards)


def new(project, changes, note=None):
    plan = {"created": datetime.date.today().isoformat(), "note": note, "status": "pending", "variants": {}}
    for ch in changes:
        v, _, op = ch.partition(":")
        if not op or op[0] not in "+-":
            sys.exit(f"bad --change {ch!r}: use VARIANT:+Card or VARIANT:-Card")
        bp = os.path.join(project, brew_file(v))
        if not os.path.exists(bp):
            sys.exit(f"no {brew_file(v)} for variant {v}")
        b = load(bp)
        pv = plan["variants"].setdefault(v, {"brew": brew_file(v), "base_version": b["version"], "base_hash": b["deck_hash"], "add": [], "cut": []})
        name, _, role = op[1:].partition("@")
        if op[0] == "+":
            e = parse_text("1 " + name.strip())[0][0]  # "Nature's Lore (SLD) 867 *F*": the printing matters for art themes
            pv["add"].append({"name": e["name"], "role": role.strip() or "flex",
                              **({"set": e["set"], "collector_number": e["cn"]} if e["set"] else {}),
                              **({"finish": e["finish"]} if e["finish"] != "nonfoil" else {})})
        else:
            pv["cut"].append(name.strip())
    save(os.path.join(project, PLAN), plan)
    return plan


def card_problems(names, brew, lookup):
    """Per added card: banned, Game Changer at bracket 1-2, outside the commander's color identity."""
    bracket = (brew.get("target_bracket") or {}).get("bracket") or 3
    cmd_ci = set()
    data = lookup([c["name"] for c in brew["commander"]["cards"]] + names)
    for c in brew["commander"]["cards"]:
        cmd_ci |= set((data.get(c["name"]) or {}).get("color_identity") or [])
    out = {}
    for n in names:
        c = data.get(n)
        if c is None:
            out[n] = "card data unavailable or not found"
        elif (c.get("legalities") or {}).get("commander") == "banned":
            out[n] = "banned in Commander"
        elif c.get("game_changer") and bracket <= 2:
            out[n] = f"a Game Changer, not allowed at bracket {bracket}"
        elif cmd_ci and not set(c.get("color_identity") or []) <= cmd_ci:
            out[n] = "outside the commander's color identity"
    return out


def scryfall_lookup(names):
    from edhcore.session import Scryfall, Session
    return Scryfall(Session()).named(names)


def check(project, plan, lookup=scryfall_lookup):
    """{variant: (ok, reasons, brew)} without changing anything."""
    res = {}
    for v, pv in plan["variants"].items():
        b = load(os.path.join(project, pv["brew"]))
        why, names = [], {c["name"] for c in b["deck"]}
        if b["deck_hash"] != pv["base_hash"] or b["version"] != pv["base_version"]:
            why.append(f"deck changed since the plan (v{pv['base_version']} {pv['base_hash']} → v{b['version']} {b['deck_hash']})")
        why += [f"-{c}: not in the deck" for c in pv["cut"] if c not in names]
        why += [f"+{a['name']}: already in the deck" for a in pv["add"] if a["name"] in names and a["name"] not in pv["cut"]]
        if not why and pv["add"]:
            why += [f"+{n}: {w}" for n, w in card_problems([a["name"] for a in pv["add"]], b, lookup).items()]
        res[v] = (not why, why, b)
    return res


def show(project, plan, res):
    print(f"PLAN.json ({plan['status']}, {plan['created']})" + (f": {plan['note']}" if plan.get("note") else ""))
    for v, (ok, why, _) in res.items():
        pv = plan["variants"][v]
        print(f"  {v} v{pv['base_version']}: " + ", ".join([f"+{a['name']}" for a in pv["add"]] + [f"-{c}" for c in pv["cut"]])
              + ("  -> would apply" if ok else "  -> REFUSED: " + "; ".join(why)))


def decklist(brew):
    def line(c, qty):
        s = f"{qty} {c['name']}"
        if c.get("set") and c.get("collector_number"):
            s += f" ({c['set'].upper()}) {c['collector_number']}"
        return s + {"foil": " *F*", "etched": " *E*"}.get(c.get("finish") or "", "")
    return ("Commander\n" + "\n".join(line(c, 1) for c in brew["commander"]["cards"]) + "\n\nDeck\n"
            + "\n".join(line(c, c["qty"]) for c in brew["deck"]) + "\n")


def apply(project, lookup=scryfall_lookup):
    pp = os.path.join(project, PLAN)
    if not os.path.exists(pp):
        print("no PLAN.json")
        return 2
    plan = load(pp)
    if plan["status"] != "pending":
        print(f"PLAN.json is {plan['status']}; make a new plan")
        return 2
    res = check(project, plan, lookup)
    show(project, plan, res)
    plan["result"] = {}
    for v, (ok, why, b) in res.items():
        if not ok:
            plan["result"][v] = {"status": "refused", "why": why}
            continue
        pv = plan["variants"][v]
        os.makedirs(os.path.join(project, ".plan"), exist_ok=True)
        backup = os.path.join(".plan", f"{pv['brew'][:-5]}.v{b['version']}.json")
        shutil.copyfile(os.path.join(project, pv["brew"]), os.path.join(project, backup))
        for c in pv["cut"]:
            e = next(x for x in b["deck"] if x["name"] == c)
            e["qty"] -= 1
            if e["qty"] <= 0:
                b["deck"].remove(e)
        for a in pv["add"]:
            b["deck"].append({k: v for k, v in {"name": a["name"], "qty": 1, "role": a["role"], "set": a.get("set"),
                              "collector_number": a.get("collector_number"), "finish": a.get("finish")}.items() if v})
        b["version"] += 1
        b["deck_hash"] = hash_of(b)
        b["updated"] = datetime.date.today().isoformat()
        b["decklist"] = f"decklists/{v}-v{b['version']}.txt"
        os.makedirs(os.path.join(project, "decklists"), exist_ok=True)
        with open(os.path.join(project, b["decklist"]), "x", encoding="utf-8", newline="\n") as h:  # never overwrite
            h.write(decklist(b))
        save(os.path.join(project, pv["brew"]), b)
        plan["result"][v] = {"status": "applied", "version": b["version"], "deck_hash": b["deck_hash"], "backup": backup}
        print(f"  {v}: applied as v{b['version']} ({b['deck_hash']}); next: deck_check.py, then audit-scope {pv['brew']}")
    plan["status"] = "applied" if any(r["status"] == "applied" for r in plan["result"].values()) else "refused"
    save(pp, plan)
    return 0 if all(r["status"] == "applied" for r in plan["result"].values()) else 1


def revert(project):
    pp = os.path.join(project, PLAN)
    plan = load(pp) if os.path.exists(pp) else {}
    if plan.get("status") != "applied":
        print("nothing applied to revert")
        return 2
    rc = 0
    for v, r in plan["result"].items():
        if r["status"] != "applied":
            continue
        bp = os.path.join(project, plan["variants"][v]["brew"])
        if load(bp)["deck_hash"] != r["deck_hash"]:
            print(f"  {v}: changed after the apply; not reverted")
            rc = 1
            continue
        shutil.copyfile(os.path.join(project, r["backup"]), bp)  # the new decklist file stays: lists are never deleted
        r["status"] = "reverted"
        print(f"  {v}: back to v{load(bp)['version']}")
    plan["status"] = "reverted"
    save(pp, plan)
    return rc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["new", "show", "apply", "revert"])
    ap.add_argument("project")
    ap.add_argument("--change", action="append", default=[])
    ap.add_argument("--note")
    a = ap.parse_args()
    if a.cmd == "new":
        if not a.change:
            ap.error("new needs at least one --change")
        plan = new(a.project, a.change, a.note)
        show(a.project, plan, check(a.project, plan))
    elif a.cmd == "show":
        plan = load(os.path.join(a.project, PLAN))
        show(a.project, plan, check(a.project, plan))
    elif a.cmd == "apply":
        sys.exit(apply(a.project))
    else:
        sys.exit(revert(a.project))


if __name__ == "__main__":
    main()
