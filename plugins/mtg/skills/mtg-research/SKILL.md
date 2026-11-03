---
name: mtg-research
description: Accurate Magic the Gathering research with cited, verified facts. Use for any MTG question about cards, rulings, prices, printings, bans, Game Changers, Commander staples, combos, cEDH results or what content creators recommend. Checks every card fact against a local Scryfall index and logs claims with sources.
when_to_use: Any question about MTG cards or Commander/EDH where being wrong matters, e.g. "is this card good in my deck", "what do people play with X", "is X banned", "cheapest printing of X", "is X a real cEDH commander".
---

# MTG research

Goal: every fact the user sees is either computed from the card index or traced to a dated source. When you cannot verify something, say so.

Script: `uv run ${CLAUDE_SKILL_DIR}/scripts/mtgdb.py <cmd>` (run with `--help`). Index lives at `~/.cache/mtg/cards.sqlite`.

## Tools in mtgdb.py
- Facts: `card`, `printings` (themed first, vendor prices and owned copies when synced), `normalize`, `gamechangers`.
- Search: `search "<any Scryfall query>"` (cached and rate limited across processes; use it instead of live MCP Scryfall calls). Tagger tags work here: `otag:` for function, `art:` for what the art shows.
- Decks: `validate`, `stats` (roles from Scryfall Tagger tags once `tags-sync` has run), `swaptest`, `combos` (Spellbook fallback).
- Optional data: `tags-sync` (role tags), `prices-sync` (MTGJSON multi-vendor prices; `--history` for 90 days), `price-history`, `collection import|show`.
- Accuracy: `audit-claims`, `selftest`, `contact-sheet` (grid of card images to check art by eye).
- Goldfish: `simulate deck.txt` (percent of games the commander is castable by each turn; matches exact hypergeometric math).

## Before answering
1. `mtgdb.py info`. No index, or `stale: true` (over 7 days) and the question involves prices, bans or Game Changers: run `mtgdb.py index`.
2. First use after building an index: `mtgdb.py selftest`. If it fails, tell the user the card data may be wrong and why.

## Which source answers what
Facts have one authority each. Read [references/sources.md](references/sources.md) for the tool map.

| Question | Authority | Never from |
|---|---|---|
| Card text, legality, color identity, printings, prices, Game Changer flag | `mtgdb.py` (Scryfall bulk) | memory, video, EDHREC |
| What a card does (role) | Scryfall Tagger tags (`tags-sync`), then the oracle text | regex hints, memory |
| Price trends, vendor spread | MTGJSON via `prices-sync` (TCGplayer, Card Kingdom, Cardmarket, Cardsphere) | one-day snapshot alone |
| What the user owns | `collection show` | assumptions |
| Rulings, interactions | Scryfall rulings, comprehensive rules (MCP `rules_*`) | memory |
| Bans, Game Changers changes, bracket rules | Wizards announcements (web), confirmed in index | creators |
| What people play (inclusion, lift, salt) | EDHREC | videos |
| Combos and their pieces | Commander Spellbook | memory, videos |
| What wins competitively | EDHTop16, TopDeck.gg, cEDH Decklist Database | EDHREC, casual creators |
| Why a card is good, plans, traps, lines | Creators (videos, articles), cross-checked | a single source |

## Research loop
- Plan the questions first. Effort scales with the ask: 1 fact = index lookup, no web; a card evaluation = 3 to 8 calls; a full commander profile = 10 to 20.
- Search broad, then narrow. After every result, ask: is this source authoritative, current, and does it answer the question? Then pick the next call.
- Run independent lookups in parallel.
- Videos: follow [references/youtube.md](references/youtube.md). Every card name from a transcript goes through `mtgdb.py normalize` before you use it.
- **Commander-text search**: read the commander's oracle text, name its mechanics (copy, attack trigger, tokens, a creature type, a cost it cares about), and run `mtgdb.py search` for cards that scale with exactly that (e.g. `o:"copy" o:creature id<=ub`). Cards that multiply the commander's own ability are usually the strongest picks and the easiest to miss.
- **Community pass**: after data and creators, read what players say (r/EDH, r/CompetitiveEDH, deck primers, Moxfield comments) for gaps the data hides, like "this deck needs instant-speed casting". Community posts are supporting evidence: they raise questions, data and rules settle them.
- **Rules check**: any combo or interaction not confirmed by Commander Spellbook needs a comprehensive-rules citation (MCP `rules_lookup` / `rules_interaction`) and a step-by-step walk through, listing every required piece. Don't credit one card with what needs three.
- Recency: for anything about power or legality, prefer sources after the most recent bans/Game Changers update. Older sources can support but not decide.

## Evidence rules
- Card facts: computed, never recalled. Say "per Scryfall data as of <bulk_updated>".
- Opinion claims (must-play, trap, best line): 2 independent sources (different creators, or creator + data). One source = say "one source suggests".
- Statistics: always give the sample size ("in 312 of 1,040 decks on EDHREC"). Under ~50 decks, label it low confidence.
- Popularity is not power. Don't present EDHREC inclusion as strength, or casual results as cEDH viability.
- Conflicts: data beats opinion for "what's played"; tournament data beats both for "what wins"; newest creator content beats older for "what's good now". Report the conflict when it matters.
- Anything you couldn't verify goes in a short "Unverified" note, not into the answer as fact.
- When two good sources measure different things (Tagger role count vs a creator's count), show both and say why they differ. Don't silently pick one.
- Never hand-type a computed field (color identity, price, legality, MV), even when a tool is rate limited. Wait, use the index, or mark it missing.

## Longer research: keep a claim ledger
For multi-step work (deck profiles, vault runs), log claims to `claims.jsonl` per [references/claims.md](references/claims.md), then run `mtgdb.py audit-claims claims.jsonl --since <last bans/GC update>` and fix every problem before presenting.

## Answer format
Lead with the answer. Cite inline (link + date, or timestamp for video). Close with confidence (high / medium / low) when the answer is a judgment call.
