# Vault pages (G5)

Used only at the vault's G5 gate. Single decks are shared with `mtg_export` (Moxfield / Archidekt give players a shareable page).

You don't write the page. You assemble validated data, and a fixed template renders it. That keeps every page consistent, cheap and tested, and every number traceable to `mtgdb.py` (found automatically; set `MTGDB_SCRIPT` to override).

Scripts (run with `uv run`, which installs their dependencies):
- `${CLAUDE_SKILL_DIR}/scripts/site_data.py`: builds `site-data.json` from mtgdb output (`init`, `add-deck`, `add-tier`, `add-swaps`, `add-claims`, `summary`).
- `${CLAUDE_SKILL_DIR}/scripts/build_site.py`: validates the data, packs card images into WebP atlases, renders `assets/template.html`, checks the artifact limits.

Page design and its reasons: [page-spec.md](page-spec.md). Read it only when changing the template.

## Page styles
| Choice | Flags | What it is |
|---|---|---|
| Fancy (default) | `--style fancy` | every section: card rankings, decks with charts, cards to consider, sources, header card fan, prices, 3D card viewer; images downloaded into WebP atlases |
| Fancy, local only | `--style fancy --images cdn` | the same, but images load from Scryfall's servers: no download, opens from disk, **can't be published** (artifact pages block outside images) |
| Basic | `--style basic` | deck summary, numbers, decklist and sources; no images, no charts, no libraries; instant |
| Custom | a style plus `--show a,b` / `--hide a,b` / `--viewer simple|3d` / `--images atlas|cdn|none` | sections: tiers, charts, swaps, sources, fan, prices, viewer |

The page records the result as `page.style` ("custom" once anything is overridden).

## Steps
1. **Init**: `uv run site_data.py init site-data.json --title "..." --bracket <default> [--themes themed-printings.json] [--viewer 3d]`. Use `--viewer 3d` only when the player chose the 3D card viewer. Omit `--themes` for unthemed decks; the page then has no pills, theme counts or theme filters.
2. **Add content.** Each command runs mtgdb itself, so you never type card data:
   - Decks: `add-deck site-data.json --group "<tab title>" --slug <commander-slug> --deck b3.txt --bracket 3 --notes notes.json [--reasons off-theme.json] [--budget X] [--commanders 2]`. Write `notes.json` yourself (pitch, how it wins, key cards, strengths, weaknesses, tips, YouTube picks, checks run); format is in the script's help.
   - Tier lists (optional): `add-tier ... --cards edhrec.json [--staples staples.json]`, from EDHREC numbers you pulled, with `n` per card.
   - Swap lists (optional): `add-swaps ... --merged merged.json`.
   - Claims (optional): `add-claims ... --ledger claims.verified.jsonl`. This fills the sources and accuracy tab.
3. **Build**: `uv run build_site.py site-data.json --out site/`. Fix every error it prints. It refuses 101-card decks, missing images, unknown theme labels, swaps pointing at missing decks, and base64 images.
4. **Look at it**: open `site/index.html` in the browser (chrome-browser skill) at desktop and 390 px width. Click a card, flip it (F), switch brackets, check the console. Spot-check 5 random cards' prices and pills against `mtgdb.py printings`.
5. **Deliver**:
   - Artifact tool available (needs a claude.ai login on a paid plan; not available in `claude -p`): publish `site/index.html` with everything else in `site/` as supporting files (`img/atlas_*.webp`, and `site-data.json` if the build put data in a separate file). One sentence in reply.
   - Local-only pages (`--images cdn`): never publish; give the player the path to `site/index.html` to open in their browser.
   - Otherwise: hand over `site/` as a folder or zip. `index.html` opens locally when data is inline; the default inlines data under 3 MB.

## Sizes (checked by build_site.py)
16 MB page · 15 MB per file · 511 files · 256 MB total. One atlas holds 100 cards at 488 px (roughly 4 to 8 MB). If a build fails a limit: `--width 366` or split the vault into two pages.

## Don't
- Hand-edit numbers in `site-data.json`. Re-run the add command instead.
- Edit `assets/template.html` for one page's needs. Template changes are for every page; test them with `tests/test_pages.py`.
- Hotlink Scryfall images in the page. The artifact viewer blocks them, and atlases are the fix.
