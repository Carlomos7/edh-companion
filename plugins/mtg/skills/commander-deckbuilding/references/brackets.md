# Commander Brackets

Official WotC system. Last verified against Wizards' Feb 9 2026 update (no bracket rule changes then; Farewell and Biorhythm added as Game Changers). **Before a build, check magic.wizards.com for a newer bracket or Game Changers announcement.** If there is one, follow it and tell the user this file is out of date.

| Bracket | Game Changers | 2-card infinite combos | Mass land denial | Extra turns | Expected game length |
|---|---|---|---|---|---|
| B1 Exhibition | 0 | none | none | none | 9+ turns |
| B2 Core | 0 | none | none | few, not chained or looped | 8+ turns |
| B3 Upgraded | up to 3 | none early in the game, and don't hold one for later | none | few, not chained | 6+ turns |
| B4 Optimized | any | ban list only | ban list only | ban list only | 4+ turns |
| B5 cEDH | any | ban list only | ban list only | ban list only | any turn |

- Tutors: no separate limit since Oct 2025. Efficient tutors are Game Changers.
- The Game Changers list comes from the index (`mtgdb.py gamechangers`), never memory.
- Brackets are also intent. A B3 deck that "technically" passes but wins on turn 4 is not B3. State the intended win turn.
- `mtgdb.py validate` checks: Game Changer count, extra-turn cards (count), mass land denial patterns (regex, confirm by reading). It cannot check combos or intent: Spellbook and judgment do that.

## B4 vs B5
B5 is about the competitive metagame, not just raw power. For a B5 list, state how realistic the commander is in cEDH:
- EDHTop16 meta share, top cuts and conversion rate (with dates and entry counts)
- cEDH Decklist Database listing, if any
- If the evidence is thin: "Not an established cEDH commander; this is the strongest version" is a correct answer.
