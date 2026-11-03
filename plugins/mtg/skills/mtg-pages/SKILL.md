---
name: mtg-pages
description: Render MTG Commander results (one deck, an optimized deck, or a whole vault) as an interactive page from a fixed, tested template, then publish it as an artifact or hand over the HTML. Use when the user wants a page, site, artifact or shareable view of decks or tier lists.
when_to_use: After building or optimizing a deck when the user says yes to "want a page for this?", at the vault's artifact gate, or when asked to make a deck page, tier list page or shareable deck view.
---

# MTG pages

You don't write the page. You assemble validated data, and a fixed template renders it. That keeps every page consistent, cheap and tested, and every number traceable to `mtgdb.py`.

Scripts (run with `uv run`, which installs their dependencies):
- `${CLAUDE_SKILL_DIR}/scripts/site_data.py`: builds `site-data.json` from mtgdb output (`init`, `add-deck`, `add-tier`, `add-swaps`, `add-claims`, `summary`).
- `${CLAUDE_SKILL_DIR}/scripts/build_site.py`: validates the data, packs card images into WebP atlases, renders `assets/template.html`, checks the artifact limits.

Page design and its reasons: [references/page-spec.md](references/page-spec.md). Read it only when changing the template.

## Steps
1. **Init**: `uv run site_data.py init site-data.json --title "..." --bracket <default> [--themes themed-printings.json]`. Omit `--themes` for unthemed decks; the page then has no pills, theme counts or theme filters.
2. **Add content.** Each command runs mtgdb itself, so you never type card data:
   - Decks: `add-deck site-data.json --group "<tab title>" --slug <commander-slug> --deck b3.txt --bracket 3 --notes notes.json [--reasons off-theme.json] [--budget X] [--commanders 2]`. Write `notes.json` yourself (pitch, how it wins, key cards, strengths, weaknesses, tips, YouTube picks, checks run); format is in the script's help.
   - Tier lists (optional): `add-tier ... --cards edhrec.json [--staples staples.json]`, from EDHREC numbers you pulled, with `n` per card.
   - Swap lists (optional): `add-swaps ... --merged merged.json`.
   - Claims (optional): `add-claims ... --ledger claims.verified.jsonl`. This fills the sources and accuracy tab.
3. **Build**: `uv run build_site.py site-data.json --out site/`. Fix every error it prints. It refuses 101-card decks, missing images, unknown theme labels, swaps pointing at missing decks, and base64 images.
4. **Look at it**: open `site/index.html` in the browser (chrome-browser skill) at desktop and 390 px width. Click a card, flip it (F), switch brackets, check the console. Spot-check 5 random cards' prices and pills against `mtgdb.py printings`.
5. **Deliver**:
   - Artifact tool available: publish `site/index.html` with everything else in `site/` as supporting files (`img/atlas_*.webp`, and `site-data.json` if the build put data in a separate file). One sentence in reply.
   - No artifact tool: send `site/` as a zip. `index.html` opens locally when data is inline; the default inlines data under 3 MB.

## Sizes (checked by build_site.py)
16 MB page · 15 MB per file · 511 files · 256 MB total. One atlas holds 100 cards at 488 px (roughly 4 to 8 MB). If a build fails a limit: `--width 366` or split the vault into two pages.

## Don't
- Hand-edit numbers in `site-data.json`. Re-run the add command instead.
- Edit `assets/template.html` for one page's needs. Template changes are for every page; test them with `tests/test_pages.py`.
- Hotlink Scryfall images in the page. The artifact viewer blocks them, and atlases are the fix.
