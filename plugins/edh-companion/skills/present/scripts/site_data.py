#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "jsonschema>=4.18", "certifi"]
# ///
"""Build the page data for the template from a project folder, so no number on the page is typed by hand.

  site_data.py from-workspace PROJECT [--out PROJECT/reports/page-data.json] [--title T] [--subtitle S]
               [--style fancy|basic] [--images atlas|cdn|none] [--viewer simple|3d] [--show a,b] [--hide a,b]

Reads PROJECT.md, DECISIONS.md, research.json (all optional) and brew.json / brew-<variant>.json, each paired with
audit.json / audit-<variant>.json. Card data (names, printings, images, prices, stats) comes from the audit skill's
deck_check.py. Refuses a project that fails `companion.py validate` or has no brew file. The audit state is derived,
never upgraded: no audit file -> "not audited"; audit of another version or hash -> "audit out of date"; else the
audit verdict. Writes reports/presentation-checks.md with the inputs and sections (the skill adds test results).

Styles: fancy = every section, card images, charts, 3D viewer (default); basic = summary, numbers, decklist,
sources, no images. --images: atlas = downloaded into the page (needed to publish), cdn = Scryfall links (local
page only), none. Sections for --show/--hide: charts, swaps, sources, fan, prices, viewer.
"""
import argparse, glob, json, os, re, shutil, ssl, subprocess, sys, tempfile, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DECK_CHECK = os.path.normpath(os.path.join(HERE, "..", "..", "audit", "scripts", "deck_check.py"))
PLUGIN_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts"))
# shortcut: every single-faced card shows Magic's standard back; deck_check has no card_back_id. Upgrade if it adds one.
STD_BACK = "0aeebaf5-8c7d-4636-9e82-8c27447861f7"
TEMPLATE_RANGES = {"lands": (35, 38), "ramp": (8, 12), "draw": (8, 12), "removal": (8, 12), "wipe": (2, 4)}
CLASS_LABEL = {"verified_fact": "Verified facts", "calculated": "Calculated", "popularity_metric": "Popularity stats",
               "community_opinion": "Community opinions", "model_assessment": "Claude's assessments", "unresolved": "Unresolved"}

SECTIONS = ("charts", "swaps", "sources", "fan", "prices", "viewer")
PRESETS = {
    "fancy": {"show": dict.fromkeys(SECTIONS, True), "images": "atlas", "viewer": "three"},
    "basic": {"show": {"charts": False, "swaps": False, "sources": True, "fan": False, "prices": True, "viewer": False},
              "images": "none", "viewer": "simple"},
}


def page_settings(a):
    """Style preset, then the player's overrides. Returns (page, viewer)."""
    p = PRESETS[a.style]
    show = dict(p["show"])
    for flag, val in (("show", True), ("hide", False)):
        for name in filter(None, (getattr(a, flag) or "").split(",")):
            name = name.strip()
            if name not in SECTIONS:
                sys.exit(f"unknown section '{name}': choose from {', '.join(SECTIONS)}")
            show[name] = val
    images = a.images or p["images"]
    viewer = {"3d": "three", "simple": "simple"}.get(a.viewer) or p["viewer"]
    if images == "none":
        show["viewer"] = show["fan"] = False  # nothing to show without images
    style = a.style if not (a.images or a.viewer or a.show or a.hide) else "custom"
    return {"style": style, "show": show, "images": images}, viewer


def load(path):
    import yaml
    with open(path, encoding="utf-8") as h:
        return yaml.safe_load(h) if path.endswith(".yaml") else json.load(h)


def opt(path):
    return load(path) if os.path.exists(path) else None


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def contract_errors(ws):
    """Run the plugin's project validator (scripts/companion.py validate)."""
    sys.path.insert(0, PLUGIN_SCRIPTS)
    import companion
    return companion.validate(ws)[0]


