#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi"]
# ///
"""Deterministic Commander deck checks from Scryfall and Commander Spellbook's public APIs.

Why a script: the same deck must get the same answer every time. MCP deck validators were down (502) and the
bracket estimator missed Game Changers and banned cards when this was written; card-by-card web lookups are slow
and drift. This file only reports facts with fixed rules. Judgment (theme fit, power, art) stays with the auditor.

Usage:
  deck_check.py DECK [--commander NAME ...] [--bracket N] [--theme-sets spm,spe,...] [--no-combos] [--json OUT]

DECK is a Moxfield/Archidekt-style text list ("1 Sol Ring (C21) 263 *F*", sections Commander/Deck/Sideboard),
or a brew.json. Commanders come from --commander, the "Commander" section, or brew.json.
Exit: 0 every check passed, 1 a check failed, 2 a check could not run (network/unknown cards).
"""
import argparse, hashlib, json, re, ssl, sys, time, urllib.error, urllib.request
import certifi

UA = {"User-Agent": "mtg-skills-deck-check/1.0", "Accept": "application/json"}
CTX = ssl.create_default_context(cafile=certifi.where())
GC_LIMIT = {1: 0, 2: 0, 3: 3, 4: None, 5: None}
LINE = re.compile(r"^\s*(\d+)\s*x?\s+(.+?)(?:\s+\(([A-Za-z0-9]{2,6})\)\s*([^\s*]+)?)?(?:\s+\*[A-Z]+\*)*\s*$")
SECTION = re.compile(r"^\s*(commanders?|deck|main(board)?|sideboard|maybeboard|companion|considering)\s*:?\s*$", re.I)


def http(url, body=None, tries=3):
    data = json.dumps(body).encode() if body is not None else None
    hdr = dict(UA, **({"Content-Type": "application/json"} if data else {}))
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=hdr), timeout=60, context=CTX) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(2 * (i + 1) + (30 if e.code == 429 else 0))
                continue
            raise
        except urllib.error.URLError:
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"{url} unreachable after {tries} tries")


def parse_text(text):
    cards, cmd, section = [], [], "deck"
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith(("#", "//")):
            continue
        m = SECTION.match(s)
        if m:
            section = "commander" if m.group(1).lower().startswith("commander") else ("deck" if m.group(1).lower() in ("deck", "main", "mainboard") else "skip")
            continue
        if section == "skip":
            continue
        m = LINE.match(s)
        if not m:
            m = LINE.match("1 " + s)
        if not m:
            continue
        e = {"qty": int(m.group(1)), "name": m.group(2).strip(), "set": (m.group(3) or "").lower() or None, "cn": m.group(4)}
        (cmd if section == "commander" else cards).append(e)
    return cards, cmd


def parse_brew(doc):
    cmd = [{"qty": 1, "name": c["name"], "set": c.get("set"), "cn": c.get("collector_number")} for c in doc["commander"]["cards"]]
    cards = [{"qty": c["qty"], "name": c["name"], "set": c.get("set"), "cn": c.get("collector_number")} for c in doc["deck"]]
    return cards, cmd


def deck_hash(entries, printings=False):
    key = sorted(f"{e['qty']} {e['name'].lower()}" + (f" {e.get('set') or ''} {e.get('cn') or ''}" if printings else "") for e in entries)
    return hashlib.sha1("\n".join(key).encode()).hexdigest()[:12]


def fetch(entries):
    """Scryfall /cards/collection, 75 per call. Returns {index: card} and a list of not-found entries."""
    found, missing = {}, []
    ids = [({"set": e["set"], "collector_number": e["cn"]} if e.get("set") and e.get("cn") else {"name": e["name"].split(" // ")[0] if " // " in e["name"] else e["name"]}) for e in entries]
    for start in range(0, len(ids), 75):
        chunk = ids[start:start + 75]
        res = http("https://api.scryfall.com/cards/collection", {"identifiers": chunk})
        for card in res.get("data", []):
            for k, ident in enumerate(chunk):
                i = start + k
                if i in found:
                    continue
                if ("name" in ident and match_name(card, ident["name"])) or ("set" in ident and card["set"] == ident["set"].lower() and card["collector_number"] == ident["collector_number"]):
                    found[i] = card
                    break
        time.sleep(0.5)
    for i, e in enumerate(entries):
        if i not in found:
            missing.append(e["name"])
    return found, missing


def match_name(card, name):
    n = name.lower()
    return card["name"].lower() == n or any(f["name"].lower() == n for f in card.get("card_faces", []))


