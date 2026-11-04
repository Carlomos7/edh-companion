"""Card types: the one rule deck_check's stats, page groups, filters, charts and summaries all use."""
import collections


TYPE_ORDER = ("Land", "Creature", "Planeswalker", "Battle", "Artifact", "Enchantment", "Instant", "Sorcery")
GROUP_ORDER = ("Commander",) + TYPE_ORDER + ("Other",)
OTHER_TYPES = {"Kindred", "Tribal", "Conspiracy", "Plane", "Phenomenon", "Scheme", "Vanguard", "Dungeon", "Stickers", "Emblem"}
SUPERTYPES = {"Legendary", "Basic", "Snow", "World", "Ongoing", "Elite", "Host", "Token"}
OTHER_SUBTYPES = {"Attraction", "Contraption"}  # non-deck artifacts: grouped as Other
WHOLE_CARD = {"split", "adventure", "aftermath"}  # one card, several halves: every half counts


def _face(type_line):
    left, _, right = (type_line or "").replace(" - ", " — ").partition("—")
    words = left.split()
    return [w for w in words if w in TYPE_ORDER or w in OTHER_TYPES], [w for w in words if w in SUPERTYPES], right.split()


def card_types(card):
    """Type facts for a Scryfall card or a deck_check record: {type_group, types, supertypes, subtypes, face_types,
    mdfc_land}. Group precedence Commander > Land > Creature > Planeswalker > Battle > Artifact > Enchantment > Instant >
    Sorcery > Other (deck_check's `types` tally uses the same order; it leaves the commander out). Double-faced cards
    (transform, modal, flip, meld) count by their front face; split and adventure cards by every half. `types` keeps
    every type so a filter for Artifact also finds artifact creatures. A modal spell // land is grouped as its spell and
    flagged mdfc_land. Unknown or non-deck types (Conspiracy, Plane, Attraction, tokens...) group as Other."""
    faces = [f.get("type_line") or "" for f in card.get("card_faces") or []] or [x.strip() for x in (card.get("type_line") or "").split("//")]
    layout = card.get("layout")
    # deck_check records carry no layout: a real back image means double-faced; no back image with halves = split/adventure
    whole = layout in WHOLE_CARD if layout else ("back_image" in card and not card["back_image"] and len(faces) > 1)
    parsed = [_face(f) for f in faces]
    used = parsed if whole else parsed[:1]
    types = list(dict.fromkeys(t for p in used for t in p[0]))
    supers = list(dict.fromkeys(t for p in used for t in p[1]))
    subs = list(dict.fromkeys(t for p in used for t in p[2]))
    dfc = layout == "modal_dfc" if layout else bool(card.get("back_image"))
    mdfc = dfc and len(parsed) > 1 and "Land" in parsed[1][0] and "Land" not in parsed[0][0]
    if card.get("commander"):
        group = "Commander"
    elif "Token" in supers or set(subs) & OTHER_SUBTYPES:
        group = "Other"
    else:
        group = next((t for t in TYPE_ORDER if t in types), "Other")
    return {"type_group": group, "types": types, "supertypes": supers, "subtypes": subs,
            "face_types": [p[0] for p in parsed], "mdfc_land": mdfc}


def type_counts(cards):
    """{group: quantity} in GROUP_ORDER for cards that carry card_types() fields (or raw records), plus mdfc_lands."""
    n = collections.Counter()
    mdfc = 0
    for c in cards:
        t = c if "type_group" in c else card_types(c)
        n[t["type_group"]] += c.get("qty", 1)
        mdfc += c.get("qty", 1) if t["mdfc_land"] else 0
    return {g: n[g] for g in GROUP_ORDER if n[g]}, mdfc
