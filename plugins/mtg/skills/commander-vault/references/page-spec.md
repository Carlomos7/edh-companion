# Page spec (for template changes only)

The template answers three questions in reading order:
1. Which cards are good? (tier tabs)
2. Which deck, how strong? (deck tabs)
3. How do I make it mine? (swaps, price ladders, Moxfield export)

## Tabs
- **Tier lists**: one per `tiers[]` entry. EDHREC inclusion % in S to D tiers (S ≥ 60, A ≥ 40, B ≥ 25, C ≥ 10, D below 10; cutoffs printed on the page). `n` is shown per card, with a low-confidence note under 50 decks. Generic staples in their own section. Charted: price vs inclusion (log price).
- **Deck tabs**: one per `groups[]` entry, not one per commander (12 tabs overflow on a phone). Top to bottom:
  1. comparison strip (default bracket: price, average MV, Game Changers, on-curve %)
  2. commander picker
  3. bracket buttons (opens on the default)
  4. summary: pitch, how it wins, key cards, strengths, weaknesses, tips, theme line, YouTube picks, checks run
  5. stat tiles and template check (bullet bars with target bands)
  6. charts: curve, types, pips vs sources, cast-by-turn
  7. decklist (group, sort, filter, Copy for Moxfield)
  8. the tab's shared swap list, with the selected commander's rows highlighted
- **Sources & accuracy**: data dates, claim counts, still-unverified items, every source link.

## Detail on demand
Full notes behind a disclosure, price ladders in the viewer, big images in the viewer, tooltips on hover and focus.

## Visual system
- Tokens on `:root`, with dark values under `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`, and again under `:root[data-theme="dark"]`. A manual toggle is remembered.
- Colors:
  - categorical slots from the dataviz reference palette
  - theme labels get slots 1, 2 and 3 (more than 3 triggers a warning)
  - off-theme uses slot 4
  - tiers use one blue ramp, and the tier letter is always shown
- Type: Inter for text, JetBrains Mono for numbers.
- Pills always carry their text, so meaning never depends on color alone.

## Charts (Chart.js 4 from cdnjs)
- One question per chart and one axis.
- 4 px rounded bar ends, a 2 px surface gap between bars, 2 px lines, ticks at least 11 px.
- A tooltip on every chart; a legend only for 2+ series.
- Charts redraw on theme change.

## Card viewer (CSS 3D by default, three.js on request)
- Front and back faces with `backface-visibility`.
- Drag to tilt (clamped), click or F to flip, arrows or swipe to browse the whole list in display order.
- A pointer-tracking sheen. Esc closes and focus returns to the opener.
- `prefers-reduced-motion` turns off tilt, sheen and animation.
- Backs: a double-faced card shows its real back (`<id>_b`); every other card shows its Scryfall card back (`back_<card_back_id>`).
- Default is CSS 3D: no extra download, works everywhere. The player can choose the three.js viewer instead (`init --viewer 3d`): the page then loads three.js r128 from cdnjs (about 600 KB) only at that point, draws each card as two textured planes cut from the atlas with rounded corners, lights it from the pointer for the foil shine, and lets the player spin it freely. No WebGL or no script: it falls back to the CSS viewer with one console warning. Reduced motion: no easing.

## Images
- WebP atlases only. Never base64 in JSON or HTML (that fails the sharing review), and never hotlinked (the viewer blocks outside images).
- Cards are cut from sheets with CSS `background-position`.
- Atlas cell is 488 px wide, so rules text is readable in the viewer.

## Accessibility and phones
- Every card is a button: Tab and Enter work, arrow keys move between tabs, the dialog is modal.
- 390 px with no horizontal scroll, a 16 px gutter, and grids that stack.
- `content-visibility` on tier rows; fixed aspect boxes, so there's no layout shift.

## Tests
`tests/test_pages.py` builds a fixture site and drives it in headless Chrome at 1280 and 390 px. It checks:
- tabs, the tier list, the decklist and charts
- bracket switch, viewer flip and browsing, and focus restore
- no wrapped numbers, no horizontal scroll, no console errors
- agent text shown as text, never parsed as HTML

Set `CHARTJS=/path/chart.umd.js` when cdnjs is unreachable.
