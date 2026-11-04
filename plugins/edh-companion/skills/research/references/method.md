# Research method

## Depth and when to stop
Three modes. The source ranges are starting guidelines, not quotas.

| Mode | Typical sources per subject | Use for |
|---|---|---|
| **Quick** | card data, EDHREC, 1 to 2 community threads, a video only if it's central (about 3 to 6 sources) | a first look, a narrow question |
| **Comprehensive** (default) | card data, EDHREC, 3 to 6 decklists, 2 to 3 creator deck techs, 3 to 5 community threads or articles | a commander, a theme, a build |
| **Deep** | comprehensive, plus tournament data where power matters, more decklists across brackets, smaller creators, older discussions for context | comparisons, unusual strategies, contested questions |

Plan the **important questions** first (what the deck does, what real lists play, what creators and players recommend and warn about, what's contested, what's missing for this player's goals). Then research until they're answered well enough, judged by:
- **Coverage:** each kind of evidence the question needs is present: authoritative card data, what's played (EDHREC with sample sizes, real decklists), why (creator deck techs, prioritized when transcripts are available), how it plays at tables (community threads).
- **Corroboration:** key claims have independent support (different creators, creator + data, data + lists).
- **Disagreements:** important conflicts are found and explained, not smoothed over.
- **Gaps:** what's still unknown is named.
- **Saturation:** the last few sources mostly repeated what was already found.

**Stop** when the important questions are adequately answered or further searching is clearly giving diminishing returns. **Keep going** when a key claim has only one source, a major source type is missing, a disagreement is unexplained, or the latest sources are still turning up new cards or angles. Don't stop early just to save time, and don't keep going just to hit a number. Stay within the approved tools, the player's depth and preferences, and say if the time or token cost is getting large.

Record in research.json `methodology`: sources actually reviewed (including ones not cited), coverage per type, why research stopped (`stopped_because`, e.g. "key questions answered; last 4 threads repeated earlier points"), and the limitations. Give an overall confidence in the reply.

## Writing findings
Each finding is one claim the player could act on or dispute, written so a page can show the conclusion first and the evidence on demand ([schemas/README.md](../../../schemas/README.md), "Findings and checks"):
- **One claim per finding.** A video that makes three points gives three findings; a finding never bundles a recommendation, a warning and a card list.
- **`headline`**: the conclusion as a sentence of about 90 characters or fewer ("Flash enablers are a trap for Azula: 4 creators skip them"), not a topic ("Flash").
- **`claim`**: the claim in 1 to 3 plain sentences, attributed ("EDHRECast cuts…"). Citation brackets and timestamps stay out of the text.
- **`locators`**: for each cited source, where this claim is supported: `[{"source": "src-106", "at": ["8:00-9:20"]}]`. Each finding carries its own moments, even when several findings cite the same video; `sources[].timestamps` lists every moment cited from that video.
- **`cards`**: every card the claim names, exact Scryfall names; a long list lives here, not in the claim.
- **`explanation`** for the reasoning or context; **`limitations`** for what weakens it (one source, old, sponsored, small sample).

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
- Cite with the timestamp: the source URL (`https://www.youtube.com/watch?v=ID`), its `timestamps`, and the finding's `locators` for the moments behind that claim.

## Unusual strategies (from a video or thread)
1. Get the original source and its decklist.
2. Verify the cards and the interaction (Scryfall text, Spellbook, rules).
3. Look for independent evidence: other lists using it, threads discussing it, results.
4. Report what the strategy needs, how fragile it is, and whether anyone besides the original source vouches for it.

## RESEARCH.md shape
One shape for every research file, answer first ([writing.md](../../../references/writing.md)):
1. **Header line:** date, depth, the deck version it was written for ("written for main v3"; or "no deck yet"), and the size of the evidence (sources, findings in research.json).
2. **Recommendation:** the answer, with any caveat that changes it, and the overall confidence.
3. **Key evidence:** the findings behind the recommendation, most decision-relevant first, each with its IDs and the readable source and moment.
4. **Options compared** (when there's a choice): the directions in the shared layout ([writing.md](../../../references/writing.md), "Recommending directions").
5. **Key cards and why** (when relevant), grouped by role.
6. **Disagreements:** both sides, cited.
7. **Gaps and limits:** what's unknown, what failed, why research stopped.
The full evidence lives in research.json; RESEARCH.md is the readable layer over it.

## When the deck changes after research
Research about an existing deck records the deck it describes in `scope.deck` (`{version, deck_hash}` from brew.json) and in RESEARCH.md's header line. When brew.json's version is newer, say which version the research describes ("Research was written for v3; the deck is now v5") and flag the claims about cards or plans that changed. When the changes affect the recommendation, offer a refresh as the next step (a new research.json version with an updated `scope.deck`).
