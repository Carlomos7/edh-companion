# Optimize an existing deck (user journey)

## 1. Get the deck
A deck link (read with an installed add-on that supports that site), a pasted export from any site, or a file. Save it as `before.txt` (Moxfield format, commander first) and keep the working copy as `<commander-slug>.txt` with a `deck-brief.md`, like a new build, so `/mtg:commander-vault` can pick it up later. Never edit the user's original.

## 2. Profile it before asking anything
Check it at the bracket it seems to be. That gives: legality problems, Game Changers, bracket signal, combos, cost, owned share, mana and curve health, and whether the printings already lean on a theme.

Tell the user in 4 to 6 lines what you found **before** the questions, so the questions make sense. For example: "Legal except Mana Crypt (banned). Plays like B3 (2 Game Changers, no 2-card combos). Commander on curve 44% of games. 58% of cards are Lord of the Rings printings. Worth about $480." Mention cost once here; don't repeat it in every later message.

## 3. Ask (fast path first)
Offer the recommended setup in one question first: "Yeah, use your defaults (Recommended)" with the defaults in the description (keep its current bracket, light tune of 5 to 10 swaps, no new money concerns, keep its theme if it has one) · "Let me set it up". Taking the defaults goes straight to step 4.

The full question card (one AskUserQuestion call, up to 4 questions; skip any the user already answered):
1. **Target bracket**: "Your deck plays like B3. Target?" Options: Stay B3 (Recommended, unless they said otherwise) · Push to B4 · Tune down to B2 · Make it cEDH (B5).
2. **Theme** (only if the profile shows a theme lean, or the user mentioned one), per themes.md: Ignore theme · Themed printings only (power) · Theme first with upgrades (prefer) · Strict.
   - Follow-up only if they chose prefer or strict and the theme has factions or a franchise: "What counts as on theme?" Options: Any <franchise> · Only <side A> (e.g. the Fellowship) · Only <side B> (Sauron's forces) · <character> only.
3. **How much change**: Light tune, 5 to 10 swaps (Recommended for a first pass) · Solid upgrade (15 to 25) · Rebuild around the commander.
4. **Money** (the only money question): No limit (Recommended) · Keep it cheap (cheapest copies, cheaper swaps where it matters) · Up to $X of new cards · No new spend (cards I own; needs a collection) · "Wanna drip it out?" (fancy printings; then ask "how much are you down to spend on a single card?"). AskUserQuestion shows 4 options at most: offer "No new spend" only if they have a collection, otherwise leave it out.

Then, in plain text, one optional line: "Any cards that must stay (pet cards)?"

## 4. Diagnose
If EDHREC data is available, pull this commander's staples and synergy first (no question) and use them to spot what the deck is missing. Against the target bracket and construction.md: role gaps, mana problems (sources vs pips), weak cards (read each before calling it weak), missing commander payoffs (commander-text search), and bracket violations for the target (Game Changers, combos, MLD, extra turns).

## 5. Propose
- Every add has a specific cut and a reason, checked against the target bracket, theme map and budget.
- Respect the change budget and locked cards. Order by impact.
- Close calls go to the picker page (`scripts/picker.py`).
- Money: only with "keep it cheap" or a limit they'd exceed do adds come with cheaper options; with "drippy", printing upgrades within their per-card max are their own optional list; with "no limit", don't bring up price until the hand-back.
- Theme on: every upgrade stays inside their theme mode. Don't propose off-theme upgrades unless they ask for them.

## 6. Apply and verify
Write `after.txt`, then re-run the checks and the price in the player's price style, and compare with `before.txt`.

## 7. Hand back
- The diff: cuts, adds, printing swaps, cost of adds, cost to buy (minus owned).
- Before vs after: bracket, Game Changers, commander-on-curve %, role counts, price, theme line.
- The new list in the format they want (Moxfield keeps exact printings).
- What wasn't checked, if anything.
- If the new deck passes every check, offer the commander vault page exactly as in the main skill's hand-back.
- Recommend 2 or 3 next steps, recommended first: export for Moxfield / Archidekt (Recommended), another pass at a different bracket, or what they still need from their collection.

## Edge cases
- **Illegal deck**: fix legality first (banned, identity, count) and list those fixes separately. They don't count toward the change budget.
- **Over target bracket**: removals to reach it come first, then upgrades.
- **Proxies or "rule 0" cards**: ask once whether they play with rule 0. If not, flag them as illegal.
- **Owned-only budget but no collection**: offer to import their collection (the `collection` skill), or treat as "suggest, don't assume owned".
- **Deck already optimal for the target**: say so, with evidence, and offer side-grades instead of forcing changes.
