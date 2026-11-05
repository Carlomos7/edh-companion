#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "jsonschema>=4.18", "certifi", "pillow"]
# ///
"""Build the page data for the template from project files, so no number on the page is typed by hand.

  site_data.py from-workspace PROJECT  [--out PROJECT/reports/page-data.json] [common flags]
  site_data.py from-showcase SHOWCASE  [--out SHOWCASE/report/page-data.json] [common flags]
  common flags: [--mode summary|interactive|showcase] [--theme FILE|JSON] [--title T] [--subtitle S]
                [--style fancy|basic] [--images atlas|cdn|none] [--viewer simple|3d] [--show a,b] [--hide a,b]
                [--include-notes]

A project gives PROJECT.md, DECISIONS.md, research.json (all optional) and brew.json / brew-<variant>.json, each paired
with audit.json / audit-<variant>.json. A project needs a brew file or research.json. Card data (names, printings,
images, prices, Oracle-text roles, mana, cast-by-turn, price ladder) comes from the audit skill's deck_check.py.
Projects that fail `companion.py validate` are refused. The audit state is derived, never upgraded: no audit file ->
"not audited"; audit of another version or hash -> "audit out of date"; else the audit verdict.
Presentation views (findings, disagreements, sources, audit, recommendations, notices, hero, card types) come from
views.py, colours from palette.py. Private notes (DECISIONS.md lines, PROJECT.md text) are left out unless
--include-notes, and so are quotes of them (or of STATE.md) inside research, audit and recommendation text: each becomes
"[private note]" and the privacy notice says how many. STATE.md is read only for that.

A showcase is a folder with showcase.yaml (title, mode, theme, projects[] with project path relative to
<workspace>/projects = SHOWCASE/../../projects, or absolute, plus optional group and theme). Project files are only read.

Modes: showcase = every section, 3D viewer, card fan (default); interactive = same data, simple CSS viewer, no fan,
minimal animation; summary = reports/summary.md only (Markdown). --style basic = no images or charts.
Writes presentation-checks.md next to the output with the inputs, sections and theme source.
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
DECK_CHECK = os.path.normpath(os.path.join(HERE, "..", "..", "audit", "scripts", "deck_check.py"))
PLUGIN_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts"))
sys.path.insert(0, HERE)
import palette as artpal, views  # noqa: E402  (site_data.palette() below is the legacy accent pair)
# shortcut: every single-faced card shows Magic's standard back; deck_check has no card_back_id. Upgrade if it adds one.
STD_BACK = "0aeebaf5-8c7d-4636-9e82-8c27447861f7"
TEMPLATE_RANGES = {"lands": (35, 38), "ramp": (8, 12), "draw": (8, 12), "removal": (8, 12), "wipe": (2, 4)}
CLASS_LABEL, BRACKETS = views.CLASS_LABEL, views.BRACKETS  # one label set for the page, the summary and the docs

SECTIONS = ("charts", "swaps", "sources", "fan", "prices", "viewer")
ALL = dict.fromkeys(SECTIONS, True)
PRESETS = {
    "showcase": {"show": ALL, "images": "atlas", "viewer": "three", "calm": False},
    "interactive": {"show": dict(ALL, fan=False), "images": "atlas", "viewer": "simple", "calm": True},
    "summary": {"show": dict(ALL, charts=False, fan=False, viewer=False), "images": "none", "viewer": "simple", "calm": True},
    "basic": {"show": {"charts": False, "swaps": False, "sources": True, "fan": False, "prices": True, "viewer": False},
              "images": "none", "viewer": "simple", "calm": False},
}


def page_settings(a):
    """Mode (or --style basic) preset, then the player's overrides. Returns (page, viewer)."""
    name = "basic" if a.style == "basic" else a.mode
    p = PRESETS[name]
    show = dict(p["show"])
    for flag, val in (("show", True), ("hide", False)):
        for s in filter(None, (getattr(a, flag) or "").split(",")):
            s = s.strip()
            if s not in SECTIONS:
                sys.exit(f"unknown section '{s}': choose from {', '.join(SECTIONS)}")
            show[s] = val
    images = a.images or p["images"]
    viewer = {"3d": "three", "simple": "simple"}.get(a.viewer) or p["viewer"]
    if images == "none":
        show["viewer"] = show["fan"] = False  # nothing to show without images
    style = name if not (a.images or a.viewer or a.show or a.hide) else "custom"
    return {"style": style, "mode": a.mode, "show": show, "images": images, "calm": p["calm"]}, viewer


def load(path):
    import yaml
    with open(path, encoding="utf-8") as h:
        return yaml.safe_load(h) if path.endswith((".yaml", ".yml")) else json.load(h)


def opt(path):
    return load(path) if os.path.exists(path) else None


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def contract_errors(ws):
    """Run the plugin's project validator (scripts/companion.py validate)."""
    sys.path.insert(0, PLUGIN_SCRIPTS)
    import companion
    return companion.validate(ws)[0]


def deck_check(deck_path, tmp, project, cheapest=False, cards_only=False):
    """Run deck_check.py (card facts from Scryfall, served from the shared cache) and return its JSON. `project` is the
    project folder: its research preferences decide which providers may be called.
    Exit codes 1/2 are check results, not errors. Cards it has no data for are listed in "unavailable", not fatal."""
    uv = shutil.which("uv") or sys.exit("uv not found: deck_check.py runs with `uv run --script`")
    out = os.path.join(tmp, f"check-{len(os.listdir(tmp))}.json")
    p = subprocess.run([uv, "run", "--quiet", "--script", DECK_CHECK, deck_path, "--json", out, "--no-combos", "--project", project]
                       + (["--cheapest"] if cheapest else []) + (["--cards-only"] if cards_only else []),
                       capture_output=True, text=True, encoding="utf-8")
    if not os.path.exists(out):
        sys.exit(f"deck_check.py failed on {deck_path}: {(p.stderr or p.stdout).strip()[:500]}")
    return json.load(open(out, encoding="utf-8"))


def note_unavailable(site, res, where):
    """Show missing or stale card data on the page (sources & accuracy, and a notice) instead of failing the build."""
    v = (res.get("data") or {}).get("verification")
    items = list(res.get("unavailable") or []) + ([f"card data {v} (as of {res['data'].get('as_of')})"] if v in ("stale", "unavailable") else [])
    site.D["accuracy"]["unverified"] += [{"text": x, "where": where} for x in items]
    if v in ("stale", "unavailable"):
        site.notice("warn", f"Card data is {v} (as of {res['data'].get('as_of') or 'unknown'}, {where}): prices, legality and printings may have changed.")
    for x in res.get("unavailable") or []:
        site.notice("warn", f"{x} ({where}).")


video_link = views.time_url  # one link rule for every timestamp on the page


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


def private_lines(ws):
    """Every non-heading line of DECISIONS.md and PROJECT.md (what page text must not quote without --include-notes).
    STATE.md isn't scanned: it's a progress log that restates the audit and research, so its overlap with them is
    those files' own public facts, not a leak (STATE.md itself is still never put on the page)."""
    out = []
    for f in ("DECISIONS.md", "PROJECT.md"):
        p = os.path.join(ws, f)
        if os.path.exists(p):
            out += [l.strip().lstrip("-*").strip() for l in open(p, encoding="utf-8") if l.strip() and not l.lstrip().startswith("#")]
    return out


def json_strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, (dict, list)):
        for v in (o.values() if isinstance(o, dict) else o):
            yield from json_strings(v)


