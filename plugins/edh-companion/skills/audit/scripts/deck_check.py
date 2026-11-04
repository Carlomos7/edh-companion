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
                [--fresh | --offline] [--project DIR]
  deck_check.py --commander NAME [--commander NAME]      only check commander eligibility and the pairing

DECK is a Moxfield/Archidekt-style text list ("1 Sol Ring (C21) 263 *F*", sections Commander/Deck/Sideboard),
or a brew.json. Finish markers *F* (foil) and *E* (etched) are read, and Archidekt [Commander] tags.
Commanders come from --commander, the "Commander" section/tag, or brew.json.
Prices are Scryfall's daily prices for the listed printing and finish (verified source, dated); --cheapest also
finds the cheapest paper printing of each card so gameplay cost and the aesthetic premium can be told apart.
Card data is cached (scripts/edhcore): --fresh refetches everything (final audits, exports), --offline uses the cache
only. Checks that relied on stale or unavailable data are reported unverified, never pass; see the "data" block.
Exit: 0 every check passed, 1 a check failed, 2 a check could not run (network/unknown cards).
"""
import argparse, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "scripts"))
import analytics  # noqa: E402  roles, mana, simulation
from edhcore.cards import front_type, is_land, match_name, oracle, price, prices_any, record, treatment  # noqa: E402,F401
from edhcore.decklist import FINISH, LINE, SECTION, deck_hash, parse_brew, parse_text  # noqa: E402,F401
from edhcore.http import CTX, MAX_WAIT, Client, RequestError, Unavailable  # noqa: E402,F401
from edhcore.session import RANK, Session, ident_for  # noqa: E402
from edhcore.types import card_types  # noqa: E402

GC_LIMIT = {1: 0, 2: 0, 3: 3, 4: None, 5: None}
_SESSION = None


def session():
    """The run's data session (main() sets it from the flags; library callers get a default one)."""
    global _SESSION
    if _SESSION is None:
        _SESSION = Session()
    return _SESSION


def measured(fn, *args):
    """(result, how fresh the data of this one call was), keeping the session's overall status."""
    s = session()
    before, s.status = s.status, "fresh"
    try:
        return fn(*args), s.status
    finally:
        s.status = max(before, s.status, key=RANK.get)


def http(url, body=None, tries=3, sleep=time.sleep):
    """GET (or POST JSON) through the shared client (edhcore.http): 429 waits for Retry-After, 5xx and network errors
    back off; raises Unavailable when retries run out, RequestError at once for other 4xx. Not cached."""
    c = Client(policy=session().policy, tries=tries, sleep=sleep)
    return c.post_json(url, body) if body is not None else c.get_json(url)


def fetch(entries):
    """Card data for decklist entries (cached, 75 per request). Returns {index: card} and the names not found.
    Raises Unavailable when some cards have no data at all (network down and nothing cached)."""
    cards, not_found, unavailable = session().scryfall.collection([ident_for(e) for e in entries])
    if unavailable:
        raise Unavailable("api.scryfall.com/cards/collection", f"no data for {len(unavailable)} cards")
    return {i: c for i, c in enumerate(cards) if c is not None}, [entries[i]["name"] for i in not_found]