def deck_check(deck_path, tmp):
    """Run deck_check.py (card facts from Scryfall) and return its JSON. Exit codes 1/2 are check results, not errors."""
    uv = shutil.which("uv") or sys.exit("uv not found: deck_check.py runs with `uv run --script`")
    out = os.path.join(tmp, f"check-{len(os.listdir(tmp))}.json")
    p = subprocess.run([uv, "run", "--quiet", "--script", DECK_CHECK, deck_path, "--json", out, "--no-combos"],
                       capture_output=True, text=True, encoding="utf-8")
    if not os.path.exists(out):
        sys.exit(f"deck_check.py failed on {deck_path}: {(p.stderr or p.stdout).strip()[:500]}")
    res = json.load(open(out, encoding="utf-8"))
    if res.get("unavailable") and not res.get("cards"):
        sys.exit(f"card data unavailable for {deck_path}: {'; '.join(res['unavailable'])}")
    return res


def back_image(printing_id):
    """Real back face of a double-faced card (deck_check gives the front only). None for split/adventure cards."""
    import certifi
    req = urllib.request.Request(f"https://api.scryfall.com/cards/{printing_id}",
                                 headers={"User-Agent": "edh-companion-present/1.0", "Accept": "application/json"})
    time.sleep(0.1)  # Scryfall asks for 50-100 ms between API calls
    with urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context(cafile=certifi.where())) as r:
        faces = json.load(r).get("card_faces") or []
    return ((faces[1].get("image_uris") or {}).get("normal")) if len(faces) > 1 else None


def video_link(url, ts):
    """Link that starts the video at mm:ss or h:mm:ss."""
    secs = 0
    for part in ts.split(":"):
        secs = secs * 60 + int(part)
    u = urllib.parse.urlparse(url)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(u.query) if k != "t"] + [("t", f"{secs}s")]
    return urllib.parse.urlunparse(u._replace(query=urllib.parse.urlencode(q)))


def theme_setup(brews):
    """Theme pills exist only when a build has a theme policy or themed cards. Returns (site theme, label map)."""
    used = {c.get("theme") for b in brews for c in b["deck"]}
    policy = any((b.get("theme_policy") or {}).get("mode") not in (None, "none") for b in brews)
    if not policy and not used & {"on_theme", "exception", "off_theme"}:
        return None, {}
    labels = {"on_theme": "On theme", "exception": "Exception", "off_theme": "off-theme"}
    mode = next((b["theme_policy"]["mode"] for b in brews if b.get("theme_policy")), None) or "prefer"
    site = {"mode": mode, "labels": [{"label": "On theme"}] + ([{"label": "Exception"}] if "exception" in used else [])}
    return site, labels


def md_sections(path):
    """PROJECT.md as {heading: [non-empty lines]} plus its title. Shown as text, never parsed into rules."""
    if not os.path.exists(path):
        return {}, None
    text = open(path, encoding="utf-8").read()
    title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), None)
    out = {}
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        head, *body = block.splitlines()
        out[head.strip()] = [l.strip().lstrip("-* ").strip() for l in body if l.strip()]
    return out, title


def decision_lines(ws):
    p = os.path.join(ws, "DECISIONS.md")
    return [l.strip()[2:] for l in open(p, encoding="utf-8") if l.strip().startswith(("- ", "* "))] if os.path.exists(p) else []


def shown_validation(brew, audit, current_hash):
    """Derive the audit state; never upgrade it. Checks show only for a current audit."""
    if not audit:
        return {"state": "not audited", "note": None}
    seen = (audit.get("subject") or {}).get("deck") or {}
    v = {"state": audit["verdict"]["status"], "audited": audit.get("created"), "note": None}
    if seen.get("version") != brew["version"] or seen.get("deck_hash") != brew["deck_hash"]:
        v.update(state="audit out of date", note=f"the audit checked v{seen.get('version')} ({seen.get('deck_hash')}); this is "
                 f"v{brew['version']} ({brew['deck_hash']}), so its results are not shown")
    elif current_hash != brew["deck_hash"]:
        v.update(state="audit out of date", note=f"the card list hashes to {current_hash}, not the recorded {brew['deck_hash']}: it changed after the audit")
    else:
        v["checks"] = [{k: c.get(k) for k in ("id", "area", "requirement", "kind", "status", "detail")} for c in audit["checks"]]
        v["verdict"] = audit["verdict"]
        v["independent"] = audit["auditor"].get("independent")
    return v


