#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi"]
# ///
"""Research findings -> verified card candidates for brewing, with citations, theme fit and a verdict per card.

  candidates.py <project> [--commander NAME ...] [--bracket N] [--theme-sets a,b] [--add names.txt] [--add-name NAME ...]
                [--fresh|--offline] [--out <project>/candidates.json]

Reads research.json (card_candidates, rankings, findings[].cards) and brew.json (or the newest brew*.json) for the
commanders, target bracket and theme_policy; flags override. Cards added with --add/--add-name are kept with no
evidence ("no research evidence yet"), never rejected for it. One batched Scryfall lookup through the shared cache.
Verdicts: ineligible only for hard rules (not found, banned / not legal in Commander, outside the commanders' color
identity); needs_review for anything a
person must decide (Game Changer vs bracket, upcoming, unclear theme, no evidence, stale or missing data); eligible
otherwise. With art_required, choosing a printing is not a verdict reason: each card gets printing_choice
needed|done|n/a (done = brew.json already names a printing) next to printings_on_theme, and the top-level
printing_choice sums them. Prints a short summary; the full result is in candidates.json.
"""
import argparse, glob, json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edhcore.http import RequestError, Unavailable  # noqa: E402
from edhcore.session import Session  # noqa: E402

CLASS_RANK = ["verified_fact", "calculated", "popularity_metric", "community_opinion", "model_assessment", "unresolved"]
CONF_RANK = ["high", "medium", "low"]
SOURCE_CLASS = {"card_data": "verified_fact", "official": "verified_fact", "rules": "verified_fact", "combo": "verified_fact",
                "price": "verified_fact", "stats": "popularity_metric", "decklist": "popularity_metric",
                "tournament": "popularity_metric", "video": "community_opinion", "community": "community_opinion",
                "article": "community_opinion"}
GC_NOTE = {1: "bracket 1 allows no Game Changers", 2: "bracket 2 allows no Game Changers", 3: "bracket 3 allows up to 3 per deck",
           4: "bracket 4 allows any", 5: "bracket 5 allows any"}
EDHREC_TOLERANCE = 2.0  # inclusion % points; wider differences are a conflict, never averaged


def load(path):
    with open(path, encoding="utf-8") as h:
        return json.load(h)


def find_brew(project):
    p = os.path.join(project, "brew.json")
    if os.path.exists(p):
        return p
    brews = glob.glob(os.path.join(project, "brew*.json"))
    return max(brews, key=os.path.getmtime) if brews else None


def gather(research, added):
    """{lowercase name: info} from research candidates, rankings, findings and added names (in that order)."""
    info, fclass = {}, {f["id"]: (f.get("class"), f.get("confidence")) for f in research.get("findings", [])}
    sclass = {s["id"]: SOURCE_CLASS.get(s.get("type")) for s in research.get("sources", [])}

    def entry(name):
        return info.setdefault(name.strip().lower(), {"name": name.strip(), "evidence": [], "classes": [], "edhrec": [],
                                                      "theme_fit": set(), "added": False})

    def cite(e, ids):
        for i in ids or []:
            if i not in e["evidence"]:
                e["evidence"].append(i)
            if i in fclass:
                e["classes"].append(fclass[i])
            elif sclass.get(i):
                e["classes"].append((sclass[i], None))

    for c in research.get("card_candidates", []):
        e = entry(c["card"]["name"])
        cite(e, c.get("evidence"))
        if c.get("theme_fit"):
            e["theme_fit"].add(c["theme_fit"])
    for r in research.get("rankings", []):
        for c in r.get("cards", []):
            e = entry(c["card"]["name"])
            cite(e, c.get("evidence"))
            if c.get("inclusion_pct") is not None:
                e["classes"].append(("popularity_metric", None))
                e["edhrec"].append({"inclusion_pct": c["inclusion_pct"], "decks": c.get("decks"), "total_decks": c.get("total_decks"),
                                    "group": r.get("group"), "tier": c.get("tier"), "research_status": c.get("status")})
    for f in research.get("findings", []):
        for n in f.get("cards") or []:
            cite(entry(n), [f["id"]])
    for n in added:
        entry(n)["added"] = True
    return info


