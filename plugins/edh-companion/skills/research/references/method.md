# Research method

## Evidence rules
- **Opinion claims** (must-play, trap, best line) need two independent sources (different creators, or creator + data). One source: say "one source suggests" and set confidence low.
- **Statistics** always carry the sample ("in 312 of 1,040 decks on EDHREC"). Under ~50 decks: low confidence.
- **Popularity ≠ power.** EDHREC inclusion says what people play; tournament data says what wins; neither says what's fun at a bracket 3 table. Say which one you mean.
- **Conflicts:** data beats opinion for "what's played"; tournament data beats both for "what wins"; newer beats older for "what's good now". Record the conflict in `disagreements` when it matters to the player's choice.
- **Primary vs commentary:** a decklist, Scryfall record, Spellbook combo or tournament result is primary (`primary: true`); a video or thread about it is commentary.
- **Model assessment** is allowed and useful, labelled as such. Never dress it up as a community consensus.
- **Rules:** an interaction not confirmed by Commander Spellbook needs a Comprehensive Rules citation and a step-by-step walk listing every required piece. Don't credit one card with what needs three.

## Commander profile (standard depth)
1. Scryfall: the commander's exact text, identity, legality, printings (for themes: which printings carry the theme's art).
2. EDHREC: top/high-synergy cards with deck counts; themes people build.
3. 3 to 6 recent public decklists across brackets: cards in most lists, cards the player's theme can't use, unusual inclusions worth a look.
4. Creators: 2 to 3 deck techs from different channels in the last 12 months; extract plan, must-plays, traps, combos, with mm:ss.
5. Community: 3 to 5 threads/primers: what's missing, overrated, frustrating at tables, "too strong for bracket N?".
6. Commander-text search: name the commander's mechanics and search Scryfall for cards that scale exactly those (e.g. `o:"copy" o:"spell" id<=ubr`).
7. Combos: Spellbook for the commander plus the most-played cards.

## Theme research
- Eligibility is the player's definition (PROJECT.md, Theme section), not yours. When it's ambiguous ("does Venom count as Spider-Man?"), record it in `gaps`/open questions for brew to ask.
- Printings matter: a card can be on theme only in one printing (Secret Lair art, a Universes Beyond reprint). Use Scryfall `unique:prints` searches with `e:`, `art:` and `ft:` and record printing IDs.
- Search both ways: cards the franchise printed (set codes), and older cards with matching art or flavor. Name/flavor matches are leads; only the art (or the player's rule) decides.

## YouTube
- Search "<commander> deck tech", "<commander> upgrade", "<strategy> commander". Prefer the last 12 months and anything after the latest bans/Game Changers update.
- Prefer videos with a linked decklist; the list is primary, the transcript explains it.
- Flag sponsored and precon-promo videos: they can support, not decide.
- Transcripts garble names ("Rhystic Studdy"): resolve every name on Scryfall; drop or flag what doesn't resolve.
- Cite with the timestamp: `https://www.youtube.com/watch?v=ID&t=754s` and `timestamps: ["12:34"]`.

## Unusual strategies (from a video or thread)
1. Get the original source and its decklist.
2. Verify the cards and the interaction (Scryfall text, Spellbook, rules).
3. Look for independent evidence: other lists using it, threads discussing it, results.
4. Report what the strategy needs, how fragile it is, and whether anyone besides the original source vouches for it.

## research.md shape
1. Answer / recommendation-relevant summary (3 to 6 bullets with refs).
2. Commanders or options compared (one short block each, same layout).
3. Key cards and why (refs).
4. Disagreements.
5. Gaps and limitations.
Keep it short; the evidence lives in research.json.
