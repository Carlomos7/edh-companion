---
name: commander-deckbuilding
description: Build, review or upgrade a Commander/EDH deck that is legal, hits its target bracket and holds up to scrutiny. Use when the user wants a decklist built, a deck reviewed, cuts or upgrades suggested, a bracket checked, or a swap tested. Every list is machine-validated and combo-checked before it is shown.
when_to_use: Requests like build me a <commander> deck, what bracket is this, what should I cut, upgrade my precon, is this swap OK, or a pasted or linked decklist.
---

# Commander deckbuilding

Script: `uv run ${CLAUDE_SKILL_DIR}/../mtg-research/scripts/mtgdb.py` (shared with `mtg-research`; load that skill too for any research).
Rules: [references/brackets.md](references/brackets.md), [references/construction.md](references/construction.md), and [references/themes.md](references/themes.md) only when the user wants a theme.

## Intake (ask only what changes the build)
Commander(s), target bracket, budget, must-include / must-avoid. Default the rest and say what you assumed.
- **Theme: default none.** A themed commander is not a themed deck. Only if the user mentions a theme or flavor for the deck, ask the themes.md intake question, build the map with `theme-build`, and pass `--themes` to every validate. Otherwise never add theme checks, tags or "off-theme" language.
- If `mtgdb.py collection show` finds a collection, ask whether to prefer owned cards. When yes: favor owned cards when close in quality, and report "cost to buy" alongside total price.
- Role counts are accurate only after `mtgdb.py tags-sync` (one time, about 5 minutes). If `stats` says "regex guesses", offer to run it.

## Build
1. Research the commander with `mtg-research` (plan, staples, combos, traps). Log claims if it is a long build.
2. Draft by role: lands, ramp, draw, interaction, wipes, then the plan cards (construction.md).
3. Write the list to a `.txt` (Moxfield format, commander first, `1 Name (SET) cn` once printings are chosen).
4. **Validate loop** (repeat until clean):
   - `mtgdb.py validate deck.txt --bracket N [--budget X] [--commanders 2] [--themes map.json --reasons off-theme.json]`. Fix every error.
   - `spellbook_find_decklist_combos`. For B1 to B3, remove every 2-card infinite; for B3, also any early game-winning combo.
   - `spellbook_estimate_bracket`. If it disagrees with the target, fix or explain.
   - `mtgdb.py stats deck.txt`. Check curve, lands, color sources vs pips, role counts against construction.md.
   - `mtgdb.py simulate deck.txt`. Report the turn-by-turn cast percentage for the commander. If it's under about 50% by the turn after its MV, add ramp or lands. Compare before and after when upgrading ("Doom by turn 4: 47% to 61%").
5. Present: the list, the plan in 3 to 5 lines, an offer of a page (`mtg-pages`), bracket reasoning (Game Changers, combos, intended win turn), price with `prices_as_of`, and anything unverified.

## Close calls: let the user choose
When 2 to 4 cards are close for a slot (or the user wants to pick), write candidates JSON and run
`uv run ${CLAUDE_SKILL_DIR}/scripts/picker.py candidates.json --out picker.html` (format in the script's help). Each option carries the why, price, theme and evidence. The user opens it, picks, and pastes the picks back. Then swaptest them.

## Optimize an existing deck
Follow [references/optimize.md](references/optimize.md): profile first, then ask target bracket, theme (only if relevant), change size and money in one question card, then diagnose, propose tested swaps, verify, and hand back a diff.

## Review a deck
Import it (Moxfield/Archidekt via MCP, or pasted text), run validate + stats + Spellbook, then report: legality problems, bracket (with reasons), role gaps, mana problems, weakest cards (read each card before calling it weak), combos present or one card away.

## Upgrade / cuts
- Every suggested add names a specific cut. Test each pairing with `mtgdb.py swaptest deck.txt --bracket N --swap "-Out +In"`; drop pairings that fail.
- Never cut a combo piece, a commander-enabling card or the last source of a role without saying so.
- Rank adds by: fixes a gap, fits the plan, data support (EDHREC lift/inclusion with n), price.

## Don't miss the commander's own payoffs
Before finalizing, run the mtg-research commander-text search. Any card that copies, doubles or scales the commander's ability must be either in the deck or listed with a clear reason it's out. Never park such a card in "cards to consider" without saying why.

## Accuracy rules
- Never write a card into a list without it resolving in the index (`normalize` first if unsure).
- Combos not in Spellbook: rules citation and the full piece list (mtg-research rules check) before calling it a combo.
- Never state bracket, legality, price or Game Changer status from memory.
- Read the actual oracle text (`mtgdb.py card`) before claiming what a card does or which role it fills. Regex role hints are guesses.
- If a tool is down, say which check didn't run. Don't present an unchecked list as checked.