def card_names(o):
    """Card names in a project file: "name", "card", "add", "cut" strings and "cards" lists, at any depth."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("name", "card", "add", "cut") and isinstance(v, str):
                yield v
            elif k == "cards" and isinstance(v, list):
                yield from (x for x in v if isinstance(x, str))
            yield from card_names(v)
    elif isinstance(o, list):
        for v in o:
            yield from card_names(v)


# not page text, or not from research, audit or recommendations (accuracy is walked for "unverified" only)
PRIVATE_SKIP = {"images", "look", "page", "viewer", "fan", "data_dates", "notices", "sources", "tiers", "validation", "errors",
                "community", "youtube", "moxfield", "url", "img", "back", "accuracy", "title"}
PRIVATE_NOTICE = ("Private notes (DECISIONS.md, PROJECT.md text, STATE.md) are not included in this page{}; "
                  "rebuild with --include-notes for your own copy.")


def hide_private(site):
    """Replace quotes of private notes in page-bound text (views.Redactor); say how many in the privacy notice."""
    R = views.Redactor(site.private, site.public, site.names)

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k not in PRIVATE_SKIP:
                    o[k] = walk(v)
        elif isinstance(o, list):
            o[:] = [walk(v) for v in o]
        elif isinstance(o, str):
            return R(o)
        return o
    walk(site.D)
    walk(site.D["accuracy"]["unverified"])
    for n in site.D["notices"]:
        if n["text"] == PRIVATE_NOTICE.format("") and R.count:
            n["text"] = PRIVATE_NOTICE.format(f"; {R.count} quoted private note{'s were' if R.count != 1 else ' was'} hidden")
    site.report["private_quotes_hidden"] = R.count


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


def rule0_rows(tb, gcs):
    """Rule 0 rows [{label, value}]. A Game Changer restriction folds into the Game Changers row ("Fierce Guardianship,
    Mystical Tutor (max 3)"); only a bare "no Game Changers" next to an empty list is dropped, since the row says None."""
    gc_rules = [r for r in tb.get("restrictions", []) if "game changer" in r.lower()]
    limits = []
    for r in gc_rules:
        rest = " ".join(re.sub(r"\bgame changers?\b", " ", r, flags=re.I).split()).strip(" ,;:.-")
        if not (not gcs and rest.lower() == "no"):
            limits.append(r if rest.lower() in ("", "no", "none") else rest)
    rows = [{"label": "Bracket", "value": f"{tb['bracket']} ({BRACKETS[tb['bracket']]})"},
            {"label": "Game Changers", "value": (", ".join(gcs) if gcs else "None") + (f" ({'; '.join(limits)})" if limits else "")}]
    rows += [{"label": "Restrictions", "value": r} for r in tb.get("restrictions", []) if r not in gc_rules]
    return rows + ([{"label": "Win turn", "value": str(tb["intended_win_turn"])}] if tb.get("intended_win_turn") else [])


# ---------- report look: accent colors from the commander's color identity or a saved theme ----------
COLORS = "WUBRG"
HUES = {"W": "#a08c5b", "U": "#1f6fd1", "B": "#6b4c9a", "R": "#d0312d", "G": "#2e8b47"}
GOLD, NEUTRAL = "#b08d2f", "#5a6678"  # 3+ colors: one muted gold, never a rainbow
LIGHT_BG = ("#ffffff", "#eef1f6", "#e3e8f1")  # template --surface, --bg, --surface-2 (light)
DARK_BG = ("#0d111a", "#161c29", "#222a3b")   # the same tokens in dark mode
LOOK_STYLES = ("comic", "gothic", "flames")


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(h):
    lin = [(x / 255 / 12.92) if x / 255 <= .03928 else ((x / 255 + .055) / 1.055) ** 2.4 for x in _rgb(h)]
    return .2126 * lin[0] + .7152 * lin[1] + .0722 * lin[2]


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + .05) / (lo + .05)


def readable(h, dark):
    """The hue, darkened (light mode) or lightened (dark mode) until it has 4.5:1 on every page background."""
    bgs, to = (DARK_BG, 255) if dark else (LIGHT_BG, 0)
    for i in range(0, 101, 2):
        c = "#" + "".join(f"{round(x + (to - x) * i / 100):02x}" for x in _rgb(h))
        if min(contrast(c, b) for b in bgs) >= 4.5:
            return c
    return "#ffffff" if dark else "#000000"


def identity_hues(identity):
    ci = [c for c in COLORS if c in (identity or [])]
    if not ci:
        return NEUTRAL, NEUTRAL
    if len(ci) >= 3:
        return GOLD, GOLD
    return HUES[ci[0]], HUES[ci[-1]]


def palette(a1, a2=None, **meta):
    return {"l": {"a": readable(a1, False), "a2": readable(a2 or a1, False)},
            "d": {"a": readable(a1, True), "a2": readable(a2 or a1, True)}, **meta}


def theme_cfg(cfg, where):
    """Check a saved or given theme: {accent, accent2?, style?, label?}."""
    hexok = lambda v: isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v)
    if not isinstance(cfg, dict) or not hexok(cfg.get("accent")) or (cfg.get("accent2") is not None and not hexok(cfg["accent2"])):
        sys.exit(f"{where}: a theme needs accent (and optional accent2) as #rrggbb")
    if cfg.get("style") not in (None, *LOOK_STYLES):
        sys.exit(f"{where}: style must be one of {', '.join(LOOK_STYLES)} or null")
    return cfg


def resolve_look(candidates, identity=None):
    """candidates: [(source, theme or None)] highest precedence first. Then the commander's color identity
    (a list; [] = colorless), then neutral (identity None: views that show several commanders)."""
    for src, cfg in candidates:
        if cfg:
            c = theme_cfg(cfg, src)
            return palette(c["accent"], c.get("accent2"), source=src, label=c.get("label"), style=c.get("style"))
    if identity is not None:
        ci = "".join(c for c in COLORS if c in identity) or "colorless"
        return palette(*identity_hues(identity), source=f"commander color identity ({ci})", label=None, style=None)
    return palette(NEUTRAL, source="neutral", label=None, style=None)


def theme_arg(s):
    if not s:
        return None
    return load(s) if os.path.exists(s) else json.loads(s)


def look_for(candidates, identity=None, art_url=None, fetch=True):
    """resolve_look plus look.palette (full light/dark roles): explicit theme > commander artwork > identity > neutral.
    The art crop comes from the shared image cache (downloaded once); offline or unreadable art falls back."""
    look = resolve_look(candidates, identity)
    theme = next((c for _, c in candidates if c), None)
    art = artpal.art_file(art_url) if art_url and fetch and not theme else None
    look["palette"] = artpal.resolve(theme, art, identity_hues(identity) if identity else None, NEUTRAL)
    return look


# ---------- one report, many projects ----------
class Site:
    def __init__(self, a, multi):
        self.a, self.multi, self.tmp = a, multi, tempfile.mkdtemp()
        self.D = {"schema": 3, "title": "", "subtitle": "", "generated": time.strftime("%Y-%m-%d"), "tiers": [], "groups": [], "rankings": [],
                  "research": [], "images": {f"back_{STD_BACK}": f"https://backs.scryfall.io/normal/{STD_BACK[0]}/{STD_BACK[1]}/{STD_BACK}.jpg"},
                  "default_back": f"back_{STD_BACK}", "sources": [], "data_dates": {}, "fan": [], "multi": multi,
                  "accuracy": {"counts": {}, "findings": [], "unverified": [], "decks": []},
                  "notices": [], "findings_view": [], "disagreements_view": [], "sources_view": [], "research_tab": []}
        self.D["page"], self.D["viewer"] = page_settings(a)
        self.report = {"inputs": [], "sections": [], "looks": []}
        self.swaps, self.swap_cards, self.cms, self.slugs, self.titles = {}, {}, {}, set(), []
        self.brews, self.researches, self.recs, self.hero_in = [], [], [], {}
        self.notes = bool(getattr(a, "include_notes", False))
        self.rslug, self.private, self.public, self.names = {}, [], [], set()  # anchors; quote hiding (views.Redactor)
        self.fetch_art = self.D["page"]["mode"] != "summary"

    def notice(self, level, text, proj=None):
        text = f"{proj}: {text}" if proj else text
        if all(n["text"] != text for n in self.D["notices"]):
            self.D["notices"].append({"level": level, "text": text, "project": proj})

    def add_img(self, card):
        if not card.get("image") or self.D["page"]["images"] == "none":
            return None, None
        f = card["printing_id"] + "_f"
        self.D["images"][f] = card["image"]
        b = None
        if card.get("back_image"):  # deck_check sets it only for real double-faced cards (not split or adventure)
            b = card["printing_id"] + "_b"
            self.D["images"][b] = card["back_image"]
        return f, b

    def lookup(self, refs, project):
        """Card data for loose card names (research commanders, rankings, recommended adds): one deck_check call."""
        if not refs:
            return {}
        path = os.path.join(self.tmp, f"lookup-{len(os.listdir(self.tmp))}.txt")
        lines = [f"1 {r['name']}" + (f" ({r['set'].upper()}) {r['collector_number']}" if r.get("set") and r.get("collector_number") else "") for r in refs]
        open(path, "w", encoding="utf-8").write("\n".join(lines))
        out, res = {}, deck_check(path, self.tmp, project, cards_only=True)
        note_unavailable(self, res, "card lookup")
        for c in res["cards"]:
            out[c["name"].lower()] = c
            out.setdefault(c["name"].split(" // ")[0].lower(), c)
        return out

    def group(self, title):
        g = next((x for x in self.D["groups"] if x["title"] == title), None)
        if not g:
            gid, n = slug(title) or "decks", 2
            while any(x["id"] == gid for x in self.D["groups"]):
                gid, n = f"{slug(title)}-{n}", n + 1
            g = {"id": gid, "title": title, "commanders": [], "swaps": [], "alts": []}
            self.D["groups"].append(g)
        return g


