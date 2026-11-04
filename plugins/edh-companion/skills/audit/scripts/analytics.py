"""Reproducible deck analytics from Scryfall card data: functional roles, mana sources vs color requirements,
and a seeded cast-by-turn simulation. Pure functions (no network) so they can be tested offline.

Roles come from fixed text rules over Oracle text and type lines, not from labels anyone typed. A card can have
several roles. Every role says which rule matched, so a surprising count can be traced.
"""
import random, re

COLORS = "WUBRG"

# (role, rule name, regex over lowercased Oracle text). Order doesn't matter: every match counts.
ROLE_RULES = [
    ("ramp", "adds mana", r"\{t\}(?:, [^:]*)?: add \{|add (?:one|two|three) mana|adds? \{[wubrgc]\}"),
    ("ramp", "puts lands onto the battlefield", r"search your library for (?:up to \w+ )?(?:a |an )?(?:basic )?(?:land|forest|plains|island|swamp|mountain)[^.]*onto the battlefield|put (?:a|up to \w+) land cards? from your hand onto the battlefield"),
    ("ramp", "makes Treasure", r"create[^.]*treasure token"),
    ("draw", "draws cards", r"\bdraws? (?:a|an|one|two|three|four|x|that many|cards?)\b"),
    ("draw", "plays cards from exile or the top", r"exile the top [^.]*(?:you may (?:play|cast)|until end of turn, you may)|you may (?:play|cast) [^.]*from the top of your library|look at the top \w+ cards[^.]*put (?:one|two|\w+) of them into your hand"),
    ("removal", "destroys or exiles a target", r"(?:destroy|exile) (?:another )?target (?:creature|artifact|enchantment|planeswalker|permanent|nonland permanent|battle|land)"),
    ("removal", "damages a target", r"deals? (?:\d+|x|that much) damage to (?:any target|target creature|target planeswalker|target player or planeswalker|another target)"),
    ("removal", "shrinks a target", r"target creature gets -\d+/-\d+|target creature gets -x/-x"),
    ("removal", "bounces a target", r"return target (?:creature|nonland permanent|permanent|artifact|enchantment)[^.]* to its owner's hand"),
    ("removal", "fights", r"\bfights? (?:target|another target|up to one target)"),
    ("removal", "shuffles or tucks a target", r"target (?:creature|permanent|nonland permanent|artifact|enchantment)[^.]*(?:shuffles it into|on the (?:top|bottom) of (?:its|their) owner's library)|owner of target (?:creature|permanent|nonland permanent)[^.]*shuffles it into"),
    ("counter", "counters a spell", r"counter target (?:spell|creature spell|noncreature spell|activated|triggered|instant|sorcery)"),
    ("wipe", "hits every creature or permanent", r"(?:destroy|exile) all (?:creatures|nonland permanents|permanents|artifacts|enchantments|other creatures)|deals? \d+ damage to each creature|all creatures get -\d+/-\d+|return all (?:creatures|nonland permanents)"),
    ("tutor", "searches for a nonland card", r"search your library for (?:a|an|up to \w+) (?!basic|land)(?:[\w-]+ )?(?:card|cards|instant|sorcery|creature|artifact|enchantment|planeswalker)"),
    ("protection", "gives protection", r"(?:gains?|have|has) (?:hexproof|indestructible|shroud|protection from)|phase(?:s)? out|can't be the target"),
    ("recursion", "returns cards from the graveyard", r"return (?:target|up to \w+ target|a|an|all) [^.]*from (?:your|a) graveyard to (?:the battlefield|your hand)"),
]


def oracle(card):
    return "\n".join([card.get("oracle_text", "")] + [f.get("oracle_text", "") for f in card.get("card_faces", [])])


def front_type(card):
    return (card.get("card_faces") or [card])[0].get("type_line", card.get("type_line", ""))


