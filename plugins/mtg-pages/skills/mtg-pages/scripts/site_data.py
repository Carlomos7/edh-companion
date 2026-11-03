#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Assemble site-data.json from mtgdb output, so no number on the page is typed by hand.

  site_data.py init site-data.json --title "..." [--subtitle ...] [--bracket 3] [--themes map.json]
  site_data.py add-deck site-data.json --group "Atraxa decks" --slug atraxa --deck b3.txt --bracket 3
               [--notes notes.json] [--commanders 2] [--budget 300] [--reasons off-theme.json]
  site_data.py add-tier site-data.json --id atraxa --title "Atraxa staples" --cards edhrec.json [--staples staples.json]
  site_data.py add-swaps site-data.json --group "Atraxa decks" --merged merged.json
  site_data.py add-claims site-data.json --ledger claims.verified.jsonl [...]
  site_data.py summary site-data.json

notes.json (per deck, written by the agent; every field optional):
  {"pitch": "", "wins": "", "key_cards": [], "strengths": [], "weaknesses": [], "tips": [], "notes": "",
   "youtube": [{"title": "", "url": "", "channel": "", "date": ""}], "checks": {"spellbook": true, "verifier": "pass"},
   "role_builder_counts": {"draw": 11}}
edhrec.json: [{"name": "Card", "pct": 41.2, "n": 1203}]  (n = decks behind the number)
"""
import argparse, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))


def find_mtgdb():
    """mtgdb.py ships in the core `mtg` plugin. Order: $MTGDB_SCRIPT, the repo checkout, then the path the mtg plugin's
    MCP server records in its cache each time it starts (installed plugins live in versioned folders)."""
    cache = os.path.expanduser(os.environ.get("MTG_CACHE", "~/.cache/mtg"))
    recorded = os.path.join(cache, "mtgdb-path.txt")
    for cand in (os.environ.get("MTGDB_SCRIPT"),
                 os.path.join(HERE, "..", "..", "..", "..", "mtg", "scripts", "mtgdb.py"),
                 open(recorded, encoding="utf-8").read().strip() if os.path.exists(recorded) else None):
        if cand and os.path.isfile(cand):
            return os.path.normpath(cand)
    sys.exit("mtgdb.py not found: install the `mtg` plugin and start a session once, or set MTGDB_SCRIPT")


MTGDB = None
TEMPLATE_RANGES = {"lands": (35, 38), "ramp": (8, 12), "draw": (8, 12), "removal": (8, 12), "wipe": (2, 4)}
TYPE_ORDER = ["Creature", "Planeswalker", "Battle", "Instant", "Sorcery", "Artifact", "Enchantment", "Land"]


def mtgdb(*args, themes=None, ok_codes=(0, 1)):
    global MTGDB
    MTGDB = MTGDB or find_mtgdb()
    cmd = [sys.executable, MTGDB] + (["--themes", themes] if themes else []) + list(args)
    if os.environ.get("MTGDB"):
        cmd[2:2] = ["--db", os.environ["MTGDB"]]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if p.returncode not in ok_codes:
        sys.exit(f"mtgdb {' '.join(args)} failed: {p.stderr.strip()[:500]}")
    return json.loads(p.stdout)


def load(path):
    return json.load(open(path, encoding="utf-8"))


def save(path, d):
    tmp = path + ".tmp"
    json.dump(d, open(tmp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def main_type(t):
    return next((x for x in TYPE_ORDER if x in (t or "")), "Other")


def add_image(D, p):
    """Register front/back images for a printing; return (front_key, back_key)."""
    imgs = D.setdefault("images", {})
    f = p["id"] + "_f"
    if p.get("img_front"):
        imgs[f] = p["img_front"]
    if p.get("img_back"):
        b = p["id"] + "_b"
        imgs[b] = p["img_back"]
    elif p.get("back_id"):
        b = "back_" + p["back_id"]
        imgs[b] = f"https://backs.scryfall.io/normal/{p['back_id'][0]}/{p['back_id'][1]}/{p['back_id']}.jpg"
    else:
        b = None
    if b and b.startswith("back_") and not D.get("default_back"):
        D["default_back"] = b
    return f, b


def ladder(D, name, themes):
    P = D.setdefault("printings", {})
    if name in P:
        return
    r = mtgdb("printings", name, themes=themes)
    rows = [p for p in r.get("printings", []) if p.get("legal")]
    rows.sort(key=lambda p: (p["usd"] if p["usd"] is not None else (p["usd_foil"] or 1e9)))
    P[name] = [{"set": p["set_code"], "cn": p["cn"], "price": p["usd"], "foil": p["usd_foil"], "theme": p.get("theme")}
               for p in rows[:12]]


def cmd_init(a):
    D = {"schema": 1, "title": a.title, "subtitle": a.subtitle or "", "generated": time.strftime("%Y-%m-%d"),
         "default_bracket": a.bracket, "theme": None, "tiers": [], "groups": [], "printings": {}, "images": {},
         "sources": [], "accuracy": {"checks": [], "unverified": []}, "data_dates": {}, "fan": []}
    info = mtgdb("info")
    D["data_dates"] = {"card_index": info.get("bulk_updated") or info.get("built"), "prices": info.get("bulk_updated"),
                       "game_changers": f"{info.get('game_changers')} cards ({info.get('gc_source')})"}
    if a.themes:
        t = load(a.themes)
        spec = t.get("spec", {})
        if spec.get("mode", "prefer") != "none":
            labs = spec.get("labels") or list(dict.fromkeys(t.get("printings", {}).values()))
            D["theme"] = {"mode": spec.get("mode", "prefer"), "franchise_label": spec.get("franchise_label"),
                          "labels": [{"label": l} for l in labs]}
            D["data_dates"]["theme_map"] = t.get("built", "unknown")
        D["themes_path"] = os.path.abspath(a.themes)
    save(a.site, D)
    print(a.site)


def cmd_add_deck(a):
    D = load(a.site)
    themes = D.get("themes_path") if D.get("theme") else None
    res = mtgdb("resolve", a.deck, themes=themes)
    extra = ["--commanders", str(a.commanders)] + (["--budget", str(a.budget)] if a.budget else []) + \
            (["--reasons", a.reasons] if a.reasons else [])
    val = mtgdb("validate", a.deck, "--bracket", str(a.bracket), *extra, themes=themes)
    st = mtgdb("stats", a.deck, "--commanders", str(a.commanders))
    sim = mtgdb("simulate", a.deck, "--commanders", str(a.commanders), "--runs", "20000")
    notes = load(a.notes) if a.notes else {}
    reasons = load(a.reasons) if a.reasons else {}
    cards, types = [], {}
    for i, x in enumerate(res["cards"]):
        if "error" in x:
            sys.exit(f"{a.deck}: {x.get('name')}: {x['error']} (fix the deck before adding it to the page)")
        o, p = x["oracle"], x["printing"]
        f, b = add_image(D, p)
        is_cmdr = i < a.commanders
        land = "Land" in o["type_line"] and not o["type_line"].startswith(("Instant", "Sorcery", "Creature"))
        role = next((r for r, v in (st.get("roles") or {}).items() if o["name"] in v["cards"]), None)
        cards.append({"name": o["name"], "qty": x["qty"], "type": o["type_line"], "mv": int(o["cmc"] or 0), "land": land,
                      "commander": is_cmdr, "set": p["set_code"], "cn": p["cn"], "price": p["usd"] if p["usd"] is not None else p["usd_foil"],
                      "theme": x.get("theme") if D.get("theme") else None, "img": f, "back": b, "role": role,
                      "flags": x.get("flags", []), "reason": reasons.get(o["name"])})
        if not is_cmdr:
            types[main_type(o["type_line"])] = types.get(main_type(o["type_line"]), 0) + x["qty"]
        if a.ladders:
            ladder(D, o["name"], themes)
    roles = {k: v["count"] for k, v in (st.get("roles") or {}).items()}
    template = {"lands": [st["lands"], *TEMPLATE_RANGES["lands"]]}
    for r in ("ramp", "draw", "removal", "wipe"):
        template[r] = [roles.get(r, 0), *TEMPLATE_RANGES[r]]
    compare = {r: {"tagger": roles.get(r, 0), "builder": n} for r, n in (notes.get("role_builder_counts") or {}).items()
               if roles.get(r, 0) != n}
    stats = {"price": val["price_usd"], "unpriced": val["unpriced"], "avg_mv": st["avg_mv_nonland"], "lands": st["lands"],
             "game_changers": val["game_changers"], "curve": st["curve"], "types": dict(sorted(types.items(), key=lambda kv: TYPE_ORDER.index(kv[0]) if kv[0] in TYPE_ORDER else 99)),
             "pips": st["pips"], "sources": st["sources"], "sim": sim["pct_commander_cast_by"], "template": template,
             "template_source": "Starting ranges from construction.md (not an official template).", "roles_source": st.get("roles_source")}
    if compare:
        stats["role_compare"] = compare
    if val.get("collection"):
        stats["cost_to_buy"] = val["collection"]["cost_to_buy_usd"]
    checks = {"validate": val["pass"], **(notes.get("checks") or {})}
    deck = {"bracket": a.bracket, "cards": cards, "stats": stats, "theme": val.get("theme"), "checks": checks,
            "summary": {k: notes[k] for k in ("pitch", "wins", "key_cards", "strengths", "weaknesses", "tips", "notes") if k in notes},
            "moxfield": open(a.deck, encoding="utf-8").read().strip(), "errors": val["errors"]}
    grp = next((g for g in D["groups"] if g["title"] == a.group), None)
    if not grp:
        grp = {"id": a.group.lower().replace(" ", "-")[:40], "title": a.group, "commanders": [], "swaps": []}
        D["groups"].append(grp)
    cm = next((c for c in grp["commanders"] if c["slug"] == a.slug), None)
    first = cards[0]
    if not cm:
        cm = {"slug": a.slug, "name": " / ".join(c["name"] for c in cards[:a.commanders]), "img": first["img"],
              "mv": first["mv"], "decks": [], "youtube": []}
        grp["commanders"].append(cm)
        if first["img"] not in D["fan"]:
            D["fan"].append(first["img"])
    if notes.get("youtube"):
        cm["youtube"] = notes["youtube"]
    cm["decks"] = sorted([d for d in cm["decks"] if d["bracket"] != a.bracket] + [deck], key=lambda d: d["bracket"])
    save(a.site, D)
    out = {"added": f"{a.slug}/b{a.bracket}", "validate_pass": val["pass"], "errors": val["errors"], "price": val["price_usd"]}
    print(json.dumps(out, indent=1))
    sys.exit(0 if val["pass"] else 1)


def cmd_add_tier(a):
    D = load(a.site)
    themes = D.get("themes_path") if D.get("theme") else None

    def enrich(rows):
        outl = []
        for r in rows:
            nm = mtgdb("normalize", r["name"], ok_codes=(0, 1))[0]
            if not nm.get("name"):
                print(f"skipped unresolved card: {r['name']}", file=sys.stderr)
                continue
            pr = mtgdb("printings", nm["name"], themes=themes)
            legal = [p for p in pr["printings"] if p["legal"]]
            if not legal:
                continue
            best = legal[0]  # themed first, then cheapest (mtgdb order)
            cheapest = min((p["usd"] for p in legal if p["usd"] is not None), default=None)
            f, b = add_image(D, {"id": best["id"], "img_front": best["img_front"]})
            outl.append({"name": nm["name"], "pct": r["pct"], "n": r.get("n"), "price": cheapest,
                         "theme": best.get("theme") if D.get("theme") else None, "img": f})
            if a.ladders:
                ladder(D, nm["name"], themes)
        return outl
    cards = enrich(load(a.cards))
    staples = enrich(load(a.staples)) if a.staples else []
    low = min((c["n"] for c in cards if c.get("n")), default=None)
    tier = {"id": a.id, "title": a.title, "cards": cards, "staples": staples,
            "method": a.method or "Ranked by EDHREC inclusion: the share of decks that could play a card that do.",
            "cutoffs": {"S": 60, "A": 40, "B": 25, "C": 10}, "low_n": 50 if low is not None and low < 50 else None}
    D["tiers"] = [t for t in D["tiers"] if t["id"] != a.id] + [tier]
    save(a.site, D)
    print(json.dumps({"tier": a.id, "cards": len(cards), "staples": len(staples)}))


def cmd_add_swaps(a):
    D = load(a.site)
    grp = next((g for g in D["groups"] if g["title"] == a.group), None)
    if not grp:
        sys.exit(f"no group {a.group}; add decks first")
    rows = load(a.merged)
    decks = {f"{c['slug']}/b{d['bracket']}" for c in grp["commanders"] for d in c["decks"]}
    bad = [f"{r['card']} -> {f['deck']}" for r in rows for f in r["fits"] if f["deck"] not in decks]
    if bad:
        sys.exit("swap rows point at decks not on this page: " + "; ".join(bad[:10]))
    themes = D.get("themes_path") if D.get("theme") else None
    for r in rows:
        pr = mtgdb("printings", r["card"], themes=themes)
        legal = [p for p in pr.get("printings", []) if p["legal"]]
        if legal:
            r["img"], _ = add_image(D, {"id": legal[0]["id"], "img_front": legal[0]["img_front"]})
            r["price"] = legal[0]["usd"]
    grp["swaps"] = rows
    save(a.site, D)
    print(json.dumps({"group": a.group, "swaps": len(rows)}))


def cmd_add_claims(a):
    D = load(a.site)
    acc, seen = D["accuracy"], {s["url"] for s in D["sources"]}
    ver = unver = 0
    for path in a.ledger:
        for ln in open(path, encoding="utf-8"):
            if not ln.strip():
                continue
            c = json.loads(ln)
            if c.get("status") == "verified":
                ver += 1
            else:
                unver += 1
                acc["unverified"].append({"text": c.get("claim", ""), "where": c.get("subject", "")})
            for s in c.get("sources", []):
                if s.get("url") and s["url"] not in seen:
                    seen.add(s["url"])
                    D["sources"].append({"title": s.get("title") or s.get("author") or s["url"], "url": s["url"],
                                         "kind": s.get("kind"), "date": s.get("date"), "locator": s.get("locator")})
    acc["claims_verified"] = acc.get("claims_verified", 0) + ver
    acc["claims_unverified"] = acc.get("claims_unverified", 0) + unver
    save(a.site, D)
    print(json.dumps({"verified": ver, "unverified": unver, "sources": len(D["sources"])}))


def cmd_summary(a):
    D = load(a.site)
    decks = [(g["title"], c["slug"], d["bracket"], d["checks"].get("validate")) for g in D["groups"] for c in g["commanders"] for d in c["decks"]]
    print(json.dumps({"title": D["title"], "tiers": [(t["id"], len(t["cards"])) for t in D["tiers"]], "decks": decks,
                      "images": len(D.get("images", {})), "ladders": len(D.get("printings", {})),
                      "theme": D.get("theme")}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("init"); s.add_argument("site"); s.add_argument("--title", required=True); s.add_argument("--subtitle")
    s.add_argument("--bracket", type=int, default=3); s.add_argument("--themes"); s.set_defaults(f=cmd_init)
    s = sp.add_parser("add-deck"); s.add_argument("site"); s.add_argument("--group", required=True); s.add_argument("--slug", required=True)
    s.add_argument("--deck", required=True); s.add_argument("--bracket", type=int, required=True); s.add_argument("--notes")
    s.add_argument("--commanders", type=int, default=1); s.add_argument("--budget", type=float); s.add_argument("--reasons")
    s.add_argument("--no-ladders", dest="ladders", action="store_false"); s.set_defaults(f=cmd_add_deck)
    s = sp.add_parser("add-tier"); s.add_argument("site"); s.add_argument("--id", required=True); s.add_argument("--title", required=True)
    s.add_argument("--cards", required=True); s.add_argument("--staples"); s.add_argument("--method")
    s.add_argument("--no-ladders", dest="ladders", action="store_false"); s.set_defaults(f=cmd_add_tier)
    s = sp.add_parser("add-swaps"); s.add_argument("site"); s.add_argument("--group", required=True); s.add_argument("--merged", required=True)
    s.set_defaults(f=cmd_add_swaps)
    s = sp.add_parser("add-claims"); s.add_argument("site"); s.add_argument("--ledger", nargs="+", required=True); s.set_defaults(f=cmd_add_claims)
    s = sp.add_parser("summary"); s.add_argument("site"); s.set_defaults(f=cmd_summary)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