def research_parts(site, research, proj):
    """Sources (with timestamp links), community takes, YouTube list and the accuracy findings from research.json."""
    D, A = site.D, site.D["accuracy"]
    src_by_id, community, youtube, cites = {}, [], [], {}
    for f in research["findings"]:
        for e in f["evidence"]:
            cites.setdefault(e, []).append(f["claim"])
    for s in research["sources"]:
        src_by_id[s["id"]] = s
        loc = [s.get("author"), f"{s['sample_size']:,} decks" if s.get("sample_size") else None, "primary source" if s.get("primary") else None]
        D["sources"].append({"title": s["title"], "url": s["url"], "kind": s["type"], "date": s.get("published") or s.get("accessed"), "project": proj,
                             "locator": " · ".join(x for x in loc if x), "used_for": "; ".join(cites.get(s["id"], [])) or None,
                             "links": [{"label": t, "url": video_link(s["url"], t)} for t in s.get("timestamps", [])]})
        if s["type"] == "video":
            youtube.append({"title": s["title"], "url": s["url"], "channel": s.get("author"), "date": s.get("published")})
    for f in research["findings"]:
        A["counts"][CLASS_LABEL[f["class"]]] = A["counts"].get(CLASS_LABEL[f["class"]], 0) + 1
        srcs = [src_by_id[e] for e in f["evidence"] if e in src_by_id]
        if f["class"] == "community_opinion" and srcs:
            s = srcs[0]
            url = video_link(s["url"], s["timestamps"][0]) if s.get("timestamps") else s["url"]
            community.append({"text": f["claim"], "source": f"{s['title']} · {f['confidence']} confidence", "url": url, "date": s.get("published")})
        elif f["class"] != "unresolved":
            A["findings"].append({"id": f["id"], "claim": f["claim"], "class": CLASS_LABEL[f["class"]], "confidence": f["confidence"], "project": proj,
                                  "sources": [{"title": s["title"], "url": s["url"]} for s in srcs]})
    A["unverified"] += [{"text": f["claim"], "where": f["id"] + (f" ({proj})" if proj else "")} for f in research["findings"] if f["class"] == "unresolved"]
    A["unverified"] += [{"text": g, "where": "research gap" + (f" ({proj})" if proj else "")} for g in research.get("gaps", [])]
    D["data_dates"]["research" + (f" ({proj})" if proj else "")] = research.get("created")
    fnd = {f["id"]: f for f in research["findings"]}

    def links(refs):
        """Evidence ids -> source links; a finding id stands for its own sources."""
        ids = []
        for r in refs or []:
            for x in ([r] if r in src_by_id else fnd.get(r, {}).get("evidence", [])):
                if x in src_by_id and x not in ids:
                    ids.append(x)
        return [{"title": src_by_id[x]["title"], "url": src_by_id[x]["url"]} for x in ids]
    return community, youtube, links


def status_of(card, data=None):
    """Legality status: research data wins (it was checked when ranked), else deck_check's."""
    st = (data or {}).get("status") or (card or {}).get("status")
    rel = (data or {}).get("releases") or (card or {}).get("releases")
    return (st if st in ("upcoming", "banned", "not_legal") else None), (rel if st == "upcoming" else None)


def research_views(site, research, proj, title, links, built, groups, ws, deck_names=()):
    """Commanders compared and rankings tabs. A research-only project gets its own research tab; otherwise the
    commanders go into the deck tabs of that project as a compact comparison. Every project with research content
    also gets a research_tab entry (candidates, recommendations, gaps, next steps; findings live in findings_view)."""
    refs = ([c["card"] for c in research.get("commanders", [])] + [x["card"] for r in research.get("rankings", []) for x in r["cards"]]
            + [c["card"] for c in research.get("card_candidates", [])])
    found = site.lookup(refs, ws)
    card = lambda ref: found.get(ref["name"].lower()) or found.get(ref["name"].split(" // ")[0].lower()) or {}
    rows = []
    for c in research.get("commanders", []):
        k = card(c["card"])
        rows.append({"name": c["card"]["name"], "img": site.add_img(k)[0] if k else None, "strategy": c["strategy"], "advantages": c.get("advantages", []),
                     "disadvantages": c.get("disadvantages", []), "theme_fit": c.get("theme_fit"), "legal_check": c.get("legal_check"),
                     "evidence": links(c["evidence"]), "built": c["card"]["name"] in built, "project": proj,
                     "set": k.get("set"), "cn": k.get("collector_number")})
    for r in research.get("rankings", []):
        rid, n = slug(f"{proj or ''} {r['group']}") or "ranking", 2
        while any(x["id"] == rid for x in site.D["rankings"]):
            rid, n = f"{slug(f'{proj or ''} {r['group']}')}-{n}", n + 1
        cards = []
        for x in sorted(r["cards"], key=lambda x: x["rank"]):
            k = card(x["card"])
            f, b = site.add_img(k) if k else (None, None)
            st, rel = status_of(k, x)
            cards.append({"name": x["card"]["name"], "img": f, "back": b, "rank": x["rank"], "tier": x.get("tier"), "pct": x.get("inclusion_pct"),
                          "decks": x.get("decks"), "n": x.get("total_decks"), "why": x["why"], "evidence": links(x["evidence"]),
                          "status": st, "releases": rel, "set": k.get("set"), "cn": k.get("collector_number"), "type": k.get("type_line"),
                          **(views.card_types(k) if k else {})})
        site.D["rankings"].append({"id": rid, "title": r["group"], "project": proj, "scope": r.get("scope"), "method": r["method"],
                                   "as_of": r.get("as_of"), "cards": cards})
    if groups:
        for g in groups:
            g["alts"] += [x for x in rows if not any(y["name"] == x["name"] and y["project"] == proj for y in g["alts"])]
    elif rows or research.get("disagreements") or research.get("findings"):
        site.D["research"].append({"id": slug(f"research {proj or ''}"), "title": "Research" + (f": {title}" if site.multi else ""), "project": proj,
                                   "question": research["scope"]["question"], "commanders": rows,
                                   "disagreements": [{"topic": d["topic"], "explanation": d.get("explanation"),
                                                      "positions": [{"position": p["position"], "sources": links(p["evidence"])} for p in d["positions"]]}
                                                     for d in research.get("disagreements", [])],
                                   "feasibility": (research.get("feasibility") or {}).get("verdict")})
    if any(research.get(k) for k in ("findings", "disagreements", "card_candidates", "recommended_next_steps", "recommendations")):
        names = {n.lower() for n in deck_names}
        cands = []
        for c in research.get("card_candidates", []):
            k = card(c["card"])
            f, b = site.add_img(k) if k else (None, None)
            cands.append({"name": c["card"]["name"], "img": f, "back": b, "set": k.get("set"), "cn": k.get("collector_number"),
                          "relevance": c["relevance"], "synergy": c.get("synergy"), "role": c.get("role"), "theme_fit": c.get("theme_fit"),
                          "in_deck": c["card"]["name"].lower() in names, "_ev": c.get("evidence", []), **(views.card_types(k) if k else {})})
        site.D["research_tab"].append({
            "id": slug(f"research-tab {proj or ''}"), "title": "Research" + (f": {title}" if site.multi else ""), "project": proj,
            "has_builds": bool(groups), "question": research["scope"]["question"], "version": research["version"], "created": research.get("created"),
            "scope": {k: research["scope"].get(k) for k in ("theme", "depth")},
            "methodology": {k: v for k, v in (research.get("methodology") or {}).items() if k in ("approach", "tools_used", "tools_failed", "stopped_because") and v},
            "feasibility": research.get("feasibility"), "candidates": cands, "gaps": list(research.get("gaps", [])),
            "recommendations": [dict(r, _ev=r.get("evidence", [])) for r in research.get("recommendations", [])],
            "alternatives": [dict(x, _ev=x.get("evidence", [])) for x in research.get("alternatives", [])],
            "next_steps": list(research.get("recommended_next_steps", [])), "follow_up_questions": list(research.get("follow_up_questions", []))})


