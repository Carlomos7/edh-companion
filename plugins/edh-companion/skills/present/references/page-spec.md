# Page spec (for template changes only)

The template answers, in reading order: which deck and how strong, is it checked, and how do I make it mine (cards to consider, Moxfield export). Conclusions come first and evidence stays one click away: every citation, quote and timestamp is kept, grouped, never cut.

## Data to sections
| Page part | Comes from |
|---|---|
| title, subtitle | `--title`/`--subtitle`, else PROJECT.md's `#` title, then archetype and build list (PROJECT.md's Goal only with `--include-notes`); a showcase: showcase.yaml's, never one project's archetype |
| tabs | Overview (showcase only), one tab per build group (`brew.json` `group`, overridden by showcase.yaml; none = per commander), Research (`research_tab`: any project with research content), one tab per research.json `rankings` group, Sources & accuracy |
| notices | `notices[]` (`level` info or warn): research written for an older deck version, stale or missing card data, private notes left out (with the number of quotes hidden). Shown near the top, never hidden |
| hero | `groups[].commanders[].hero`: name, one metadata line (bracket, color identity, archetype, version), the audit verdict with counts, 4 stats (value, average mana value, lands + MDFC lands, Game Changers with the bracket's limit), the card image key and the art crop (`img/art_*.webp` after build_site; Scryfall URL with `--images cdn`; null without images) |
| commander picker | a group with builds for 2+ commanders; each build labelled with its project in a showcase |
| build switch (B3, B4, b4-budget...) | one button per `brew.json` / `brew-<variant>.json`, keyed by variant |
| Rule 0 line, planned-for-release note | `decks[].rule0_items` `[{label, value}]`: Bracket, Game Changers (deck_check's list; a restriction about them folds in as "(max 3)", a bare "no Game Changers" with none in the list is dropped), one Restrictions row each, Win turn; `brew.json.future` |
| audit | `decks[].audit_view` (below); the older `validation` (state, checks with raw `detail`) stays for old templates |
| the plan, how it wins | `brew.json.strategy` game plan, win conditions, intended win turn |
| game plan lists | commander rationale, archetype, key synergies, bracket restrictions, known limitations, theme exceptions and open questions, alternatives, proposed cuts, the theme rules (mode, what counts as on theme, art required); PROJECT.md's Theme section and DECISIONS.md lines only with `--include-notes`; strengths and disadvantages from `research.json.commanders` |
| commanders compared | `research.json.commanders`: strategy, advantages, disadvantages, theme fit, `legal_check`, evidence links; in the deck tab of that project, or the research tab |
| rankings tab | `research.json.rankings[]`: `method` and `as_of` at the top, rank, `tier` only if given, card image, `inclusion_pct` with `decks` of `total_decks` labelled as popularity, `why`, evidence links, status pill |
| decklist, stat tiles, curve and type charts | `deck_check.py` cards and stats (Scryfall); grouping and type filters use each card's `type_group`/`types` and `stats.type_counts` (below) |
| roles, template check | deck_check `stats.roles` and per-card `roles` (fixed Oracle-text rules, several per card, the matching rule in the card's tooltip and viewer); `brew.json.deck[].role` only as "builder's label" where it differs |
| price ladder | deck_check `stats.price_ladder` (affordable, as listed, premium, dated) and per-card `cheapest` (cheapest and priciest printing, in the viewer) |
| mana sources vs color requirements, cast-by-turn | deck_check `stats.mana` and `stats.cast_by_turn` (with runs, seed and assumptions text) |
| status pills | deck_check per-card `status`/`releases`; rankings `status`/`releases` |
| colors | `look.palette` per commander and for the page (pages.md, "Theme and palette"); the older `look.l/d.a/a2` pair stays |
| theme pills, filters and counts | `brew.json.deck[].theme` and `theme_policy` (On theme, Exception, Off-theme); no theme means no pills. `decks[].theme_stats` `{on, exception, off, exempt, total}` by quantity, commander left out: `theme.on_theme_pct` = on / total, total = on + exception + off; exempt (n/a, unchecked) is outside the percentage |
| recommendations | `decks[].recs_view`: applied (in the list), proposed, rejected; the older group `swaps` ("cards to consider", every status except rejected) stays for old templates |
| research tab | `research_tab[]` plus `findings_view`, `disagreements_view` and `sources_view` filtered by `project` |
| Sources & accuracy | `sources_view` (numbered, grouped by kind, `cited_by`, `moments`); audit state per build; finding counts by evidence class; unresolved findings and gaps as "still unverified"; data dates. The older `sources[]` (with `used_for`, `links`) stays but isn't rendered |

Hidden when there's no data for them (never estimated): rankings and research tabs, cast-by-turn and mana charts and the price ladder (each with a short "not available" note), status pills, the compare strip (only with 2+ commanders), the hero art. The page computes no tier and no number: tiers come only from a research ranking's `tier`. Top-level `tiers` is a legacy field that site_data always leaves empty; build_site still accepts it for old page data.

## View model (page-data additions; all old fields stay)
Built by `scripts/views.py` from the project files, deterministically; every field is described in its module docstring.

## Deck tab, top to bottom
1. compare strip and commander picker (2+ commanders), build switch
2. deck header: name, project and version (showcase), bracket, card count, audit pill, Rule 0, planned-for-release note, Copy for Moxfield
3. overview (plan, how it wins, Game Changers, theme counts, commander image) next to the numbers (stat tiles, price note, template check)
4. decklist (group, sort, chip filters, Cards/List toggle, pips, GC pills, theme tags, ⇄ swap marks, price = buy link, ↗ Scryfall)
5. cards to consider, game plan with checks, community takes, charts (curve, types, mana sources, cast-by-turn)
6. commanders compared (research.json commanders of that project)

## Visual system
- Tokens on `:root`, with dark values under `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`, and again under `:root[data-theme="dark"]`. A manual toggle is remembered.
- Colours per commander come from `look.palette.l` / `.d` (contrast already checked in Python); neutral on tabs with several commanders. Status colours are fixed tokens, the same everywhere, always with an icon and text. `body[data-look]` adds a faint comic, gothic or flames header texture.
- Interactive mode adds `body.calm`: no animations or transitions.
- Theme labels get categorical slots 1 to 3 (more than 3 triggers a warning); off-theme uses slot 4. Pills always carry their text.
- Type: Anton for display, IBM Plex Sans for text, IBM Plex Mono for numbers and states.

## Charts (Chart.js 4 from cdnjs)
One question per chart, 4 px rounded bar ends, ticks at least 11 px, a tooltip on every chart, a legend only for 2+ series, redrawn on theme change.

## Card viewer
- `<dialog>`, front and back faces. A double-faced card shows its real back (`<id>_b`, deck_check's `back_image`); every other card shows the standard card back.
- Hover leans the card, drag spins and snaps back, click or F flips, arrows or swipe browse in display order, Esc closes and focus returns.
- Showcase pages load three.js r128 from cdnjs for a lit 3D card; no WebGL falls back to CSS 3D. `prefers-reduced-motion` turns off tilt, sheen and easing.

## Images
WebP atlases only, cut with CSS `background-position`, 488 px cells; the hero art crop is one WebP file per commander in `img/`. Never base64, never hotlinked in a published page.

## Template folder (swappable)
`assets/template/` holds `index.html` (markup), `page.css` (styles) and `page.js` (behaviour). `build_site.py` assembles them into one self-contained page through four placeholders in index.html: `__TITLE__`, `/*__CSS__*/`, `/*__JS__*/` and `/*__DATA__*/` (the page data, `window.SITE_DATA`, inserted last). Another look or layout is another folder with the same three files and placeholders, used with `build_site.py --template DIR`; it reads the same page data, so nothing upstream changes. build_site refuses a folder that's missing a file or a placeholder. Keep JS in page.js (never in Python strings: that's where line breaks broke pages before); `node --check page.js` and the browser test in test_present.py catch syntax and runtime errors.

## Project conventions on the page
- `brew.json role_targets` (lands and per-role `{min, max}`, `max` null = open-ended) replace the typical ranges in the role check ("Against your targets") and the lands tile ("your target 36–37"). Without them the page shows the typical ranges and says so.
- `theme_policy.tiers` plus `deck[].theme_tier` add a preference sub-label to on-theme cards (e.g. Spider-Verse, Other Marvel) and a count per tier in the theme line. On theme stays on theme: the percentage and filters don't change.

## Accessibility and phones
Every card is a button, tabs take arrow keys, scrollable tables are focusable regions, 390 px has no horizontal scroll, fixed aspect boxes prevent layout shift. Target: axe-core wcag2a, wcag2aa and wcag22aa clean in light and dark.

## Tests (maintainers only: `tests/` is in the repo, not the installed plugin)
Edit `assets/template/` (index.html, page.css, page.js) only for something every page needs, keep existing behaviour working, and re-run `tests/unit/test_present.py` plus the browser check on the fixture project.
`tests/unit/test_present.py` builds `tests/fixtures/krenko` and the showcase `tests/fixtures/showcase/showcases/test-showcase` (krenko and spider-gwen reused, a short padded talrand list, a research-only project) across the three modes (needs uv and network), plus offline tests for theme precedence and contrast. `tests/unit/test_views.py` covers the view model offline (legacy citation forms, timestamp links, headlines, grouping, audit splitting and labels, applied recommendations, notices, card types, palette contrast for many hues and odd artwork, privacy) and, with `EDHC_REAL_PROJECT=<project folder>`, a temporary copy of a real project (completeness, type counts, privacy). The browser check is step 3 of [pages.md](pages.md).