def research_parts(research, D):
    """Sources (with timestamp links), community takes, YouTube list and the accuracy findings from research.json."""
    src_by_id, community, youtube, cites = {}, [], [], {}
    for f in research["findings"]:
        for e in f["evidence"]:
            cites.setdefault(e, []).append(f["claim"])
    for s in research["sources"]:
        src_by_id[s["id"]] = s
        loc = [s.get("author"), f"{s['sample_size']:,} decks" if s.get("sample_size") else None, "primary source" if s.get("primary") else None]
        D["sources"].append({"title": s["title"], "url": s["url"], "kind": s["type"], "date": s.get("published") or s.get("accessed"),
                             "locator": " · ".join(x for x in loc if x), "used_for": "; ".join(cites.get(s["id"], [])) or None,
                             "links": [{"label": t, "url": video_link(s["url"], t)} for t in s.get("timestamps", [])]})
        if s["type"] == "video":
            youtube.append({"title": s["title"], "url": s["url"], "channel": s.get("author"), "date": s.get("published")})
    findings, counts = [], {}
    for f in research["findings"]:
        counts[CLASS_LABEL[f["class"]]] = counts.get(CLASS_LABEL[f["class"]], 0) + 1
        srcs = [src_by_id[e] for e in f["evidence"] if e in src_by_id]
        if f["class"] == "community_opinion" and srcs:
            s = srcs[0]
            url = video_link(s["url"], s["timestamps"][0]) if s.get("timestamps") else s["url"]
            community.append({"text": f["claim"], "source": f"{s['title']} · {f['confidence']} confidence", "url": url, "date": s.get("published")})
        elif f["class"] != "unresolved":
            findings.append({"id": f["id"], "claim": f["claim"], "class": CLASS_LABEL[f["class"]], "confidence": f["confidence"],
                             "sources": [{"title": s["title"], "url": s["url"]} for s in srcs]})
    D["accuracy"] = {"counts": list(counts.items()), "findings": findings,
                     "unverified": [{"text": f["claim"], "where": f["id"]} for f in research["findings"] if f["class"] == "unresolved"]
                     + [{"text": g, "where": "research gap"} for g in research.get("gaps", [])]}
    D["data_dates"]["research"] = research.get("created")
    return community, youtube


