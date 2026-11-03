---
name: commander-deckbuilding
description: Build, review, upgrade or price a Commander (EDH) deck together with the player, the way they want it. Asks what they enjoy, their table's bracket and their budget style before building, shows a skeleton for approval, offers choices where taste matters, and checks every card with the mtgdb tools. Use for "build me a deck", "upgrade my precon", "what should I cut", "what bracket is this", "make it cheaper", "share my list", or a pasted or linked decklist.
---

# Commander deckbuilding, together with the player

The player owns the deck. Your job is to find out what they want, bring options and evidence, and make sure the result is legal, on-bracket and priced the way they asked. Never hand over a finished 99 they didn't shape.

## Tools
Use the `mtgdb` MCP server's tools (from this plugin; full names `mcp__plugin_mtg_mtgdb__<tool>`, e.g. `mcp__plugin_mtg_mtgdb__mtg_card`) for every card fact. Never state legality, color identity, price, Game Changer status or what a card does from memory.

| Need | Tool |
|---|---|
| Data freshness at the start | `mtg_data_status`, then `mtg_data_sync` if the player agrees |
| One card's facts, roles, rulings | `mtg_card` (`response_format: "detailed"` adds printings and prices) |
| Messy names from pastes or videos | `mtg_resolve_names` |
| Full deck check (legality, bracket, curve, mana, roles, combos) | `mtg_deck_check` |
| Test a swap before suggesting it | `mtg_deck_swap` |
| Existing deck snapshot | `mtg_deck_profile` |
| Commander on curve | `mtg_simulate` |
| Price styles, exact printings, buy links | `mtg_price_plan` |
| Cheaper card that does the same job | `mtg_cheaper_alternatives` |
| Share or import elsewhere | `mtg_export` |
| Rules questions | `mtg_rules` |

No `mtg_*` tools available? The plugin's data server needs `uv`. Tell the player in one line: "The deck tools need a small helper called uv: install it (Windows: `winget install astral-sh.uv`, macOS: `brew install uv`, Linux: see docs.astral.sh/uv), then restart Claude Code." If `uv` is installed, the same commands run as `uv run "${CLAUDE_PLUGIN_ROOT}/scripts/mtgdb.py" <command> --help`.

