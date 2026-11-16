#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi", "truststore"]
# ///
"""A project's theme card pool as a reviewed lockfile, so brew and audit stop re-discovering it every session.

  pool.py sweep <project>                 discover printings through every channel in sources/theme-rule.json and
                                          update sources/pool.lock.json (+ pool.diff.md listing what changed)
  pool.py accept|reject <project> ID ...  the player's call on entries (ID = Scryfall id or set:number, e.g. sld:863)
  pool.py footer <project> --marvel ID ... | --not ID ...
                                          record what each card's copyright footer says (read from art_sheet.py sheets)
  pool.py art <project> ID --characters "Spider-Man, Venom" | --none [--by NAME]
                                          record who the art shows, keyed by illustration_id (sources/art_notes.json)
  pool.py art-seed <project>              seed art_notes from Scryfall's Art Tags bulk (community data: unverified)
  pool.py freshness <project>             data ages and changes since the last check (Game Changers, bans, theme set
                                          sizes, Scryfall card ID migrations); exit 1 warning, 2 error
  pool.py list <project> [--status accepted|pending|rejected]

Channels (sources/theme-rule.json says which count and which wins a conflict):
  set        the printing's set name matches `set_name` (Scryfall default_cards bulk, plus a date>now search for
             cards newer than the bulk file)
  drop       an MTGJSON Secret Lair drop (card `subsets`) matches `drop_name`; other_drop: a drop that doesn't
  untagged   a card in `untagged_sets` with no drop name at all (Universes Beyond bonus cards hide here)
  footer     the © line on the card image, read once per card; footer_absent when it names someone else
  player     the player's accept / reject
Bulk hosts have no rate limit; the bulk file is fetched only when Scryfall's updated_at changes. Brew and audit read
only `accepted` entries. Deck usage is not stored here: derive it from the brew files.
"""
import argparse, datetime, gzip, hashlib, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edhcore.cache import cache_dir  # noqa: E402
from edhcore.http import Client, RequestError, Unavailable  # noqa: E402

API = "https://api.scryfall.com"
MTGJSON = "https://mtgjson.com/api/v5"
STRONG_DEFAULT = ["set", "drop", "footer", "player"]
DEFAULT_RULE = {
    "theme": "Marvel",
    "set_name": r"Marvel|Spider-Man|Darkhold",
    "drop_name": r"Marvel|Spider-Man|Spider-Verse|Avengers|X-Men|Deadpool|Wolverine|Venom|Black Panther|Iron Man|Captain America|Hulk|Thor|Fantastic Four|Daily Bugle|Doctor Strange",
    "untagged_sets": ["sld"],
    "footer": "MARVEL",
    "art_tag": r"spider-man|spider-woman|spider-gwen|peter parker|miles morales|venom|marvel",
    "strong": STRONG_DEFAULT,
    "weak": ["untagged"],
    "rejecting": ["footer_absent", "other_drop"],
    "wins": ["player", "footer"],
    "_doc": "strong: one is enough to accept. weak: pending until something strong or rejecting arrives. rejecting: "
            "rejected unless strong evidence exists. wins: first kind present decides a conflict outright.",
}
FRESH_DEFAULT = {"warn_days": 7, "error_days": 30}


def today():
    return datetime.date.today().isoformat()


def P(project, *parts):
    return os.path.join(project, "sources", *parts)


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as h:
            return json.load(h)
    except FileNotFoundError:
        return default