def oracle(card):
    return "\n".join([card.get("oracle_text", "")] + [f.get("oracle_text", "") for f in card.get("card_faces", [])])


def is_land(card):
    return "Land" in card.get("type_line", "").split("//")[0]


def can_be_commander(card):
    t, o = card.get("type_line", ""), oracle(card).lower()
    return ("Legendary" in t and "Creature" in t) or "can be your commander" in o or "Background" in t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck")
    ap.add_argument("--commander", action="append", default=[])
    ap.add_argument("--bracket", type=int, choices=range(1, 6))
    ap.add_argument("--theme-sets", default="", help="comma-separated set codes counted as on theme (printing check)")
    ap.add_argument("--no-combos", action="store_true")
    ap.add_argument("--json", metavar="OUT", help="write the full result (per-card data included) to this file; '-' for stdout")
    a = ap.parse_args()

    raw = open(a.deck, encoding="utf-8").read()
    cards, cmd = parse_brew(json.loads(raw)) if a.deck.endswith(".json") else parse_text(raw)
    for n in a.commander:
        if not any(c["name"].lower() == n.lower() for c in cmd):
            cards = [c for c in cards if c["name"].lower() != n.lower()]
            cmd.append({"qty": 1, "name": n, "set": None, "cn": None})
    entries = cmd + cards
    out = {"deck_hash": deck_hash(entries), "printings_hash": deck_hash(entries, True), "checked": time.strftime("%Y-%m-%d"),
           "commanders": [c["name"] for c in cmd], "checks": [], "cards": [], "combos": None, "stats": {}, "unavailable": []}

    def check(cid, area, req, status, detail="", cards_=()):
        out["checks"].append({"id": cid, "area": area, "requirement": req, "kind": "deterministic", "status": status, "detail": detail, "cards": list(cards_)})

    try:
        found, missing = fetch(entries)
    except Exception as e:
        out["unavailable"].append(f"Scryfall: {e}")
        check("chk-legality-1", "legality", "Every card legal in Commander", "unverified", f"Scryfall unreachable: {e}")
        return finish(out, a)

    if missing:
        check("chk-cards-1", "other", "Every name is a real paper card", "fail", "not found on Scryfall: " + "; ".join(missing), missing)
    else:
        check("chk-cards-1", "other", "Every name is a real paper card", "pass")
    # A (SET) number that points at a different card is a wrong printing, not the named card.
    wrong = [f"{e['name']} ({e['set'].upper()} {e['cn']} is {c['name']})" for i, e in enumerate(entries) if (c := found.get(i)) and e.get("set") and not match_name(c, e["name"])]
    if wrong:
        check("chk-printing-2", "printing", "Each listed set and collector number is a printing of the named card", "fail", "; ".join(wrong), [w.split(" (")[0] for w in wrong])
    rows = []
    for i, e in enumerate(entries):
        c = found.get(i)
        if not c:
            continue
        rows.append((e, c))
        out["cards"].append({
            "name": c["name"], "qty": e["qty"], "commander": i < len(cmd), "oracle_id": c.get("oracle_id"), "printing_id": c["id"],
            "set": c["set"], "collector_number": c["collector_number"], "set_name": c.get("set_name"), "type_line": c.get("type_line"),
            "mana_cost": c.get("mana_cost") or (c.get("card_faces") or [{}])[0].get("mana_cost"), "cmc": c.get("cmc"),
            "color_identity": c.get("color_identity", []), "legal": c["legalities"].get("commander"), "game_changer": bool(c.get("game_changer")),
            "digital": c.get("digital", False), "border": c.get("border_color"), "oversized": c.get("oversized", False),
            "price_usd": (c.get("prices") or {}).get("usd"), "artist": c.get("artist"), "scryfall_uri": c.get("scryfall_uri"),
            "image": (c.get("image_uris") or (c.get("card_faces") or [{}])[0].get("image_uris") or {}).get("normal"),
            "art_crop": (c.get("image_uris") or (c.get("card_faces") or [{}])[0].get("image_uris") or {}).get("art_crop"),
        })

    total = sum(e["qty"] for e in entries)
    check("chk-count-1", "count", "Exactly 100 cards including commanders", "pass" if total == 100 else "fail", f"{total} cards")

    names = {}
    for e, c in rows:
        names[c["name"]] = names.get(c["name"], 0) + e["qty"]
    dup = [n for n, q in names.items() if q > 1 and not any(
        ("Basic" in c["type_line"] and n == c["name"]) or "any number of cards named" in oracle(c).lower() or re.search(r"up to \w+ cards named", oracle(c).lower())
        for e, c in rows if c["name"] == n)]
    check("chk-singleton-1", "singleton", "No duplicates except basics and 'any number' cards", "fail" if dup else "pass", ", ".join(dup), dup)

    cmd_cards = [c for e, c in rows[:len(cmd)]] if len(rows) >= len(cmd) else []
    bad_cmd = [c["name"] for c in cmd_cards if not can_be_commander(c)]
    if not cmd:
        check("chk-legality-2", "legality", "A commander is named", "unverified", "no commander given (use --commander or a Commander section)")
    else:
        check("chk-legality-2", "legality", "Commander can be a commander (legendary creature or says so)", "fail" if bad_cmd else "pass", ", ".join(bad_cmd), bad_cmd)
        if len(cmd) == 2:
            kw = [set(c.get("keywords", [])) | ({"Background"} if "Background" in c.get("type_line", "") else set()) for c in cmd_cards]
            ok = len(kw) == 2 and (("Partner" in kw[0] and "Partner" in kw[1]) or "Background" in kw[0] | kw[1] or "Friends forever" in kw[0] & kw[1]
                                   or "Doctor's companion" in kw[0] | kw[1] or any("partner with" in oracle(c).lower() for c in cmd_cards))
            check("chk-legality-3", "legality", "Two commanders are allowed together (partner, background, friends forever...)", "pass" if ok else "warning",
                  "" if ok else "could not confirm the pairing from keywords; read both cards")

    identity = set(x for c in cmd_cards for x in c.get("color_identity", []))
    off = [c["name"] for e, c in rows[len(cmd):] if not set(c.get("color_identity", [])) <= identity]
    check("chk-identity-1", "identity", f"Every card within the commander color identity ({''.join(sorted(identity)) or 'C'})", "fail" if off else "pass", ", ".join(off), off)

    banned = [c["name"] for e, c in rows if c["legalities"].get("commander") == "banned"]
    illegal = [c["name"] for e, c in rows if c["legalities"].get("commander") not in ("legal", "banned")]
    check("chk-legality-1", "legality", "No banned or non-Commander-legal cards", "fail" if banned or illegal else "pass",
          "; ".join(x for x in [("banned: " + ", ".join(banned)) if banned else "", ("not legal: " + ", ".join(illegal)) if illegal else ""] if x), banned + illegal)

    unplayable = [f"{c['name']} ({c['set'].upper()} {c['collector_number']}: " + ", ".join(x for x in ["digital" if c.get("digital") else "", "gold border" if c.get("border_color") == "gold" else "", "oversized" if c.get("oversized") else ""] if x) + ")"
                  for e, c in rows if e.get("set") and (c.get("digital") or c.get("border_color") == "gold" or c.get("oversized"))]
    if any(e.get("set") for e, c in rows):
        check("chk-printing-1", "printing", "Listed printings are tournament-playable paper cards", "fail" if unplayable else "pass", "; ".join(unplayable))

    gcs = sorted(c["name"] for e, c in rows if c.get("game_changer"))
    out["stats"]["game_changers"] = gcs
    if a.bracket:
        lim = GC_LIMIT[a.bracket]
        st = "pass" if lim is None or len(gcs) <= lim else "fail"
        check("chk-game-changers-1", "game_changers", f"Game Changers within bracket {a.bracket} limit ({'any' if lim is None else lim})", st, f"{len(gcs)}: " + ", ".join(gcs), gcs)

    ind = []
    for e, c in rows:
        o = oracle(c).lower()
        if "extra turn" in o:
            ind.append(f"extra turns: {c['name']}")
        if re.search(r"destroy all lands|each player sacrifices .*lands|lands don't untap|lands do not untap", o):
            ind.append(f"possible mass land denial: {c['name']}")
        if re.search(r"search your library for (a|an|up to \w+) (card|instant|sorcery|creature|artifact|enchantment)", o) and not is_land(c):
            ind.append(f"tutor: {c['name']}")
    out["bracket_indicators"] = ind

    if a.theme_sets:
        sets = {s.strip().lower() for s in a.theme_sets.split(",") if s.strip()}
        offt = [f"{c['name']} ({c['set'].upper()})" for e, c in rows if c["set"] not in sets and "Basic" not in c.get("type_line", "")]
        check("chk-theme-1", "theme", "Every chosen printing is from an on-theme set (" + ", ".join(sorted(sets)) + ")", "warning" if offt else "pass",
              f"{len(offt)} printings outside those sets (exceptions and art still need a human/auditor look): " + "; ".join(offt[:40]), [x.split(" (")[0] for x in offt])

    nonland = [(e, c) for e, c in rows[len(cmd):] if not is_land(c)]
    curve = {}
    for e, c in nonland:
        k = str(min(int(c.get("cmc") or 0), 7)) + ("+" if int(c.get("cmc") or 0) >= 7 else "")
        curve[k] = curve.get(k, 0) + e["qty"]
    types = {}
    for e, c in rows[len(cmd):]:
        front = c.get("type_line", "").split("//")[0]
        t = next((x for x in ("Land", "Creature", "Planeswalker", "Battle", "Artifact", "Enchantment", "Instant", "Sorcery") if x in front), "Other")
        types[t] = types.get(t, 0) + e["qty"]
    prices = [float(c["prices"]["usd"]) * e["qty"] for e, c in rows if (c.get("prices") or {}).get("usd")]
    out["stats"].update({"cards": total, "lands": types.get("Land", 0), "curve": dict(sorted(curve.items())), "types": types,
                         "average_mv": round(sum((c.get("cmc") or 0) * e["qty"] for e, c in nonland) / max(1, sum(e["qty"] for e, c in nonland)), 2),
                         "price_usd": round(sum(prices), 2), "price_note": f"{len(prices)} of {len(rows)} cards priced (Scryfall usd, listed or default printing)"})

    if not a.no_combos and cmd:
        try:
            body = {"commanders": [{"card": n} for n in out["commanders"]], "main": [{"card": c["name"], "quantity": e["qty"]} for e, c in rows[len(cmd):]]}
            res = http("https://backend.commanderspellbook.com/find-my-combos", body)
            r = res.get("results", res)
            inc = []
            for v in r.get("included", []):
                pieces = [u["card"]["name"] for u in v.get("uses", [])]
                non_cmd = [p for p in pieces if p not in out["commanders"]]
                inc.append({"cards": pieces, "spellbook_id": v.get("id"), "result": "; ".join(f["feature"]["name"] for f in v.get("produces", [])[:4]),
                            "two_card": len(non_cmd) <= 2, "url": f"https://commanderspellbook.com/combo/{v.get('id')}/"})
            out["combos"] = {"included": inc, "almost_included_count": len(r.get("almostIncluded", r.get("almost_included", [])))}
            if a.bracket and a.bracket <= 3:
                two = [" + ".join(x["cards"]) for x in inc if x["two_card"]]
                check("chk-combos-1", "combos", "No two-card combos (commander + up to 2 cards counts) at bracket 1 to 3",
                      "fail" if two and a.bracket <= 2 else ("warning" if two else "pass"),
                      ("bracket 3 allows them only late and not held as an early win; read each: " if a.bracket == 3 and two else "") + " | ".join(two))
        except Exception as e:
            out["unavailable"].append(f"Commander Spellbook: {e}")
            check("chk-combos-1", "combos", "Known combos checked against Commander Spellbook", "unverified", f"Spellbook unreachable: {e}")
    return finish(out, a)


