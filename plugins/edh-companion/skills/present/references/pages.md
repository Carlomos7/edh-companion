# Deck pages

You don't write the page. Two scripts turn project files into data, and a fixed template renders it, so every page is consistent and every number comes from a file or a script.

- `${CLAUDE_SKILL_DIR}/scripts/site_data.py`: reads one project (`from-workspace`) or a showcase of several (`from-showcase`) and writes `page-data.json` (or `summary.md`). Card facts, images, prices, Oracle-text roles, mana sources, cast-by-turn odds and the price ladder come from the audit skill's `deck_check.py` (Scryfall). The presentation views (findings, disagreements, sources, audit, recommendations, notices, hero, card types) come from `scripts/views.py`; colours from `scripts/palette.py`. Both are deterministic: no model call at build time, project files are only read.
- `${CLAUDE_SKILL_DIR}/scripts/build_site.py`: validates the data, packs card images into WebP atlases (plus one WebP art crop per commander for the hero), renders `assets/template.html` and checks the artifact limits.

Page design and the data-to-section mapping: [page-spec.md](page-spec.md). Read it only when changing the template.

## Steps
1. **Data**, one project or a showcase:
   ```bash
   uv run --script "${CLAUDE_SKILL_DIR}/scripts/site_data.py" from-workspace <project> [flags]
   uv run --script "${CLAUDE_SKILL_DIR}/scripts/site_data.py" from-showcase <showcase-dir> [flags]
   ```
   Flags: `--mode summary|interactive|showcase` (default showcase; showcase.yaml `mode:` applies when no flag is given), `--theme <file or JSON>`, `--title`, `--subtitle`, `--style basic`, `--images atlas|cdn|none`, `--viewer simple|3d`, `--show a,b` / `--hide a,b` (charts, swaps, sources, fan, prices, viewer), `--include-notes`, `--out`.
   - A project needs a brew file or research.json. With only research.json (+ PROJECT.md) the report has a research tab (commanders compared, findings, disagreements), rankings tabs and sources, and no deck tabs. A deck project with research gets the research tab too.
   - **Private notes stay out by default**: DECISIONS.md lines, PROJECT.md's own text (Goal, Theme section) and STATE.md never reach `page-data.json` or `summary.md`; the page shows a notice saying so. The theme rules from brew.json (mode, what counts as on theme, whether art matters, exceptions as card names) still show, because they explain the badges. `--include-notes` adds DECISIONS.md lines and PROJECT.md text for the player's own copy, only when they ask; never publish that build.
   - A showcase is `<workspace>/showcases/<name>/showcase.yaml` (format in the project files contract). Project paths are relative to `<workspace>/projects`, or absolute. Each project is validated with `companion.py validate` first; project files are only read. Output goes to `<showcase-dir>/report/`.
   - It writes `page-data.json` and `presentation-checks.md` (inputs with version, hash and audit state; sections shown or hidden and why; which theme and palette source won; the notices shown) into `reports/` (project) or `report/` (showcase).
2. **Build** (not in summary mode): `uv run --script "${CLAUDE_SKILL_DIR}/scripts/build_site.py" <dir>/page-data.json` (output next to it: `index.html` + `img/`). Fix every error. Warnings name builds whose audit state isn't `pass`, deck_check failures and art crops that couldn't be fetched; tell the player, don't hide them.
3. **Look at it**: serve the folder over http (`python -m http.server`) and check it in a real browser at 390 px and desktop width, light and dark: no console errors, no horizontal scroll, tabs, commander picker and build switch work, a card opens in the viewer, a rankings tab shows images, Sources links out. Run axe-core (wcag2a, wcag2aa, wcag22aa). Add the results to `presentation-checks.md` (replacing its "Not run yet" line), including what wasn't tested.
4. **Deliver**:
   - Artifact tool available: publish `index.html` with the `supporting_files` build_site printed as supporting files.
   - `--images cdn` pages load images from Scryfall: never publish them; give the player the path to `index.html`.
   - Summary mode: hand over `summary.md` (convert it to Word or PDF with other tools if asked).
   - Reply as present/SKILL.md says: what was built (mode, decks, sections), where it is (link or path), then every warning from the build, the notices on the page (research older than the deck, stale card data, notes left out) and what wasn't tested. Warnings are never left out.

## Modes
| Mode | What it is |
|---|---|
| `showcase` (default) | everything: images, charts, header card fan, prices, three.js 3D viewer |
| `interactive` | the same data, filters, comparisons, prices and charts; simple CSS viewer, no card fan, no three.js in the page, minimal animation |
| `summary` | `summary.md` only, complete and conclusion first: notices; per build the audit verdict and counts, plan, Rule 0, stats, card types, the audit checks (fails, warnings and unverified in full, passes by name, the shared method once), recommendations (in the deck / proposed / rejected) and the decklist; per research project the disagreements, every finding grouped with its citations and video moments, recommendations, gaps, next steps and card candidates; rankings; every source, numbered and grouped by kind. Nothing is cut to a "top N" |
| `--style basic` | overview, numbers, decklist, checks and sources; no images or charts |