def roles(card):
    """{role: [rule names]} for one card. Lands are 'land' only (a land that taps for mana isn't ramp)."""
    if "Land" in front_type(card):
        return {"land": ["is a land"]}
    text = re.sub(r"\(.*?\)", "", oracle(card).lower())  # reminder text doesn't count
    found = {}
    for role, rule, rx in ROLE_RULES:
        if re.search(rx, text):
            found.setdefault(role, []).append(rule)
    return found


def role_counts(rows):
    """rows: [(qty, card)] -> ({role: count}, {card name: {role: [rules]}}). A card counts once per role."""
    counts, per = {}, {}
    for qty, c in rows:
        r = roles(c)
        per[c["name"]] = r
        for role in r:
            counts[role] = counts.get(role, 0) + qty
    return counts, per


def pips(card):
    """Colored mana symbols in a card's mana cost (front face); hybrid counts for both colors."""
    cost = card.get("mana_cost") or (card.get("card_faces") or [{}])[0].get("mana_cost", "")
    out = {c: 0 for c in COLORS}
    for sym in re.findall(r"\{([^}]+)\}", cost or ""):
        for c in COLORS:
            if c in sym.split("/"):
                out[c] += 1
    return out


def mana(rows, identity=None):
    """Color requirements (pips across nonland cards) vs sources (lands and mana producers that make each color).
    Uses Scryfall's produced_mana field."""
    need = {c: 0 for c in COLORS}
    src = {c: 0 for c in COLORS}
    for qty, c in rows:
        if "Land" not in front_type(c):
            for col, n in pips(c).items():
                need[col] += n * qty
        made = set(c.get("produced_mana") or [])
        if "Land" in front_type(c) or ("ramp" in roles(c) and made):
            for col in COLORS:
                if col in made:
                    src[col] += qty
    show = [c for c in COLORS if (identity is not None and c in identity) or need[c]]  # the deck's colors only
    return {"pips": {k: need[k] for k in show}, "sources": {k: src[k] for k in show}}


def simulate(rows, commander_mv, on_play=True, runs=20000, seed=7, max_turn=8):
    """Probability the commander is castable by each turn, counting mana only (colors ignored).
    Model: 7-card hand, no mulligans, one land drop a turn if one is in hand, cheap mana producers (nonland,
    mana value <= 2, they make mana) are cast as soon as affordable and add 1 mana from the next turn.
    Seeded, so the same deck always gives the same numbers."""
    deck = []
    for qty, c in rows:
        kind = "land" if "Land" in front_type(c) else ("rock" if c.get("produced_mana") and "ramp" in roles(c) and (c.get("cmc") or 0) <= 2 else "spell")
        deck += [(kind, int(c.get("cmc") or 0))] * qty
    rng = random.Random(seed)
    hits = [0] * (max_turn + 1)
    for _ in range(runs):
        lib = deck[:]
        rng.shuffle(lib)
        hand, lib = lib[:7], lib[7:]
        lands = rocks = 0
        done = None
        for turn in range(1, max_turn + 1):
            if turn > 1 or not on_play:
                if lib:
                    hand.append(lib.pop())
            land = next((x for x in hand if x[0] == "land"), None)
            if land:
                hand.remove(land)
                lands += 1
            avail = lands + rocks
            if done is None and avail >= commander_mv:
                done = turn
            spent = 0
            for card in sorted([x for x in hand if x[0] == "rock"], key=lambda x: x[1]):
                if spent + card[1] <= avail:
                    spent += card[1]
                    hand.remove(card)
                    rocks += 1
        if done:
            for t in range(done, max_turn + 1):
                hits[t] += 1
    return {"by_turn": {t: round(hits[t] / runs, 3) for t in range(1, max_turn + 1)}, "runs": runs, "seed": seed, "on_play": on_play,
            "commander_mv": commander_mv,
            "assumptions": "7-card hand, no mulligans, colors ignored, one land a turn, mana value 2 or less mana producers count from the turn after they're cast; other ramp ignored"}