def strongest(classes):
    """(class, confidence) with the best class rank, then best confidence; (None, None) when there is none."""
    if not classes:
        return None, None
    return min(classes, key=lambda x: (CLASS_RANK.index(x[0]) if x[0] in CLASS_RANK else 9,
                                       CONF_RANK.index(x[1]) if x[1] in CONF_RANK else 9))


def edhrec(entries):
    if not entries:
        return None, None
    best = max(entries, key=lambda x: (x.get("total_decks") or 0, x.get("decks") or 0))
    conflict = [x for x in entries if abs(x["inclusion_pct"] - best["inclusion_pct"]) > EDHREC_TOLERANCE]
    pick = {k: best.get(k) for k in ("inclusion_pct", "decks", "total_decks")}
    return pick, ([best] + conflict if conflict else None)


def status_of(card, today):
    legal = (card.get("legalities") or {}).get("commander")
    if legal == "banned":
        return "banned"
    if (card.get("released_at") or "") > today and not card.get("reprint"):  # a future reprint of an old card isn't upcoming
        return "upcoming"
    return "legal" if legal == "legal" else "not_legal"


def printings_on_theme(s, cards, sets):
    """{oracle_id: [printing]} for printings in the theme sets (one search per 15 names). Raises Unavailable."""
    out, names = {}, sorted({c["name"] for c in cards})
    sets_q = " or ".join(f"e:{x}" for x in sets)
    for i in range(0, len(names), 15):
        q = "(" + " or ".join('!"' + n.replace('"', '') + '"' for n in names[i:i + 15]) + f") game:paper ({sets_q})"
        for p in s.scryfall.search(q, unique="prints", limit=500):
            if p.get("set") in sets:
                out.setdefault(p.get("oracle_id"), []).append({"set": p["set"], "collector_number": p["collector_number"],
                                                               "printing_id": p["id"], "illustration_id": p.get("illustration_id")})
    return out