## Navigation
Builds are grouped into tabs by `brew.json` `group` (a showcase entry's `group` overrides it; no group: one tab per commander). A tab with builds for several commanders gets a commander picker; each commander keeps the build switch for `brew.json` + `brew-<variant>.json`. In a showcase every build is labelled with its project and an Overview tab lists them all. research.json `commanders` appear as a compact comparison in the tab of that project's builds; each `rankings` group gets its own tab; each project with research content gets a `research_tab` entry (deck projects too).

## What each section needs
| Section | Needs |
|---|---|
| deck tabs, decklist, stats, roles, card types | a brew file (deck_check supplies the numbers) |
| research tab (findings, disagreements, candidates, next steps) | research.json with findings, disagreements, card candidates, recommendations or next steps |
| rankings tabs | research.json `rankings` |
| price ladder | deck_check `--cheapest` data (always requested; hidden with a note if missing) |
| mana sources chart, cast-by-turn chart | deck_check `stats.mana`, `stats.cast_by_turn` (hidden with a note if missing) |
| status pills, planned-for-release note | deck_check `status`/`releases` or rankings `status`; brew.json `future` |
| audit checks | a current paired audit file |
| hero artwork and artwork palette | deck_check's `art_crop` for the commander (downloaded once into the shared image cache) |

## Theme and palette (colors)
Every commander gets `look.palette`: full light and dark role sets (`bg, surface, surface2, border, text, muted, accent, accent2, on_accent, focus, art_wash`). Precedence, resolved in Python: an explicit theme (`--theme` > showcase.yaml `projects[].theme` > showcase.yaml `theme` > `<project>/report-theme.yaml`) > colours from the commander's artwork > color-identity hues (one or two in WUBRG order, a muted gold for 3+ colors) > neutral. Pages that show several commanders (overview, research, rankings, sources) use the page look: an explicit theme or neutral.
- Artwork: the art crop downsampled to 64 px, quantized to 16 colours, scored by chroma and the share of pixels near each hue (Material's method, OKLCH in place of HCT); the best colour is `accent`, the next with a clearly different hue is `accent2`. Art with no usable colour (near-black, near-white, grey), a failed download or no network falls back to identity; the build never fails on it.
- Roles keep the seed's hue and change only lightness. Text, muted, accent and accent2 are pushed until they have 4.5:1 on bg, surface and surface2 (so focus and other UI uses have 3:1+); `on_accent` is black or white, whichever reads on the accent. Explicit accents keep their hue and get the same contrast fix. Status colours (pass, warning, fail, info, unverified) are fixed in the template, never derived. `art_wash` is decoration behind the hero only.
- A saved theme: `{accent: "#c8102e", accent2: "#1f3a93", style: comic|gothic|flames|null, label: "..."}` in `<project>/report-theme.yaml` or showcase.yaml. The older `look.l/d.a/a2` accent pair and `look.source` stay for old templates (theme or identity, never artwork). Textures are faint and decorative; reduced motion (and interactive mode) stop the flames animation.

## What it refuses
- a project that fails `uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/companion.py" validate <project>`, or has neither a brew file nor research.json
- card data it can't get (Scryfall unreachable): nothing is filled in from memory
- a theme that isn't `#rrggbb` or has an unknown style
- in build_site: decks that aren't 100 cards, unknown theme labels, recommendations pointing at missing builds, audit states other than the derived ones, image keys that aren't in the images, base64 images, local paths in the page data, and pages over the size limits

The audit state is derived, never upgraded: no paired audit file is `not audited`; an audit whose `subject.deck` version or hash differs from the brew (or a list that no longer matches its hash) is `audit out of date`; otherwise it is the audit verdict. Only a current audit shows its checks. Players see labels (Pass, Pass with warnings, Fail, Incomplete, Not audited, Audit out of date), never the enum.

## Sizes (checked by build_site.py)
16 MB page · 15 MB per file · 511 files · 256 MB total. One atlas holds 100 cards at 488 px (roughly 4 to 8 MB). Over a limit: `--width 366`, or fewer builds per page.

## Don't
- Hand-edit `page-data.json` or the generated HTML. Fix the project file and re-run.
- Edit a player's research, decisions or decks to make a page look better; the views derive presentation from the files as they are.
- Edit `assets/template.html` for one page's needs. Template changes are for every page.
- Hotlink Scryfall images in a published page. Atlases (and the hero WebP) are the fix.