def cheapest(names):
    """Cheapest and priciest paper printing (any finish) per card name, via Scryfall search with unique=prints,
    15 names per query. Each name's printings are also cached on their own ("prints:<name>"), so a variant that shares
    most cards with another only searches for the rest.
    Returns {name: {usd, set, collector_number, max_usd, max_set, max_collector_number}}."""
    s, prints, misses = session(), [], []
    for n in names:
        hit = s.cached("prints:" + n.lower(), "price")
        if hit is None:
            misses.append(n)
        else:
            prints += hit
    for i in range(0, len(misses), 15):
        chunk = misses[i:i + 15]
        q = "(" + " or ".join('!"' + n.replace('"', '') + '"' for n in chunk) + ") game:paper"
        found, st = measured(s.scryfall.search, q, "prints")
        found = [{k: c.get(k) for k in ("name", "set", "collector_number", "prices")} for c in found]
        prints += found
        if st == "fresh":  # a stale or cached copy is never re-dated as new
            for n in chunk:
                s.cache.put("prints:" + n.lower(), "search", [c for c in found if c["name"].lower() == n.lower()])
    best = {}
    for c in prints:
        vals = prices_any(c)
        if not vals:
            continue
        b = best.setdefault(c["name"], {"usd": min(vals), "set": c["set"], "collector_number": c["collector_number"],
                                        "max_usd": max(vals), "max_set": c["set"], "max_collector_number": c["collector_number"]})
        if min(vals) < b["usd"]:
            b.update(usd=min(vals), set=c["set"], collector_number=c["collector_number"])
        if max(vals) > b["max_usd"]:
            b.update(max_usd=max(vals), max_set=c["set"], max_collector_number=c["collector_number"])
    return best




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
    ap.add_argument("--cards-only", action="store_true", help="just look the cards up (batched, 75 per request) and write their data; no deck checks. For research: write once to <project>/cards.json and reuse it")
    ap.add_argument("--json", metavar="OUT", help="write the full result (per-card data included) to this file; '-' for stdout")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fresh", action="store_true", help="refetch all card data (final audits, exports); cached copies only if the network fails, marked stale")
    g.add_argument("--offline", action="store_true", help="cache only, no network requests")
    ap.add_argument("--project", metavar="DIR", help="project folder: its research preferences decide which providers may be called")
    a = ap.parse_args()
    global _SESSION
    _SESSION = Session(fresh=a.fresh, offline=a.offline, project=a.project)

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

    scry = session().scryfall
    try:
        (got, not_found, unav), card_st = measured(scry.collection, [ident_for(e) for e in entries])
        why = "; ".join(session().client.unavailable.values()) or "no cached copy"
    except Exception as ex:  # noqa: BLE001  e.g. JSONDecodeError from a captive portal's HTML
        session()._mark("unavailable")
        unav, why = entries, f"{type(ex).__name__}: {ex}"
    if entries and len(unav) == len(entries):
        out["unavailable"].append(f"Scryfall: {why}")
        check("chk-legality-1", "legality", "Every card legal in Commander", "unverified", f"Scryfall unreachable: {why}")
        return finish(out, a)
    found = {i: c for i, c in enumerate(got) if c is not None}
    missing = [entries[i]["name"] for i in not_found]
    no_data = [entries[i]["name"] for i in unav]

    if missing:
        check("chk-cards-1", "other", "Every name is a real paper card", "fail", "not found on Scryfall: " + "; ".join(missing)
              + (f"; card data unavailable (not checked): {'; '.join(no_data)}" if no_data else ""), missing)
    elif no_data:
        check("chk-cards-1", "other", "Every name is a real paper card", "unverified",
              "card data unavailable (Scryfall unreachable, nothing cached): " + "; ".join(no_data), no_data)
    else:
        check("chk-cards-1", "other", "Every name is a real paper card", "pass")
    if no_data:
        out["unavailable"].append(f"Scryfall: no card data for {len(no_data)} cards: " + "; ".join(no_data))
    # A (SET) number that points at a different card is a wrong printing, not the named card.
    bad = [i for i, e in enumerate(entries) if (c := found.get(i)) and e.get("set") and not match_name(c, e["name"])]
    wrong = [f"{entries[i]['name']} ({entries[i]['set'].upper()} {entries[i]['cn']} is {found[i]['name']})" for i in bad]
    if bad:  # check the named card from here on, not the card the wrong number points at
        (byname, _, _), st2 = measured(scry.collection, [{"name": entries[i]["name"].split(" // ")[0]} for i in bad])
        card_st = max(card_st, st2, key=RANK.get)
        for k, i in enumerate(bad):
            if byname[k] is not None:
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
        out["cards"].append(record(c, e["qty"], i < len(cmd), e.get("finish")))

    today = time.strftime("%Y-%m-%d")
    upcoming = [(c["name"], c.get("released_at")) for e, c in rows
                if c["legalities"].get("commander") == "not_legal" and (c.get("released_at") or "") > today and not c.get("digital")]
    for card in out["cards"]:
        hit = next((d for n, d in upcoming if n == card["name"]), None)
        card["status"] = "banned" if card["legal"] == "banned" else ("upcoming" if hit else ("legal" if card["legal"] == "legal" else "not_legal"))
        if hit:
            card["releases"] = hit
    if a.cards_only:
        out["checks"] = [c for c in out["checks"] if c["id"] in ("chk-cards-1", "chk-printing-2")]
        return finish(out, a)

    total = sum(e["qty"] for e in entries)
    if a.deck:  # --commander alone checks eligibility, not a deck
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
            sf = {c["name"] for c in scry.search(q)} or None  # none match: no second opinion, as before
        except Exception:
            sf = None
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

    banned = [c["name"] for e, c in rows if c["legalities"].get("commander") == "banned"]
    illegal = [c["name"] for e, c in rows if c["legalities"].get("commander") not in ("legal", "banned") and c["name"] not in {n for n, _ in upcoming}]
    if upcoming:
        check("chk-legality-4", "legality", "Unreleased cards (not legal until released)", "warning",
              "; ".join(f"{n}: releases {d} (Scryfall release date; Commander legality expected on release, not yet confirmed)" for n, d in upcoming),
              [n for n, _ in upcoming])
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
    for e, c in deck_rows:  # edhcore.types: the same rule the pages use (front face for DFCs, every half for split cards)
        t = card_types(c)["type_group"]
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
    cheap_total, cheap_st, combo_st = None, "fresh", "fresh"
    if a.cheapest or a.aesthetic_budget is not None:
        try:
            names = sorted({c["name"] for e, c in rows if "Basic" not in c.get("type_line", "")})
            best, cheap_st = measured(cheapest, names)
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

    if not a.no_combos and cmd and a.deck:
        try:
            res, combo_st = measured(session().spellbook.find_my_combos, out["commanders"], [(c["name"], e["qty"]) for e, c in deck_rows])
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
    degrade(out, no_data, card_st, cheap_st, combo_st)
    return finish(out, a)