def build(a):
    ws = os.path.abspath(a.workspace)
    errs = contract_errors(ws)
    if errs:
        sys.exit("project fails companion.py validate (fix it, then rebuild):\n" + "\n".join(errs[:30]))
    research = opt(os.path.join(ws, "research.json"))
    project, ptitle = md_sections(os.path.join(ws, "PROJECT.md"))
    files = sorted(glob.glob(os.path.join(ws, "brew.json")) + glob.glob(os.path.join(ws, "brew-*.json")))
    if not files:
        sys.exit("no brew.json or brew-<variant>.json in the project: nothing to present as a deck page")
    builds = []
    for f in files:
        name = os.path.basename(f)
        brew = load(f)
        vid = name[5:-5] if name.startswith("brew-") else (brew.get("variant") or "main")
        builds.append({"file": f, "id": vid, "brew": brew, "audit": opt(os.path.join(ws, name.replace("brew", "audit", 1)))})
    decisions = decision_lines(ws)
    D = {"schema": 2, "title": "", "subtitle": "", "generated": time.strftime("%Y-%m-%d"), "tiers": [], "groups": [],
         "images": {f"back_{STD_BACK}": f"https://backs.scryfall.io/normal/{STD_BACK[0]}/{STD_BACK[1]}/{STD_BACK}.jpg"},
         "default_back": f"back_{STD_BACK}", "sources": [], "accuracy": {}, "data_dates": {}, "fan": []}
    D["page"], D["viewer"] = page_settings(a)
    D["theme"], tlabel = theme_setup([b["brew"] for b in builds])
    report = {"inputs": [], "sections": []}
    backs = {}

    def add_img(card):
        if not card.get("image"):
            return None, None
        f = card["printing_id"] + "_f"
        D["images"][f] = card["image"]
        b = None
        if " // " in (card.get("type_line") or ""):
            if card["printing_id"] not in backs:
                backs[card["printing_id"]] = back_image(card["printing_id"])
            if backs[card["printing_id"]]:
                b = card["printing_id"] + "_b"
                D["images"][b] = backs[card["printing_id"]]
        return f, b

    def price(card):
        return float(card["price_usd"]) if card.get("price_usd") else None

    community, youtube = research_parts(research, D) if research else ([], [])
    if research:
        report["inputs"].append({"file": "research.json", "version": research["version"]})
    group = {"id": "decks", "title": "Decks", "commanders": [], "swaps": []}
    D["groups"].append(group)
    swaps, decks_acc = {}, []
    with tempfile.TemporaryDirectory() as tmp:
        for B in builds:
            brew, audit = B["brew"], B["audit"]
            res = deck_check(B["file"], tmp)
            D["data_dates"]["card data and prices (Scryfall)"] = res["checked"]
            by = {c["name"].lower(): c for c in brew["deck"]}
            fails = {}
            for ch in res["checks"]:
                if ch["status"] == "fail":
                    for n in ch.get("cards") or []:
                        fails.setdefault(n, []).append(ch["requirement"])
            cards = []
            for c in res["cards"]:
                bc = by.get(c["name"].lower()) or by.get(c["name"].split(" // ")[0].lower()) or {}
                f, b = add_img(c)
                exc = next((e["reason"] for e in (brew.get("theme_policy") or {}).get("exceptions", []) if e["card"].lower() == c["name"].lower()), None)
                cards.append({"name": c["name"], "qty": c["qty"], "type": c.get("type_line"), "mv": int(c.get("cmc") or 0),
                              "land": "Land" in (c.get("type_line") or "").split("//")[0], "commander": c["commander"],
                              "set": c["set"], "cn": c["collector_number"], "price": price(c), "theme": tlabel.get(bc.get("theme")),
                              "img": f, "back": b, "role": bc.get("role"), "flags": fails.get(c["name"], []), "mana": c.get("mana_cost"),
                              "gc": c["game_changer"], "reason": (exc or bc.get("note")) if bc.get("theme") in ("exception", "off_theme") else None})
            s = res["stats"]
            roles = {}
            for c in brew["deck"]:
                roles[c["role"]] = roles.get(c["role"], 0) + c["qty"]
            tmpl = {"lands": [s["lands"], *TEMPLATE_RANGES["lands"]]}
            tmpl.update({r: [roles[r], *TEMPLATE_RANGES[r]] for r in ("ramp", "draw", "removal", "wipe") if r in roles})
            stats = {"price": s["price_usd"], "price_note": s.get("price_note"), "unpriced": [c["name"] for c in cards if c["price"] is None],
                     "avg_mv": s["average_mv"], "lands": s["lands"], "game_changers": s["game_changers"], "curve": s["curve"], "types": s["types"]}
            if len(tmpl) > 1:
                stats.update(template=tmpl, template_source="Typical ranges for a Commander deck, not rules. Role counts use the one role "
                             "the brew gave each card; lands are counted from card types.")
            theme = None
            if D["theme"]:
                cnt = {}
                for c in cards:
                    if not c["commander"] and c["theme"]:
                        cnt[c["theme"]] = cnt.get(c["theme"], 0) + c["qty"]
                total = sum(cnt.values())
                theme = {"counts": cnt, "on_theme_pct": round(100 * cnt.get(tlabel["on_theme"], 0) / total, 1) if total else None}
            st, pol, tb = brew["strategy"], brew.get("theme_policy") or {}, brew["target_bracket"]
            win = "; ".join(st.get("win_conditions", [])) + (f". Intended win turn: {tb['intended_win_turn']}." if tb.get("intended_win_turn") else "")
            secs = [("Why this commander", [brew["commander"]["rationale"]]), ("Archetype", [st["archetype"]]),
                    ("Key synergies", st.get("key_synergies", [])), ("Bracket restrictions", tb.get("restrictions", [])),
                    ("Theme exceptions", [f"{e['card']}: {e['reason']} (approved by {e['approved_by']})" for e in pol.get("exceptions", [])]),
                    ("Open theme questions", pol.get("unresolved", [])),
                    ("Alternatives considered", [f"{x['option']}: {x['why']}" for x in brew.get("alternatives", [])]),
                    ("Proposed cuts", [f"{r['cut']}: {r['reason']} ({r['id']}, {r['status']})" for r in brew["recommendations"]
                                       if r.get("cut") and not r.get("add") and r["status"] != "rejected"]),
                    ("Theme (PROJECT.md)", project.get("Theme", [])),
                    ("Player decisions (DECISIONS.md)", decisions)]
            summary = {"pitch": st["game_plan"], "wins": win or None, "sections": [{"title": t, "items": i} for t, i in secs if i], "community": community}
            cmd_names = [c["name"] for c in brew["commander"]["cards"]]
            for rc in (research or {}).get("commanders", []):
                if rc["card"]["name"] in cmd_names:
                    summary.update(strengths=rc.get("advantages", []), weaknesses=rc.get("disadvantages", []))
            val = shown_validation(brew, audit, res["deck_hash"])
            lines = [f"{c['qty']} {c['name']} ({c['set'].upper()}) {c['cn']}" for c in cards]
            ncmd = sum(c["commander"] for c in cards)
            deck = {"id": B["id"], "label": B["id"].upper() if re.fullmatch(r"b\d", B["id"]) else B["id"], "bracket": tb["bracket"],
                    "cards": cards, "stats": stats, "theme": theme, "validation": val, "summary": summary,
                    "moxfield": "Commander\n" + "\n".join(lines[:ncmd]) + "\n\nDeck\n" + "\n".join(lines[ncmd:]),
                    "errors": [f"{ch['id']}: {ch['requirement']}" + (f" ({ch['detail']})" if ch.get("detail") else "") for ch in res["checks"] if ch["status"] == "fail"]}
            cslug = slug(" ".join(cmd_names))
            cm = next((x for x in group["commanders"] if x["slug"] == cslug), None)
            if not cm:
                c0 = next(c for c in cards if c["commander"])
                cm = {"slug": cslug, "name": " / ".join(cmd_names), "img": c0["img"], "mv": c0["mv"], "decks": [], "youtube": youtube}
                group["commanders"].append(cm)
                if c0["img"]:
                    D["fan"].append(c0["img"])
            cm["decks"].append(deck)
            for r in brew["recommendations"]:
                if r["status"] != "rejected" and r.get("add"):
                    row = swaps.setdefault(r["add"].lower(), {"card": r["add"], "why": r["reason"] + (f" Trade-off: {r['tradeoffs']}" if r.get("tradeoffs") else ""),
                                                              "theme": tlabel.get(r.get("theme")), "fits": []})
                    row["fits"].append({"deck": f"{cslug}/{B['id']}", "swap_out": r.get("cut") or "", "note": f"{r['id']} {r['status']}"})
            decks_acc.append({"deck": f"{cm['name']} {deck['label']}", "state": val["state"], "audited": val.get("audited"), "note": val.get("note"),
                              "verdict": (val.get("verdict") or {}).get("status"), "summary": (val.get("verdict") or {}).get("summary")})
            if audit:
                D["data_dates"][f"audit {deck['label']}"] = audit.get("created")
            report["inputs"].append({"file": os.path.basename(B["file"]), "version": brew["version"],
                                     "deck_hash": brew["deck_hash"], "audit_state": val["state"]})
        if swaps:  # card data for the proposed adds: one more deck_check call on just those names
            path = os.path.join(tmp, "recs.txt")
            open(path, "w", encoding="utf-8").write("\n".join(f"1 {r['card']}" for r in swaps.values()))
            found = {c["name"].lower(): c for c in deck_check(path, tmp)["cards"]}
            for k, row in swaps.items():
                c = found.get(k) or next((v for n, v in found.items() if n.split(" // ")[0] == k), None)
                if c:
                    row["img"], _ = add_img(c)
                    row["price"], row["set"], row["cn"] = price(c), c["set"], c["collector_number"]
            group["swaps"] = list(swaps.values())
    D["accuracy"]["decks"] = decks_acc
    first = group["commanders"][0]
    D["default_bracket"] = first["decks"][0]["bracket"]
    D["title"] = a.title or ptitle or f"{first['name']} decks"
    decks = [d for c in group["commanders"] for d in c["decks"]]
    D["subtitle"] = a.subtitle or " · ".join(x for x in [" ".join(project.get("Goal", [])), builds[0]["brew"]["strategy"]["archetype"],
                                                          "builds " + ", ".join(d["label"] for d in decks) if len(decks) > 1 else None] if x)
    report["sections"] = sections(D, decks, group, community, youtube)
    a.out = a.out or os.path.join(ws, "reports", "page-data.json")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    tmpd = a.out + ".tmp"
    json.dump(D, open(tmpd, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    os.replace(tmpd, a.out)
    report.update(out=os.path.abspath(a.out), decks=[f"{d['label']}: {d['validation']['state']}" for d in decks],
                  swaps=len(group["swaps"]), sources=len(D["sources"]), images=len(D["images"]))
    write_checks(os.path.join(os.path.dirname(os.path.abspath(a.out)), "presentation-checks.md"), report, D)
    print(json.dumps(report, indent=1))


def write_checks(path, report, D):
    """presentation-checks.md skeleton: what the page was built from and what it shows; the skill adds test results."""
    rows = ["# Presentation checks", "", f"Built {D['generated']} · style {D['page']['style']} · images {D['page']['images']}", "",
            "## Inputs", "| File | Version | Deck hash | Audit state shown |", "|---|---|---|---|"]
    rows += [f"| {i['file']} | {i.get('version') or ''} | {i.get('deck_hash') or ''} | {i.get('audit_state') or ''} |" for i in report["inputs"]]
    rows += ["", "## Sections", "| Section | Shown | Why not |", "|---|---|---|"]
    rows += [f"| {x['name']} | {'yes' if x['included'] else 'no'} | {x['why_not'] or ''} |" for x in report["sections"]]
    rows += ["", "## Browser and accessibility", "Not run yet: widths, light/dark, console errors, overflow, viewer, build switch, sources, axe-core results.", ""]
    with open(path, "w", encoding="utf-8", newline="\n") as h:
        h.write("\n".join(rows))


def sections(D, decks, group, community, youtube):
    """What the page shows and why the rest is missing (for presentation-checks.md)."""
    show = D["page"]["show"]
    audited = any(d["validation"].get("checks") for d in decks)
    rows = [("overview and decklist", True, None),
            ("charts (curve, types)", show["charts"], "hidden by page style"),
            ("cards to consider", bool(show["swaps"] and group["swaps"]), "hidden by page style" if not show["swaps"] else "no open recommendation adds a card"),
            ("audit checks", audited, "no build has a current audit"),
            ("community takes", bool(community or youtube), "no community_opinion findings or video sources"),
            ("sources & accuracy", bool(show["sources"]), "hidden by page style"),
            ("theme pills", bool(D["theme"]), "no theme policy or themed cards"),
            ("tier lists", False, "the project has no per-card inclusion stats"),
            ("cast-by-turn simulation", False, "no simulation data in the project; never estimated"),
            ("price ladders and price styles", False, "only the listed printing's price is known"),
            ("pips vs sources chart", False, "mana sources aren't in deck_check output")]
    return [{"name": n, "included": bool(inc), "why_not": None if inc else why} for n, inc, why in rows]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("from-workspace", help="build the page data from a project folder")
    s.add_argument("workspace", metavar="PROJECT"); s.add_argument("--out", help="default: PROJECT/reports/page-data.json"); s.add_argument("--title"); s.add_argument("--subtitle")
    s.add_argument("--style", choices=sorted(PRESETS), default="fancy", help="page preset (fancy is the full page)")
    s.add_argument("--images", choices=["atlas", "cdn", "none"], help="where card images come from (default: the style's)")
    s.add_argument("--viewer", choices=["simple", "3d"], help="card viewer: simple (CSS) or 3d (three.js). Default: the style's")
    s.add_argument("--show", help=f"comma list of sections to turn on ({', '.join(SECTIONS)})")
    s.add_argument("--hide", help="comma list of sections to turn off")
    s.set_defaults(f=build)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
