"""Reproducible deck analytics from Scryfall card data: functional roles, mana sources vs color requirements,
and a seeded cast-by-turn simulation. Pure functions (no network) so they can be tested offline.

Roles come from fixed text rules over Oracle text and type lines, not from labels anyone typed. A card can have
several roles. Every role says which rule matched, so a surprising count can be traced.
"""
import os, random, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
from edhcore.cards import front_type, oracle  # noqa: E402,F401  (shared helpers, one copy each)

COLORS = "WUBRG"

# (role, rule name, regex over lowercased Oracle text). Order doesn't matter: every match counts.
ROLE_RULES = [
    ("ramp", "adds mana", r"\{t\}(?:, [^:]*)?: add \{|add (?:one|two|three) mana|adds? \{[wubrgc]\}"),
    ("ramp", "puts lands onto the battlefield", r"search your library for (?:up to \w+ )?(?:a |an )?(?:basic )?(?:land|forest|plains|island|swamp|mountain)[^.]*onto the battlefield|put (?:a|up to \w+) land cards? from your hand onto the battlefield"),
    ("ramp", "makes Treasure", r"create[^.]*treasure token"),
    ("draw", "draws cards", r"\bdraws? (?:a|an|one|two|three|four|x|that many|cards?)\b"),
    ("draw", "plays cards from exile or the top", r"exile the top [^.]*(?:you may (?:play|cast)|until end of turn, you may)|you may (?:play|cast) [^.]*from the top of your library|look at the top \w+ cards[^.]*put (?:one|two|\w+) of them into your hand"),
    ("removal", "destroys or exiles a target", r"(?:destroy|exile) (?:another )?target (?:creature|artifact|enchantment|planeswalker|permanent|nonland permanent|battle|land)(?! you control)"),
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


def roles(card):
    """{role: [rule names]} for one card. Lands are 'land' only (a land that taps for mana isn't ramp)."""
    if "Land" in front_type(card):
        return {"land": ["is a land"]}
    faces = [f for f in card.get("card_faces") or [] if "Land" not in f.get("type_line", "")]  # a spell's land back face isn't ramp
    text = "\n".join(f.get("oracle_text", "") for f in faces) if card.get("card_faces") else oracle(card)
    text = re.sub(r"\(.*?\)", "", text.lower())  # reminder text doesn't count
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


LAND_TYPES = {"plains": "W", "island": "U", "swamp": "B", "mountain": "R", "forest": "G"}


def made_colors(c, any_colors=COLORS):
    """Colors a card makes (Scryfall produced_mana). A land that searches for lands makes the colors of the land types
    it names (Bloodstained Mire: B, R); one that finds any basic (Evolving Wilds, Fabled Passage) makes any of
    `any_colors`."""
    made = set(c.get("produced_mana") or []) & set(COLORS)
    if made or "Land" not in front_type(c):
        return made
    m = re.search(r"search your library for (.*?)(?:, put|\.)", oracle(c).lower())
    if not m:
        return made
    types = {LAND_TYPES[t] for t in re.findall("|".join(LAND_TYPES), m.group(1))}
    return types or (set(any_colors) if "land" in m.group(1) else made)


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
        made = made_colors(c, identity or COLORS)
        if "Land" in front_type(c) or ("ramp" in roles(c) and made):
            for col in COLORS:
                if col in made:
                    src[col] += qty
    show = [c for c in COLORS if (identity is not None and c in identity) or need[c]]  # the deck's colors only
    return {"pips": {k: need[k] for k in show}, "sources": {k: src[k] for k in show}}

def simulate(rows, commander_mv, on_play=True, runs=20000, seed=7, max_turn=8, cost=None):
    """Probability the commander is castable by each turn, with colors. `cost` is the commander's colored pips
    ({"W": 1, ...}); without it only the amount of mana counts.
    Model (Karsten's Commander assumptions, 2022): London mulligan with the first mulligan free; mulligan a free 7 with
    0-2 or 6-7 lands, a later 7 with 0-1 or 6-7, keep 6 with 2-4 lands after bottoming, 5 with 2-4; bottom toward 3
    lands. The starting player draws on turn 1 (multiplayer). One land a turn, preferring one that adds a color the
    commander still lacks; cheap mana producers (nonland, mana value <= 2) are cast when affordable and make their
    colors from the next turn. Tapped lands and other ramp are ignored. Seeded: the same deck gives the same numbers.
    Also reports, among games where the amount of mana was there on the commander's turn but the colors weren't, how
    often each color was the missing one (`color_short`) and the worst one (`bottleneck`)."""
    need = {c: n for c, n in (cost or {}).items() if n}
    ident = set(need)
    deck = []
    for qty, c in rows:
        made = made_colors(c, ident)  # a basic-land fetch counts as any color the commander needs
        land = "Land" in front_type(c)
        kind = "land" if land else ("rock" if c.get("produced_mana") and "ramp" in roles(c) and (c.get("cmc") or 0) <= 2 else "spell")
        deck += [(kind, int(c.get("cmc") or 0), frozenset(made))] * qty
    rng = random.Random(seed)
    hits, short, short_games, mull = [0] * (max_turn + 1), {c: 0 for c in COLORS}, 0, 0

    def castable(srcs):
        if len(srcs) < commander_mv:
            return False, set()
        pips = [c for c, n in need.items() for _ in range(n)]
        match = {}  # pip index -> source index, by augmenting paths (Kuhn)

        def take(p, seen):
            for s, cols in enumerate(srcs):
                if pips[p] in cols and s not in seen:
                    seen.add(s)
                    if s not in match.values() or take(next(k for k, v in match.items() if v == s), seen):
                        match[p] = s
                        return True
            return False
        for p in range(len(pips)):
            take(p, set())
        missing = {pips[p] for p in range(len(pips)) if p not in match}
        return not missing, missing

    def keep(hand, free):
        lands = sum(1 for x in hand if x[0] == "land")
        return lands not in ((0, 1, 2, 6, 7) if free else (0, 1, 6, 7))

    for _ in range(runs):
        n_mull = 0
        while True:
            lib = deck[:]
            rng.shuffle(lib)
            hand, lib = lib[:7], lib[7:]
            bottom = max(0, n_mull - 1)  # the first mulligan is free
            for _ in range(bottom):  # bottom toward three lands
                lands = [x for x in hand if x[0] == "land"]
                hand.remove(lands[-1] if len(lands) > 3 else next((x for x in hand if x[0] != "land"), hand[-1]))
            nl = sum(1 for x in hand if x[0] == "land")
            if (keep(hand, n_mull == 0) if not bottom else 2 <= nl <= 4) or len(hand) <= 4:
                break
            n_mull += 1
        mull += n_mull
        srcs, done = [], None
        for turn in range(1, max_turn + 1):
            if lib:  # multiplayer: the starting player draws on turn 1 too
                hand.append(lib.pop())
            lands_in_hand = [x for x in hand if x[0] == "land"]
            if lands_in_hand:
                have = set().union(*srcs) if srcs else set()
                pick = max(lands_in_hand, key=lambda x: len((x[2] & ident) - have))
                hand.remove(pick)
                srcs.append(pick[2])
            ok, missing = castable(srcs)
            if done is None and ok:
                done = turn
            if turn == commander_mv and not ok and len(srcs) >= commander_mv:
                short_games += 1
                for c in missing:
                    short[c] += 1
            spent = 0
            for card in sorted([x for x in hand if x[0] == "rock"], key=lambda x: x[1]):
                if spent + card[1] <= len(srcs):
                    spent += card[1]
                    hand.remove(card)
                    srcs.append(card[2] or frozenset())
        if done:
            for t in range(done, max_turn + 1):
                hits[t] += 1
    shares = {c: round(short[c] / short_games, 3) for c in COLORS if c in ident} if short_games else {}
    return {"by_turn": {t: round(hits[t] / runs, 3) for t in range(1, max_turn + 1)}, "runs": runs, "seed": seed, "on_play": on_play,
            "commander_mv": commander_mv, "commander_pips": need, "mulligans_per_game": round(mull / runs, 3),
            "color_short_games": round(short_games / runs, 3), "color_short": shares,
            "bottleneck": max(shares, key=shares.get) if shares and max(shares.values()) > 0 else None,
            "assumptions": "London mulligan, first one free (Karsten 2022 keep rules); the starting player draws on turn 1; "
                           "colors from Scryfall produced_mana, fetch lands as the land types they find (a basic-land fetch as any needed color); one land a turn, chosen for a missing color; "
                           "mana value 2 or less mana producers count from the turn after they're cast; tapped lands and other ramp ignored"}


# Karsten 2022, 99-card decks: colored sources to cast a spell on curve consistently (89 + MV %), by (generic, pips).
# https://www.tcgplayer.com/content/article/How-Many-Sources-Do-You-Need-to-Consistently-Cast-Your-Spells-A-2022-Update/dc23a7d2-0a16-4c0b-ad36-586fcca03ad8/
KARSTEN_99 = {(0, 1): 19, (1, 1): 19, (2, 1): 18, (3, 1): 16, (4, 1): 15, (5, 1): 14,
              (0, 2): 30, (1, 2): 28, (2, 2): 26, (3, 2): 23, (4, 2): 22, (5, 2): 20,
              (0, 3): 36, (1, 3): 33, (2, 3): 30, (3, 3): 28, (4, 3): 26,
              (0, 4): 39, (1, 4): 36}


def karsten_need(card):
    """{color: sources needed} for one card per Karsten's 99-card table; gold cards +1 per color (his rule)."""
    p = {c: n for c, n in pips(card).items() if n}
    out = {}
    for c, n in p.items():
        generic = max(0, int(card.get("cmc") or 0) - n)
        keys = [k for k in KARSTEN_99 if k[1] == min(n, 4)]
        k = (min(generic, max(g for g, _ in keys)), min(n, 4))  # past the table: its largest generic (an underestimate)
        out[c] = KARSTEN_99.get(k, KARSTEN_99[max(keys)]) + (1 if len(p) > 1 else 0)
    return out


def source_check(rows):
    """Each color's sources against the most demanding card's need (Karsten 99). Lands count 1, nonland mana producers
    3/4 (his rule for rocks), so the counts are 'effective sources'."""
    have, need = {c: 0.0 for c in COLORS}, {}
    for qty, c in rows:
        made = made_colors(c)
        if "Land" in front_type(c):
            for col in made:
                have[col] += qty
        else:
            if made and "ramp" in roles(c):
                for col in made:
                    have[col] += 0.75 * qty
            for col, n in karsten_need(c).items():
                if n > need.get(col, (0, ""))[0]:
                    need[col] = (n, c["name"])
    return {col: {"sources": round(have[col], 2), "needed": n, "for": name, "short": round(max(0, n - have[col]), 2)}
            for col, (n, name) in need.items()}


def land_count(rows):
    """Karsten's Commander land formula: 31.42 + 3.13 x average mana value of nonland cards - 0.28 x cheap
    (mana value <= 2) ramp and draw cards. https://www.peasant-magic.com/articles/magic-deckbuilding/how-many-lands-do-you-need-in-your-deck-an-updated-analysis"""
    spells = [(q, c) for q, c in rows if "Land" not in front_type(c)]
    n = sum(q for q, _ in spells)
    if not n:
        return None
    avg = sum(q * (c.get("cmc") or 0) for q, c in spells) / n
    cheap = sum(q for q, c in spells if (c.get("cmc") or 0) <= 2 and {"ramp", "draw"} & set(roles(c)))
    lands = sum(q for q, c in rows if "Land" in front_type(c))
    rec = 31.42 + 3.13 * avg - 0.28 * cheap
    return {"recommended": round(rec, 1), "lands": lands, "average_mv": round(avg, 2), "cheap_ramp_draw": cheap,
            "warning": (f"{lands} lands; the formula suggests about {rec:.0f}" if abs(lands - rec) >= 2 else None)}
