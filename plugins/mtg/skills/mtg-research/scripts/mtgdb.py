#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["ijson", "pillow"]
# ///
"""mtgdb: local Scryfall index and deterministic MTG checks. Stdlib only.

The index is the single source of truth for card facts (text, legality, printings,
prices, Game Changer status, images). Build it once, reuse it everywhere.

  index          download Scryfall bulk "default_cards", build the SQLite index
  info           index build date, card count, Game Changer count
  card           one card's oracle facts (JSON)
  printings      legal printings of a card, themed first, then by price
  normalize      map messy names (transcripts, OCR, typos) to real card names
  gamechangers   current Game Changers from the index (--refresh pulls Scryfall once)
  resolve        decklist -> JSON with oracle + chosen printing + theme tag
  validate       hard checks: count, singleton, identity, legality, printings, bracket, budget
  stats          curve, pips vs sources, lands, role hints
  swaptest       apply "-OUT +IN" swaps to a copy of a deck and re-validate
  audit-claims   check a claims.jsonl ledger (sources, dates, independence, card names)
  selftest       golden facts against the live index (catches a stale or broken index)
  search         cached, rate-limited Scryfall search (any syntax, e.g. "e:sld art:lightsaber")
  tags-sync      Scryfall Tagger role tags (otag:ramp, ...) so stats counts real roles
  collection     import (Moxfield/Archidekt/ManaBox CSV or text list) / show owned cards
  prices-sync    MTGJSON multi-vendor prices (today, or --history for 90 days)
  price-history  retail price series for a card's printings
  combos         Commander Spellbook find-my-combos (fallback when the MCP is down)
  profile        existing deck snapshot for optimizing (bracket signals, cost, printing sets / theme hint)
  diff           before/after of an optimized deck (cuts, adds, printing swaps, cost to buy)
  theme-build    resolve a theme spec (Scryfall queries + includes/excludes, label priority) into a theme map
  theme-pool     how many on-theme cards exist in a commander's colors (is strict mode realistic?)
  hook           Claude Code PostToolUse hook: validates vault decks and claim ledgers as they're written

Default DB: $MTGDB or ~/.cache/mtg/cards.sqlite (cache dir: $MTG_CACHE). Exit code 1 means checks failed.
All api.scryfall.com calls share one cross-process rate limiter, so parallel agents stay under 2 req/s.
"""
import argparse, csv, difflib, gzip, json, os, re, sqlite3, sys, tempfile, time, urllib.error, urllib.request
from urllib.parse import quote, urlparse

UA = {"User-Agent": "mtgdb/1.0 (personal deckbuilding tool)", "Accept": "application/json;q=0.9,*/*;q=0.8"}
CACHE = os.path.expanduser(os.environ.get("MTG_CACHE", "~/.cache/mtg"))
DB_DEFAULT = os.environ.get("MTGDB", os.path.join(CACHE, "cards.sqlite"))
EXTRA_DB = os.environ.get("MTGDB_EXTRA", os.path.join(CACHE, "extra.sqlite"))  # survives re-index
COLLECTION = os.environ.get("MTG_COLLECTION", os.path.join(CACHE, "collection.json"))
EXTRA_SCHEMA = """
CREATE TABLE IF NOT EXISTS tags(oracle_id TEXT, name TEXT, tag TEXT, synced TEXT);
CREATE INDEX IF NOT EXISTS ix_tags ON tags(oracle_id);
CREATE INDEX IF NOT EXISTS ix_tags_tag ON tags(tag);
CREATE TABLE IF NOT EXISTS tag_sync(tag TEXT PRIMARY KEY, synced TEXT, count INTEGER);
CREATE TABLE IF NOT EXISTS prices(scryfall_id TEXT, date TEXT, vendor TEXT, kind TEXT, finish TEXT, price REAL, currency TEXT,
  PRIMARY KEY(scryfall_id, date, vendor, kind, finish));
CREATE TABLE IF NOT EXISTS search_cache(query TEXT PRIMARY KEY, fetched REAL, body TEXT);
"""
# Scryfall Tagger oracle tags per deck role. Unknown tag names show up as count 0 in tags-sync.
ROLE_TAGS = {
    "ramp": ["ramp", "mana-rock", "mana-dork", "land-ramp"],
    "draw": ["card-advantage", "draw", "repeatable-draw"],
    "removal": ["removal", "spot-removal", "counterspell", "creature-removal", "artifact-removal", "enchantment-removal"],
    "wipe": ["board-wipe", "sweeper", "mass-removal"],
    "tutor": ["tutor"],
    "protection": ["protection", "gives-hexproof", "gives-indestructible"],
    "recursion": ["recursion", "reanimation"],
}
SCHEMA = """
CREATE TABLE oracle(oracle_id TEXT PRIMARY KEY, name TEXT, color_identity TEXT, type_line TEXT,
  oracle_text TEXT, cmc REAL, mana_cost TEXT, commander_legal TEXT, gc INTEGER, produced_mana TEXT,
  edhrec_rank INTEGER, keywords TEXT);
CREATE TABLE printings(id TEXT PRIMARY KEY, oracle_id TEXT, set_code TEXT, cn TEXT, set_name TEXT,
  border TEXT, digital INTEGER, usd REAL, usd_foil REAL, released TEXT, layout TEXT, back_id TEXT,
  img_front TEXT, img_back TEXT, img_small TEXT, promo_types TEXT, frame_effects TEXT, artist TEXT,
  oversized INTEGER, set_type TEXT, security_stamp TEXT);
CREATE TABLE alias(name_lc TEXT, oracle_id TEXT);
CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
CREATE INDEX ix_p_or ON printings(oracle_id);
CREATE INDEX ix_p_set ON printings(set_code, cn);
CREATE INDEX ix_alias ON alias(name_lc);
"""


# ---------- io helpers ----------
def throttle(min_gap=0.55):
    """Cross-process limiter for api.scryfall.com (2 req/s on search endpoints), so parallel agents can't exceed it."""
    os.makedirs(CACHE, exist_ok=True)
    lock, stamp = os.path.join(CACHE, ".scryfall.lock"), os.path.join(CACHE, ".scryfall.last")
    deadline = time.time() + 120
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.time() - os.path.getmtime(lock) > 30:  # stale lock from a crashed process
                try:
                    os.remove(lock)
                except FileNotFoundError:
                    pass
            if time.time() > deadline:
                raise RuntimeError("Scryfall lock busy for 120s")
            time.sleep(0.1)
    try:
        last = float(open(stamp, encoding="utf-8").read() or 0) if os.path.exists(stamp) else 0
        wait = min_gap - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        open(stamp, "w", encoding="utf-8").write(str(time.time()))
    finally:
        os.close(fd)
        os.remove(lock)


def http_get(url, data=None, headers=None):
    if urlparse(url).netloc == "api.scryfall.com":
        throttle()
    h = dict(UA, **(headers or {}))
    req = urllib.request.Request(url, data=data, headers=h, method="POST" if data else "GET")
    for _ in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:  # Scryfall locks you out for 30s; never hammer
                print("429 from Scryfall, waiting 31s", file=sys.stderr)
                time.sleep(31)
                continue
            raise
    raise RuntimeError(f"gave up on {url}")


def out(obj, fail=False):
    print(json.dumps(obj, indent=1, ensure_ascii=False))
    sys.exit(1 if fail else 0)


def open_db(path):
    if not os.path.exists(path):
        sys.exit(f"No index at {path}. Run: mtgdb.py index")
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def meta(c, k):
    r = c.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
    return r[0] if r else None


# ---------- index ----------
def iter_bulk(fp):
    """Bulk files hold one card object per line inside a JSON array."""
    for line in fp:
        line = line.strip().rstrip(",")
        if line not in ("[", "]", ""):
            yield json.loads(line)


def price(card, k):
    v = (card.get("prices") or {}).get(k)
    return float(v) if v else None