def add_project(site, ws, group_override=None, look_cands=()):
    """Read one project folder into the site. look_cands: theme sources above the project's own file, highest first."""
    a, D = site.a, site.D
    ws = os.path.abspath(ws)
    errs = contract_errors(ws)
    if errs:
        sys.exit(f"project {ws} fails companion.py validate (fix it, then rebuild):\n" + "\n".join(errs[:30]))
    pname = os.path.basename(ws.rstrip("/\\"))
    proj = pname if site.multi else None
    research = opt(os.path.join(ws, "research.json"))
    project, ptitle = md_sections(os.path.join(ws, "PROJECT.md"))
    site.titles.append((ptitle, project))
    files = sorted(glob.glob(os.path.join(ws, "brew.json")) + glob.glob(os.path.join(ws, "brew-*.json")))
    if not files and not research:
        sys.exit(f"{ws}: no brew file and no research.json: nothing to present")
    own_theme = opt(os.path.join(ws, "report-theme.yaml"))
    cands = list(look_cands) + [(f"{pname}/report-theme.yaml", own_theme)]
    builds = []
    for f in files:
        name = os.path.basename(f)
        brew = load(f)
        vid = name[5:-5] if name.startswith("brew-") else (brew.get("variant") or "main")
        builds.append({"file": f, "id": vid, "brew": brew, "audit": opt(os.path.join(ws, name.replace("brew", "audit", 1)))})
    site.brews += [b["brew"] for b in builds]
    tsite, tlabel = theme_setup([b["brew"] for b in builds])
    if tsite:
        D["theme"] = D.get("theme") or tsite
    decisions = decision_lines(ws) if site.notes else []
    if not site.notes and (decision_lines(ws) or project or os.path.exists(os.path.join(ws, "STATE.md"))):
        site.notice("info", PRIVATE_NOTICE.format(""))
    if not site.notes:  # for hide_private: what may not be quoted, and what is public anyway (the deck file, source titles, card names)
        site.private += private_lines(ws)
        for x in [b["brew"] for b in builds] + [b["audit"] for b in builds] + [research]:
            site.names.update(card_names(x))
        site.public += [t for b in builds for t in json_strings(b["brew"])]
        site.public += [s.get(k) or "" for s in (research or {}).get("sources", []) for k in ("title", "author")]
    community, youtube, links = research_parts(site, research, proj) if research else ([], [], lambda r: [])
    if research:
        site.researches.append((proj, research))
        site.rslug[proj] = pname
        site.report["inputs"].append({"file": f"{pname}/research.json" if proj else "research.json", "version": research["version"]})
    deck_names = set()
    price = lambda card: float(card["price_usd"]) if card.get("price_usd") else None
    used_groups, built = [], set()
    for B in builds:
        brew, audit = B["brew"], B["audit"]
        res = deck_check(B["file"], site.tmp, ws, cheapest=True)
        where = os.path.basename(B["file"]) + (f" ({proj})" if proj else "")
        note_unavailable(site, res, where)
        if not res.get("cards"):
            D["accuracy"]["unverified"].append({"text": f"build {B['id']} not shown: no card data", "where": where})
            continue
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
            f, b = site.add_img(c)
            exc = next((e["reason"] for e in (brew.get("theme_policy") or {}).get("exceptions", []) if e["card"].lower() == c["name"].lower()), None)
            st, rel = status_of(c)
            cards.append({"name": c["name"], "qty": c["qty"], "type": c.get("type_line"), "mv": int(c.get("cmc") or 0),
                          "land": "Land" in (c.get("type_line") or "").split("//")[0], "commander": c["commander"],
                          "set": c["set"], "cn": c["collector_number"], "price": price(c), "theme": tlabel.get(bc.get("theme")),
                          "img": f, "back": b, "roles": c.get("roles") or {}, "label": bc.get("role"), "flags": fails.get(c["name"], []),
                          "mana": c.get("mana_cost"), "gc": c["game_changer"], "status": st, "releases": rel, "cheapest": c.get("cheapest"),
                          "reason": (exc or bc.get("note")) if bc.get("theme") in ("exception", "off_theme") else None, **views.card_types(c)})
        deck_names.update(c["name"] for c in cards)
        s = res["stats"]
        roles = s.get("roles") or {}
        stats = {"price": s["price_usd"], "price_note": s.get("price_note"), "unpriced": [c["name"] for c in cards if c["price"] is None],
                 "avg_mv": s["average_mv"], "lands": s["lands"], "game_changers": s["game_changers"], "curve": s["curve"], "types": s["types"],
                 "roles": roles, "roles_note": s.get("roles_note"), "price_as_of": s.get("price_as_of"),
                 "label_diff": [{"name": c["name"], "label": c["label"], "rules": sorted(c["roles"])} for c in cards
                                if c["label"] and not c["commander"] and c["label"] not in c["roles"]]}
        for k in ("mana", "cast_by_turn", "price_ladder"):
            if s.get(k):
                stats[k] = s[k]
        stats["type_counts"], stats["mdfc_lands"] = views.type_counts(cards)  # views.card_types: one rule for groups, filters, charts
        if "roles" in s:
            stats["template"] = {"lands": [s["lands"], *TEMPLATE_RANGES["lands"]], **{r: [roles.get(r, 0), *TEMPLATE_RANGES[r]] for r in ("ramp", "draw", "removal", "wipe")}}
            stats["template_source"] = ("Typical ranges for a Commander deck, not rules. Role counts come from fixed Oracle-text rules "
                                        "(deck_check), a card can count in several roles; lands are counted from card types.")
        theme = theme_stats = None
        if tsite:
            cnt, exempt = {}, 0
            for c in cards:
                if not c["commander"] and c["theme"]:
                    cnt[c["theme"]] = cnt.get(c["theme"], 0) + c["qty"]
                elif not c["commander"]:
                    exempt += c["qty"]  # n/a or unchecked: not in the percentage
            total = sum(cnt.values())
            theme = {"counts": cnt, "on_theme_pct": round(100 * cnt.get(tlabel["on_theme"], 0) / total, 1) if total else None}
            # on_theme_pct = on / total; total = on + exception + off (commander and exempt cards left out)
            theme_stats = {"on": cnt.get(tlabel["on_theme"], 0), "exception": cnt.get(tlabel["exception"], 0), "off": cnt.get(tlabel["off_theme"], 0),
                           "exempt": exempt, "total": total}
        st, pol, tb = brew["strategy"], brew.get("theme_policy") or {}, brew["target_bracket"]
        win = "; ".join(st.get("win_conditions", [])) + (f". Intended win turn: {tb['intended_win_turn']}." if tb.get("intended_win_turn") else "")
        secs = [("Why this commander", [brew["commander"]["rationale"]]), ("Archetype", [st["archetype"]]),
                ("Key synergies", st.get("key_synergies", [])), ("Bracket restrictions", tb.get("restrictions", [])),
                ("Known limitations", brew.get("limitations", [])),
                ("Theme exceptions", [f"{e['card']}: {e['reason']} (approved by {e['approved_by']})" for e in pol.get("exceptions", [])]),
                ("Open theme questions", pol.get("unresolved", [])),
                ("Alternatives considered", [f"{x['option']}: {x['why']}" for x in brew.get("alternatives", [])]),
                ("Proposed cuts", [f"{r['cut']}: {r['reason']} ({r['id']}, {r['status']})" for r in brew["recommendations"]
                                   if r.get("cut") and not r.get("add") and r["status"] != "rejected"]),
                # the theme rules explain the badges, so they always show; PROJECT.md's own words only with --include-notes
                ("Theme rules", [x for x in [f"Mode: {pol['mode']}" if pol.get("mode") else None,
                                             f"Counts as on theme: {pol['eligibility']}" if pol.get("eligibility") else None,
                                             f"Artwork matters: {'yes' if pol['art_required'] else 'no'}" if "art_required" in pol else None] if x]),
                ("Theme (PROJECT.md)", project.get("Theme", []) if site.notes else []),
                ("Player decisions (DECISIONS.md)", decisions)]
        summary = {"pitch": st["game_plan"], "wins": win or None, "sections": [{"title": t, "items": i} for t, i in secs if i], "community": community}
        if not site.notes:
            site.public += [x for _, items in secs for x in items]  # built from brew.json ("Artwork matters: yes"): shown anyway
        cmd_names = [c["name"] for c in brew["commander"]["cards"]]
        built.update(cmd_names)
        for rc in (research or {}).get("commanders", []):
            if rc["card"]["name"] in cmd_names:
                summary.update(strengths=rc.get("advantages", []), disadvantages=rc.get("disadvantages", []))
        val = shown_validation(brew, audit, res["deck_hash"])
        lines = [f"{c['qty']} {c['name']} ({c['set'].upper()}) {c['cn']}" for c in cards]
        ncmd = sum(c["commander"] for c in cards)
        rule0_items = rule0_rows(tb, s["game_changers"])
        by_label = {}
        for x in rule0_items:
            by_label.setdefault(x["label"], []).append(x["value"])
        rule0 = "; ".join(f"{k}: {', '.join(v)}" for k, v in by_label.items())  # summary.md: each label once, its values joined
        site.public.append(rule0)  # from brew.json: never a private quote
        label = B["id"].upper() if re.fullmatch(r"b\d", B["id"]) else B["id"]
        deck = {"id": B["id"], "label": label, "bracket": tb["bracket"], "project": proj, "rule0": rule0, "rule0_items": rule0_items, "future": brew.get("future"),
                "cards": cards, "stats": stats, "theme": theme, "theme_stats": theme_stats, "validation": val, "summary": summary, "version": brew["version"],
                "archetype": st["archetype"], "audit_view": views.audit_view(audit, val),
                "moxfield": "Commander\n" + "\n".join(lines[:ncmd]) + "\n\nDeck\n" + "\n".join(lines[ncmd:]),
                "errors": [f"{ch['id']}: {ch['requirement']}" + (f" ({ch['detail']})" if ch.get("detail") else "") for ch in res["checks"] if ch["status"] == "fail"]}
        g = site.group(group_override or brew.get("group") or " / ".join(cmd_names))
        if g not in used_groups:
            used_groups.append(g)
        key = (g["id"], pname, tuple(cmd_names))
        cm = site.cms.get(key)
        if not cm:
            cslug = slug(" ".join(cmd_names))
            if cslug in site.slugs:
                cslug = slug(f"{pname} {' '.join(cmd_names)}")
            site.slugs.add(cslug)
            c0 = next((c for c in cards if c["commander"]), {"img": None, "mv": 0})  # the commander's data may be unavailable
            identity = sorted({x for c in res["cards"] if c["commander"] for x in c.get("color_identity", [])})
            art = next((c.get("art_crop") for c in res["cards"] if c["commander"]), None)
            cm = site.cms[key] = {"slug": cslug, "name": " / ".join(cmd_names), "project": proj, "img": c0["img"], "mv": c0["mv"], "decks": [],
                                  "youtube": youtube, "look": look_for(cands, identity, art, site.fetch_art)}
            site.hero_in[cslug] = (identity, art)
            g["commanders"].append(cm)
            site.report["looks"].append({"for": cm["name"] + (f" ({proj})" if proj else ""), "source": cm["look"]["source"],
                                         "palette": cm["look"]["palette"]["source"]})
            if c0["img"]:
                D["fan"].append(c0["img"])
        cm["decks"].append(deck)
        site.recs.append((deck, brew["recommendations"], proj, [c["name"] for c in cards]))
        if research:
            lists = glob.glob(os.path.join(ws, "decklists", f"{B['id']}-v*.txt"))
            for n in views.research_notices(research, brew, label if len(builds) > 1 else None, lists):
                site.notice(n["level"], n["text"], proj)
        for r in brew["recommendations"]:
            if r["status"] != "rejected" and r.get("add"):
                row = site.swaps.setdefault(g["id"], {}).setdefault(r["add"].lower(), {
                    "card": r["add"], "why": r["reason"] + (f" Trade-off: {r['tradeoffs']}" if r.get("tradeoffs") else ""), "theme": tlabel.get(r.get("theme")), "fits": []})
                row["fits"].append({"deck": f"{cm['slug']}/{B['id']}", "swap_out": r.get("cut") or "", "note": f"{r['id']} {r['status']}"})
        D["accuracy"]["decks"].append({"deck": f"{cm['name']} {label}" + (f" ({proj})" if proj else ""), "state": val["state"], "audited": val.get("audited"),
                                       "note": val.get("note"), "verdict": (val.get("verdict") or {}).get("status"), "summary": (val.get("verdict") or {}).get("summary")})
        if audit:
            D["data_dates"][f"audit {label}" + (f" ({proj})" if proj else "")] = audit.get("created")
        prefix = f"{pname}/" if proj else ""
        site.report["inputs"].append({"file": prefix + os.path.basename(B["file"]), "version": brew["version"], "deck_hash": brew["deck_hash"], "audit_state": val["state"]})
    if research:
        research_views(site, research, proj, ptitle or pname, links, built, used_groups, ws, deck_names)
    # swap cards are looked up per project, under that project's provider exclusions
    want = [{"name": r["card"]} for rows in site.swaps.values() for k, r in rows.items() if k not in site.swap_cards]
    site.swap_cards.update(site.lookup(want, ws))


