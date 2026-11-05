# Construction defaults

Starting points, not laws. Adjust for the commander and say why when you deviate.

## Role counts (100 cards)
| Role | Typical range | Notes |
|---|---|---|
| Lands | 35 to 38 | Fewer with lots of cheap ramp/low curve (avg MV under ~2.5); more for landfall or high curve. cEDH often 28 to 32 with fast mana. |
| Ramp | 8 to 12 | Prefer 2-MV and cheaper. |
| Card advantage | 8 to 12 | Repeatable engines count more than one-shots. |
| Targeted interaction | 8 to 12 | Instant speed preferred; cover artifacts/enchantments too. |
| Board wipes | 2 to 4 | Fewer if the deck is the board; 0 to 2 in go-wide decks. |
| Plan / synergy | the rest | Win conditions, payoffs, enablers. |

The Command Zone's template ("Commander Deckbuilding Template for the New Era", episode 658, Feb 2025) is the common reference. If you show "template check" numbers to a user, cite that episode and pull its current numbers from the episode, not from memory.

## Mana
- Check land sources vs pips. As a rule of thumb, a color you need early wants about 15+ sources in 99 cards for a single-pip early play, more for double pips (Frank Karsten's analysis is the reference for exact numbers).
- Count only untapped-enough lands for low brackets' tempo needs; avoid more than a few taplands at B3+.
- Commander tax: if the plan depends on the commander, include protection or recursion.

## Theme vs power
- When the player chose a theme, build the best deck inside it. Mention a big trade-off once at the skeleton; don't name stronger off-theme cards unless they ask (see themes.md, "The player's theme is the goal").
- Never claim a card is "on theme" without checking its printing (art and set); see themes.md.

## Cards that may underperform here (always read the card first; say what falls short: speed, consistency, interaction, resilience)
High MV with one job, no interaction with the plan, redundant beyond need in a role, slow taplands, cards the deck's own data (EDHREC lift with this commander) shows people cut.

## Building the list
- **Research → deck:** build from verified candidates, not from memory or raw research: `uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/candidates.py" <project> [--add-name "New Card" …]` writes `candidates.json` with a verdict per card. `eligible` cards are ready; `needs_review` ones (Game Changer vs the bracket, upcoming, art/printing choice, theme unclear, no evidence yet) are a judgment call you make or ask about; `ineligible` (not a real card, banned, outside the identity) stay out. Newly found cards are fine: add them with `--add-name`, they're never rejected for not being in the research.
- **Carry the evidence into the deck:** copy each card's evidence IDs from candidates.json into `deck[].evidence` and set `research_version`. This is how a card's citations reach the audit and the pages; a deck built from research without it loses its sources.
- **Card facts:** `card_lookup.py names …` gives the compact facts; never paste full card JSON. Commander check without a deck: `deck_check.py --commander "A" [--commander "B"]`.
- **Self-check** (catches count, identity, bans, Game Changers, commander + 2 combos, wrong or off-set printings):
  `uv run --script "${CLAUDE_PLUGIN_ROOT}/skills/audit/scripts/deck_check.py" <decklist> --bracket N [--theme-sets …] --project <project> --json <project>/deck_check.json`
  Fix every fail. This is not the audit. Role counts (ramp, draw, removal...) come from deck_check's Oracle-text rules, not your own labels; a card can fill several roles. Unreleased cards show as upcoming with their release date: keep them out of the playable list, or plan a `future` version in brew.json.
- **Splitting a card pool** (a Secret Lair, a box) between decks or players: `uv run --script "${CLAUDE_PLUGIN_ROOT}/skills/brew/scripts/allocate.py" pool.txt --target Me=decklists/main-v3.txt --target "Sam=Doctor Doom" [--want Sam:Card]`. It never assigns a copy twice and leaves ties to the players.
