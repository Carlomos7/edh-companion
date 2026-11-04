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
                [--budget USD] [--aesthetic-budget USD] [--per-card-max USD] [--cheapest] [--hard-budget]
  deck_check.py --commander NAME [--commander NAME]      only check commander eligibility and the pairing

DECK is a Moxfield/Archidekt-style text list ("1 Sol Ring (C21) 263 *F*", sections Commander/Deck/Sideboard),
or a brew.json. Finish markers *F* (foil) and *E* (etched) are read, and Archidekt [Commander] tags.
Commanders come from --commander, the "Commander" section/tag, or brew.json.
Prices are Scryfall's daily prices for the listed printing and finish (verified source, dated); --cheapest also
finds the cheapest paper printing of each card so gameplay cost and the aesthetic premium can be told apart.
Exit: 0 every check passed, 1 a check failed, 2 a check could not run (network/unknown cards).
"""
import argparse, hashlib, json, os, re, ssl, sys, time, urllib.error, urllib.parse, urllib.request
import certifi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analytics  # noqa: E402  roles, mana, simulation

UA = {"User-Agent": "mtg-skills-deck-check/1.0", "Accept": "application/json"}
CTX = ssl.create_default_context(cafile=certifi.where())
GC_LIMIT = {1: 0, 2: 0, 3: 3, 4: None, 5: None}
LINE = re.compile(r"^\s*(\d+)\s*x?\s+(.+?)(?:\s+\(([A-Za-z0-9]{2,6})\)\s*([^\s*\[]+)?)?((?:\s+\*[A-Z]+\*)*)(?:\s+\[([^\]]*)\])?\s*$")
FINISH = {"F": "foil", "E": "etched"}
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
        marks = re.findall(r"\*([A-Z]+)\*", m.group(5) or "")
        finish = next((FINISH[x] for x in marks if x in FINISH), "nonfoil")
        e = {"qty": int(m.group(1)), "name": m.group(2).strip(), "set": (m.group(3) or "").lower() or None, "cn": m.group(4), "finish": finish}
        is_cmd = section == "commander" or "commander" in (m.group(6) or "").lower()
        (cmd if is_cmd else cards).append(e)
    return cards, cmd


def parse_brew(doc):
    cmd = [{"qty": 1, "name": c["name"], "set": c.get("set"), "cn": c.get("collector_number"), "finish": c.get("finish") or "nonfoil"} for c in doc["commander"]["cards"]]
    cards = [{"qty": c["qty"], "name": c["name"], "set": c.get("set"), "cn": c.get("collector_number"), "finish": c.get("finish") or "nonfoil"} for c in doc["deck"]]
    return cards, cmd


def deck_hash(entries, printings=False):
    key = sorted(f"{e['qty']} {e['name'].lower()}" + (f" {e.get('set') or ''} {e.get('cn') or ''} {e.get('finish') or 'nonfoil'}" if printings else "") for e in entries)
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


def price(card, finish):
    """Scryfall price for one finish of this printing, or None."""
    key = {"foil": "usd_foil", "etched": "usd_etched"}.get(finish, "usd")
    v = (card.get("prices") or {}).get(key)
    return float(v) if v else None


def treatment(card):
    """Plain-language printing treatment: what makes this printing look different."""
    bits = [x for x in card.get("frame_effects") or [] if x in ("showcase", "extendedart", "etched", "inverted", "fullart")]
    bits += ["borderless"] if card.get("border_color") == "borderless" else []
    bits += ["full art"] if card.get("full_art") else []
    bits += ["Secret Lair"] if card.get("set") == "sld" else []
    bits += [p for p in card.get("promo_types") or [] if p in ("serialized", "galaxyfoil", "surgefoil", "textured", "halofoil")]
    return ", ".join(dict.fromkeys(bits)) or "regular"


def cheapest(names):
    """Cheapest and priciest paper printing (any finish) per card name, via Scryfall search with unique=prints,
    15 names per query. Returns {name: {usd, set, collector_number, max_usd, max_set, max_collector_number}}."""
    best = {}
    for i in range(0, len(names), 15):
        q = "(" + " or ".join('!"' + n.replace('"', '') + '"' for n in names[i:i + 15]) + ") game:paper"
        url = "https://api.scryfall.com/cards/search?unique=prints&q=" + urllib.parse.quote(q)
        while url:
            res = http(url)
            for c in res.get("data", []):
                vals = [float(v) for k, v in (c.get("prices") or {}).items() if k in ("usd", "usd_foil", "usd_etched") and v]
                if not vals:
                    continue
                b = best.setdefault(c["name"], {"usd": min(vals), "set": c["set"], "collector_number": c["collector_number"],
                                                "max_usd": max(vals), "max_set": c["set"], "max_collector_number": c["collector_number"]})
                if min(vals) < b["usd"]:
                    b.update(usd=min(vals), set=c["set"], collector_number=c["collector_number"])
                if max(vals) > b["max_usd"]:
                    b.update(max_usd=max(vals), max_set=c["set"], max_collector_number=c["collector_number"])
            url = res.get("next_page") if res.get("has_more") else None
            time.sleep(0.5)
    return best


def match_name(card, name):
    n = name.lower()
    return card["name"].lower() == n or any(f["name"].lower() == n for f in card.get("card_faces", []))


def oracle(card):
    return "\n".join([card.get("oracle_text", "")] + [f.get("oracle_text", "") for f in card.get("card_faces", [])])


def is_land(card):
    return "Land" in card.get("type_line", "").split("//")[0]


def front_type(card):
    return (card.get("card_faces") or [card])[0].get("type_line", card.get("type_line", ""))


def can_be_commander(card):
    """CR 903.3 (Sep 2026): a legendary creature, Vehicle, or Spacecraft with power/toughness, or a card that says it
    can be your commander (903.3a). A Background only with a 'choose a Background' partner (702.124k), so not alone."""
    face = (card.get("card_faces") or [card])[0]
    t = front_type(card)
    if "can be your commander" in oracle(card).lower():
        return True
    if "Legendary" not in t:
        return False
    if "Creature" in t or "Vehicle" in t:
        return True
    return "Spacecraft" in t and (face.get("power") is not None or card.get("power") is not None)


def partner_abilities(card):
    """The partner abilities a card has (CR 702.124), read from its Oracle text lines."""
    found = set()
    for line in oracle(card).split("\n"):
        ln = re.sub(r"\s*\(.*?\)\s*$", "", line.strip())
        if re.fullmatch(r"Partner", ln):
            found.add(("partner",))
        elif m := re.fullmatch(r"Partner\s*[—-]\s*(.+)", ln):
            found.add(("partner-text", m.group(1).strip().lower()))
        elif m := re.fullmatch(r"Partner with (.+)", ln):
            found.add(("partner-with", m.group(1).strip().lower()))
        elif ln.lower() == "friends forever":  # pre-2026 printed wording, now "Partner—Friends forever"
            found.add(("partner-text", "friends forever"))
        elif ln.lower() == "choose a background":
            found.add(("background-chooser",))
        elif ln.lower() == "doctor's companion":
            found.add(("doctors-companion",))
    return found


def is_background(card):
    t = front_type(card)
    return "Legendary" in t and "Enchantment" in t and "Background" in t


def is_lone_doctor(card):
    t = front_type(card)
    return "Legendary" in t and "Creature" in t and t.split("—")[-1].split() == ["Time", "Lord", "Doctor"]


def pairing(a, b):
    """Can a and b be commanders together (CR 702.124)? Returns (ok, how or why not). Abilities can't be mixed (702.124f)."""
    pa, pb = partner_abilities(a), partner_abilities(b)
    if ("partner",) in pa and ("partner",) in pb:
        return True, "both have partner"
    shared = {x for x in pa if x[0] == "partner-text"} & {x for x in pb if x[0] == "partner-text"}
    if shared:
        return True, f"both have partner—{sorted(shared)[0][1]}"
    if ("partner-with", b["name"].lower()) in pa and ("partner-with", a["name"].lower()) in pb:
        return True, "partner with each other"
    for x, y in ((a, b), (b, a)):
        if ("background-chooser",) in partner_abilities(x) and is_background(y):
            return True, f"{x['name']} chooses the Background {y['name']}"
        if ("doctors-companion",) in partner_abilities(x) and is_lone_doctor(y) and "Creature" in front_type(x):
            return True, f"{x['name']} is the Doctor's companion of {y['name']}"
    why = "no shared partner ability"
    if is_background(a) or is_background(b):
        why = "a Background needs a commander with 'choose a Background'"
    elif any(x[0] == "partner-with" for x in pa | pb):
        why = "'partner with' only pairs with the named card"
    return False, why


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", nargs="?", help="decklist or brew.json; omit to check only the --commander card(s)")
    ap.add_argument("--commander", action="append", default=[])
    ap.add_argument("--bracket", type=int, choices=range(1, 6))
    ap.add_argument("--theme-sets", default="", help="comma-separated set codes counted as on theme (printing check)")
    ap.add_argument("--no-combos", action="store_true")
    ap.add_argument("--budget", type=float, help="gameplay budget for the whole deck (USD): compared with the cheapest-printing total when --cheapest is on, else the listed total")
    ap.add_argument("--aesthetic-budget", type=float, help="extra spend allowed for chosen printings over the cheapest ones (USD); needs --cheapest")
    ap.add_argument("--per-card-max", type=float, help="most a single listed printing may cost (USD)")
    ap.add_argument("--cheapest", action="store_true", help="also look up each card's cheapest paper printing (slower)")
    ap.add_argument("--hard-budget", action="store_true", help="budgets are hard limits (over = fail); by default they're flexible targets (over = warning with the amount)")
    ap.add_argument("--json", metavar="OUT", help="write the full result (per-card data included) to this file; '-' for stdout")
    a = ap.parse_args()

    if a.deck:
        raw = open(a.deck, encoding="utf-8").read()
        cards, cmd = parse_brew(json.loads(raw)) if a.deck.endswith(".json") else parse_text(raw)
    elif a.commander:
        cards, cmd = [], []
    else:
        ap.error("give a deck, or --commander NAME to check commander eligibility only")
    for n in a.commander:
        if not any(c["name"].lower() == n.lower() for c in cmd):
            cards = [c for c in cards if c["name"].lower() != n.lower()]
            cmd.append({"qty": 1, "name": n, "set": None, "cn": None, "finish": "nonfoil"})
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
    bad = [i for i, e in enumerate(entries) if (c := found.get(i)) and e.get("set") and not match_name(c, e["name"])]
    wrong = [f"{entries[i]['name']} ({entries[i]['set'].upper()} {entries[i]['cn']} is {found[i]['name']})" for i in bad]
    if bad:  # check the named card from here on, not the card the wrong number points at
        byname, _ = fetch([{"name": entries[i]["name"]} for i in bad])
        for k, i in enumerate(bad):
            if k in byname:
                found[i] = byname[k]
            else:
                found.pop(i)
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
            "finish": e.get("finish") or "nonfoil", "finishes_available": c.get("finishes", []), "price_usd": price(c, e.get("finish")),
            "price_source": "Scryfall daily price", "illustration_id": c.get("illustration_id"), "treatment": treatment(c),
            "artist": c.get("artist"), "scryfall_uri": c.get("scryfall_uri"),
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

    cmd_cards = [found[i] for i in range(len(cmd)) if i in found]
    deck_rows = [(entries[i], found[i]) for i in range(len(cmd), len(entries)) if i in found]
    if not cmd:
        check("chk-legality-2", "legality", "A commander is named", "unverified", "no commander given (use --commander or a Commander section)")
    elif len(cmd) > 2:
        check("chk-legality-2", "legality", "One commander, or two with a partner ability (CR 702.124g)", "fail", f"{len(cmd)} commanders listed", [c["name"] for c in cmd])
    elif len(cmd_cards) == len(cmd):
        # Scryfall's is:commander is the second, independent source for eligibility; disagreements are flagged.
        try:
            q = "(" + " or ".join('!"' + c["name"].replace('"', "") + '"' for c in cmd_cards) + ") is:commander"
            sf = {c["name"] for c in http("https://api.scryfall.com/cards/search?q=" + urllib.parse.quote(q)).get("data", [])}
        except Exception:
            sf = None  # 404 when none match is also an exception; handled below
        bad_cmd, notes = [], []
        for c in cmd_cards:
            ok = can_be_commander(c) or (len(cmd) == 2 and is_background(c))
            if sf is not None and (c["name"] in sf) != can_be_commander(c) and not is_background(c):
                notes.append(f"Scryfall is:commander disagrees for {c['name']}")
            if not ok:
                bad_cmd.append(c["name"])
        if len(cmd) == 1 and is_background(cmd_cards[0]):
            bad_cmd, why = [cmd_cards[0]["name"]], "a Background can only be a second commander (CR 702.124k)"
        else:
            why = "not a legendary creature, Vehicle or Spacecraft with power/toughness, and doesn't say it can be your commander (CR 903.3)"
        banned_cmd = [c["name"] for c in cmd_cards if c["legalities"].get("commander") == "banned"]
        st = "fail" if bad_cmd or banned_cmd else ("warning" if notes else "pass")
        detail = "; ".join(x for x in [(", ".join(bad_cmd) + ": " + why) if bad_cmd else "", ("banned: " + ", ".join(banned_cmd)) if banned_cmd else "", "; ".join(notes)] if x)
        check("chk-legality-2", "legality", "Commander is eligible (CR 903.3) and not banned", st, detail, bad_cmd + banned_cmd)
        if len(cmd) == 2:
            ok, how = pairing(cmd_cards[0], cmd_cards[1])
            check("chk-legality-3", "legality", "The two commanders share a partner ability (CR 702.124)", "pass" if ok else "fail", how,
                  [] if ok else [c["name"] for c in cmd_cards])

    identity = set(x for c in cmd_cards for x in c.get("color_identity", []))
    off = [c["name"] for e, c in deck_rows if not set(c.get("color_identity", [])) <= identity]
    check("chk-identity-1", "identity", f"Every card within the commander color identity ({''.join(sorted(identity)) or 'C'})", "fail" if off else "pass", ", ".join(off), off)

    today = time.strftime("%Y-%m-%d")
    banned = [c["name"] for e, c in rows if c["legalities"].get("commander") == "banned"]
    upcoming = [(c["name"], c.get("released_at")) for e, c in rows
                if c["legalities"].get("commander") == "not_legal" and (c.get("released_at") or "") > today and not c.get("digital")]
    illegal = [c["name"] for e, c in rows if c["legalities"].get("commander") not in ("legal", "banned") and c["name"] not in {n for n, _ in upcoming}]
    if upcoming:
        check("chk-legality-4", "legality", "Unreleased cards (not legal until released)", "warning",
              "; ".join(f"{n}: releases {d} (Scryfall release date; Commander legality expected on release, not yet confirmed)" for n, d in upcoming),
              [n for n, _ in upcoming])
    for card in out["cards"]:
        hit = next((d for n, d in upcoming if n == card["name"]), None)
        card["status"] = "banned" if card["legal"] == "banned" else ("upcoming" if hit else ("legal" if card["legal"] == "legal" else "not_legal"))
        if hit:
            card["releases"] = hit
    check("chk-legality-1", "legality", "No banned or non-Commander-legal cards", "fail" if banned or illegal else "pass",
          "; ".join(x for x in [("banned: " + ", ".join(banned)) if banned else "", ("not legal: " + ", ".join(illegal)) if illegal else ""] if x), banned + illegal)

    unplayable = [f"{c['name']} ({c['set'].upper()} {c['collector_number']}: " + ", ".join(x for x in ["digital" if c.get("digital") else "", "gold border" if c.get("border_color") == "gold" else "", "oversized" if c.get("oversized") else ""] if x) + ")"
                  for e, c in rows if e.get("set") and (c.get("digital") or c.get("border_color") == "gold" or c.get("oversized"))]
    if any(e.get("set") for e, c in rows):
        check("chk-printing-1", "printing", "Listed printings are tournament-playable paper cards", "fail" if unplayable else "pass", "; ".join(unplayable))

    nofinish = [f"{c['name']} ({c['set'].upper()} {c['collector_number']}): no {e['finish']} version" for e, c in rows
                if e.get("finish", "nonfoil") != "nonfoil" and e["finish"] not in (c.get("finishes") or [])]
    if nofinish:
        check("chk-printing-3", "printing", "Each listed finish (foil, etched) exists for that printing", "fail", "; ".join(nofinish))

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

    nonland = [(e, c) for e, c in deck_rows if not is_land(c)]
    curve = {}
    for e, c in nonland:
        k = str(min(int(c.get("cmc") or 0), 7)) + ("+" if int(c.get("cmc") or 0) >= 7 else "")
        curve[k] = curve.get(k, 0) + e["qty"]
    types = {}
    for e, c in deck_rows:
        front = c.get("type_line", "").split("//")[0]
        t = next((x for x in ("Land", "Creature", "Planeswalker", "Battle", "Artifact", "Enchantment", "Instant", "Sorcery") if x in front), "Other")
        types[t] = types.get(t, 0) + e["qty"]
    priced = [(e, c, price(c, e.get("finish"))) for e, c in rows]
    prices = [p * e["qty"] for e, c, p in priced if p is not None]
    unpriced = [c["name"] for e, c, p in priced if p is None and "Basic" not in c.get("type_line", "")]
    out["stats"].update({"cards": total, "lands": types.get("Land", 0), "curve": dict(sorted(curve.items())), "types": types,
                         "average_mv": round(sum((c.get("cmc") or 0) * e["qty"] for e, c in nonland) / max(1, sum(e["qty"] for e, c in nonland)), 2),
                         "price_usd": round(sum(prices), 2), "price_unpriced": unpriced, "price_as_of": out["checked"],
                         "price_note": f"{len(prices)} of {len(rows)} lines priced: Scryfall daily price for the listed printing and finish (default printing when none listed)"})
    deck_qty = [(e["qty"], c) for e, c in deck_rows]
    counts, per = analytics.role_counts(deck_qty)
    out["stats"]["roles"] = counts
    out["stats"]["roles_note"] = "from fixed Oracle-text rules (analytics.py); a card can count in several roles"
    for card in out["cards"]:
        card["roles"] = per.get(card["name"], {}) if not card["commander"] else analytics.roles(next(c for c in cmd_cards if c["name"] == card["name"]))
    out["stats"]["mana"] = analytics.mana([(e["qty"], c) for e, c in rows], identity)
    if len(cmd_cards) == 1 and deck_rows:
        mv = int(cmd_cards[0].get("cmc") or 0)
        out["stats"]["cast_by_turn"] = analytics.simulate(deck_qty, mv)
    elif len(cmd_cards) == 2 and deck_rows:
        out["stats"]["cast_by_turn"] = analytics.simulate(deck_qty, max(int(c.get("cmc") or 0) for c in cmd_cards))
        out["stats"]["cast_by_turn"]["assumptions"] += "; two commanders: the more expensive one"
    listed = out["stats"]["price_usd"]
    cheap_total = None
    if a.cheapest or a.aesthetic_budget is not None:
        try:
            names = sorted({c["name"] for e, c in rows if "Basic" not in c.get("type_line", "")})
            best = cheapest(names)
            cheap_total = round(sum(best[c["name"]]["usd"] * e["qty"] for e, c in rows if c["name"] in best), 2)
            both = [(e, c, p) for e, c, p in priced if p is not None and c["name"] in best]
            premium = round(sum((p - best[c["name"]]["usd"]) * e["qty"] for e, c, p in both), 2)
            out["stats"]["price_ladder"] = {"affordable_usd": cheap_total, "as_listed_usd": listed,
                                            "premium_usd": round(sum(best[c["name"]]["max_usd"] * e["qty"] for e, c in rows if c["name"] in best), 2),
                                            "note": "affordable = cheapest paper printing of each card, premium = most expensive; basics excluded; Scryfall daily prices", "as_of": out["checked"]}
            out["stats"].update({"price_cheapest_usd": cheap_total, "aesthetic_premium_usd": premium,
                                 "premium_note": f"over {len(both)} cards priced both ways",
                                 "cheapest_missing": [n for n in names if n not in best]})
            for card in out["cards"]:
                if card["name"] in best:
                    card["cheapest"] = best[card["name"]]
        except Exception as ex:
            out["unavailable"].append(f"Scryfall printings search: {ex}")
    if a.budget is not None:
        basis, total = ("cheapest printings", cheap_total) if cheap_total is not None else ("listed printings", listed)
        missing = out["stats"].get("cheapest_missing", []) if cheap_total is not None else unpriced
        over = "fail" if a.hard_budget else "warning"
        st = over if total > a.budget else ("unverified" if missing else "pass")
        check("chk-budget-1", "other", f"Gameplay cost within ${a.budget:g} ({basis}, {'hard limit' if a.hard_budget else 'flexible target'})", st,
              f"${total} for {basis}" + (f"; no price for: {', '.join(missing)}" if missing else ""))
    if a.aesthetic_budget is not None:
        if cheap_total is None:
            check("chk-budget-2", "other", f"Aesthetic premium within ${a.aesthetic_budget:g}", "unverified", "cheapest printings couldn't be looked up")
        else:
            prem = out["stats"]["aesthetic_premium_usd"]
            st = ("fail" if a.hard_budget else "warning") if prem > a.aesthetic_budget else ("unverified" if unpriced else "pass")
            check("chk-budget-2", "other", f"Aesthetic premium (chosen printings over their cheapest) within ${a.aesthetic_budget:g}", st,
                  f"premium ${prem} ({out['stats']['premium_note']})" + (f"; no price for the chosen printing of: {', '.join(unpriced)}" if unpriced else ""))
    if a.per_card_max is not None:
        over = [f"{c['name']} ${p}" for e, c, p in priced if p is not None and p > a.per_card_max]
        check("chk-budget-3", "other", f"No listed printing over ${a.per_card_max:g} each ({'hard limit' if a.hard_budget else 'flexible target'})",
              ("fail" if a.hard_budget else "warning") if over else "pass", "; ".join(over))

    if not a.no_combos and cmd:
        try:
            body = {"commanders": [{"card": n} for n in out["commanders"]], "main": [{"card": c["name"], "quantity": e["qty"]} for e, c in deck_rows]}
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
