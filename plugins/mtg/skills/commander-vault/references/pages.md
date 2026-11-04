# Vault pages (G5)

Used for every deck page: a single deck at the end of a build (commander-deckbuilding step 7) and the vault's G5 gate. Moxfield or Archidekt (via `mtg_export`) are the other way to share a deck.

You don't write the page. You assemble validated data, and a fixed template renders it. That keeps every page consistent, cheap and tested, and every number traceable to `mtgdb.py` (found automatically; set `MTGDB_SCRIPT` to override).

Scripts (run with `uv run`, which installs their dependencies):
- `${CLAUDE_SKILL_DIR}/scripts/site_data.py`: builds `site-data.json` from mtgdb output (`init`, `add-deck`, `add-tier`, `add-swaps`, `add-claims`, `summary`).
- `${CLAUDE_SKILL_DIR}/scripts/build_site.py`: validates the data, packs card images into WebP atlases, renders `assets/template.html`, checks the artifact limits.

Page design and its reasons: [page-spec.md](page-spec.md). Read it only when changing the template.

## Page styles
| Choice | Flags | What it is |
|---|---|---|
| Fancy (default) | `--style fancy` | every section: card rankings, decks with charts, cards to consider, community takes, sources, header card fan, prices, three.js 3D card viewer; images downloaded into WebP atlases |
| Fancy, local only | `--style fancy --images cdn` | the same, but images load from Scryfall's servers: no download, opens from disk, **can't be published** (artifact pages block outside images) |
| Basic | `--style basic` | deck summary, numbers, decklist and sources; no images, no charts, no libraries; instant |
| Custom | a style plus `--show a,b` / `--hide a,b` / `--viewer simple|3d` / `--images atlas|cdn|none` | sections: tiers, charts, swaps, sources, fan, prices, viewer |

The page records the result as `page.style` ("custom" once anything is overridden).

## Every page has (the build warns when one is missing)
- per deck: pitch, how it wins, key cards, strengths, weaknesses, how to play it; Rule 0 facts (bracket, Game Changers, combos) in `checks`
- per deck tab: "What the community says" (`community` in notes.json, from the research's `takes.json`: 8 to 15 linked takes, disagreements included) and a Watch list (`youtube`)
- per tab: cards to consider (`add-swaps`), each tested with `mtg_deck_swap` at every deck's bracket, each "why" with its evidence; the decklist marks replaceable cards with ⇄ and the viewer lists the options
- every card links to Scryfall, EDHREC, TCGplayer and Cardmarket (automatic; the price buys the exact printing)
- Sources & accuracy: every source from `research/claims.jsonl` (`add-claims`), grouped by kind, with what it was used for; "researched from N sources" in each deck header
`build_site.py` prints an `incomplete:` warning for each gap. Fix it, or write why it's missing into `plan.md` (for example "no videos exist for this commander yet").

## Steps
1. **Init**: `uv run site_data.py init site-data.json --title "..." --bracket <default> [--themes themed-printings.json] [--viewer 3d]`. Fancy uses the three.js 3D viewer by default; pass `--viewer simple` if the player chose the simple one. Omit `--themes` for unthemed decks; the page then has no pills, theme counts or theme filters.
2. **Add content.** Each command runs mtgdb itself, so you never type card data:
   - Decks: `add-deck site-data.json --group "<tab title>" --slug <commander-slug> --deck b3.txt --bracket 3 --notes notes.json [--reasons off-theme.json] [--budget X] [--commanders 2]`. `notes.json`: pitch, how it wins, key cards, strengths, weaknesses, tips, `community` (copy the research's `takes.json` entries: text, source, url, date), `youtube` (title, url, channel, date from the research's video sources), checks run; format is in the script's help.
   - Tier lists (optional): `add-tier ... --cards edhrec.json [--staples staples.json]`, from EDHREC numbers you pulled, with `n` per card.
   - Swap lists: `add-swaps ... --merged merged.json` (one per tab).
   - Claims: `add-claims ... --ledger claims.verified.jsonl` (or the research's `research/claims.jsonl` for a single deck). This fills the Sources tab, grouped by kind.
3. **Build**: `uv run build_site.py site-data.json --out site/`. Fix every error it prints. It refuses 101-card decks, missing images, unknown theme labels, swaps pointing at missing decks, and base64 images.
4. **Look at it**: serve `site/` over http (`python -m http.server`; from disk the 3D viewer falls back) and open it in the browser (chrome-browser skill) at desktop and 390 px width. Click a card, flip it (F), drag and release (it snaps back), check a ⇄ card shows its swap options and the card links, switch brackets, open Sources, check the console. Spot-check 5 random cards' prices and pills against `mtgdb.py printings`.
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
