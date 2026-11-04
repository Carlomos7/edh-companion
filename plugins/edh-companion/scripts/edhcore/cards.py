"""One normalized card record and the small card helpers every script needs (one copy of each)."""
import re, unicodedata


def oracle(card):
    return "\n".join([card.get("oracle_text", "")] + [f.get("oracle_text", "") for f in card.get("card_faces", [])])


def front_type(card):
    return (card.get("card_faces") or [card])[0].get("type_line", card.get("type_line", ""))


def is_land(card):
    return "Land" in card.get("type_line", "").split("//")[0]


def is_basic(card):
    return "Basic" in card.get("type_line", "")


def norm_name(name):
    """Comparable card name: case, diacritics, curly quotes, hyphens and punctuation ignored ("Lim-Dûl's Vault" ==
    "Lim-Dul's Vault", "Kozilek’s Return" == "Kozilek's Return", "Jace Vryn's Prodigy" == "Jace, Vryn's Prodigy")."""
    return re.sub(r"[^a-z0-9]+", "", unicodedata.normalize("NFKD", name.replace("Æ", "Ae").replace("æ", "ae")).encode("ascii", "ignore").decode().casefold())


def match_name(card, name):
    """True when name is this card's name or one of its faces (split / double-faced cards)."""
    n = norm_name(name)
    return any(norm_name(x) == n for x in [card["name"]] + [f.get("name", "") for f in card.get("card_faces", [])])


def price(card, finish):
    """Scryfall price for one finish of this printing, or None."""
    key = {"foil": "usd_foil", "etched": "usd_etched"}.get(finish, "usd")
    v = (card.get("prices") or {}).get(key)
    return float(v) if v else None


def prices_any(card):
    """Every USD price of this printing (any finish)."""
    return [float(v) for k, v in (card.get("prices") or {}).items() if k in ("usd", "usd_foil", "usd_etched") and v]


def images(card):
    return card.get("image_uris") or (card.get("card_faces") or [{}])[0].get("image_uris") or {}


def back_image(card):
    """Back face image of a double-faced card (separate images per face); None for single-image cards (split, adventure)."""
    faces = card.get("card_faces") or []
    if card.get("image_uris") or len(faces) < 2:
        return None
    return (faces[1].get("image_uris") or {}).get("normal")


def treatment(card):
    """Plain-language printing treatment: what makes this printing look different."""
    bits = [x for x in card.get("frame_effects") or [] if x in ("showcase", "extendedart", "etched", "inverted", "fullart")]
    bits += ["borderless"] if card.get("border_color") == "borderless" else []
    bits += ["full art"] if card.get("full_art") else []
    bits += ["Secret Lair"] if card.get("set") == "sld" else []
    bits += [p for p in card.get("promo_types") or [] if p in ("serialized", "galaxyfoil", "surgefoil", "textured", "halofoil")]
    return ", ".join(dict.fromkeys(bits)) or "regular"


def record(c, qty=1, commander=False, finish="nonfoil"):
    """The per-card record deck_check writes (and other scripts read)."""
    img = images(c)
    return {
        "name": c["name"], "qty": qty, "commander": commander, "oracle_id": c.get("oracle_id"), "printing_id": c["id"],
        "set": c["set"], "collector_number": c["collector_number"], "set_name": c.get("set_name"), "type_line": c.get("type_line"),
        "mana_cost": c.get("mana_cost") or (c.get("card_faces") or [{}])[0].get("mana_cost"), "cmc": c.get("cmc"),
        "color_identity": c.get("color_identity", []), "legal": (c.get("legalities") or {}).get("commander"), "game_changer": bool(c.get("game_changer")),
        "digital": c.get("digital", False), "border": c.get("border_color"), "oversized": c.get("oversized", False),
        "finish": finish or "nonfoil", "finishes_available": c.get("finishes", []), "price_usd": price(c, finish),
        "price_source": "Scryfall daily price", "illustration_id": c.get("illustration_id"), "treatment": treatment(c),
        "artist": c.get("artist"), "scryfall_uri": c.get("scryfall_uri"),
        "image": img.get("normal"), "art_crop": img.get("art_crop"), "back_image": back_image(c), "layout": c.get("layout"),
    }


def brief(c):
    """One compact line per card for terminal output (token-light): name, cost, type, identity, legality, GC, price."""
    legal = (c.get("legalities") or {}).get("commander", "?")
    p = c.get("prices", {}).get("usd") or "-"
    gc = " GC" if c.get("game_changer") else ""
    ci = "".join(c.get("color_identity", [])) or "C"
    return f"{c['name']} | {c.get('mana_cost') or (c.get('card_faces') or [{}])[0].get('mana_cost') or ''} | {c.get('type_line', '')} | {ci} | {legal}{gc} | ${p}"
