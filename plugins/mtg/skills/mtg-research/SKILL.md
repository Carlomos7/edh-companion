---
name: mtg-research
description: Accurate Magic: The Gathering answers with checked facts and cited sources: what a card does, legality, bans, Game Changers, printings and prices, rulings and rules interactions, combos, what people play with a commander, what creators recommend, and whether a commander is real in cEDH. Use for questions like "is X banned", "how do trample and deathtouch work", "cheapest printing of X", "what do people run in Krenko", "is X good". Not for building, checking or changing a whole deck (commander-deckbuilding, which loads this skill when it needs research) or for a player's own collection (collection).
---

# MTG research

Goal: every fact the user sees is traced to a dated, checked source. When you cannot verify something, say so.

Tools: whatever MCP servers and web tools are installed (see [references/sources.md](references/sources.md)). Judge them by what they do, not by name.

## Which source answers what
Facts have one authority each. Read [references/sources.md](references/sources.md) for where to find them.

| Question | Authority | Never from |
|---|---|---|
| Card text, legality, color identity, printings, prices, Game Changer flag | Scryfall (live lookup or a Scryfall-backed add-on) | memory, video, EDHREC |
| What a card does (role) | The oracle text, then Scryfall Tagger tags | memory |
| Price trends, vendor spread | Vendor pages and price add-ons (TCGplayer, Card Kingdom, Cardmarket) | one-day snapshot alone |
| What the user owns | The player's own list | assumptions |
| Rulings, interactions | Scryfall rulings, the Comprehensive Rules (with effective date) | memory |
| Bans, Game Changers changes, bracket rules | Wizards announcements (web) | creators |
| What people play (inclusion, lift, salt) | EDHREC | videos |
| Combos and their pieces | Commander Spellbook | memory, videos |
| What wins competitively | EDHTop16, TopDeck.gg, cEDH Decklist Database | EDHREC, casual creators |
| Why a card is good, plans, traps, lines | Creators (videos, articles), cross-checked | a single source |

## Research loop
- Plan the questions first. Effort scales with the ask: 1 fact = one lookup; a card evaluation = 3 to 8 calls; a full commander profile = 10 to 20.
- Search broad, then narrow. After every result, ask: is this source authoritative, current, and does it answer the question? Then pick the next call.
- Run independent lookups in parallel.
- Videos: follow [references/youtube.md](references/youtube.md). Every card name from a transcript is checked against Scryfall before you use it.
- **Commander-text search**: read the commander's oracle text, name its mechanics (copy, attack trigger, tokens, a creature type, a cost it cares about), and search Scryfall (an add-on's search tool, or scryfall.com/search) for cards that scale with exactly that (e.g. `o:"copy" o:creature id<=ub`). Cards that multiply the commander's own ability are usually the strongest picks and the easiest to miss.
- **Community pass**: after data and creators, read what players say (r/EDH, r/CompetitiveEDH, deck primers, Moxfield comments) for gaps the data hides, like "this deck needs instant-speed casting". Community posts are supporting evidence: they raise questions, data and rules settle them.
- **Rules check**: any combo or interaction not confirmed by Commander Spellbook needs a Comprehensive Rules citation from the Comprehensive Rules and a step-by-step walk through, listing every required piece. Don't credit one card with what needs three.
- Recency: for anything about power or legality, prefer sources after the most recent bans/Game Changers update. Older sources can support but not decide.

## Evidence rules
- Card facts: looked up, never recalled. Say "per Scryfall as of <date>".
- Opinion claims (must-play, trap, best line): 2 independent sources (different creators, or creator + data). One source = say "one source suggests".
- Statistics: always give the sample size ("in 312 of 1,040 decks on EDHREC"). Under ~50 decks, label it low confidence.
- Popularity is not power. Don't present EDHREC inclusion as strength, or casual results as cEDH viability.
- Conflicts: data beats opinion for "what's played"; tournament data beats both for "what wins"; newest creator content beats older for "what's good now". Report the conflict when it matters.
- Anything you couldn't verify goes in a short "Unverified" note, not into the answer as fact.
- When two good sources measure different things (Tagger role count vs a creator's count), show both and say why they differ. Don't silently pick one.
- Never hand-type a computed field (color identity, price, legality, MV), even when a tool is rate limited. Wait, or mark it missing.

## Longer research: keep a claim ledger
For multi-step work (deck profiles, vault runs), log claims per [references/claims.md](references/claims.md) and fix every problem before presenting.

## Answer format
Lead with the answer. Cite inline (link + date, or timestamp for video). Close with confidence (high / medium / low) when the answer is a judgment call.

## Gotchas
- **Transcripts mangle card names** ("Rhystic Studdy"); every name is checked against Scryfall.
- **Popularity isn't power.** EDHREC inclusion says what people play, not what wins; cEDH questions need tournament data.
- **New cards lag a day** in Scryfall's files: say it's missing instead of guessing.
- **A card name can match a digital-only Alchemy card;** check you have the paper card, not the Alchemy one.