def build(project, a, s, today=None):
    today = today or time.strftime("%Y-%m-%d")
    rp = os.path.join(project, "research.json")
    research = load(rp) if os.path.exists(rp) else {}
    bp = find_brew(project)
    brew = load(bp) if bp else {}
    commanders = a.commander or [c["name"] for c in (brew.get("commander") or {}).get("cards", [])]
    bracket = a.bracket or (brew.get("target_bracket") or {}).get("bracket")
    pol = brew.get("theme_policy") or {}
    mode, art = pol.get("mode") or "none", bool(pol.get("art_required"))
    sets = [x.strip().lower() for x in (a.theme_sets or "").split(",") if x.strip()]
    exceptions = {e["card"].lower(): e for e in pol.get("exceptions", [])}
    chosen = {d["name"].lower() for d in brew.get("deck", []) if d.get("name") and (d.get("printing_id") or (d.get("set") and d.get("collector_number")))}
    added = list(a.add_name or [])
    if a.add:
        with open(a.add, encoding="utf-8") as h:
            added += [re.sub(r"^\d+x?\s+", "", x.strip()) for x in h if x.strip() and not x.startswith("#")]

    info = gather(research, added)
    for c in commanders:
        info.pop(c.lower(), None)
    names = list(info)
    found, missing, unavail = s.scryfall.collection([{"name": x.split(" // ")[0]} for x in [info[n]["name"] for n in names] + commanders])
    cmd_cards = found[len(names):]
    identity = None if not commanders or None in cmd_cards else sorted({x for c in cmd_cards for x in c.get("color_identity", [])})

    # merge research names that resolve to the same card
    merged = {}
    for i, n in enumerate(names):
        c, key = found[i], (found[i] or {}).get("oracle_id") or "?" + n
        e = merged.setdefault(key, {**info[n], "card": c, "missing": i in missing, "unavailable": i in unavail, "evidence": [], "classes": [],
                                    "edhrec": [], "theme_fit": set(), "added": False})
        e["evidence"] += [x for x in info[n]["evidence"] if x not in e["evidence"]]
        e["classes"] += info[n]["classes"]
        e["edhrec"] += info[n]["edhrec"]
        e["theme_fit"] |= info[n]["theme_fit"]
        e["added"] |= info[n]["added"]

    prints, prints_err = {}, None
    if sets:
        try:
            prints = printings_on_theme(s, [e["card"] for e in merged.values() if e["card"]], sets)
        except (Unavailable, RequestError) as err:
            prints_err = str(err)
    data = s.data_block()

    out = []
    for e in merged.values():
        c, why, hard = e["card"], [], []
        cls, conf = strongest(e["classes"])
        pick, conflict = edhrec(e["edhrec"])
        rec = {"name": c["name"] if c else e["name"], "oracle_id": None, "scryfall_uri": None, "type_line": None, "color_identity": None,
               "legal": None, "game_changer": None, "status": None, "in_identity": None, "evidence": e["evidence"],
               "evidence_class": cls, "evidence_confidence": conf, "edhrec": pick, "theme": {"fit": "unchecked", "how": None},
               "printings_on_theme": None, "printing_choice": "n/a", "added": e["added"], "verdict": None, "reasons": why}
        if conflict:
            rec["edhrec_conflict"] = conflict
        if not e["evidence"]:
            why.append("no research evidence yet")
        if e["missing"]:
            hard.append("not found on Scryfall")
        elif c is None:
            why.append("card data unavailable")
        else:
            st = status_of(c, today)
            rec.update(oracle_id=c.get("oracle_id"), scryfall_uri=c.get("scryfall_uri"), type_line=c.get("type_line"),
                       color_identity=c.get("color_identity", []), legal=(c.get("legalities") or {}).get("commander"),
                       game_changer=bool(c.get("game_changer")), status=st)
            if st == "banned":
                hard.append("banned in Commander")
            elif st == "not_legal":
                hard.append("not legal in Commander")
            elif st == "upcoming":
                why.append(f"upcoming: releases {c.get('released_at')}")
            if identity is None:
                why.append("commander color identity unknown")
            else:
                off = sorted(set(rec["color_identity"]) - set(identity))
                rec["in_identity"] = not off
                if off:
                    hard.append(f"outside commander identity ({''.join(off)} not in {''.join(identity) or 'C'})")
            if rec["game_changer"]:
                why.append("Game Changer: " + GC_NOTE.get(bracket, "bracket not set; the limit is per deck"))
            if c.get("id") in s.scryfall.stale_ids:
                why.append(f"data stale (as of {data['as_of']}): re-check legality before relying on it")
            hard += theme(rec, e, mode, art, sets, exceptions, prints, prints_err, why)
            if art and rec["theme"]["fit"] != "exception":  # a choice to make, not a verdict reason
                rec["printing_choice"] = "done" if {rec["name"].lower(), e["name"].lower()} & chosen else "needed"
        why[:0] = hard
        rec["verdict"] = "ineligible" if hard else "needs_review" if why else "eligible"
        out.append(rec)

    out.sort(key=lambda r: (["ineligible", "needs_review", "eligible"].index(r["verdict"]), r["name"]))
    counts = {k: sum(r["verdict"] == k for r in out) for k in ("eligible", "needs_review", "ineligible")}
    printing = {k: sum(r["printing_choice"] == k for r in out) for k in ("needed", "done")}
    return {"schema_version": "1.0", "generated": today, "research_version": research.get("version"), "brew": os.path.basename(bp) if bp else None,
            "commanders": commanders, "color_identity": identity, "bracket": bracket,
            "theme_policy": {"mode": mode, "eligibility": pol.get("eligibility"), "art_required": art, "theme_sets": sets,
                             "exceptions": [x["card"] for x in pol.get("exceptions", [])]},
            "data": data, "counts": counts, "printing_choice": printing, "cards": out}