def page_fields(D):
    """The page-data the template reads, nothing more: working fields the Markdown summary and presentation-checks use
    (validation, swaps, the old sources list, per-commander video lists...) stay out of the published page."""
    P = {k: v for k, v in D.items() if k not in ("tiers", "sources", "schema", "generated")}
    P["accuracy"] = {"unverified": D["accuracy"]["unverified"]}
    P["look"] = {k: v for k, v in D["look"].items() if k not in ("l", "d")}
    P["groups"] = []
    for g in D["groups"]:
        G = {k: v for k, v in g.items() if k != "swaps"}
        G["commanders"] = []
        for c in g["commanders"]:
            C = {k: v for k, v in c.items() if k != "youtube"}
            C["look"] = {k: v for k, v in (c.get("look") or {}).items() if k not in ("l", "d")}
            C["decks"] = []
            for d in c["decks"]:
                X = {k: v for k, v in d.items() if k not in ("validation", "errors", "archetype", "rule0")}
                X["summary"] = {k: v for k, v in d["summary"].items() if k != "community"}
                X["stats"] = {k: v for k, v in d["stats"].items() if k != "types"}
                X["cards"] = [{k: v for k, v in x.items() if k != "land"} for x in d["cards"]]
                C["decks"].append(X)
            G["commanders"].append(C)
        P["groups"].append(G)
    return P