def cmd_index(a):
    os.makedirs(os.path.dirname(a.db) or ".", exist_ok=True)
    raw, updated = a.bulk_file, "local file"
    if not raw:
        entry = next(d for d in json.loads(http_get("https://api.scryfall.com/bulk-data"))["data"]
                     if d["type"] == "default_cards")
        # Scryfall replaced download_uri/size with gzipped JSON Lines (jsonl_download_uri/compressed_size) in 2026
        uri = entry.get("jsonl_download_uri") or entry["download_uri"]
        size = entry.get("compressed_size") or entry.get("size") or 0
        raw, updated = os.path.join(os.path.dirname(a.db), "default_cards.download"), entry["updated_at"]
        print(f"Downloading {size / 1e6:.0f} MB ({updated})", file=sys.stderr)
        req = urllib.request.Request(uri, headers=UA)
        with urllib.request.urlopen(req, timeout=900) as r, open(raw, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
    tmp = a.db + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    c = sqlite3.connect(tmp)
    c.executescript(SCHEMA)
    n, gc_field = 0, False
    with open(raw, "rb") as probe:
        gz = probe.read(2) == b"\x1f\x8b"
    with (gzip.open(raw, "rt", encoding="utf-8") if gz else open(raw, encoding="utf-8")) as fp:
        for card in iter_bulk(fp):
            faces = card.get("card_faces") or []
            oid = card.get("oracle_id") or (faces[0].get("oracle_id") if faces else None)
            if card.get("lang") != "en" or not oid:
                continue
            gc_field |= "game_changer" in card
            text = card.get("oracle_text") or " // ".join(f.get("oracle_text", "") for f in faces)
            c.execute("INSERT OR REPLACE INTO oracle VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (
                oid, card["name"], "".join(card.get("color_identity", [])), card.get("type_line", ""), text,
                card.get("cmc", 0), card.get("mana_cost") or (faces[0].get("mana_cost", "") if faces else ""),
                (card.get("legalities") or {}).get("commander", ""), int(bool(card.get("game_changer"))),
                "".join(card.get("produced_mana", [])), card.get("edhrec_rank"), ",".join(card.get("keywords", []))))
            iu = card.get("image_uris") or (faces[0].get("image_uris") if faces else None) or {}
            back = (faces[1].get("image_uris") or {}).get("normal") if len(faces) > 1 else None
            c.execute("INSERT OR REPLACE INTO printings VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                card["id"], oid, card["set"], card["collector_number"], card.get("set_name"), card.get("border_color"),
                int(bool(card.get("digital"))), price(card, "usd"), price(card, "usd_foil"), card.get("released_at"),
                card.get("layout"), card.get("card_back_id"), iu.get("normal"), back, iu.get("small"),
                ",".join(card.get("promo_types", [])), ",".join(card.get("frame_effects", [])), card.get("artist"),
                int(bool(card.get("oversized"))), card.get("set_type"), card.get("security_stamp")))
            for nm in {card["name"].lower()} | {f["name"].lower() for f in faces if f.get("name")}:
                c.execute("INSERT INTO alias VALUES(?,?)", (nm, oid))
            n += 1
    c.execute("DELETE FROM alias WHERE rowid NOT IN (SELECT MIN(rowid) FROM alias GROUP BY name_lc, oracle_id)")
    for k, v in (("built", time.strftime("%Y-%m-%d")), ("bulk_updated", updated), ("gc_field", str(gc_field)),
                 ("gc_source", "bulk" if gc_field else "none")):
        c.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (k, v))
    c.commit()
    c.close()
    os.replace(tmp, a.db)
    print(f"Indexed {n} English printings -> {a.db}")
    if not gc_field:
        print("Bulk data lacks game_changer: run `mtgdb.py gamechangers --refresh`", file=sys.stderr)


def cmd_info(a):
    c = open_db(a.db)
    built = meta(c, "built")
    age = (time.time() - time.mktime(time.strptime(built, "%Y-%m-%d"))) / 86400 if built else None
    out({"db": a.db, "built": built, "bulk_updated": meta(c, "bulk_updated"), "age_days": round(age or 0, 1),
         "stale": bool(age and age > 7), "oracle_cards": c.execute("SELECT COUNT(*) FROM oracle").fetchone()[0],
         "printings": c.execute("SELECT COUNT(*) FROM printings").fetchone()[0],
         "game_changers": c.execute("SELECT COUNT(*) FROM oracle WHERE gc=1").fetchone()[0],
         "gc_source": meta(c, "gc_source")})


# ---------- lookups ----------
def find_oracle(c, name):
    r = c.execute("SELECT oracle_id FROM alias WHERE name_lc=?", (name.lower().strip(),)).fetchone()
    return r[0] if r else None


_names = None


def all_names(c):
    global _names
    if _names is None:
        _names = [r[0] for r in c.execute("SELECT DISTINCT name_lc FROM alias")]
    return _names


def suggest(c, name, n=3, cutoff=0.82):
    q = re.sub(r"[^a-z0-9 ,'/-]", "", name.lower()).strip()
    hits = difflib.get_close_matches(q, all_names(c), n=n, cutoff=cutoff)
    res = []
    for h in hits:
        oid = find_oracle(c, h)
        nm = c.execute("SELECT name FROM oracle WHERE oracle_id=?", (oid,)).fetchone()[0]
        res.append({"name": nm, "score": round(difflib.SequenceMatcher(None, q, h).ratio(), 3)})
    return res


def cmd_card(a):
    c = open_db(a.db)
    oid = find_oracle(c, a.name)
    if not oid:
        out({"error": "not found", "suggestions": suggest(c, a.name)}, fail=True)
    out(dict(c.execute("SELECT * FROM oracle WHERE oracle_id=?", (oid,)).fetchone()))


def cmd_normalize(a):
    c = open_db(a.db)
    names = a.names or [ln.strip() for ln in sys.stdin if ln.strip()]
    res = []
    for nm in names:
        oid = find_oracle(c, nm)
        if oid:
            res.append({"input": nm, "name": c.execute("SELECT name FROM oracle WHERE oracle_id=?", (oid,)).fetchone()[0],
                        "match": "exact"})
        else:
            s = suggest(c, nm, cutoff=a.cutoff)
            res.append({"input": nm, "name": s[0]["name"] if s and s[0]["score"] >= 0.9 else None,
                        "match": "fuzzy" if s and s[0]["score"] >= 0.9 else ("ambiguous" if s else "none"),
                        "candidates": s})
    out(res, fail=any(r["match"] in ("ambiguous", "none") for r in res))


THEME_MODES = ("none", "power", "prefer", "strict")
THEME_DEFAULTS = {"mode": "prefer", "labels": [], "franchise_label": None, "max_off_theme": None, "max_franchise": None,
                  "count_basics": False, "exempt_commanders": True, "commander_must_match": False,
                  "max_premium_per_card": None, "max_map_age_days": 45}


def load_theme(path):
    """Theme map: {"built", "spec": {...}, "printings": {key: label}}. Keys: printing id, set#cn, set:code, oracle:<oracle_id>.
    A bare {key: label} file (older format) still works, with default spec."""
    if not path or not os.path.exists(path):
        return None
    d = json.load(open(path, encoding="utf-8"))
    if "printings" not in d:
        d = {"printings": d}
    spec = dict(THEME_DEFAULTS, **(d.get("spec") or {}))
    if not spec["labels"]:
        spec["labels"] = list(dict.fromkeys(d["printings"].values()))
    d["spec"] = spec
    return d


def load_themes(path):
    t = load_theme(path)
    if not t or t["spec"]["mode"] == "none":
        return {}
    pr = dict(t["printings"])
    pr["__order__"] = t["spec"]["labels"]
    return pr


def theme_of(p, themes):
    """Highest-priority label among all keys this printing matches."""
    order = themes.get("__order__", [])
    hits = [themes[k] for k in (p["id"], f"{p['set_code']}#{p['cn']}", f"set:{p['set_code']}", f"oracle:{p.get('oracle_id')}")
            if k in themes]
    if not hits:
        return None
    return min(hits, key=lambda l: order.index(l) if l in order else len(order))


NON_PLAY_SET_TYPES = {"memorabilia", "token", "minigame"}


def legal_printing(p):
    """A printing you can sleeve in a sanctioned-style game: no gold border, digital-only, oversized or memorabilia."""
    return (p["border"] != "gold" and not p["digital"] and not p.get("oversized")
            and (p.get("set_type") or "") not in NON_PLAY_SET_TYPES)


def cmd_printings(a):
    c, themes = open_db(a.db), load_themes(a.themes)
    oid = find_oracle(c, a.card)
    if not oid:
        out({"error": "not found", "suggestions": suggest(c, a.card)}, fail=True)
    rows = []
    for r in c.execute("SELECT * FROM printings WHERE oracle_id=?", (oid,)):
        p = dict(r)
        p["theme"], p["legal"] = theme_of(p, themes), legal_printing(p)
        rows.append(p)
    rows.sort(key=lambda p: (not p["legal"], p["theme"] is None, p["usd"] if p["usd"] is not None else 1e9))
    keep = ["id", "set_code", "cn", "set_name", "released", "usd", "usd_foil", "theme", "legal", "border",
            "promo_types", "artist", "img_front"]
    col = load_collection()
    name = c.execute("SELECT name FROM oracle WHERE oracle_id=?", (oid,)).fetchone()[0]
    owned = (col or {}).get("cards", {}).get(name)
    res = []
    for p in rows:
        r = {k: p[k] for k in keep}
        vp = vendor_prices(p["id"])
        if vp:
            r["vendors"] = vp
        if owned:
            r["owned_qty"] = owned["printings"].get(f"{p['set_code']}#{p['cn']}", 0)
        res.append(r)
    out({"card": name, "prices_as_of": meta(c, "bulk_updated"), "owned_total": owned["qty"] if owned else 0,
         "printings": res})