def theme(rec, e, mode, art, sets, exceptions, prints, prints_err, why):
    """Fill rec['theme'] / printings_on_theme; append review reasons; return hard (ineligible) reasons."""
    exc = exceptions.get(rec["name"].lower()) or exceptions.get(e["name"].lower())
    research_fit = "on_theme" if "on_theme" in e["theme_fit"] else "off_theme" if "off_theme" in e["theme_fit"] else None
    if exc:
        rec["theme"] = {"fit": "exception", "how": f"approved exception ({exc['approved_by']}): {exc['reason']}"}
        return []
    if mode == "none" and not sets and not art:
        rec["theme"]["how"] = "no theme"
        return []
    if sets:
        if prints_err:
            why.append("printing data unavailable: theme not checked")
            return []
        ps = prints.get(rec["oracle_id"], [])
        rec["printings_on_theme"] = ps
        if ps:
            rec["theme"] = {"fit": "on_theme", "how": f"printing in theme sets ({', '.join(sorted({p['set'] for p in ps}))})"}
            return []
        if research_fit == "on_theme":
            rec["theme"] = {"fit": "on_theme", "how": "research marks it on theme; no printing in theme sets"}
            return []
        rec["theme"] = {"fit": "off_theme", "how": "no printing in theme sets"}
        if mode == "strict" and not art:  # set codes are one signal, never the only reason to reject (a reprint or promo may fit)
            why.append("strict theme and no printing in the theme sets: confirm it fits or record an exception")
            return []
        if mode != "printings":  # printings mode allows any card and only prefers themed printings
            why.append("no printing in theme sets (one signal, not the rule): check the theme")
        return []
    if research_fit:
        rec["theme"] = {"fit": research_fit, "how": "research theme_fit"}
        if research_fit == "off_theme" and mode != "printings":
            why.append("research marks it off theme")
    else:
        why.append("theme unclear: check against the theme rules")
    if art:
        rec["printings_on_theme"] = []
    return []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--commander", action="append", help="commander name (repeat for partners); overrides brew.json")
    ap.add_argument("--bracket", type=int, choices=range(1, 6))
    ap.add_argument("--theme-sets", help="comma-separated set codes whose printings count as on theme")
    ap.add_argument("--add", help="file with one card name per line (newly found cards, no research evidence yet)")
    ap.add_argument("--add-name", action="append", help="a newly found card name (repeatable)")
    ap.add_argument("--out")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fresh", action="store_true", help="ignore cached data (final checks)")
    g.add_argument("--offline", action="store_true", help="cache only, no network")
    a = ap.parse_args()
    s = Session(fresh=a.fresh, offline=a.offline, project=a.project)
    doc = build(a.project, a, s)
    out = a.out or os.path.join(a.project, "candidates.json")
    with open(out + ".tmp", "w", encoding="utf-8") as h:
        json.dump(doc, h, ensure_ascii=False, indent=1)
    os.replace(out + ".tmp", out)
    n, d = doc["counts"], doc["data"]
    pc = doc["printing_choice"]
    print(f"{n['eligible']} eligible, {n['needs_review']} needs review, {n['ineligible']} ineligible"
          + (f"; printing/art to choose: {pc['needed']} (chosen: {pc['done']})" if pc["needed"] or pc["done"] else "")
          + f"; data {d['verification'] or 'none looked up'}"
          + (f", as of {d['as_of']}" if d["as_of"] else "") + "".join(f"; {x}" for x in d["endpoints_unavailable"]))
    flagged = [r for r in doc["cards"] if r["verdict"] != "eligible"]
    for r in flagged[:30]:
        print(f"{r['verdict']}: {r['name']}: {'; '.join(r['reasons'])}")
    if len(flagged) > 30:
        print(f"+{len(flagged) - 30} more")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
