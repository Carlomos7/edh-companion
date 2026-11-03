---
name: mtg-research
description: Accurate Magic the Gathering research with cited, verified facts. Use for any MTG question about cards, rulings, prices, printings, bans, Game Changers, Commander staples, combos, cEDH results or what content creators recommend. Checks every card fact against a local Scryfall index and logs claims with sources.
when_to_use: A question about cards, rules or the format where being wrong matters, e.g. "what does X do", "is X banned", "cheapest printing of X", "how do trample and deathtouch work", "what do people play with X", "is X a real cEDH commander". Building, checking, upgrading or pricing a whole deck belongs to commander-deckbuilding, which loads this skill when it needs research.
---

# MTG research

Goal: every fact the user sees is either computed from the card index or traced to a dated source. When you cannot verify something, say so.

Tools: the plugin's `mtgdb` MCP server (full names `mcp__plugin_mtg_mtgdb__<tool>`) for every card fact (`mtg_card`, `mtg_resolve_names`, `mtg_rules`, `mtg_deck_check` and the rest; see [references/sources.md](references/sources.md)). Commands without an MCP tool run as `uv run "${CLAUDE_PLUGIN_ROOT}/scripts/mtgdb.py" <command>` (`--help` lists them): `search` (any Scryfall query, cached and rate limited; Tagger `otag:` and `art:` work), `printings`, `audit-claims`, `selftest`, `contact-sheet`, `collection import|show`, `price-history`. Data lives in `~/.cache/mtg/`.

## Before answering
1. `mtg_data_status`. If `refresh` lists a source the question depends on (prices, bans, Game Changers, rules), tell the user the data date and offer `mtg_data_sync`. No index at all: sync first.
2. After a fresh sync, run `selftest` once. If it fails, tell the user the card data may be wrong and why.

## Which source answers what
Facts have one authority each. Read [references/sources.md](references/sources.md) for the tool map.

| Question | Authority | Never from |
|---|---|---|
| Card text, legality, color identity, printings, prices, Game Changer flag | `mtg_card` (Scryfall bulk) | memory, video, EDHREC |
| What a card does (role) | Scryfall Tagger tags (in `mtg_card`), then the oracle text | regex hints, memory |
| Price trends, vendor spread | MTGJSON via `mtg_data_sync` (prices) (TCGplayer, Card Kingdom, Cardmarket, Cardsphere) | one-day snapshot alone |
| What the user owns | `collection show` | assumptions |
| Rulings, interactions | `mtg_card` rulings, `mtg_rules` (Comprehensive Rules with effective date) | memory |
| Bans, Game Changers changes, bracket rules | Wizards announcements (web), confirmed in index | creators |
| What people play (inclusion, lift, salt) | EDHREC | videos |
| Combos and their pieces | Commander Spellbook | memory, videos |
| What wins competitively | EDHTop16, TopDeck.gg, cEDH Decklist Database | EDHREC, casual creators |
| Why a card is good, plans, traps, lines | Creators (videos, articles), cross-checked | a single source |

## Research loop
- Plan the questions first. Effort scales with the ask: 1 fact = index lookup, no web; a card evaluation = 3 to 8 calls; a full commander profile = 10 to 20.
- Search broad, then narrow. After every result, ask: is this source authoritative, current, and does it answer the question? Then pick the next call.
- Run independent lookups in parallel.
- Videos: follow [references/youtube.md](references/youtube.md). Every card name from a transcript goes through `mtg_resolve_names` before you use it.
- **Commander-text search**: read the commander's oracle text, name its mechanics (copy, attack trigger, tokens, a creature type, a cost it cares about), and run the `search` command for cards that scale with exactly that (e.g. `o:"copy" o:creature id<=ub`). Cards that multiply the commander's own ability are usually the strongest picks and the easiest to miss.
- **Community pass**: after data and creators, read what players say (r/EDH, r/CompetitiveEDH, deck primers, Moxfield comments) for gaps the data hides, like "this deck needs instant-speed casting". Community posts are supporting evidence: they raise questions, data and rules settle them.
- **Rules check**: any combo or interaction not confirmed by Commander Spellbook needs a Comprehensive Rules citation (`mtg_rules`) and a step-by-step walk through, listing every required piece. Don't credit one card with what needs three.
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
For multi-step work (deck profiles, vault runs), log claims to `claims.jsonl` per [references/claims.md](references/claims.md), then run `audit-claims claims.jsonl --since <last bans/GC update>` and fix every problem before presenting.

## Answer format
Lead with the answer. Cite inline (link + date, or timestamp for video). Close with confidence (high / medium / low) when the answer is a judgment call.