def cmd_gamechangers(a):
    c = open_db(a.db)
    if a.refresh:
        names, url = [], "https://api.scryfall.com/cards/search?q=is%3Agamechanger&unique=cards"
        while url:
            page = json.loads(http_get(url))
            names += [x["name"] for x in page["data"]]
            url = page.get("next_page")
            time.sleep(0.6)
        c.execute("UPDATE oracle SET gc=0")
        for nm in names:
            oid = find_oracle(c, nm)
            if oid:
                c.execute("UPDATE oracle SET gc=1 WHERE oracle_id=?", (oid,))
        c.execute("INSERT OR REPLACE INTO meta VALUES('gc_source', ?)", (f"scryfall search {time.strftime('%Y-%m-%d')}",))
        c.commit()
    names = [r[0] for r in c.execute("SELECT name FROM oracle WHERE gc=1 ORDER BY name")]
    out({"count": len(names), "source": meta(c, "gc_source"), "cards": names})


# ---------- decks ----------
LINE = re.compile(r"^\s*(\d+)x?\s+(.+?)(?:\s+\(([A-Za-z0-9]+)\)\s*([^\s*]+))?(?:\s+\*[A-Z]+\*)*\s*$")


def parse_deck(path):
    rows = []
    for ln in open(path, encoding="utf-8"):
        s = ln.strip()
        if not s or s.startswith(("//", "#")) or s.endswith(":"):
            continue
        m = LINE.match(s)
        rows.append({"qty": int(m[1]), "name": m[2].strip(), "set": (m[3] or "").lower(), "cn": m[4] or ""}
                    if m else {"error": f"unparsed line: {s}"})
    return rows


def resolve(c, path, themes):
    cards = []
    for e in parse_deck(path):
        if "error" in e:
            cards.append(e)
            continue
        oid = find_oracle(c, e["name"])
        if not oid:
            cards.append({**e, "error": "unknown card", "suggestions": suggest(c, e["name"])})
            continue
        o = dict(c.execute("SELECT * FROM oracle WHERE oracle_id=?", (oid,)).fetchone())
        prints = [dict(r) for r in c.execute("SELECT * FROM printings WHERE oracle_id=?", (oid,))]
        chosen = next((p for p in prints if p["set_code"] == e["set"] and p["cn"] == e["cn"]), None)
        flags = []
        if not chosen:
            flags.append("printing_not_found" if e["set"] else "no_printing_given")
            legal = [p for p in prints if legal_printing(p)] or prints
            chosen = min(legal, key=lambda p: p["usd"] if p["usd"] is not None else 1e9)
        tag = theme_of(chosen, themes) if themes else None
        alts = [p for p in prints if themes and theme_of(p, themes) and legal_printing(p)]
        if themes and not tag and alts:
            flags.append("themed_printing_available")
        cards.append({**e, "oracle": o, "printing": chosen, "theme": tag or ("off-theme" if themes else None),
                      "flags": flags, "themed_alternatives": [f"{p['set_code']}#{p['cn']}" for p in alts][:5]})
    return cards