def save(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as h:
        h.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    os.replace(path + ".tmp", path)


def rule_for(project):
    path = P(project, "theme-rule.json")
    r = load(path)
    if r is None:
        save(path, DEFAULT_RULE)
        print(f"wrote {path} (default Marvel rule: edit it for another theme)")
        r = DEFAULT_RULE
    return {**DEFAULT_RULE, **r}


def status_of(evidence, rule):
    """Deterministic status from evidence kinds, per the rule file."""
    kinds = {e.split(":", 1)[0] if not e.startswith("player") else e for e in evidence}
    for w in rule["wins"]:  # e.g. the player's call, then the footer, decide outright
        if w == "player":
            if "player:reject" in kinds:
                return "rejected"
            if "player:accept" in kinds:
                return "accepted"
        elif w in kinds:
            return "accepted"
        elif w + "_absent" in kinds:
            return "rejected"
    if kinds & set(rule["strong"]):
        return "accepted"
    if kinds & set(rule["rejecting"]):
        return "rejected"
    return "pending"


# --- data sources ----------------------------------------------------------------------------------------------------
def bulk_cards(client, kind="default_cards"):
    """Stream Scryfall bulk JSONL (gzip). Downloaded into the cache dir only when updated_at changes."""
    info = client.get_json(f"{API}/bulk-data/{kind.replace('_', '-')}")
    path = os.path.join(cache_dir(), "bulk", kind + ".jsonl.gz")
    meta = client.snapshot(info["jsonl_download_uri"], path, key=info["updated_at"])
    meta["updated_at"] = info["updated_at"]

    def rows():
        with gzip.open(path, "rt", encoding="utf-8") as h:
            for line in h:
                line = line.strip().rstrip(",")
                if line and line not in "[]":
                    yield json.loads(line)
    return rows, meta


def drops(client, sets):
    """{scryfall_id: [drop names]} from MTGJSON set files (Secret Lair `subsets`), plus snapshot meta per set."""
    out, metas = {}, {}
    for code in sets:
        path = os.path.join(cache_dir(), "mtgjson", code.upper() + ".json")
        metas[code] = client.snapshot(f"{MTGJSON}/{code.upper()}.json", path)
        with open(path, encoding="utf-8") as h:
            doc = json.load(h)
        metas[code]["version"] = doc.get("meta", {}).get("version")
        for c in doc["data"]["cards"]:
            sid = (c.get("identifiers") or {}).get("scryfallId")
            if sid:
                out[sid] = c.get("subsets") or []
    return out, metas


def upcoming(client, set_codes):
    """Cards Scryfall shows before they reach the bulk file (date>now in the theme's sets)."""
    if not set_codes:
        return []
    q = "(" + " or ".join(f"e:{s}" for s in sorted(set_codes)) + ") date>now"
    url, out = f"{API}/cards/search?unique=prints&q=" + __import__("urllib.parse").parse.quote(q), []
    while url:
        try:
            page = client.get_json(url)
        except RequestError as e:  # 404: nothing upcoming
            if e.code == 404:
                return out
            raise
        out += page.get("data", [])
        url = page.get("next_page")
    return out


# --- sweep ------------------------------------------------------------------------------------------------------------
def entry(c, evidence):
    return {"name": c["name"], "oracle_id": c.get("oracle_id") or (c.get("card_faces") or [{}])[0].get("oracle_id"),
            "illustration_id": c.get("illustration_id") or (c.get("card_faces") or [{}])[0].get("illustration_id"),
            "set": c["set"], "number": c["collector_number"], "released_at": c.get("released_at"),
            "image_status": c.get("image_status"), "evidence": sorted(set(evidence))}


def classify(cards, drop_map, rule):
    """{scryfall_id: entry} for every card some channel finds, from bulk card dicts and the drop map."""
    set_rx, drop_rx = re.compile(rule["set_name"], re.I), re.compile(rule["drop_name"], re.I)
    untagged = {s.lower() for s in rule["untagged_sets"]}
    found, theme_sets = {}, set()
    for c in cards:
        if c.get("digital") or c.get("set_type") in ("token", "memorabilia") or c.get("layout") in ("token", "double_faced_token", "art_series", "emblem"):
            continue  # not deck cards
        ev = []
        if set_rx.search(c.get("set_name") or ""):
            ev.append("set")
            theme_sets.add(c["set"])
        if c["set"] in untagged:
            names = drop_map.get(c["id"])
            if names is None:
                pass  # MTGJSON doesn't list it: no drop evidence either way
            elif not names:
                ev.append("untagged")
            else:
                ev += [("drop:" if drop_rx.search(n) else "other_drop:") + n for n in names]
        if any(e == "set" or e == "untagged" or e.startswith("drop:") for e in ev):
            found[c["id"]] = entry(c, ev)
    return found, theme_sets


def sweep(project, client=None, cards=None, drop_map=None, extra=None, sources=None):
    """Merge a new discovery into pool.lock.json. Sticky: first_seen, footer and player evidence, notes."""
    rule = rule_for(project)
    client = client or Client()
    if cards is None:
        rows, bmeta = bulk_cards(client)
        drop_map, dmetas = drops(client, rule["untagged_sets"])
        cards = rows()
        sources = {"scryfall_default_cards": {k: bmeta.get(k) for k in ("updated_at", "sha256")},
                   **{f"mtgjson_{k}": {"version": v.get("version"), "sha256": v.get("sha256")} for k, v in dmetas.items()}}
    found, theme_sets = classify(cards, drop_map or {}, rule)
    if extra is None:
        try:
            extra = upcoming(client, theme_sets)
        except Unavailable:
            extra = []
    more, more_sets = classify(extra, drop_map or {}, rule)
    theme_sets |= more_sets
    for k, v in more.items():
        found.setdefault(k, v)
    lock = load(P(project, "pool.lock.json"), {"cards": {}})
    old = lock["cards"]
    diff = {"added": [], "status": [], "gone": []}
    new = {}
    for sid, e in found.items():
        prev = old.get(sid, {})
        keep = [x for x in prev.get("evidence", []) if x.split(":", 1)[0] in ("footer", "footer_absent", "player")]
        e["evidence"] = sorted(set(e["evidence"]) | set(keep))
        e["first_seen"] = prev.get("first_seen") or today()
        e["status"] = status_of(e["evidence"], rule)
        if not prev:
            diff["added"].append((sid, e))
        elif prev.get("status") != e["status"]:
            diff["status"].append((sid, e, prev.get("status")))
        new[sid] = e
    for sid, prev in old.items():  # kept when the player or a footer spoke for it; otherwise reported as gone
        if sid not in new:
            if prev.get("status") == "removed" or any(x.split(":", 1)[0] in ("footer", "player") for x in prev.get("evidence", [])):
                new[sid] = prev
            else:
                diff["gone"].append((sid, prev))
    lock = {"theme": rule["theme"], "swept": today(), "sources": sources or lock.get("sources") or {},
            "theme_sets": sorted(theme_sets | set(lock.get("theme_sets", []))),
            "counts": {s: sum(1 for e in new.values() if e["status"] == s) for s in ("accepted", "pending", "rejected", "removed")},
            "cards": dict(sorted(new.items(), key=lambda kv: (kv[1]["set"], kv[1]["number"].zfill(6))))}
    save(P(project, "pool.lock.json"), lock)
    write_diff(project, lock, diff)
    return lock, diff


def label(sid, e):
    return f"{e['set'].upper()} {e['number']} {e['name']} [{', '.join(e['evidence'])}] ({sid[:8]})"


def write_diff(project, lock, diff):
    L = [f"# Pool changes, {lock['swept']}", "", "Counts: " + ", ".join(f"{k} {v}" for k, v in lock["counts"].items()), ""]
    for st in ("accepted", "pending", "rejected"):
        rows = [label(s, e) for s, e in diff["added"] if e["status"] == st]
        if rows:
            L += [f"## New, {st} ({len(rows)})"] + [f"- {r}" for r in rows] + [""]
    if diff["status"]:
        L += ["## Status changed"] + [f"- {label(s, e)}: {old} → {e['status']}" for s, e, old in diff["status"]] + [""]
    if diff["gone"]:
        L += ["## No longer found (dropped)"] + [f"- {label(s, e)}" for s, e in diff["gone"]] + [""]
    if len(L) == 4:
        L.append("No changes.")
    with open(P(project, "pool.diff.md"), "w", encoding="utf-8", newline="\n") as h:
        h.write("\n".join(L) + "\n")


# --- the player's and the reader's calls --------------------------------------------------------------------------------
def resolve(lock, ids):
    by_num = {f"{e['set']}:{e['number']}".lower(): s for s, e in lock["cards"].items()}
    out, missing = [], []
    for i in ids:
        s = i if i in lock["cards"] else by_num.get(i.lower())
        (out if s else missing).append(s or i)
    if missing:
        sys.exit("not in the pool: " + ", ".join(missing))
    return out


def add_evidence(project, ids, ev, drop_prefixes=()):
    rule, lock = rule_for(project), load(P(project, "pool.lock.json"))
    if not lock:
        sys.exit("no pool.lock.json yet: run `pool.py sweep` first")
    for s in resolve(lock, ids):
        e = lock["cards"][s]
        e["evidence"] = sorted({x for x in e["evidence"] if not x.startswith(drop_prefixes)} | {ev})
        e["status"] = status_of(e["evidence"], rule)
        print(f"{e['status']:9} {label(s, e)}")
    lock["counts"] = {st: sum(1 for e in lock["cards"].values() if e["status"] == st) for st in ("accepted", "pending", "rejected", "removed")}
    save(P(project, "pool.lock.json"), lock)


def art(project, ident, characters, by):
    lock = load(P(project, "pool.lock.json"), {"cards": {}})
    notes = load(P(project, "art_notes.json"), {})
    ill = ident
    if ident in lock["cards"] or ":" in ident:
        e = lock["cards"][resolve(lock, [ident])[0]]
        ill = e["illustration_id"]
        status = e.get("image_status")
    else:
        status = next((e.get("image_status") for e in lock["cards"].values() if e.get("illustration_id") == ill), None)
    notes[ill] = {**notes.get(ill, {}), "characters": characters, "verified_by": by, "image_status": status, "checked_at": today()}
    notes[ill].pop("stale", None)
    save(P(project, "art_notes.json"), notes)
    print(f"{ill}: {', '.join(characters) or 'no theme characters'} ({by}, {status})")


def stale_art(project):
    """Mark notes whose image got better since they were checked (lowres → highres_scan): they need a new look."""
    lock, notes = load(P(project, "pool.lock.json"), {"cards": {}}), load(P(project, "art_notes.json"), {})
    rank = {"missing": 0, "placeholder": 0, "lowres": 1, "highres_scan": 2}
    n = 0
    for e in lock["cards"].values():
        note = notes.get(e.get("illustration_id"))
        if (note and not note.get("verified_by", "").startswith("scryfall-tagger")  # tags were never an image check
                and rank.get(e.get("image_status"), 0) > rank.get(note.get("image_status"), 0) and not note.get("stale")):
            note["stale"], n = True, n + 1
    if n:
        save(P(project, "art_notes.json"), notes)
    return n


def art_seed(project, client=None, tags=None):
    rule = rule_for(project)
    rx = re.compile(rule["art_tag"], re.I)
    lock = load(P(project, "pool.lock.json"), {"cards": {}})
    want = {e["illustration_id"] for e in lock["cards"].values() if e.get("illustration_id")}
    if tags is None:
        rows, _ = bulk_cards(client or Client(), "art_tags")
        tags = rows()
    notes, n = load(P(project, "art_notes.json"), {}), 0
    for t in tags:
        if t.get("type") != "illustration" or not rx.search(t.get("label", "")):
            continue
        for tg in t.get("taggings", []):
            ill = tg.get("illustration_id")
            if ill not in want:
                continue
            note = notes.setdefault(ill, {"characters": [], "tag_ids": [], "verified_by": "scryfall-tagger (community, unverified)",
                                          "image_status": None, "checked_at": today()})
            if t["id"] not in note.setdefault("tag_ids", []):
                note["tag_ids"].append(t["id"])
                if note["verified_by"].startswith("scryfall-tagger"):
                    note["characters"] = sorted(set(note["characters"]) | {t["label"]})
                n += 1
    save(P(project, "art_notes.json"), notes)
    return n


# --- freshness ----------------------------------------------------------------------------------------------------------
def search_ids(client, q):
    url, ids = f"{API}/cards/search?q=" + __import__("urllib.parse").parse.quote(q), []
    while url:
        page = client.get_json(url)
        ids += [c.get("oracle_id") or c["id"] for c in page["data"]]
        url = page.get("next_page")
    return hashlib.sha1("\n".join(sorted(ids)).encode()).hexdigest()[:12], len(ids)


def migrations(client, since):
    url, out = f"{API}/migrations", []
    while url:
        page = client.get_json(url)
        rows = [m for m in page["data"] if (m.get("performed_at") or "") >= since]
        out += rows
        url = page.get("next_page") if len(rows) == len(page["data"]) else None
    return out


def apply_migrations(project, migs):
    lock = load(P(project, "pool.lock.json"))
    if not lock:
        return []
    done = []
    for m in migs:
        old = lock["cards"].get(m["old_scryfall_id"])
        if not old:
            continue
        if m["migration_strategy"] == "merge" and m.get("new_scryfall_id"):
            lock["cards"].pop(m["old_scryfall_id"])
            lock["cards"].setdefault(m["new_scryfall_id"], {**old, "migrated_from": m["old_scryfall_id"]})
            done.append(f"{label(m['old_scryfall_id'], old)} merged into {m['new_scryfall_id'][:8]}")
        elif m["migration_strategy"] == "delete":
            old["status"] = "removed"
            done.append(f"{label(m['old_scryfall_id'], old)} deleted by Scryfall")
    if done:
        save(P(project, "pool.lock.json"), lock)
    return done


def days(a, b):
    return (datetime.date.fromisoformat(b[:10]) - datetime.date.fromisoformat(a[:10])).days


def freshness(project, client=None, now=None):
    """(level, lines): 0 ok, 1 warning, 2 error. Records the values so the next run reports changes."""
    client, now = client or Client(), now or today()
    fp = P(project, "freshness.json")
    doc = load(fp, {})
    th = {**FRESH_DEFAULT, **doc.get("thresholds", {})}
    last = doc.get("last", {})
    lock = load(P(project, "pool.lock.json"))
    cur, lines, level = {"checked": now}, [], 0

    def flag(lv, msg):
        nonlocal level
        level = max(level, lv)
        lines.append(("ok  " if lv == 0 else "WARN" if lv == 1 else "ERR ") + " " + msg)
    try:
        b = client.get_json(f"{API}/bulk-data/default-cards")
        cur["scryfall_bulk"] = b["updated_at"]
        m = client.get_json(f"{MTGJSON}/Meta.json")["data"]
        cur["mtgjson"] = f"{m.get('date')} {m.get('version')}"
        cur["game_changers"], ngc = search_ids(client, "is:gamechanger")
        cur["commander_banned"], nban = search_ids(client, "banned:commander")
        sets = {s["code"]: s["card_count"] for s in client.get_json(f"{API}/sets")["data"]}
        cur["theme_sets"] = {s: sets.get(s) for s in (lock or {}).get("theme_sets", [])}
    except (Unavailable, RequestError, KeyError) as e:
        flag(2, f"couldn't reach the card data ({e}); theme and legality checks are unverified until it works")
        return level, lines
    flag(0, f"Scryfall bulk {cur['scryfall_bulk'][:10]}, MTGJSON {cur['mtgjson']}; {ngc} Game Changers, {nban} banned")
    for k, what, fix in (("game_changers", "Game Changers list changed", "re-audit bracket checks"),
                         ("commander_banned", "Commander banned list changed", "re-audit legality")):
        if last.get(k) and last[k] != cur[k]:
            flag(1, f"{what} since {last.get('checked')}: {fix}")
    grown = [f"{s.upper()} {last['theme_sets'].get(s)} → {n}" for s, n in cur["theme_sets"].items()
             if (last.get("theme_sets") or {}).get(s) not in (None, n)]
    if grown:
        flag(1, "theme set sizes changed (" + ", ".join(grown) + "): run `pool.py sweep`")
    if lock:
        age = days(lock["swept"], now)
        lv = 2 if age > th["error_days"] else 1 if age > th["warn_days"] else 0
        flag(lv, f"pool swept {lock['swept']} ({age} days ago; warn after {th['warn_days']}, error after {th['error_days']})")
        for msg in apply_migrations(project, migrations(client, last.get("checked") or lock["swept"])):
            flag(1, "Scryfall ID migration: " + msg)
        if (n := stale_art(project)):
            flag(1, f"{n} art notes have a better image now: re-check them (art_sheet.py)")
        if lock["counts"].get("pending"):
            flag(0, f"{lock['counts']['pending']} pool entries pending (not used until accepted)")
    else:
        flag(1, "no pool.lock.json: run `pool.py sweep` before theme checks rely on the pool")
    save(fp, {"thresholds": th, "last": cur})
    return level, lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["sweep", "accept", "reject", "footer", "art", "art-seed", "freshness", "list"])
    ap.add_argument("project")
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--marvel", nargs="*", default=[], help="footer: cards whose footer names the theme's owner")
    ap.add_argument("--not", dest="other", nargs="*", default=[], help="footer: cards whose footer names someone else")
    ap.add_argument("--characters", help="art: comma-separated characters the art shows")
    ap.add_argument("--none", action="store_true", help="art: the art shows no theme character")
    ap.add_argument("--by", default="claude (image viewed)")
    ap.add_argument("--status")
    a = ap.parse_args()
    if a.cmd == "sweep":
        lock, diff = sweep(a.project)
        print(f"pool: {lock['counts']}; {len(diff['added'])} new, {len(diff['status'])} changed, {len(diff['gone'])} gone "
              f"(see {P(a.project, 'pool.diff.md')})")
    elif a.cmd in ("accept", "reject"):
        add_evidence(a.project, a.ids, "player:" + a.cmd, ("player",))
    elif a.cmd == "footer":
        if a.marvel:
            add_evidence(a.project, a.marvel, "footer", ("footer",))
        if a.other:
            add_evidence(a.project, a.other, "footer_absent", ("footer",))
    elif a.cmd == "art":
        if not a.ids or not (a.characters or a.none):
            sys.exit("art needs one ID and --characters or --none")
        art(a.project, a.ids[0], [] if a.none else [c.strip() for c in a.characters.split(",") if c.strip()], a.by)
    elif a.cmd == "art-seed":
        print(f"{art_seed(a.project)} tag links added to art_notes.json (community tags: unverified)")
    elif a.cmd == "freshness":
        level, lines = freshness(a.project)
        print("\n".join(lines))
        sys.exit(level)
    else:
        lock = load(P(a.project, "pool.lock.json"), {"cards": {}})
        for s, e in lock["cards"].items():
            if not a.status or e["status"] == a.status:
                print(f"{e['status']:9} {label(s, e)}")


if __name__ == "__main__":
    main()