def finish(out, a):
    if a.json:
        txt = json.dumps(out, indent=1, ensure_ascii=False)
        if a.json == "-":
            print(txt)
        else:
            open(a.json, "w", encoding="utf-8").write(txt)
    if a.json != "-":
        print(f"deck_hash {out['deck_hash']}  printings_hash {out['printings_hash']}  checked {out['checked']}")
        for c in out["checks"]:
            print(f"[{c['status'].upper():10}] {c['id']}: {c['requirement']}" + (f" -- {c['detail']}" if c["detail"] else ""))
        if out.get("stats"):
            s = out["stats"]
            print(f"stats: {s.get('cards')} cards, {s.get('lands')} lands, avg MV {s.get('average_mv')}, GC {len(s.get('game_changers', []))}, ${s.get('price_usd')}")
        if out.get("bracket_indicators"):
            print("indicators (read in context): " + "; ".join(out["bracket_indicators"]))
        if out.get("combos"):
            for x in out["combos"]["included"]:
                print(f"combo{' (two-card)' if x['two_card'] else ''}: {' + '.join(x['cards'])} -> {x['result']}  {x['url']}")
        for u in out["unavailable"]:
            print("UNAVAILABLE:", u)
    st = [c["status"] for c in out["checks"]]
    sys.exit(1 if "fail" in st else (2 if "unverified" in st or out["unavailable"] else 0))


if __name__ == "__main__":
    main()