def cmd_resolve(a):
    c = open_db(a.db)
    res = {"deck": a.deck, "index_built": meta(c, "built"), "cards": resolve(c, a.deck, load_themes(a.themes))}
    if a.out:
        json.dump(res, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(a.out)
    else:
        out(res)


EXTRA_TURN = re.compile(r"take an extra turn|takes an extra turn", re.I)
MLD = re.compile(r"destroy all (?:nonbasic )?lands|each player sacrifices (?:all|\w+) lands|"
                 r"lands don't untap|destroy all permanents|sacrifice all lands", re.I)


def check(c, path, themes, bracket, commanders=1, budget=None, theme=None, reasons=None):
    cards = resolve(c, path, themes)
    errors, warns = [], []
    for x in cards:
        if "error" in x:
            sug = ", ".join(s["name"] for s in x.get("suggestions", []))
            errors.append(f"{x.get('name', '')}: {x['error']}" + (f" (did you mean: {sug})" if sug else ""))
    ok = [x for x in cards if "error" not in x]
    total = sum(x["qty"] for x in ok)
    if total != 100:
        errors.append(f"card count is {total}, must be 100")
    cmdrs = ok[:commanders]
    ident = set("".join(x["oracle"]["color_identity"] for x in cmdrs))
    for x in cmdrs:
        t, txt = x["oracle"]["type_line"], x["oracle"]["oracle_text"] or ""
        if not (("Legendary" in t and "Creature" in t) or "can be your commander" in txt or "Background" in t):
            errors.append(f"{x['oracle']['name']} may not be a legal commander ({t})")
    counts = {}
    for x in ok:
        counts[x["oracle"]["name"]] = counts.get(x["oracle"]["name"], 0) + x["qty"]
    seen = set()
    for x in ok:
        o, p = x["oracle"], x["printing"]
        if o["name"] in seen:
            continue
        seen.add(o["name"])
        n = counts[o["name"]]
        if n > 1 and "Basic" not in o["type_line"] and "any number of cards named" not in (o["oracle_text"] or ""):
            errors.append(f"{o['name']} x{n} breaks singleton")
        if not set(o["color_identity"]) <= ident:
            errors.append(f"{o['name']} outside color identity ({o['color_identity']} vs {''.join(sorted(ident)) or 'C'})")
        if o["commander_legal"] != "legal":
            errors.append(f"{o['name']} is {o['commander_legal'] or 'not legal'} in Commander")
        if not legal_printing(p):
            errors.append(f"{o['name']}: printing {p['set_code']}#{p['cn']} is not playable (gold border, digital-only, oversized or memorabilia)")
        for f in x["flags"]:
            alt = f" ({', '.join(x['themed_alternatives'])})" if f == "themed_printing_available" else ""
            warns.append(f"{o['name']}: {f}{alt}")
    gcs = sorted({x["oracle"]["name"] for x in ok if x["oracle"]["gc"]})
    limit = {1: 0, 2: 0, 3: 3}.get(bracket)
    if limit is not None and len(gcs) > limit:
        errors.append(f"{len(gcs)} Game Changers, bracket {bracket} allows {limit}: {', '.join(gcs)}")
    extra = sorted({x["oracle"]["name"] for x in ok if EXTRA_TURN.search(x["oracle"]["oracle_text"] or "")})
    mld = sorted({x["oracle"]["name"] for x in ok if MLD.search(x["oracle"]["oracle_text"] or "")})
    if bracket in (1, 2, 3):
        if mld:
            errors.append(f"possible mass land denial at B{bracket}: {', '.join(mld)} (confirm by reading the card)")
        if extra and bracket == 1:
            errors.append(f"extra-turn cards at B1: {', '.join(extra)}")
        elif len(extra) > 2:
            warns.append(f"{len(extra)} extra-turn cards at B{bracket}; must be few and never chained: {', '.join(extra)}")
    cost = round(sum((x["printing"]["usd"] or x["printing"]["usd_foil"] or 0) * x["qty"] for x in ok), 2)
    unpriced = sorted({x["oracle"]["name"] for x in ok if x["printing"]["usd"] is None and x["printing"]["usd_foil"] is None})
    if unpriced:
        warns.append(f"{len(unpriced)} card(s) have no price, so the total is understated: {', '.join(unpriced)}")
    if budget and cost > budget:
        errors.append(f"deck costs ${cost}, budget ${budget}")
    tags = {}
    for x in ok:
        if x["theme"]:
            tags[x["theme"]] = tags.get(x["theme"], 0) + x["qty"]
    rep = {"deck": path, "bracket": bracket, "pass": not errors, "errors": errors, "warnings": warns,
           "game_changers": gcs, "extra_turn_cards": extra, "price_usd": cost,
           "prices_as_of": meta(c, "bulk_updated"), "unpriced": unpriced, "theme_counts": tags,
           "not_checked": "2-card combos and intent: run Commander Spellbook on this list"}
    if theme and theme["spec"]["mode"] != "none":
        te, tw, trep = theme_eval(c, ok, theme, commanders, reasons or {})
        errors += te
        warns += tw
        rep["theme"] = trep
        rep["pass"] = not errors
        rep["errors"], rep["warnings"] = errors, warns
    col = load_collection()
    if col:
        owned_cards = col["cards"]
        own, buy = [], 0.0
        for x in ok:
            have = owned_cards.get(x["oracle"]["name"], {}).get("qty", 0)
            if have >= x["qty"] or ("Basic" in x["oracle"]["type_line"] and have):
                own.append(x["oracle"]["name"])
            else:
                buy += (x["printing"]["usd"] or x["printing"]["usd_foil"] or 0) * x["qty"]
        rep["collection"] = {"owned": len(own), "cost_to_buy_usd": round(buy, 2), "collection_imported": col["imported"],
                             "note": "owned = you have the card in any printing"}
    return cards, rep


def theme_eval(c, ok, theme, commanders, reasons):
    """Apply theme mode and limits. Printing swaps are free in power terms, so every mode except none
    flags a missed themed printing of the same card."""
    sp = theme["spec"]
    mode, labels, fr = sp["mode"], sp["labels"], sp["franchise_label"]
    primary = [l for l in labels if l != fr]
    errors, warns = [], []
    cmdr_names = {x["oracle"]["name"] for x in ok[:commanders]}
    counted, on_counted, off, fran, premium, by_label = 0, 0, [], [], 0.0, {}
    for x in ok:
        o, p, tag = x["oracle"], x["printing"], x["theme"]
        is_basic = "Basic" in o["type_line"]
        is_cmdr = o["name"] in cmdr_names
        by_label[tag] = by_label.get(tag, 0) + x["qty"]
        if is_cmdr:
            if sp["commander_must_match"] and tag == "off-theme":
                errors.append(f"commander {o['name']} is off-theme but the theme requires an on-theme commander")
            if sp["exempt_commanders"]:
                continue
        if is_basic and not sp["count_basics"]:
            continue
        counted += x["qty"]
        if tag in primary:
            on_counted += x["qty"]
        if tag == "off-theme":
            off.append(o["name"])
        elif fr and tag == fr:
            fran.append(o["name"])
        if tag != "off-theme":
            legal = [r for r in c.execute("SELECT usd, usd_foil, border, digital, oversized, set_type FROM printings WHERE oracle_id=?",
                                          (o["oracle_id"],)) if legal_printing(dict(r))]
            cheapest = min((r["usd"] if r["usd"] is not None else r["usd_foil"] or 1e9) for r in legal) if legal else None
            mine = p["usd"] if p["usd"] is not None else p["usd_foil"]
            if cheapest is not None and mine is not None and cheapest < 1e9:
                extra = round((mine - cheapest) * x["qty"], 2)
                premium += max(extra, 0)
                if sp["max_premium_per_card"] is not None and extra > sp["max_premium_per_card"]:
                    warns.append(f"{o['name']}: themed printing costs ${extra} more than the cheapest legal one "
                                 f"(limit ${sp['max_premium_per_card']}); ask the user or pick a cheaper themed printing")
    if mode == "strict" and off:
        errors.append(f"strict theme: {len(off)} off-theme card(s): {', '.join(sorted(set(off)))}")
    if sp["max_off_theme"] is not None and len(off) > sp["max_off_theme"]:
        errors.append(f"{len(off)} off-theme cards, limit {sp['max_off_theme']}")
    if sp["max_franchise"] is not None and len(fran) > sp["max_franchise"]:
        errors.append(f"{len(fran)} '{fr}' cards, limit {sp['max_franchise']}")
    if mode == "prefer":
        missing = sorted(n for n in set(off) if n not in reasons)
        if missing:
            warns.append(f"{len(missing)} off-theme card(s) without a reason: {', '.join(missing)}")
    built = theme.get("built")
    if built:
        age = (time.time() - time.mktime(time.strptime(built, "%Y-%m-%d"))) / 86400
        if age > sp["max_map_age_days"]:
            warns.append(f"theme map is {int(age)} days old; rebuild with theme-build so new printings are included")
    return errors, warns, {"mode": mode, "labels": labels, "counts": by_label, "counted_cards": counted,
                           "on_theme_pct": round(100 * on_counted / counted, 1) if counted else None,
                           "off_theme": sorted(set(off)), "franchise": sorted(set(fran)),
                           "theme_premium_usd": round(premium, 2),
                           "exempt": ("commanders " if sp["exempt_commanders"] else "") + ("" if sp["count_basics"] else "basics")}


def theme_args(a):
    theme = load_theme(a.themes)
    if theme:
        for k in ("mode", "max_off_theme", "max_franchise"):
            v = getattr(a, "theme_" + k if k == "mode" else k, None)
            if v is not None:
                theme["spec"][k] = v
    reasons = json.load(open(a.reasons, encoding="utf-8")) if getattr(a, "reasons", None) else {}
    return theme, reasons


def cmd_validate(a):
    c = open_db(a.db)
    theme, reasons = theme_args(a)
    _, rep = check(c, a.deck, load_themes(a.themes) if theme and theme["spec"]["mode"] != "none" else {},
                   a.bracket, a.commanders, a.budget, theme, reasons)
    out(rep, fail=not rep["pass"])


ROLE_RX = {
    "ramp": re.compile(r"add \{|search your library for (?:a|up to \w+) (?:basic )?land|put .*land.* onto the battlefield", re.I),
    "draw": re.compile(r"draw (?:a|two|three|\w+) cards?|draws? cards", re.I),
    "removal": re.compile(r"(?:destroy|exile) target|deals? \d+ damage to (?:any|target)|counter target", re.I),
    "wipe": re.compile(r"(?:destroy|exile) all|each creature gets -|all creatures get -", re.I),
    "tutor": re.compile(r"search your library for (?:a|an) (?!basic|land)", re.I),
}


def cmd_stats(a):
    c = open_db(a.db)
    cards = [x for x in resolve(c, a.deck, {}) if "error" not in x]
    tagmap = tags_for([x["oracle"]["oracle_id"] for x in cards])
    curve, pips, sources, roles, lands, mv = {}, {k: 0 for k in "WUBRG"}, {k: 0 for k in "WUBRGC"}, {}, 0, []
    for x in cards[a.commanders:]:
        o, q = x["oracle"], x["qty"]
        is_land = "Land" in o["type_line"] and "//" not in o["type_line"]
        if is_land:
            lands += q
        else:
            b = min(int(o["cmc"] or 0), 7)
            curve[b] = curve.get(b, 0) + q
            mv += [o["cmc"] or 0] * q
        for ch in re.findall(r"\{([^}]+)\}", o["mana_cost"] or ""):
            for col in "WUBRG":
                if col in ch:
                    pips[col] += q
        if is_land or ("Artifact" in o["type_line"] and o["produced_mana"]):
            for col in set(o["produced_mana"] or ""):
                if col in sources:
                    sources[col] += q
        if is_land:
            continue
        if tagmap:
            ctags = tagmap.get(o["oracle_id"], set())
            for role, tl in ROLE_TAGS.items():
                if ctags & set(tl):
                    roles.setdefault(role, []).append(o["name"])
        else:
            for role, rx in ROLE_RX.items():
                if rx.search(o["oracle_text"] or ""):
                    roles.setdefault(role, []).append(o["name"])
    out({"deck": a.deck, "lands": lands, "avg_mv_nonland": round(sum(mv) / len(mv), 2) if mv else 0,
         "curve": {("7+" if k == 7 else str(k)): v for k, v in sorted(curve.items())}, "pips": pips,
         "sources": sources, "roles": {k: {"count": len(v), "cards": v} for k, v in roles.items()},
         "roles_source": "Scryfall Tagger oracle tags" if tagmap else "regex guesses (run tags-sync for real tags)"})


def cmd_swaptest(a):
    c = open_db(a.db)
    lines = open(a.deck, encoding="utf-8").read().splitlines()
    applied, problems = [], []
    for sw in a.swap:
        m = re.match(r"^-(.+?)\s*\+(.+)$", sw.strip())
        if not m:
            problems.append(f"bad swap syntax: {sw} (use '-Out Card +In Card')")
            continue
        out_c, in_c = m[1].strip(), m[2].strip()
        idx = next((i for i, ln in enumerate(lines) if (e := parse_deck_line(ln)) and e["name"].lower() == out_c.lower()), None)
        if idx is None:
            problems.append(f"swap_out not in deck: {out_c}")
            continue
        lines[idx] = f"1 {in_c}"
        applied.append(sw)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as t:
        t.write("\n".join(lines) + "\n")
    theme, reasons = theme_args(a)
    _, rep = check(c, t.name, load_themes(a.themes) if theme and theme["spec"]["mode"] != "none" else {},
                   a.bracket, a.commanders, a.budget, theme, reasons)
    os.unlink(t.name)
    rep["deck"], rep["swaps"] = a.deck, applied
    rep["errors"] = problems + rep["errors"]
    rep["pass"] = not rep["errors"]
    out(rep, fail=not rep["pass"])


def parse_deck_line(ln):
    m = LINE.match(ln.strip()) if ln.strip() and not ln.strip().startswith(("//", "#")) else None
    return {"name": m[2].strip()} if m else None


# ---------- claims ----------
HIGH_IMPACT = {"must-play", "combo", "cedh", "printing-theme", "ban-or-gc", "trap"}


def cmd_audit_claims(a):
    c = open_db(a.db) if os.path.exists(a.db) else None
    rep = audit(c, a.ledger, a.since, a.require_verified)
    out(rep, fail=not rep["pass"])


def audit(c, ledger, cutoff, require_verified):
    problems, stats = [], {"claims": 0, "high_impact": 0, "verified": 0, "refuted": 0, "unverified": 0}
    for i, ln in enumerate(open(ledger, encoding="utf-8"), 1):
        if not ln.strip():
            continue
        try:
            cl = json.loads(ln)
        except json.JSONDecodeError as e:
            problems.append({"line": i, "problem": f"bad JSON: {e}"})
            continue
        stats["claims"] += 1
        stats[cl.get("status", "unverified")] = stats.get(cl.get("status", "unverified"), 0) + 1
        cid, typ, srcs = cl.get("id", f"line{i}"), cl.get("type"), cl.get("sources") or []
        def bad(msg):
            problems.append({"id": cid, "type": typ, "problem": msg})
        for k in ("id", "type", "claim", "sources", "confidence"):
            if k not in cl:
                bad(f"missing field {k}")
        if typ in HIGH_IMPACT:
            stats["high_impact"] += 1
        for s in srcs:
            if not s.get("url"):
                bad("source without url")
            if not s.get("date"):
                bad(f"source without date: {s.get('url')}")
            elif cutoff and s["date"] < cutoff and typ in HIGH_IMPACT:
                bad(f"source older than {cutoff}: {s['url']} ({s['date']})")
            if s.get("kind") == "video" and not s.get("locator"):
                bad(f"video source without timestamp: {s.get('url')}")
        indep = {(s.get("author") or urlparse(s.get("url", "")).netloc).lower() for s in srcs if s.get("url")}
        if typ in ("must-play", "combo", "trap") and len(indep) < 2:
            bad(f"{typ} needs 2 independent sources, has {len(indep)}")
        if typ == "stat" and not cl.get("n"):
            bad("stat claim without sample size n")
        if c:
            for nm in cl.get("cards", []):
                if not find_oracle(c, nm):
                    sug = ", ".join(s["name"] for s in suggest(c, nm))
                    bad(f"unknown card '{nm}'" + (f" (did you mean: {sug})" if sug else ""))
        if typ in HIGH_IMPACT and cl.get("status") != "verified" and require_verified:
            bad("high-impact claim not verified")
    return {"ledger": ledger, "stats": stats, "problems": problems, "pass": not problems}


# ---------- selftest ----------
def cmd_selftest(a):
    c = open_db(a.db)
    gold = json.load(open(a.golden, encoding="utf-8"))
    results = []
    for g in gold["checks"]:
        oid = find_oracle(c, g["card"])
        if not oid:
            results.append({**g, "ok": False, "got": "card not found"})
            continue
        o = dict(c.execute("SELECT * FROM oracle WHERE oracle_id=?", (oid,)).fetchone())
        got = {"legal": o["commander_legal"], "gc": bool(o["gc"]), "identity": o["color_identity"]}[g["field"]]
        results.append({**g, "got": got, "ok": got == g["expect"]})
    bad = [r for r in results if not r["ok"]]
    out({"golden_as_of": gold.get("as_of"), "passed": len(results) - len(bad), "failed": bad,
         "hint": "A failure means the index is stale/broken OR the golden fact changed (bans, GC updates). Check WotC before editing golden.json."},
        fail=bool(bad))


# ---------- existing decks ----------
def cmd_profile(a):
    """Snapshot of an existing deck for the optimize journey: legality, bracket signals, cost, owned,
    which sets/IPs its printings come from (to detect a theme the user may already have)."""
    c = open_db(a.db)
    theme = load_theme(a.themes)
    cards, rep = check(c, a.deck, load_themes(a.themes) if theme else {}, 4, a.commanders, None, theme, {})
    ok = [x for x in cards if "error" not in x]
    sets, ub = {}, 0
    for x in ok[a.commanders:]:
        if "Basic" in x["oracle"]["type_line"]:
            continue
        p = x["printing"]
        key = f"{p['set_name']} ({p['set_code']})"
        sets[key] = sets.get(key, 0) + x["qty"]
        if (p.get("security_stamp") or "") == "triangle":
            ub += x["qty"]
    nonbasic = sum(x["qty"] for x in ok[a.commanders:] if "Basic" not in x["oracle"]["type_line"])
    top = sorted(sets.items(), key=lambda kv: -kv[1])[:8]
    gcs = rep["game_changers"]
    signal = ("B4+" if len(gcs) > 3 else "B3" if gcs else "B1-B2") + " by Game Changers alone; confirm combos with Spellbook"
    out({"deck": a.deck, "commanders": [x["oracle"]["name"] for x in ok[:a.commanders]],
         "identity": "".join(sorted(set("".join(x["oracle"]["color_identity"] for x in ok[:a.commanders])))) or "C",
         "legal_problems": [e for e in rep["errors"] if "Game Changers" not in e],
         "game_changers": gcs, "bracket_signal": signal, "extra_turn_cards": rep["extra_turn_cards"],
         "price_usd": rep["price_usd"], "unpriced": rep["unpriced"], "collection": rep.get("collection"),
         "printing_sets_top": [{"set": k, "cards": v} for k, v in top],
         "universes_beyond_pct": round(100 * ub / nonbasic, 1) if nonbasic else 0,
         "theme": rep.get("theme"),
         "theme_hint": ("The deck already leans on themed printings: ask whether to keep that theme." if nonbasic and
                        (ub / nonbasic > 0.3 or (top and top[0][1] / nonbasic > 0.3 and top[0][0].lower().find("commander") < 0))
                        else "No strong printing theme detected; default to no theme unless the user says otherwise.")})


def cmd_diff(a):
    """Before/after for an optimized deck: cuts, adds, printing-only swaps, cost of adds (minus owned)."""
    c = open_db(a.db)
    def load(path):
        d = {}
        for x in resolve(c, path, {}):
            if "error" in x:
                continue
            e = d.setdefault(x["oracle"]["name"], {"qty": 0, "printing": f"{x['printing']['set_code']}#{x['printing']['cn']}",
                                                   "usd": x["printing"]["usd"] or x["printing"]["usd_foil"] or 0})
            e["qty"] += x["qty"]
        return d
    old, new = load(a.before), load(a.after)
    col = (load_collection() or {}).get("cards", {})
    cuts = sorted(n for n in old if n not in new)
    adds = sorted(n for n in new if n not in old)
    qty = sorted(f"{n}: {old[n]['qty']} -> {new[n]['qty']}" for n in old if n in new and old[n]["qty"] != new[n]["qty"])
    reprint = sorted(f"{n}: {old[n]['printing']} -> {new[n]['printing']}" for n in old if n in new and old[n]["printing"] != new[n]["printing"])
    buy = [n for n in adds if col.get(n, {}).get("qty", 0) == 0]
    out({"cuts": cuts, "adds": adds, "quantity_changes": qty, "printing_swaps": reprint,
         "changes": len(adds), "cost_of_adds_usd": round(sum(new[n]["usd"] * new[n]["qty"] for n in adds), 2),
         "to_buy": buy, "cost_to_buy_usd": round(sum(new[n]["usd"] * new[n]["qty"] for n in buy), 2),
         "owned_adds": [n for n in adds if n not in buy]})


# ---------- themes ----------
def cmd_theme_build(a):
    """Resolve a theme spec into a printing map. Spec:
    {"mode": "prefer", "labels": [{"label": "Spider-Man", "queries": ["e:spm", "e:sld art:spider-man"],
      "include": ["sld#1996", "oracle:<id>", "name:Card Name"], "exclude": ["sld#123"]}, ...],
     "franchise_label": "Marvel", "max_off_theme": null, ...}
    Labels are in priority order: a printing matched by several labels gets the first one."""
    c = open_db(a.db)
    spec = json.load(open(a.spec, encoding="utf-8"))
    if spec.get("mode", "prefer") not in THEME_MODES:
        sys.exit(f"mode must be one of {THEME_MODES}")
    labels = spec.get("labels") or []
    if spec.get("mode") == "none" or not labels:
        out({"built": time.strftime("%Y-%m-%d"), "spec": dict(THEME_DEFAULTS, **{k: v for k, v in spec.items() if k != "labels"},
             mode="none", labels=[]), "printings": {}, "note": "no theme: all theme checks are skipped"})
    printings, report, problems = {}, {}, []
    for entry in reversed(labels):  # lowest priority first, so higher priority overwrites
        lab, keys = entry["label"], set()
        for q in entry.get("queries", []):
            hits = scryfall_search(q, unique="prints")
            if not hits:
                problems.append(f"{lab}: query matched nothing: {q}")
            keys |= {h["id"] for h in hits}
        for inc in entry.get("include", []):
            if inc.startswith("name:"):
                oid = find_oracle(c, inc[5:])
                if not oid:
                    problems.append(f"{lab}: include name not found: {inc[5:]}")
                    continue
                keys.add(f"oracle:{oid}")
            else:
                keys.add(inc)
        excl = set(entry.get("exclude", []))
        for k in keys:
            if k in excl:
                continue
            if not k.startswith(("oracle:", "set:")) and "#" not in k:
                r = c.execute("SELECT set_code, cn FROM printings WHERE id=?", (k,)).fetchone()
                if r and f"{r['set_code']}#{r['cn']}" in excl:
                    continue
            printings[k] = lab
        report[lab] = len(keys - excl)
    out_spec = dict(THEME_DEFAULTS, **{k: v for k, v in spec.items() if k != "labels"})
    out_spec["labels"] = [e["label"] for e in labels]
    res = {"built": time.strftime("%Y-%m-%d"), "spec": out_spec, "printings": printings,
           "sources": {e["label"]: e.get("queries", []) for e in labels}}
    json.dump(res, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    final = {}
    for v in printings.values():
        final[v] = final.get(v, 0) + 1
    out({"out": a.out, "keys_per_label_after_priority": final, "matched_per_label": report, "problems": problems,
         "next": "Check false positives with contact-sheet and look for gaps with search before trusting this map."},
        fail=bool(problems) and not printings)


def cmd_theme_pool(a):
    """Feasibility: how many distinct, playable, commander-legal cards exist per label inside the commander's colors."""
    c, theme = open_db(a.db), load_theme(a.themes)
    if not theme or theme["spec"]["mode"] == "none":
        out({"error": "no theme map (or mode none)"}, fail=True)
    ident = set()
    for nm in a.commander:
        oid = find_oracle(c, nm)
        if not oid:
            out({"error": f"commander not found: {nm}", "suggestions": suggest(c, nm)}, fail=True)
        ident |= set(c.execute("SELECT color_identity FROM oracle WHERE oracle_id=?", (oid,)).fetchone()[0])
    themes = load_themes(a.themes)
    pool = {}
    for r in c.execute("SELECT p.*, o.name, o.color_identity, o.type_line, o.commander_legal FROM printings p "
                       "JOIN oracle o USING(oracle_id)"):
        r = dict(r)
        if r["commander_legal"] != "legal" or not legal_printing(r) or not set(r["color_identity"]) <= ident:
            continue
        lab = theme_of(r, themes)
        if lab:
            kind = "land" if "Land" in r["type_line"] else "nonland"
            if "Basic" in r["type_line"]:
                kind = "basic"
            pool.setdefault(lab, {"land": set(), "nonland": set(), "basic": set()})[kind].add(r["name"])
    summary = {lab: {k: len(v) for k, v in d.items()} for lab, d in pool.items()}
    primary = [l for l in theme["spec"]["labels"] if l != theme["spec"]["franchise_label"]]
    nonland = len(set().union(*[pool[l]["nonland"] for l in primary if l in pool])) if pool else 0
    allnon = len(set().union(*[d["nonland"] for d in pool.values()])) if pool else 0
    verdict = ("strict looks feasible" if nonland >= 75 else
               "strict is tight: expect weak filler; consider allowing the franchise label" if nonland >= 55 else
               "strict is not realistic: too few on-theme cards in these colors; use prefer with a max_off_theme")
    out({"commander": a.commander, "identity": "".join(sorted(ident)) or "C", "pool": summary,
         "primary_nonland_cards": nonland, "nonland_incl_franchise": allnon, "verdict": verdict,
         "note": "Counts are distinct cards in color identity with a playable themed printing. A 100-card deck needs ~62 nonland cards."})


# ---------- goldfish simulation ----------
def cmd_simulate(a):
    """Monte Carlo goldfish: how often can you cast the commander by turn N, and how often is the opener keepable.
    Model (stated in the output): on the play unless --draw, one land per turn, untapped lands, mana rocks/dorks
    (nonland, cmc <= 3, produce mana; or Tagger ramp tags) cast as soon as affordable and usable next turn,
    land-search ramp counts as +1 land next turn. Colors and tapped lands are ignored, so results are optimistic."""
    import random
    c = open_db(a.db)
    cards = [x for x in resolve(c, a.deck, {}) if "error" not in x]
    cmdrs, library = cards[:a.commanders], []
    tagmap = tags_for([x["oracle"]["oracle_id"] for x in cards])
    ramp_tags = set(ROLE_TAGS["ramp"])
    for x in cards[a.commanders:]:
        o = x["oracle"]
        is_land = "Land" in o["type_line"] and not o["type_line"].startswith(("Instant", "Sorcery", "Creature"))
        tagged = bool(tagmap.get(o["oracle_id"], set()) & ramp_tags) if tagmap else False
        ramp = not is_land and (o["cmc"] or 0) <= 3 and (bool(o["produced_mana"]) or tagged or
                                                       bool(re.search(r"search your library for .*land", o["oracle_text"] or "", re.I)))
        library += [("land" if is_land else "ramp" if ramp else "spell", int(o["cmc"] or 0))] * x["qty"]
    target = a.cmc if a.cmc is not None else max(int(x["oracle"]["cmc"] or 0) for x in cmdrs)
    rng, n, turns = random.Random(a.seed), a.runs, a.turns
    on_turn = [0] * (turns + 1)
    keep_hits = 0
    for _ in range(n):
        deck = library[:]
        rng.shuffle(deck)
        hand, idx = deck[:7], 7
        lands_in_hand = sum(1 for k, _ in hand if k == "land")
        if 2 <= lands_in_hand <= 5:
            keep_hits += 1
        lands, rocks, cast_turn = 0, 0, None  # no mulligans modelled: every opener is kept
        for t in range(1, turns + 1):
            if t > 1 or a.draw:
                if idx < len(deck):
                    hand.append(deck[idx]); idx += 1
            li = next((i for i, h in enumerate(hand) if h[0] == "land"), None)
            if li is not None:
                hand.pop(li); lands += 1
            mana = lands + rocks
            if mana >= target:
                cast_turn = t
                break
            for h in sorted([h for h in hand if h[0] == "ramp"], key=lambda h: h[1]):
                if h[1] <= mana:
                    mana -= h[1]; hand.remove(h); rocks += 1
        if cast_turn:
            on_turn[cast_turn] += 1
    cum, res = 0, {}
    for t in range(1, turns + 1):
        cum += on_turn[t]
        res[f"turn_{t}"] = round(100 * cum / n, 1)
    counts = {k: sum(1 for kk, _ in library if kk == k) for k in ("land", "ramp", "spell")}
    out({"deck": a.deck, "commander_mv": target, "runs": n, "on_the": "draw" if a.draw else "play",
         "pct_commander_cast_by": res, "pct_opening_7_with_2_to_5_lands": round(100 * keep_hits / n, 1),
         "counts": counts, "model": cmd_simulate.__doc__.split("\n", 1)[1].strip()})


# ---------- contact sheet for eyeballing art ----------
def cmd_contact_sheet(a):
    """Grid of card images with labels, so a human or the verifier can check many printings' art at once."""
    from PIL import Image, ImageDraw
    import io
    items = json.load(open(a.items, encoding="utf-8"))  # [{"label": "...", "img": url}]
    W, H, cols = 244, 340, a.cols
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W, rows * (H + 28)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for i, it in enumerate(items):
        x, y = (i % cols) * W, (i // cols) * (H + 28)
        try:
            im = Image.open(io.BytesIO(http_get(it["img"]))).convert("RGB").resize((W, H))
            sheet.paste(im, (x, y))
        except Exception as e:
            d.text((x + 6, y + H // 2), f"image failed: {e}"[:40], fill=(200, 0, 0))
        d.text((x + 4, y + H + 6), str(it.get("label", ""))[:38], fill=(0, 0, 0))
    sheet.save(a.out, quality=85)
    print(a.out)


# ---------- extra store (tags, prices, search cache) ----------
def open_extra():
    os.makedirs(os.path.dirname(EXTRA_DB) or ".", exist_ok=True)
    x = sqlite3.connect(EXTRA_DB, timeout=30)  # parallel agents share this file
    x.row_factory = sqlite3.Row
    x.executescript(EXTRA_SCHEMA)
    return x


def scryfall_search(query, unique="cards", max_age_days=7):
    """Paged Scryfall search, cached in extra.sqlite, rate limited across processes."""
    x = open_extra()
    key = f"{unique}|{query}"
    row = x.execute("SELECT fetched, body FROM search_cache WHERE query=?", (key,)).fetchone()
    if row and time.time() - row["fetched"] < max_age_days * 86400:
        return json.loads(row["body"])
    url = f"https://api.scryfall.com/cards/search?q={quote(query)}&unique={unique}"
    cards = []
    while url:
        try:
            page = json.loads(http_get(url))
        except urllib.error.HTTPError as e:
            if e.code == 404:  # Scryfall: no matches
                break
            raise
        cards += [{"id": c["id"], "oracle_id": c.get("oracle_id") or (c.get("card_faces") or [{}])[0].get("oracle_id"),
                   "name": c["name"], "set": c["set"], "cn": c["collector_number"], "set_name": c.get("set_name"),
                   "img": (c.get("image_uris") or (c.get("card_faces") or [{}])[0].get("image_uris") or {}).get("normal")}
                  for c in page["data"]]
        url = page.get("next_page")
    x.execute("INSERT OR REPLACE INTO search_cache VALUES(?,?,?)", (key, time.time(), json.dumps(cards)))
    x.commit()
    return cards


def cmd_search(a):
    res = scryfall_search(a.query, unique=a.unique, max_age_days=0 if a.fresh else 7)
    out({"query": a.query, "unique": a.unique, "count": len(res), "cards": res[:a.limit] if a.limit else res})


def cmd_tags_sync(a):
    x, today = open_extra(), time.strftime("%Y-%m-%d")
    tags = a.tags or sorted({t for ts in ROLE_TAGS.values() for t in ts})
    report = {}
    for tag in tags:
        cards = scryfall_search(f"otag:{tag}", unique="cards", max_age_days=0 if a.fresh else 30)
        x.execute("DELETE FROM tags WHERE tag=?", (tag,))
        x.executemany("INSERT INTO tags VALUES(?,?,?,?)", [(c["oracle_id"], c["name"], tag, today) for c in cards])
        x.execute("INSERT OR REPLACE INTO tag_sync VALUES(?,?,?)", (tag, today, len(cards)))
        x.commit()  # scryfall_search writes through its own connection; an open transaction here locks it out
        report[tag] = len(cards)
        print(f"{tag}: {len(cards)}", file=sys.stderr)
    x.commit()
    empty = [t for t, n in report.items() if n == 0]
    out({"synced": today, "counts": report,
         "empty_tags": empty, "hint": "Empty tags are probably wrong names: check tagger.scryfall.com and edit ROLE_TAGS"},
        fail=bool(empty) and len(empty) == len(report))


def tags_for(oracle_ids):
    if not os.path.exists(EXTRA_DB):
        return {}
    x = open_extra()
    if not x.execute("SELECT COUNT(*) FROM tag_sync").fetchone()[0]:
        return {}
    res = {}
    for oid in oracle_ids:
        res[oid] = {r[0] for r in x.execute("SELECT tag FROM tags WHERE oracle_id=?", (oid,))}
    return res


# ---------- collection ----------
COL_KEYS = {"name": ["name", "card name", "card"], "qty": ["count", "quantity", "qty", "amount"],
            "set": ["edition", "set code", "set", "edition code"], "cn": ["collector number", "collector_number", "cn", "number"]}


def load_collection():
    if not os.path.exists(COLLECTION):
        return None
    return json.load(open(COLLECTION, encoding="utf-8"))


def cmd_collection(a):
    if a.action == "show":
        col = load_collection()
        if not col:
            out({"error": f"no collection at {COLLECTION}; run: mtgdb.py collection import <file>"}, fail=True)
        if a.card:
            hit = {k: v for k, v in col["cards"].items() if k.lower() == a.card.lower()}
            out({"card": a.card, "owned": hit or None})
        out({k: col[k] for k in ("imported", "source", "unique_cards", "total_cards")})
    c = open_db(a.db)
    rows, unresolved = [], []
    text = open(a.file, encoding="utf-8-sig").read()
    if "," in text.splitlines()[0]:
        rd = csv.DictReader(text.splitlines())
        cols = {k: next((h for h in rd.fieldnames if h.strip().lower() in v), None) for k, v in COL_KEYS.items()}
        if not cols["name"]:
            sys.exit(f"Can't find a name column in {rd.fieldnames}")
        for r in rd:
            q = r.get(cols["qty"]) if cols["qty"] else "1"
            rows.append({"name": r[cols["name"]].strip(), "qty": int(float(q or 1)),
                         "set": (r.get(cols["set"]) or "").strip().lower() if cols["set"] else "",
                         "cn": (r.get(cols["cn"]) or "").strip() if cols["cn"] else ""})
    else:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
        tmp.write(text)
        tmp.close()
        rows = [r for r in parse_deck(tmp.name) if "error" not in r]
        os.unlink(tmp.name)
    cards = {}
    for r in rows:
        oid = find_oracle(c, r["name"])
        if not oid:
            unresolved.append({"name": r["name"], "suggestions": suggest(c, r["name"])})
            continue
        nm = c.execute("SELECT name FROM oracle WHERE oracle_id=?", (oid,)).fetchone()[0]
        e = cards.setdefault(nm, {"qty": 0, "printings": {}})
        e["qty"] += r["qty"]
        if r["set"]:
            k = f"{r['set']}#{r['cn']}"
            e["printings"][k] = e["printings"].get(k, 0) + r["qty"]
    col = {"imported": time.strftime("%Y-%m-%d"), "source": os.path.abspath(a.file), "unique_cards": len(cards),
           "total_cards": sum(v["qty"] for v in cards.values()), "cards": cards}
    os.makedirs(os.path.dirname(COLLECTION) or ".", exist_ok=True)
    json.dump(col, open(COLLECTION, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    out({"saved": COLLECTION, "unique_cards": len(cards), "total_cards": col["total_cards"],
         "unresolved": unresolved}, fail=bool(unresolved) and not cards)


# ---------- MTGJSON prices ----------
MTGJSON = "https://mtgjson.com/api/v5/"


def stream_kv(path):
    """Yield (key, value) from the top-level "data" object, streaming with ijson when available."""
    opener = gzip.open if path.endswith(".gz") else open
    try:
        import ijson
        with opener(path, "rb") as f:
            yield from ijson.kvitems(f, "data", use_float=True)
    except ImportError:
        print("ijson not installed: loading the whole file in memory (pip install ijson)", file=sys.stderr)
        with opener(path, "rt", encoding="utf-8") as f:
            yield from json.load(f)["data"].items()


def fetch_to(url, dst):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=1800) as r, open(dst, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)


def cmd_prices_sync(a):
    os.makedirs(CACHE, exist_ok=True)
    ids = a.identifiers or os.path.join(CACHE, "AllIdentifiers.json.gz")
    if not a.identifiers and (a.refresh_ids or not os.path.exists(ids)):
        print("Downloading MTGJSON AllIdentifiers (large, one time)", file=sys.stderr)
        fetch_to(MTGJSON + "AllIdentifiers.json.gz", ids)
    name = "AllPrices.json.gz" if a.history else "AllPricesToday.json.gz"
    prices = a.prices_file or os.path.join(CACHE, name)
    if not a.prices_file:
        print(f"Downloading MTGJSON {name}", file=sys.stderr)
        fetch_to(MTGJSON + name, prices)
    uuid_to_sf = {}
    for uuid, card in stream_kv(ids):
        sf = (card.get("identifiers") or {}).get("scryfallId")
        if sf:
            uuid_to_sf[uuid] = sf
    x, n, unmapped = open_extra(), 0, 0
    batch = []
    for uuid, fmts in stream_kv(prices):
        sf = uuid_to_sf.get(uuid)
        if not sf:
            unmapped += 1
            continue
        for vendor, pl in (fmts.get("paper") or {}).items():
            cur = pl.get("currency", "")
            for kind in ("retail", "buylist"):
                for finish, series in (pl.get(kind) or {}).items():
                    for date, p in (series or {}).items():
                        batch.append((sf, date, vendor, kind, finish, float(p), cur))
        if len(batch) > 50000:
            x.executemany("INSERT OR REPLACE INTO prices VALUES(?,?,?,?,?,?,?)", batch)
            n += len(batch)
            batch = []
    x.executemany("INSERT OR REPLACE INTO prices VALUES(?,?,?,?,?,?,?)", batch)
    n += len(batch)
    x.commit()
    if n == 0:
        out({"error": "0 price rows parsed: MTGJSON format may have changed; check mtgjson.com/data-models/price"}, fail=True)
    out({"rows": n, "mapped_printings": len(uuid_to_sf), "unmapped_price_entries": unmapped,
         "latest_date": x.execute("SELECT MAX(date) FROM prices").fetchone()[0]})


def vendor_prices(scryfall_id):
    if not os.path.exists(EXTRA_DB):
        return None
    x = open_extra()
    rows = x.execute("""SELECT vendor, kind, finish, price, currency, date FROM prices p WHERE scryfall_id=? AND
        date=(SELECT MAX(date) FROM prices q WHERE q.scryfall_id=p.scryfall_id AND q.vendor=p.vendor)""", (scryfall_id,)).fetchall()
    if not rows:
        return None
    res = {}
    for r in rows:
        res.setdefault(r["vendor"], {})[f"{r['kind']}_{r['finish']}"] = r["price"]
        res[r["vendor"]]["currency"], res[r["vendor"]]["date"] = r["currency"], r["date"]
    return res


def cmd_price_history(a):
    c, x = open_db(a.db), open_extra()
    oid = find_oracle(c, a.card)
    if not oid:
        out({"error": "not found", "suggestions": suggest(c, a.card)}, fail=True)
    q = "SELECT id, set_code, cn FROM printings WHERE oracle_id=?" + (" AND set_code=? AND cn=?" if a.set else "")
    prints = c.execute(q, (oid, a.set.lower(), a.cn) if a.set else (oid,)).fetchall()
    res = []
    for p in prints:
        rows = x.execute("SELECT date, vendor, kind, finish, price FROM prices WHERE scryfall_id=? AND kind='retail' "
                         "ORDER BY date", (p["id"],)).fetchall()
        if rows:
            res.append({"printing": f"{p['set_code']}#{p['cn']}", "series": [dict(r) for r in rows]})
    out({"card": a.card, "printings": res, "note": "Empty means run prices-sync (add --history for 90 days)."})


# ---------- Commander Spellbook (fallback when the MCP is down) ----------
def cmd_combos(a):
    rows = [r for r in parse_deck(a.deck) if "error" not in r]
    body = {"commanders": [{"card": r["name"], "quantity": 1} for r in rows[:a.commanders]],
            "main": [{"card": r["name"], "quantity": r["qty"]} for r in rows[a.commanders:]]}
    raw = http_get("https://backend.commanderspellbook.com/find-my-combos", data=json.dumps(body).encode(),
                   headers={"Content-Type": "application/json"})
    data = json.loads(raw)
    res = data.get("results", data)
    if not isinstance(res, dict) or "included" not in res:
        out({"error": "unexpected Spellbook response shape; use the MCP tool", "keys": list(res)[:20] if isinstance(res, dict) else str(type(res))}, fail=True)
    def summ(v):
        return {"id": v.get("id"), "cards": [u.get("card", {}).get("name") for u in v.get("uses", [])],
                "produces": [p.get("feature", {}).get("name") for p in v.get("produces", [])],
                "bracket_tag": v.get("bracketTag") or v.get("bracket_tag"),
                "url": f"https://commanderspellbook.com/combo/{v.get('id')}/"}
    inc = [summ(v) for v in res.get("included", [])]
    two = [v for v in inc if len([c for c in v["cards"] if c]) == 2]
    out({"deck": a.deck, "included": inc, "two_card": two,
         "almost_included_count": len(res.get("almostIncluded", res.get("almost_included", []))),
         "source": "Commander Spellbook API"})


# ---------- hook (PostToolUse on Write/Edit) ----------
def find_vault(path):
    d = os.path.dirname(os.path.abspath(path))
    while d and d != os.path.dirname(d):
        if os.path.basename(d) == "vault" and os.path.exists(os.path.join(d, "config.json")):
            return d
        d = os.path.dirname(d)
    return None


def cmd_hook(a):
    """Reads Claude Code hook JSON on stdin. Validates vault deck files and claim ledgers as they are written.
    Exit 2 sends the problems back to Claude. Anything unrelated exits 0 silently."""
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    path = (ev.get("tool_input") or {}).get("file_path") or ""
    deck = re.search(r"[\\/]vault[\\/]([^\\/]+)[\\/]b([1-5])\.txt$", path)
    ledger = re.search(r"[\\/]vault[\\/]([^\\/]+)[\\/]claims(\.verified)?\.jsonl$", path)
    if not (deck or ledger) or not os.path.exists(a.db):
        sys.exit(0)
    vault = find_vault(path)
    cfg = json.load(open(os.path.join(vault, "config.json"), encoding="utf-8")) if vault else {}
    themes = os.path.join(vault, "themed-printings.json") if vault else None
    c = open_db(a.db)
    if deck:
        slug, br = deck[1], int(deck[2])
        theme = load_theme(themes)
        rp = os.path.join(os.path.dirname(path), "off-theme.json")
        reasons = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else {}
        _, rep = check(c, path, load_themes(themes), br, (cfg.get("commanders") or {}).get(slug, 1), cfg.get("budget"),
                       theme, reasons)
        if not rep["pass"]:
            print(f"mtgdb validate FAILED for {os.path.basename(path)} (bracket {br}):\n- " + "\n- ".join(rep["errors"])
                  + "\nFix these before reporting the deck as done.", file=sys.stderr)
            sys.exit(2)
        warn = [w for w in rep["warnings"] if "themed_printing_available" in w]
        if warn:
            print("mtgdb: deck passes, but themed printings exist for:\n- " + "\n- ".join(warn[:15]), file=sys.stderr)
            sys.exit(2)
        sys.exit(0)
    rep = audit(c, path, cfg.get("since"), bool(ledger[2]))
    if not rep["pass"]:
        lines = [f"{p.get('id', p.get('line'))}: {p['problem']}" for p in rep["problems"][:25]]
        print(f"audit-claims FAILED for {os.path.basename(path)}:\n- " + "\n- ".join(lines), file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


# ---------- cli ----------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--themes", help="themed-printings.json (keys: printing id, set#cn, set:code)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    def deckargs(s):
        s.add_argument("deck"); s.add_argument("--bracket", type=int, required=True)
        s.add_argument("--commanders", type=int, default=1); s.add_argument("--budget", type=float)
        s.add_argument("--theme-mode", choices=THEME_MODES, help="override the theme map's mode")
        s.add_argument("--max-off-theme", type=int); s.add_argument("--max-franchise", type=int)
        s.add_argument("--reasons", help='JSON {"Card": "why it is off-theme"}')
    s = sp.add_parser("index"); s.add_argument("--bulk-file"); s.set_defaults(f=cmd_index)
    sp.add_parser("info").set_defaults(f=cmd_info)
    s = sp.add_parser("card"); s.add_argument("name"); s.set_defaults(f=cmd_card)
    s = sp.add_parser("printings"); s.add_argument("card"); s.set_defaults(f=cmd_printings)
    s = sp.add_parser("normalize"); s.add_argument("names", nargs="*"); s.add_argument("--cutoff", type=float, default=0.75)
    s.set_defaults(f=cmd_normalize)
    s = sp.add_parser("gamechangers"); s.add_argument("--refresh", action="store_true"); s.set_defaults(f=cmd_gamechangers)
    s = sp.add_parser("resolve"); s.add_argument("deck"); s.add_argument("--out"); s.set_defaults(f=cmd_resolve)
    s = sp.add_parser("validate"); deckargs(s); s.set_defaults(f=cmd_validate)
    s = sp.add_parser("stats"); s.add_argument("deck"); s.add_argument("--commanders", type=int, default=1)
    s.set_defaults(f=cmd_stats)
    s = sp.add_parser("swaptest"); deckargs(s); s.add_argument("--swap", action="append", required=True)
    s.set_defaults(f=cmd_swaptest)
    s = sp.add_parser("audit-claims"); s.add_argument("ledger"); s.add_argument("--since", help="YYYY-MM-DD recency cutoff")
    s.add_argument("--require-verified", action="store_true"); s.set_defaults(f=cmd_audit_claims)
    s = sp.add_parser("selftest"); s.add_argument("--golden", default=os.path.join(os.path.dirname(__file__), "golden.json"))
    s.set_defaults(f=cmd_selftest)
    s = sp.add_parser("search", help="cached, rate-limited Scryfall search (e.g. 'e:sld art:lightsaber')")
    s.add_argument("query"); s.add_argument("--unique", default="cards", choices=["cards", "prints", "art"])
    s.add_argument("--limit", type=int, default=0); s.add_argument("--fresh", action="store_true"); s.set_defaults(f=cmd_search)
    s = sp.add_parser("tags-sync", help="pull Scryfall Tagger role tags (otag:) into extra.sqlite")
    s.add_argument("tags", nargs="*"); s.add_argument("--fresh", action="store_true"); s.set_defaults(f=cmd_tags_sync)
    s = sp.add_parser("collection", help="import or show your card collection")
    s.add_argument("action", choices=["import", "show"]); s.add_argument("file", nargs="?"); s.add_argument("--card")
    s.set_defaults(f=cmd_collection)
    s = sp.add_parser("prices-sync", help="MTGJSON multi-vendor prices (TCGplayer, Card Kingdom, Cardmarket, Cardsphere)")
    s.add_argument("--history", action="store_true", help="90-day AllPrices instead of today only")
    s.add_argument("--identifiers"); s.add_argument("--prices-file"); s.add_argument("--refresh-ids", action="store_true")
    s.set_defaults(f=cmd_prices_sync)
    s = sp.add_parser("price-history"); s.add_argument("card"); s.add_argument("--set"); s.add_argument("--cn")
    s.set_defaults(f=cmd_price_history)
    s = sp.add_parser("combos", help="Commander Spellbook find-my-combos (fallback if the MCP is down)")
    s.add_argument("deck"); s.add_argument("--commanders", type=int, default=1); s.set_defaults(f=cmd_combos)
    sp.add_parser("hook", help="Claude Code PostToolUse hook entry (reads JSON on stdin)").set_defaults(f=cmd_hook)
    s = sp.add_parser("profile", help="snapshot of an existing deck: legality, bracket signals, cost, printing sets (theme hint)")
    s.add_argument("deck"); s.add_argument("--commanders", type=int, default=1); s.set_defaults(f=cmd_profile)
    s = sp.add_parser("diff", help="before/after of an optimized deck: cuts, adds, printing swaps, cost to buy")
    s.add_argument("before"); s.add_argument("after"); s.set_defaults(f=cmd_diff)
    s = sp.add_parser("theme-build", help="resolve a theme spec (queries, includes, excludes, priority) into a theme map")
    s.add_argument("spec"); s.add_argument("--out", default="themed-printings.json"); s.set_defaults(f=cmd_theme_build)
    s = sp.add_parser("theme-pool", help="how many on-theme cards exist in a commander's colors (strict feasibility)")
    s.add_argument("commander", nargs="+"); s.set_defaults(f=cmd_theme_pool)
    s = sp.add_parser("simulate", help="goldfish: percent of games the commander is castable by each turn")
    s.add_argument("deck"); s.add_argument("--commanders", type=int, default=1); s.add_argument("--cmc", type=int)
    s.add_argument("--runs", type=int, default=20000); s.add_argument("--turns", type=int, default=8)
    s.add_argument("--draw", action="store_true"); s.add_argument("--seed", type=int, default=7)
    s.set_defaults(f=cmd_simulate)
    s = sp.add_parser("contact-sheet", help="grid of labelled card images for checking art (needs Pillow)")
    s.add_argument("items", help='JSON list [{"label": "...", "img": "<url>"}]'); s.add_argument("--out", default="sheet.jpg")
    s.add_argument("--cols", type=int, default=8); s.set_defaults(f=cmd_contact_sheet)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
