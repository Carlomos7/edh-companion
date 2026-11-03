# Optimize an existing deck (user journey)

## 1. Get the deck
Moxfield / Archidekt link (MCP `moxfield_decklist`, or the page), a pasted list, or a file. Save it as `before.txt` (Moxfield format, commander first). Never edit the user's original.

## 2. Profile it before asking anything
`mtgdb.py profile before.txt` (+ `--commanders 2` for partners), plus `stats`, `simulate`, and Spellbook combos. That gives: legality problems, Game Changers, bracket signal, combos, cost, owned share, mana and curve health, and whether the printings already lean on a theme.

Tell the user in 4 to 6 lines what you found **before** the questions, so the questions make sense. For example: "Legal except Mana Crypt (banned). Plays like B3 (2 Game Changers, no 2-card combos). Commander on curve 44% of games. 58% of cards are Spider-Man printings."

## 3. Ask (one AskUserQuestion call, up to 4 questions; skip any the user already answered)
1. **Target bracket**: "Your deck plays like B3. Target?" Options: Stay B3 · Push to B4 · Tune down to B2 · Make it cEDH (B5).
2. **Theme** (only if the profile shows a theme lean, or the user mentioned one), per themes.md: Ignore theme · Themed printings only (power) · Theme first with upgrades (prefer) · Strict.
   - Follow-up only if they chose prefer or strict and the theme has factions or a franchise: "What counts as on theme?" Options: Any <franchise> · Only <side A> (e.g. heroes) · Only <side B> (villains) · <character> only.
3. **How much change**: Light tune (5 to 10 swaps) · Solid upgrade (15 to 25) · Rebuild around the commander.
4. **Money**: No new spend (owned cards only, needs a collection) · Up to $X · No limit.

Then, in plain text, one optional line: "Any cards that must stay (pet cards)?"

## 4. Diagnose
Against the target bracket and construction.md: role gaps (Tagger counts), mana problems (sources vs pips, simulate), weak cards (read each before calling it weak), missing commander payoffs (commander-text search), and bracket violations for the target (Game Changers, combos, MLD, extra turns).

## 5. Propose
- Every add has a specific cut and a reason, tested with `swaptest` against the target bracket, theme map and budget.
- Respect the change budget and locked cards. Order by impact.
- Close calls go to the picker page (`scripts/picker.py`).
- Theme cost is shown when a theme is on: "Off-theme upgrade available: X (+power) instead of Y."

## 6. Apply and verify
Write `after.txt`, then run the full validate loop (with `--themes`/`--reasons` if themed), `simulate`, and Spellbook. Then `mtgdb.py diff before.txt after.txt`.

## 7. Hand back
- The diff: cuts, adds, printing swaps, cost of adds, cost to buy (minus owned).
- Before vs after: bracket, Game Changers, commander-on-curve %, role counts, price, theme line.
- The new list as Moxfield import text (and the file).
- What wasn't checked, if anything.
- Offer one next step: a page for the deck (the `mtg-pages` skill renders before and after as B<target> next to the original), or another pass at a different bracket.

## Edge cases
- **Illegal deck**: fix legality first (banned, identity, count) and list those fixes separately. They don't count toward the change budget.
- **Over target bracket**: removals to reach it come first, then upgrades.
- **Partners or background**: pass `--commanders 2`.
- **Proxies or "rule 0" cards**: ask once whether they play with rule 0. If not, flag them as illegal.
- **Owned-only budget but no collection**: ask for an export (`collection import`), or treat as "suggest, don't assume owned".
- **Deck already optimal for the target**: say so, with evidence, and offer side-grades instead of forcing changes.