STALE_SENSITIVE = ("chk-legality-", "chk-game-changers-", "chk-budget-", "chk-combos-")


def degrade(out, no_data, card_st, cheap_st="fresh", combo_st="fresh"):
    """A check that would pass on data we don't have or that is stale is unverified, never pass. Fails stay fails.
    card_st / cheap_st / combo_st: freshness of the card lookup, the cheapest-printing search and the Spellbook call."""
    d = session().data_block()
    stale = lambda st: RANK[st] >= RANK["stale"]
    relied = {"chk-budget-": (card_st, cheap_st), "chk-combos-": (combo_st,)}  # the rest rely on the card lookup only
    for c in out["checks"]:
        if c["status"] != "pass":
            continue
        pre = next((p for p in STALE_SENSITIVE if c["id"].startswith(p)), None)
        if no_data and c["id"] != "chk-count-1":
            c["status"], c["detail"] = "unverified", "; ".join(x for x in [c["detail"], "no card data for: " + ", ".join(no_data)] if x)
        elif pre and any(map(stale, relied.get(pre, (card_st,)))):
            c["status"], c["detail"] = "unverified", "; ".join(x for x in [c["detail"], f"data stale (as of {d['as_of']}); rerun with network"] if x)


def finish(out, a):
    out["data"] = d = session().data_block()
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
        print(f"data: {d['verification']}" + (f" (as of {d['as_of']})" if d["as_of"] else "") + f", {d['requests']} requests"
              + (f"; unavailable: {'; '.join(d['endpoints_unavailable'])}" if d["endpoints_unavailable"] else ""))
    st = [c["status"] for c in out["checks"]]
    sys.exit(1 if "fail" in st else (2 if "unverified" in st or out["unavailable"] else 0))


if __name__ == "__main__":
    main()
