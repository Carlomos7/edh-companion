# Page spec (for template changes only)

The template answers, in reading order: which deck and how strong, is it checked, and how do I make it mine (cards to consider, Moxfield export).

## Data to sections
| Page part | Comes from |
|---|---|
| title, subtitle | `--title`/`--subtitle`, else PROJECT.md's `#` title and Goal, archetype, build list |
| build switch (B3, B4, b4-budget...) | one button per `brew.json` / `brew-<variant>.json`, keyed by variant |
| audit pill and Checks table | derived from the paired `audit*.json`: `not audited`, `audit out of date` (version or hash differs), or the verdict status; a current audit also shows each check's requirement, kind (deterministic, sourced, judgment), status and detail |
| the plan, how it wins | `brew.json.strategy` game plan, win conditions, intended win turn |
| game plan lists | commander rationale, archetype, key synergies, bracket restrictions, theme exceptions and open questions, alternatives, proposed cuts, PROJECT.md's Theme section and DECISIONS.md lines (both as text); strengths and weaknesses from `research.json.commanders` |
| decklist, stat tiles, curve and type charts | `deck_check.py` cards and stats (Scryfall); roles from `brew.json.deck[].role` |
| template check | land count from card types, ramp/draw/removal/wipe counts from brew roles, against typical ranges |
| theme pills, filters and counts | `brew.json.deck[].theme` and `theme_policy` (On theme, Exception, Off-theme); no theme means no pills |
| cards to consider | `brew.json.recommendations` with an `add` card, every status except rejected, status shown per build |
| what the community says, Watch | `research.json` findings of class `community_opinion` (with confidence) and `video` sources |
| Sources & accuracy | `research.json` sources grouped by type, the claims each was used for, cited video timestamps as `?t=` links; audit state per build; finding counts by evidence class; other findings with class and confidence; unresolved findings and gaps as "still unverified"; data dates |

Hidden when there's no data for them (never estimated): tier lists, cast-by-turn simulation, price ladders and price styles, pips vs sources chart, the compare strip (only with 2+ commanders).

## Deck tab, top to bottom
1. commander picker (2+ commanders) and build switch
2. deck header: name, bracket, card count, audit pill, "researched from N sources", Copy for Moxfield
3. overview (plan, how it wins, Game Changers, theme counts, commander image) next to the numbers (stat tiles, price note, template check)
4. decklist (group, sort, chip filters, Cards/List toggle, pips, GC pills, theme tags, ⇄ swap marks, price = buy link, ↗ Scryfall)
5. cards to consider, game plan with checks, community takes, charts

## Visual system
- Tokens on `:root`, with dark values under `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`, and again under `:root[data-theme="dark"]`. A manual toggle is remembered.
- Theme labels get categorical slots 1 to 3 (more than 3 triggers a warning); off-theme uses slot 4. Pills always carry their text.
- Type: Anton for display, IBM Plex Sans for text, IBM Plex Mono for numbers and states.

## Charts (Chart.js 4 from cdnjs)
One question per chart, 4 px rounded bar ends, ticks at least 11 px, a tooltip on every chart, a legend only for 2+ series, redrawn on theme change.

## Card viewer
- `<dialog>`, front and back faces. A double-faced card shows its real back (`<id>_b`, fetched from Scryfall's API by printing id); every other card shows the standard card back.
- Hover leans the card, drag spins and snaps back, click or F flips, arrows or swipe browse in display order, Esc closes and focus returns.
- Fancy pages load three.js r128 from cdnjs for a lit 3D card; no WebGL falls back to CSS 3D. `prefers-reduced-motion` turns off tilt, sheen and easing.

## Images
WebP atlases only, cut with CSS `background-position`, 488 px cells. Never base64, never hotlinked in a published page.

## Accessibility and phones
Every card is a button, tabs take arrow keys, scrollable tables are focusable regions, 390 px has no horizontal scroll, fixed aspect boxes prevent layout shift. Target: axe-core wcag2a, wcag2aa and wcag22aa clean in light and dark.

## Tests
`tests/unit/test_present.py` builds the fixture project `tests/fixtures/krenko` (needs uv and network) and checks audit states, source links, hidden sections and that no invented numbers reach the page. The browser check is step 3 of [pages.md](pages.md).
