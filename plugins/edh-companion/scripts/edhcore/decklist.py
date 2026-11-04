"""Decklist parsing: Moxfield/Archidekt-style text and brew.json, normalised to {qty, name, set, cn, finish}."""
import hashlib, re

LINE = re.compile(r"^\s*(\d+)\s*x?\s+(.+?)(?:\s+\(([A-Za-z0-9]{2,6})\)\s*([^\s*\[]+)?)?((?:\s+\*[A-Z]+\*)*)(?:\s+\[([^\]]*)\])?\s*$")
FINISH = {"F": "foil", "E": "etched"}
SECTION = re.compile(r"^\s*(commanders?|deck|main(board)?|sideboard|maybeboard|companion|considering)\s*:?\s*$", re.I)


def parse_text(text):
    """Returns (cards, commanders). Sideboard, maybeboard, companion and considering sections are skipped."""
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
        m = LINE.match(s) or LINE.match("1 " + s)
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