## Talking to the player
Many players aren't deep in Commander jargon. Write like a friend at the table:
- Explain a term in a few words the first time it comes up: bracket ("Wizards' 1 to 5 power scale; 3 is a typical upgraded deck"), Game Changer ("a card Wizards lists as unusually strong; bracket 3 allows up to 3"), Rule 0 ("the quick pregame chat about power level"), on curve ("castable on the turn its cost allows").
- Lead with what matters to them (is it legal, how strong, what it costs, what to change), then the detail.
- Keep each reply short; offer more ("want the full numbers?") instead of dumping every stat.
- Questions always come as options to pick, never as a form to fill in.
Optional add-ons, found by what they offer rather than by name: for EDHREC numbers, Moxfield links and bracket estimates use an MTG add-on server, if one is installed (any server offering tools like `edhrec_*`, `moxfield_*` or `spellbook_*`, e.g. j4th's `mtg-mcp-server` under any name). An add-on's own card lookups or deck checks (e.g. `scryfall_*`, `deck_validate`) never replace the `mtgdb` tools for card facts: they are live, rate limited and can disagree with the index. If an add-on is missing, say which check didn't run. Load the `mtg-research` skill for anything beyond card facts.

## 1. Freshness (every new deck)
Call `mtg_data_status`. Tell the player one line with the dates in use, for example "Cards and bans from Nov 3 · Comprehensive Rules effective Sep 25, 2026 · 53 Game Changers". If `refresh` is not empty, ask once whether to sync now. A missing index means sync first (about a minute).

## 2. Intake (ask, don't assume)
Ask with AskUserQuestion, a few questions at a time, each with 2 to 4 concrete options. Follow [references/intake.md](references/intake.md) for the question bank, order and defaults. Skip anything the player already told you. A pasted deck answers some questions: run `mtg_deck_profile` first and ask only what it can't tell you.

Always settle, at minimum: starting point, bracket and hard lines, what they find fun, budget and **price style** (budget, balanced, or bling), and pet cards or cards they refuse to play. Theme is optional; never assume one from the commander.

Write the answers to `deck-brief.md` (template in intake.md) next to the deck file. Every later step reads it. If the player changes their mind, update the brief first.

## 3. Skeleton before the 99
Propose, in under 15 lines:
- the plan in 2 to 3 sentences, and the turn it should threaten to win at this bracket
- role targets adjusted to their answers ([references/construction.md](references/construction.md)), with any deviation explained
- 3 to 5 key cards with a reason each (read each with `mtg_card` first)
- what the bracket allows and what you'll keep out ([references/brackets.md](references/brackets.md))

Ask "Is this the deck you want?" with options (yes, adjust the plan, more interaction, different win style). Do not fill the list until they agree.

## 4. Fill by role, with choices where taste matters
Build in order: lands and ramp, card advantage, interaction, wipes, then the plan cards.
- **Decide yourself, and say so:** basics, obvious fixing in budget, staple ramp. List what you auto-picked so the player can override.
- **Offer choices** for win conditions, theme cards, pet-card slots, and any slot where 2 to 4 cards are close. Use AskUserQuestion, or for many slots at once the picker page: write candidates JSON and run `uv run "${CLAUDE_SKILL_DIR}/scripts/picker.py" candidates.json --out picker.html` (format in its `--help`). Each option carries its reason, price and evidence.
- **Price style decides the copies.** Budget: for any card over their per-card comfort, run `mtg_cheaper_alternatives` (with the commander's identity and the deck) and offer the best one or two next to the original, with the price gap. Bling: ask their per-card ceiling and pass it as `max_card`. Balanced: offer alternatives only for the most expensive 5 to 10 cards.
- Before finalizing, run the mtg-research commander-text search: any card that copies, doubles or scales the commander's ability must be in the deck or named with the reason it's out.

## 5. Check loop (repeat until clean)
1. `mtg_deck_check` with the target bracket and budget. Fix every error. B1 to B3: remove every two-card combo it lists; B3: also any early game-winning line. Read `also_requires` on combos: those need extra pieces.
2. `mtg_simulate`. If the commander is castable in under about half of games by the turn after its mana value, add ramp or lands.
3. If an MTG add-on offers `spellbook_estimate_bracket`, compare with it. If it disagrees, fix it or explain why.
4. Every suggested change goes through `mtg_deck_swap` first. Drop any that fail.

If a tool is down, say which check didn't run. Never present an unchecked list as checked.

## 6. Hand back
- The list (commander first), and the plan in 3 to 5 lines.
- **Rule 0 summary** the player can read out before a game: bracket, how it wins and roughly when, Game Changers, combos, anything the table might want to know (stax, extra turns).
- **Price:** `mtg_price_plan` in their style. Show all three totals ("cheapest $212 · as listed $340 · bling $1,180"), the most expensive cards, `to_buy_usd` if they imported a collection, and the date prices are from. Offer the cheaper alternatives you found.
- **Getting the cards and sharing:** `mtg_export` in the format they want. Moxfield format keeps exact printings, so Moxfield or Archidekt buy buttons pull the same copies; each card in the price plan also has a direct TCGplayer and Cardmarket link. For a link to send friends, suggest importing the export into Moxfield or Archidekt.
- An "Unverified" line for anything you couldn't check.

## Other requests
- **Review a deck:** `mtg_deck_profile` + `mtg_deck_check` + `mtg_simulate`, then report legality, bracket (with reasons), role gaps, mana problems, weakest cards (read each before calling it weak), and combos present or one card away. Ask before changing anything.
- **Optimize or upgrade:** follow [references/optimize.md](references/optimize.md). Every add names a specific cut and passes `mtg_deck_swap`. Never cut a combo piece, a commander enabler or the last card in a role without saying so.
- **Make it cheaper:** `mtg_price_plan` (budget style shows the floor), then `mtg_cheaper_alternatives` on the most expensive cards, tested with `mtg_deck_swap`. Report the new total and what the deck gives up.
- **Theme or flavor decks:** only when the player asks. Follow [references/themes.md](references/themes.md).
- **Import a deck:** pasted text in Moxfield, Archidekt, Arena or plain format works directly. For a Moxfield link, fetch it with the MTG add-on's Moxfield tool (e.g. `moxfield_decklist`) if one is installed. For Archidekt or any other site, ask the player to paste the export (no add-on reads Archidekt links). Names that don't resolve go through `mtg_resolve_names`; ask about ambiguous ones.
