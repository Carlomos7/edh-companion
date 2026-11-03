# Optimize an existing deck (user journey)

## 1. Get the deck
A deck link (read with an installed add-on that supports that site), a pasted export from any site, or a file. Save it as `before.txt` (Moxfield format, commander first). Never edit the user's original.

## 2. Profile it before asking anything
`mtg_deck_profile`, `mtg_deck_check` (at the bracket it seems to be), `mtg_simulate` and `mtg_price_plan` (all three totals). A Commander section in the list sets partners automatically. That gives: legality problems, Game Changers, bracket signal, combos, cost, owned share, mana and curve health, and whether the printings already lean on a theme.

Tell the user in 4 to 6 lines what you found **before** the questions, so the questions make sense. For example: "Legal except Mana Crypt (banned). Plays like B3 (2 Game Changers, no 2-card combos). Commander on curve 44% of games. 58% of cards are Lord of the Rings printings. Cheapest version $210, as listed $480."

## 3. Ask (one AskUserQuestion call, up to 4 questions; skip any the user already answered)
1. **Target bracket**: "Your deck plays like B3. Target?" Options: Stay B3 · Push to B4 · Tune down to B2 · Make it cEDH (B5).
2. **Theme** (only if the profile shows a theme lean, or the user mentioned one), per themes.md: Ignore theme · Themed printings only (power) · Theme first with upgrades (prefer) · Strict.
   - Follow-up only if they chose prefer or strict and the theme has factions or a franchise: "What counts as on theme?" Options: Any <franchise> · Only <side A> (e.g. the Fellowship) · Only <side B> (Sauron's forces) · <character> only.
3. **How much change**: Light tune (5 to 10 swaps) · Solid upgrade (15 to 25) · Rebuild around the commander.
4. **Money and price style**: No new spend (owned cards only, needs a collection) · Budget (cheapest copies, show cheaper alternatives) · Balanced, up to $X · Bling (fancy printings, ask the per-card ceiling).

Then, in plain text, one optional line: "Any cards that must stay (pet cards)?"

## 4. Diagnose
Against the target bracket and construction.md: role gaps (Tagger counts), mana problems (sources vs pips, simulate), weak cards (read each before calling it weak), missing commander payoffs (commander-text search), and bracket violations for the target (Game Changers, combos, MLD, extra turns).

## 5. Propose
- Every add has a specific cut and a reason, tested with `mtg_deck_swap` against the target bracket, theme map and budget.
- Respect the change budget and locked cards. Order by impact.
- Close calls go to the picker page (`scripts/picker.py`).
- Price style: in budget style, every add above their per-card comfort comes with `mtg_cheaper_alternatives` options; in bling style, printing upgrades within their per-card ceiling are their own optional list.
- Theme cost is shown when a theme is on: "Off-theme upgrade available: X (+power) instead of Y."

## 6. Apply and verify
Write `after.txt`, then run `mtg_deck_check` (CLI `validate --themes/--reasons` if themed), `mtg_simulate` and `mtg_price_plan` in the player's price style. Then `uv run "${CLAUDE_PLUGIN_ROOT}/scripts/mtgdb.py" diff before.txt after.txt`.

## 7. Hand back
- The diff: cuts, adds, printing swaps, cost of adds, cost to buy (minus owned).
- Before vs after: bracket, Game Changers, commander-on-curve %, role counts, price, theme line.
- The new list via `mtg_export` in the format they want (Moxfield keeps exact printings), plus buy links for the adds from `mtg_price_plan`.
- What wasn't checked, if anything.
- Offer one next step: another pass at a different bracket, or the export for Moxfield / Archidekt to share it.

## Edge cases
- **Illegal deck**: fix legality first (banned, identity, count) and list those fixes separately. They don't count toward the change budget.
- **Over target bracket**: removals to reach it come first, then upgrades.
- **Partners or background**: pass `--commanders 2`.
- **Proxies or "rule 0" cards**: ask once whether they play with rule 0. If not, flag them as illegal.
- **Owned-only budget but no collection**: ask for an export (`collection import`), or treat as "suggest, don't assume owned".
- **Deck already optimal for the target**: say so, with evidence, and offer side-grades instead of forcing changes.