def finish(site, default_dir):
    """Swap images, title, section report; write page-data.json (or summary.md) and presentation-checks.md."""
    a, D = site.a, site.D
    found = site.swap_cards
    for g in D["groups"]:
        rows = list(site.swaps.get(g["id"], {}).values())
        for row in rows:
            c = found.get(row["card"].lower())
            if c:
                row["img"], _ = site.add_img(c)
                row["price"], row["set"], row["cn"] = (float(c["price_usd"]) if c.get("price_usd") else None), c["set"], c["collector_number"]
                row.update(views.card_types(c))
        g["swaps"] = rows
    # presentation views: one source numbering for the page, claim-specific cites, applied vs proposed recs, hero
    R = views.Research(site.researches, site.rslug)
    D["findings_view"], D["disagreements_view"], D["sources_view"] = R.findings_view(), R.disagreements_view(), R.sources_view()
    for deck, recs, proj, names in site.recs:
        deck["recs_view"] = views.recs_view(recs, names, lambda refs, text="", p=proj: R.cites(p, refs, R.text_at(p, text)))
        in_deck = {c["name"].lower(): c for c in deck["cards"]}
        for item in [x for k in ("proposed", "applied", "rejected") for x in deck["recs_view"][k] if x.get("add")]:
            c = found.get(item["add"].lower())
            if c:  # proposed or rejected adds: the swap lookup; applied ones are in the deck already
                item["img"], _ = site.add_img(c)
                item.update(price=float(c["price_usd"]) if c.get("price_usd") else None, set=c["set"], cn=c["collector_number"])
            elif item["add"].lower() in in_deck:
                d = in_deck[item["add"].lower()]
                item.update(img=d.get("img"), price=d.get("price"), set=d.get("set"), cn=d.get("cn"))
    for t in D["research_tab"]:
        for x in t["candidates"] + t["recommendations"] + t["alternatives"]:  # "Lab Man (25:00)" in the text links that moment
            words = " ".join(str(x.get(k) or "") for k in ("relevance", "synergy", "text", "why", "option"))
            x["cites"] = R.cites(t["project"], x.pop("_ev"), R.text_at(t["project"], words))
    for g in D["groups"]:
        for cm in g["commanders"]:
            ident, art = site.hero_in.get(cm["slug"], (None, None))
            cm["hero"] = views.hero(cm, ident, art if D["page"]["images"] != "none" else None)
            for d in cm["decks"]:  # each build switch shows its own stats and verdict
                d["hero"] = views.hero(cm, ident, None, d)
    A = D["accuracy"]
    A["counts"] = list(A["counts"].items())
    decks = [d for g in D["groups"] for c in g["commanders"] for d in c["decks"]]
    if not (decks or D["research"] or D["rankings"]):
        sys.exit("nothing to show: no build has card data and there is no research: " + "; ".join(u["text"] for u in A["unverified"][:6]))
    D["default_bracket"] = decks[0]["bracket"] if decks else None
    ptitle, project = site.titles[0] if site.titles else (None, {})
    first = D["groups"][0]["commanders"][0]["name"] if D["groups"] else None
    D["title"] = a.title or D.get("title") or ptitle or (f"{first} decks" if first else "Research")
    if not D.get("subtitle"):
        goal = " ".join(project.get("Goal", [])) if site.notes else None  # PROJECT.md free text is private by default
        D["subtitle"] = a.subtitle or " · ".join(x for x in [goal, site.brews[0]["strategy"]["archetype"] if site.brews and not site.multi else None,
                                                               "builds " + ", ".join(d["label"] for d in decks) if len(decks) > 1 and not site.multi else None] if x)
    if site.multi:
        D["overview"] = [{"group": g["title"], "tab": "decks-" + g["id"], "commander": c["name"], "project": c["project"], "build": d["label"],
                          "bracket": d["bracket"], "price": d["stats"]["price"], "audit": d["validation"]["state"]}
                         for g in D["groups"] for c in g["commanders"] for d in c["decks"]]
    site.report["looks"].insert(0, {"for": "pages with several commanders (overview, research, rankings, sources)", "source": D["look"]["source"],
                                    "palette": D["look"]["palette"]["source"]})
    if not site.notes:
        hide_private(site)
    site.report["sections"] = sections(D, decks)
    summary_mode = D["page"]["mode"] == "summary"
    out = os.path.abspath(a.out or os.path.join(default_dir, "page-data.json"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if summary_mode:
        md = os.path.join(os.path.dirname(out), "summary.md")
        with open(md, "w", encoding="utf-8", newline="\n") as h:
            h.write(summary_md(D))
        site.report["summary"] = md
    else:
        tmpd = out + ".tmp"
        json.dump(page_fields(D), open(tmpd, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        os.replace(tmpd, out)
        site.report["out"] = out
    site.report.update(mode=D["page"]["mode"], decks=[f"{d['label']}" + (f" ({d['project']})" if d["project"] else "") + f": {d['validation']['state']}" for d in decks],
                       rankings=len(D["rankings"]), research_tabs=len(D["research"]), swaps=sum(len(g["swaps"]) for g in D["groups"]),
                       sources=len(D["sources"]), images=len(D["images"]))
    write_checks(os.path.join(os.path.dirname(out), "presentation-checks.md"), site.report, D)
    shutil.rmtree(site.tmp, ignore_errors=True)
    print(json.dumps(site.report, indent=1))


def build(a):
    site = Site(a, multi=False)
    cli = theme_arg(a.theme)
    ws = os.path.abspath(a.workspace)
    own = opt(os.path.join(ws, "report-theme.yaml"))
    site.D["look"] = look_for([("--theme", cli), (f"{os.path.basename(ws)}/report-theme.yaml", own)])
    add_project(site, ws, look_cands=[("--theme", cli)])
    finish(site, os.path.join(ws, "reports"))


def build_showcase(a):
    sc = os.path.abspath(a.showcase)
    cfg_path = os.path.join(sc, "showcase.yaml")
    cfg = opt(cfg_path) or sys.exit(f"no showcase.yaml in {sc}")
    if not cfg.get("projects"):
        sys.exit("showcase.yaml has no projects")
    if not a.mode_given and cfg.get("mode"):
        if cfg["mode"] not in PRESETS or cfg["mode"] == "basic":
            sys.exit("showcase.yaml mode must be summary, interactive or showcase")
        a.mode = cfg["mode"]
    site = Site(a, multi=True)
    cli = theme_arg(a.theme)
    site.D["look"] = look_for([("--theme", cli), ("showcase.yaml theme", cfg.get("theme"))])
    site.D["title"] = cfg.get("title") or ""
    site.D["subtitle"] = cfg.get("subtitle") or ""
    base = os.path.normpath(os.path.join(sc, "..", "..", "projects"))
    for e in cfg["projects"]:
        p = e["project"] if isinstance(e, dict) else e
        ws = p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))
        if not os.path.isdir(ws):
            sys.exit(f"showcase project {p} not found (looked in {ws})")
        add_project(site, ws, group_override=(e.get("group") if isinstance(e, dict) else None),
                    look_cands=[("--theme", cli), (f"showcase.yaml projects[{p}] theme", e.get("theme") if isinstance(e, dict) else None),
                                ("showcase.yaml theme", cfg.get("theme"))])
    site.report["inputs"].insert(0, {"file": "showcase.yaml"})
    finish(site, os.path.join(sc, "report"))


def write_checks(path, report, D):
    """presentation-checks.md skeleton: what the page was built from and what it shows; the skill adds test results."""
    rows = ["# Presentation checks", "", f"Built {D['generated']} · mode {D['page']['mode']} · style {D['page']['style']} · images {D['page']['images']}", "",
            "## Inputs", "| File | Version | Deck hash | Audit state shown |", "|---|---|---|---|"]
    rows += [f"| {i['file']} | {i.get('version') or ''} | {i.get('deck_hash') or ''} | {i.get('audit_state') or ''} |" for i in report["inputs"]]
    rows += ["", "## Sections", "| Section | Shown | Why not |", "|---|---|---|"]
    rows += [f"| {x['name']} | {'yes' if x['included'] else 'no'} | {x['why_not'] or ''} |" for x in report["sections"]]
    rows += ["", "## Theme", "| Applies to | Source |", "|---|---|"] + [f"| {x['for']} | {x['source']} |" for x in report["looks"]]
    rows += ["", "## Palette (theme > artwork > identity > neutral; contrast checked)", "| Applies to | Palette from |", "|---|---|"]
    rows += [f"| {x['for']} | {x.get('palette') or ''} |" for x in report["looks"]]
    rows += ["", "## Notices shown", *([f"- {n['level']}: {n['text']}" for n in D.get("notices", [])] or ["- none"])]
    rows += ["", "## Browser and accessibility", "Not run yet: widths, light/dark, console errors, overflow, viewer, build switch, sources, axe-core results.", ""]
    with open(path, "w", encoding="utf-8", newline="\n") as h:
        h.write("\n".join(rows))


def sections(D, decks):
    """What the page shows and why the rest is missing (for presentation-checks.md)."""
    show = D["page"]["show"]
    has = lambda k: any(d["stats"].get(k) for d in decks)
    rows = [("overview and decklist", bool(decks), "no brew file: research-only report"),
            ("research tab (commanders compared, disagreements)", bool(D["research"]), "every project with research also has builds (commanders shown in the deck tab)" if decks else "no research.json"),
            ("rankings tabs", bool(D["rankings"]), "research.json has no rankings"),
            ("alternative commanders in deck tabs", any(g["alts"] for g in D["groups"]), "no research.json commanders next to a build"),
            ("charts (curve, types)", bool(show["charts"] and decks), "hidden by page mode/style" if not show["charts"] else "no decks"),
            ("cards to consider", bool(show["swaps"] and any(g["swaps"] for g in D["groups"])), "hidden by page mode/style" if not show["swaps"] else "no open recommendation adds a card"),
            ("audit checks", any(d["validation"].get("checks") for d in decks), "no build has a current audit"),
            ("community takes", any(d["summary"]["community"] for d in decks), "no community_opinion findings next to a build"),
            ("sources & accuracy", bool(show["sources"]), "hidden by page mode/style"),
            ("theme pills", bool(D.get("theme")), "no theme policy or themed cards"),
            ("cast-by-turn chart", bool(show["charts"]) and has("cast_by_turn"), "hidden by page mode/style" if not show["charts"] else "deck_check gave no cast_by_turn; never estimated"),
            ("price ladder", bool(show["prices"]) and has("price_ladder"), "hidden by page mode/style" if not show["prices"] else "deck_check --cheapest found no printings; never estimated"),
            ("mana sources vs color requirements", bool(show["charts"]) and has("mana"), "hidden by page mode/style" if not show["charts"] else "deck_check gave no mana data"),
            ("upcoming / banned status pills", any(c.get("status") for d in decks for c in d["cards"]) or any(c.get("status") for r in D["rankings"] for c in r["cards"]), "no card is upcoming, banned or not legal"),
            ("planned-for-release note", any(d.get("future") for d in decks), "no brew.json future block"),
            ("research views (findings, disagreements, sources)", bool(D.get("research_tab")), "no research.json with findings, disagreements, candidates or next steps")]
    return [{"name": n, "included": bool(inc), "why_not": None if inc else why} for n, inc, why in rows]


# ---------- summary mode: clean Markdown from the same data ----------
def _cell(x):
    return str(x if x is not None else "").replace("|", "\\|").replace("\n", " ")


def money(v):
    return "–" if v is None else f"${v:,.2f}"


def cite_md(cites):
    """Markdown citations: [n](source) plus each cited moment as its own link."""
    return "; ".join(f"[{c['n']}]({c['url']})" + (" at " + ", ".join(f"[{a['t']}]({a['url']})" for a in c["at"]) if c["at"] else "") for c in cites)


def _with_cites(text, cites):
    return text + (f" ({cite_md(cites)})" if cites else "")


def audit_md(av):
    """Verdict first, then failures, warnings and unverified checks in full, then the passes by name."""
    out = []
    if av.get("method_common"):
        out += [f"Method used by most checks: {av['method_common']}", ""]
    for g in av["groups"]:
        if g["status"] == "pass":
            out += [f"**{g['label'].capitalize()}:** " + "; ".join(c["title"] for c in g["checks"]) + ".", ""]
            continue
        out += [f"**{g['label'].capitalize()}**", ""]
        for c in g["checks"]:
            extra = f" Method: {c['method']}." if c["method"] and c["method"] != av.get("method_common") else ""
            out.append(f"- **{c['title']}** ({c['status_label']}). {c['result'] or ''}{extra}".rstrip())
        out.append("")
    for title, items in (("Required fixes", [f"{f.get('title') or f.get('check')}: {f['fix']}" for f in av.get("required_fixes", [])]),
                         ("Next steps", av.get("next_steps", [])), ("Limits of this audit", av.get("limitations", []))):
        if items:
            out += [f"**{title}**", ""] + [f"- {x}" for x in items] + [""]
    return out


def recs_md(rv):
    out = []
    line = lambda r: (f"- {' / '.join(x for x in [('+' + r['add']) if r.get('add') else None, ('-' + r['cut']) if r.get('cut') else None] if x)}: "
                      + _with_cites(f"{r.get('reason') or ''}" + (f" Trade-off: {r['tradeoffs']}" if r.get("tradeoffs") else "") + f" ({r['id']}, {r['status_label']})", r["cites"]))
    for key, title in (("applied", "In the deck"), ("proposed", "Proposed, not in the deck"), ("rejected", "Rejected")):
        if rv.get(key):
            out += [f"**{title}**", ""] + [line(r) for r in rv[key]] + [""]
    return out


def summary_md(D):
    """summary.md: the same facts as the page, complete (nothing sliced), conclusion first, citations with moments."""
    out = [f"# {D['title']}", ""]
    if D.get("subtitle"):
        out += [D["subtitle"], ""]
    dd = D["data_dates"]
    out += [f"Generated {D['generated']} from the project files. Card data and prices: Scryfall"
            + (f", as of {dd['card data and prices (Scryfall)']}" if dd.get("card data and prices (Scryfall)") else "") + ".", ""]
    for n in D.get("notices", []):
        out += [f"> **{'Note' if n['level'] == 'info' else 'Warning'}.** {n['text']}", ""]
    for g in D["groups"]:
        for c in g["commanders"]:
            for d in c["decks"]:
                s, v, av = d["stats"], d["validation"], d.get("audit_view") or {}
                out += [f"## {g['title']}: {c['name']} · {d['label']}" if g["title"] != c["name"] else f"## {c['name']} · {d['label']}", ""]
                if d.get("project"):
                    out += [f"Project: {d['project']} · version {d['version']}", ""]
                verdict = av.get("verdict_label") or v["state"]
                counts = views.counts_text(av.get("counts") or {})
                lead = (av.get("summary") or {}).get("lead")
                out += [f"**Audit.** {verdict}" + (f" ({v['note']})" if v.get("note") else "") + (f": {counts}." if counts else "") + (f" {lead}" if lead else ""), ""]
                out += [f"**Plan.** {d['summary']['pitch']}", ""]
                if d["summary"].get("wins"):
                    out += [f"**How it wins.** {d['summary']['wins']}", ""]
                for sec in d["summary"]["sections"]:  # why this commander, synergies, limits, theme exceptions and rules...
                    if sec["title"] != "Bracket restrictions":  # in Rule 0
                        out += [f"**{sec['title']}.**", ""] + [f"- {x}" for x in sec["items"]] + [""]
                out += [f"**Rule 0.** {d['rule0']}", ""]
                mdfc = s.get("mdfc_lands") or 0
                out += ["| Cards | Lands | Avg mana value | Value (listed printings) | Game Changers |", "|---|---|---|---|---|",
                        f"| {sum(x['qty'] for x in d['cards'])} | {s['lands']}{f' + {mdfc} MDFC' if mdfc else ''} | {s['avg_mv']} | {money(s['price'])} | {len(s['game_changers'])} |", ""]
                ts = d.get("theme_stats")
                if ts and ts["total"]:
                    rest = ", ".join(x for x in [f"{ts['exception']} approved exceptions" if ts["exception"] else None,
                                                 f"{ts['off']} off-theme" if ts["off"] else None] if x)
                    left_out = "the commander" + (f" and {ts['exempt']} cards with no theme judgement" if ts["exempt"] else "")
                    out += [f"Theme: {ts['on']} of {ts['total']} cards on theme ({d['theme']['on_theme_pct']}%)" + (f"; {rest}" if rest else "")
                            + f". Not counted: {left_out}.", ""]
                if s.get("type_counts"):
                    out += ["Card types (front face; split and adventure cards by every half): " + " · ".join(f"{k} {n}" for k, n in s["type_counts"].items()), ""]
                if s.get("roles"):
                    out += ["Roles (from fixed Oracle-text rules; a card can count in several): "
                            + " · ".join(f"{k} {n}" for k, n in sorted(s["roles"].items()) if k != "land"), ""]
                if s.get("price_ladder"):
                    p = s["price_ladder"]
                    out += [f"Price ladder (Scryfall daily prices, {p['as_of']}): affordable {money(p['affordable_usd'])} · as listed "
                            f"{money(p['as_listed_usd'])} · premium {money(p['premium_usd'])}", ""]
                if s.get("cast_by_turn"):
                    cbt = s["cast_by_turn"]
                    turns = " · ".join(f"T{t} {round(p * 100)}%" for t, p in cbt["by_turn"].items())
                    out += [f"Commander cast by turn ({cbt['runs']:,} simulated games, seed {cbt['seed']}): {turns}. Assumptions: {cbt['assumptions']}.", ""]
                if d.get("future"):
                    f = d["future"]
                    waits = ", ".join(f"{w.get('card')} ({w.get('releases') or 'date unknown'})" for w in f.get("waits_for", []))
                    out += ["**Planned for release.** " + " ".join(x for x in [f.get("note"), f"Waits for: {waits}." if waits else None] if x), ""]
                flagged = [x for x in d["cards"] if x.get("status")]
                if flagged:
                    out += ["Status: " + "; ".join(f"{x['name']} {x['status']}" + (f" (releases {x['releases']})" if x.get("releases") else "") for x in flagged), ""]
                if av.get("groups"):
                    out += ["### Audit checks", ""] + audit_md(av)
                if any((d.get("recs_view") or {}).get(k) for k in ("applied", "proposed", "rejected")):
                    out += ["### Recommendations", ""] + recs_md(d["recs_view"])
                out += ["### Decklist", "", "```text", d["moxfield"], "```", ""]
        if g["alts"]:
            out += [f"### Commanders compared ({g['title']})", ""] + commander_table(g["alts"])
    for t in D.get("research_tab", []):
        p = t["project"]
        out += [f"## {t['title']}", "", t["question"], ""]
        sc, m = t.get("scope") or {}, t.get("methodology") or {}
        if sc.get("theme") or sc.get("depth"):
            out += ["**Scope.** " + " · ".join(x for x in [f"Theme: {sc['theme']}" if sc.get("theme") else None,
                                                          f"depth: {sc['depth']}" if sc.get("depth") else None] if x), ""]
        if m:
            out += ["### How it was researched", ""] + ([m["approach"], ""] if m.get("approach") else [])
            out += [f"- {x}" for x in ([f"Tools used: {'; '.join(m['tools_used'])}"] if m.get("tools_used") else [])
                    + [f"Failed: {f['capability']}: {f['error']}" + (f" (fallback: {f['fallback']})" if f.get("fallback") else "") for f in m.get("tools_failed", [])]
                    + ([f"Stopped because: {m['stopped_because']}"] if m.get("stopped_because") else [])] + [""]
        if t.get("feasibility"):
            out += [f"**Feasibility.** {t['feasibility'].get('verdict')}", ""]
        for r in D["research"]:
            if r["project"] == p and r["commanders"]:
                out += ["### Commanders compared", ""] + commander_table(r["commanders"])
        dis = [x for x in D.get("disagreements_view", []) if x["project"] == p]
        if dis:
            out += ["### Where sources disagree", ""]
            for x in dis:
                out += [f"**{x['topic']}**", ""] + [f"- {_with_cites(pos['text'], pos['cites'])}" for pos in x["positions"]] + ([x["explanation"]] if x.get("explanation") else []) + [""]
        groups = [x for x in D.get("findings_view", []) if x["project"] == p]
        if groups:
            out += ["### Findings", ""]
            for fg in groups:
                out += [f"#### {fg['title']} ({len(fg['items'])})", ""]
                for it in fg["items"]:
                    h = it["headline"].rstrip("…")  # a cut headline continues into the body's rest
                    head, rest = (h, it["body"][len(h):]) if it["body"].startswith(h) else (it["headline"], " " + it["body"])
                    rest = rest if rest[:1] in (":", ";", ",") else " " + rest.strip()  # "**Headline**: rest" after a clause cut
                    tags = ", ".join(x for x in [it["class_label"], f"{it['confidence']} confidence", "sources disagree" if it["disputed"] else None] if x)
                    out.append(f"- **{head}**{rest.rstrip()} [{tags}; {it['id']}]" + (f" ({cite_md(it['cites'])})" if it["cites"] else ""))
                    out += [f"  - {k}: {it[f]}" for k, f in (("Why", "explanation"), ("Limits", "limitations")) if it.get(f)]
                out.append("")
        for title, items in (("Recommendations", [_with_cites(f"{r['text']} {r.get('why') or ''}".strip(), r["cites"]) for r in t["recommendations"]]),
                             ("Alternatives", [_with_cites(f"{x['option']}: {x['why']}", x["cites"]) for x in t["alternatives"]]),
                             ("Gaps", t["gaps"]), ("Next steps", t["next_steps"]),
                             ("Open questions", [q["question"] + (f" Recommended: {q['recommended']}." if q.get("recommended") else "") for q in t["follow_up_questions"]])):
            if items:
                out += [f"### {title}", ""] + [f"- {x}" for x in items] + [""]
        if t["candidates"]:
            out += ["### Card candidates", "", "| Card | Role | Why | Theme fit | In the deck | Sources |", "|---|---|---|---|---|---|"]
            out += [f"| {_cell(c['name'])} | {_cell(c.get('role'))} | {_cell(c['relevance'])} | {_cell(c.get('theme_fit'))} | {'yes' if c['in_deck'] else 'no'} | {_cell(cite_md(c['cites']))} |"
                    for c in t["candidates"]] + [""]
    for r in D["rankings"]:
        out += [f"## Ranking: {r['title']}" + (f" ({r['project']})" if r.get("project") else ""), ""]
        out += [x for x in [r.get("scope"), f"Method: {r['method']}" + (f" (as of {r['as_of']})" if r.get("as_of") else ""),
                            "Inclusion % is popularity (share of decks that play the card), not a strength rating."] if x] + [""]
        out += ["| Rank | Tier | Card | Inclusion (popularity) | Why | Status |", "|---|---|---|---|---|---|"]
        for c in r["cards"]:
            inc = "" if c["pct"] is None else f"{c['pct']}%" + (f" ({c['decks']:,} of {c['n']:,} decks)" if c.get("decks") is not None and c.get("n") else "")
            stt = (c["status"] or "") + (f", releases {c['releases']}" if c.get("releases") else "")
            out.append(f"| {c['rank']} | {_cell(c['tier'])} | {_cell(c['name'])} | {inc} | {_cell(c['why'])} | {stt} |")
        out.append("")
    if D.get("sources_view"):
        out += ["## Sources", ""]
        for g in D["sources_view"]:
            out += [f"### {g['kind_label']}", ""]
            for s in g["items"]:
                meta = " · ".join(x for x in [s.get("creator"), s.get("date"), s.get("project")] if x)
                moments = ", ".join(f"[{m['t']}]({m['url']})" + (f" ({', '.join(m['findings'])})" if m["findings"] else "") for m in s["moments"])
                out.append(f"{s['n']}. [{s['title']}]({s['url']})" + (f" · {meta}" if meta else "")
                           + (f". Cited by {', '.join(x['id'] for x in s['cited_by'])}" if s["cited_by"] else "") + (f". Moments: {moments}" if moments else ""))
            out.append("")
    return "\n".join(out)


def commander_table(rows):
    out = ["| Commander | Strategy | Advantages | Disadvantages | Theme fit | Legal check |", "|---|---|---|---|---|---|"]
    out += [f"| {_cell(c['name'])}{' (built)' if c.get('built') else ''} | {_cell(c['strategy'])} | {_cell('; '.join(c['advantages']))} | "
            f"{_cell('; '.join(c['disadvantages']))} | {_cell(c.get('theme_fit'))} | {_cell(c.get('legal_check') or 'not recorded')} |" for c in rows]
    return out + [""]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s1 = sp.add_parser("from-workspace", help="build the page data from one project folder")
    s1.add_argument("workspace", metavar="PROJECT")
    s1.add_argument("--out", help="default: PROJECT/reports/page-data.json")
    s1.set_defaults(f=build)
    s2 = sp.add_parser("from-showcase", help="build one report from a showcase folder (showcase.yaml)")
    s2.add_argument("showcase", metavar="SHOWCASE")
    s2.add_argument("--out", help="default: SHOWCASE/report/page-data.json")
    s2.set_defaults(f=build_showcase)
    for s in (s1, s2):
        s.add_argument("--mode", choices=["summary", "interactive", "showcase"], help="summary.md, a lighter page, or the full page (default)")
        s.add_argument("--theme", help="theme file (yaml/json) or JSON {accent, accent2, style, label}; overrides saved themes")
        s.add_argument("--title"); s.add_argument("--subtitle")
        s.add_argument("--style", choices=["fancy", "basic"], help="basic: no images or charts; fancy = the mode's page")
        s.add_argument("--images", choices=["atlas", "cdn", "none"], help="where card images come from (default: the mode's)")
        s.add_argument("--viewer", choices=["simple", "3d"], help="card viewer: simple (CSS) or 3d (three.js). Default: the mode's")
        s.add_argument("--show", help=f"comma list of sections to turn on ({', '.join(SECTIONS)})")
        s.add_argument("--hide", help="comma list of sections to turn off")
        s.add_argument("--include-notes", action="store_true",
                       help="include DECISIONS.md lines and PROJECT.md text (the player's own copy; shared pages leave them out)")
    a = ap.parse_args()
    a.mode_given = a.mode is not None
    a.mode = a.mode or "showcase"
    a.f(a)


if __name__ == "__main__":
    main()
