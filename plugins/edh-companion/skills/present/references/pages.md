# Deck pages

You don't write the page. Two scripts turn a project folder into data, and a fixed template renders it, so every page is consistent and every number comes from a file or a script.

- `${CLAUDE_SKILL_DIR}/scripts/site_data.py from-workspace`: reads the project and writes `reports/page-data.json`. Card facts, images, prices and deck stats come from the audit skill's `deck_check.py` (Scryfall).
- `${CLAUDE_SKILL_DIR}/scripts/build_site.py`: validates the data, packs card images into WebP atlases, renders `assets/template.html` and checks the artifact limits.

Page design and the data-to-section mapping: [page-spec.md](page-spec.md). Read it only when changing the template.

## Steps
1. **Data**:
   ```bash
   uv run --script "${CLAUDE_SKILL_DIR}/scripts/site_data.py" from-workspace <project> [--title T] [--subtitle S] [--style fancy|basic] [--images atlas|cdn|none] [--viewer simple|3d] [--show a,b] [--hide a,b]
   ```
   It reads PROJECT.md (title, Goal, and the Theme section shown as text), DECISIONS.md (shown as text), research.json, and every `brew.json` / `brew-<variant>.json` with its `audit.json` / `audit-<variant>.json`. Each brew file becomes a switch button in the deck tab. It writes `reports/page-data.json` and `reports/presentation-checks.md` (inputs with version, hash and audit state; sections shown or hidden and why).
2. **Build**: `uv run --script "${CLAUDE_SKILL_DIR}/scripts/build_site.py" <project>/reports/page-data.json` (output goes next to it: `reports/index.html` + `reports/img/`). Fix every error. Warnings name builds whose audit state isn't `pass` and deck_check failures; tell the player, don't hide them.
3. **Look at it**: serve `reports/` over http (`python -m http.server`) and check it in a real browser at 390 px and desktop width, light and dark: no console errors, no horizontal scroll, a card opens in the viewer, the build switch works, Sources opens and links out. Run axe-core (wcag2a, wcag2aa, wcag22aa). Add the results to `reports/presentation-checks.md` (replacing its "Not run yet" line), including what wasn't tested.
4. **Deliver**:
   - Artifact tool available: publish `reports/index.html` with the `supporting_files` build_site printed (`img/atlas_*.webp`, and `site-data.json` if the data went into its own file) as supporting files. One sentence in reply.
   - `--images cdn` pages load images from Scryfall: never publish them (artifact pages block outside images); give the player the path to `reports/index.html`.
   - Otherwise hand over `reports/` as a folder. `index.html` opens locally when the data is inline (under 3 MB).

## Page styles
| Choice | Flags | What it is |
|---|---|---|
| Fancy (default) | `--style fancy` | every section, charts, header card fan, prices, three.js 3D viewer; images packed into WebP atlases |
| Fancy, local only | `--images cdn` | the same with images from Scryfall's servers: no download, **can't be published** |
| Basic | `--style basic` | overview, numbers, decklist, checks and sources; no images or charts |
| Custom | a style plus `--show`/`--hide` (charts, swaps, sources, fan, prices, viewer), `--viewer`, `--images` | recorded as `page.style: custom` |

## What it refuses
- a project that fails `uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/companion.py" validate <project>`, or has no brew file (a research-only project gets a Markdown answer, not a page)
- card data it can't get (Scryfall unreachable): nothing is filled in from memory
- in build_site: decks that aren't 100 cards, unknown theme labels, recommendations pointing at missing builds, audit states other than the derived ones, base64 images, local paths in the page data, and pages over the size limits

The audit state is derived, never upgraded: no paired audit file is `not audited`; an audit whose `subject.deck` version or hash differs from the brew (or a list that no longer matches its hash) is `audit out of date`; otherwise it is the audit verdict (`pass`, `pass_with_warnings`, `fail`, `incomplete`). Only a current audit shows its checks.

## Sizes (checked by build_site.py)
16 MB page · 15 MB per file · 511 files · 256 MB total. One atlas holds 100 cards at 488 px (roughly 4 to 8 MB). Over a limit: `--width 366`, or fewer builds per page.

## Don't
- Hand-edit `page-data.json` or the generated HTML. Fix the project file and re-run.
- Edit `assets/template.html` for one page's needs. Template changes are for every page.
- Hotlink Scryfall images in a published page. Atlases are the fix.
