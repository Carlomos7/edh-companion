# Changelog

Players get a new version with `/plugin marketplace update carlomos7-mtg-skills` and a restart.

## 5.5.0
- **Research pass built into the MCP server:** `mtg_research_plan` (every source type, its minimum, the tool and ready-made queries), `mtg_edhrec` (EDHREC numbers built in, no add-on needed; with a deck, what it lacks), `mtg_decklists` (recent public Archidekt lists by bracket; cards most lists play that you don't, and your cards nobody plays), and `mtg_research_log` / `mtg_research_report` (a cited source ledger with coverage and shortfalls).
- **Every new deck runs it**, usually as the background research agent while you answer the intake: EDHREC, 6+ real decklists, combos, 3+ creator videos, 4+ Reddit threads, 3+ articles, live prices, the Wizards bracket page, and cEDH results at bracket 4 and 5.
- **Combo fix:** a combo that needs only the commander plus two cards now counts as a two-card combo for brackets 1 to 3 (before, Azula + Frantic Search + Narset's Reversal slipped through), and `mtg_deck_swap` blocks swaps that complete one.
- **Deck pages:** "researched from N sources" in the deck header, and a Sources tab grouped by type (decklists, videos, community, articles...) with what each source was used for.

## 5.4.0
- **Community research on every build:** before the plan, the build checks Reddit (r/EDH, r/EDHBrews, r/CompetitiveEDH), articles and primers, and 2 or 3 recent creator videos, then keeps 6 to 10 takes with their sources. Combos the community mentions are checked against your bracket.
- **"What the community says" on the page:** each take links to its thread, article or video, with a Watch list and every source in Sources & accuracy.
- **YouTube fallback:** when the transcript tool is blocked, the video page is fetched with a web fetch tool instead, which usually returns the transcript.
- **Responsive pass:** phone and tablet layouts tidied (stacked overview, two-up filters, readable rows, viewer controls no longer overlap the card name), checked at 390, 768, 1024 and 1440 px.

## 5.3.0
- **Links on every card:** the card viewer has Scryfall, EDHREC, TCGplayer and Cardmarket buttons; in the decklist the price opens the exact printing on TCGplayer and ↗ opens it on Scryfall. Basic pages (no viewer) link card names to Scryfall.
- **Page layout reordered:** deck header with Copy for Moxfield up top, then the plan next to the numbers, the decklist, cards to consider, the game plan, and the charts last in a 2 by 2 grid. The bracket switch only shows when there's more than one bracket.
- **Card viewer:** the card leans toward the mouse on hover, shows a grab cursor, and snaps back to the nearest face when you let go of a drag.

## 5.2.0
- **New page design for Fancy (and Basic):** bold display type, a 3D card fan in the header (filled from the deck's key cards on one-deck pages), big-number stat tiles, a 3-column decklist with mana symbols, rarity dots and Game Changer marks, card previews on hover and a darker card viewer.
- **Swap options:** after a build you're asked if you want them (best few, or cheaper ones). Each swap is tested at the deck's bracket and shows in Cards to consider, as a ⇄ mark in the decklist, and under the card in the viewer.
- Readable price dates, one three.js load per page. Card data now includes rarity: run `/mtg:update-data` (or it refreshes on your next build) to get rarity dots.

## 5.1.0
- **Skills reviewed against Anthropic's skill-authoring guidance** (docs/research/skill-authoring.md): descriptions say where each skill stops, trigger text moved out of Claude Code-only fields, gotchas sections from real failures, rules explain their reasons, no shell blocks that can abort a skill, and routing evals with near-misses.
- **Add-ons are used by default when installed:** EDHREC staples and synergy shape the plan, the picks, reviews and upgrades (quoted with deck counts); bracket estimates and deck links too. Without them the build still works and says once what wasn't available.
- **Quick by default, customizable whenever you want:** data refreshes without asking, the default path keeps picks to the 2 or 3 that matter, and the page choice (including images) is one question.
- **Page styles:** Fancy (images, charts, rankings, cards to consider, 3D viewer) or Basic (deck and numbers, no images), or customize sections; Fancy pages can download images (shareable) or use Scryfall's image links (local, no download). Basic loads no libraries.
- **Themes are respected:** the trade-off is mentioned once at most; no re-arguing, no off-theme suggestions unless asked; a thin strict pool becomes choices, not pushback.
- **3D card viewer option:** vault pages can use a three.js viewer (spin cards freely, pointer-lit foil shine) instead of the default simple one; it loads only when chosen and falls back on devices without 3D.
- **Fast path:** one click to use the recommended setup and skip the questions; the upgrade flow has it too.
- **Collection:** import from Moxfield, Archidekt or ManaBox, add and remove cards, undo, value, search, what a deck still needs, what fits a commander, export (`/mtg:collection`).
- **Money is asked once:** no limit (default), keep it cheap, a set budget, or drippy (fancy printings up to a per-card max). "Bling" is now "drippy".
- **Recommended next steps** at every stage, with the recommended option marked.
- **Decks are saved as you build** (`deck-brief.md` and `<commander>.txt`), and `/mtg:commander-vault` with nothing after it builds a vault from that deck.
- **Page offer:** once a deck passes every check, Claude offers to show it as a commander vault page.
- Optional add-ons are found by what they do; deck links work with any add-on that reads that site.
- Fixes from two independent reviews (foil marks on export, Arena and Archidekt pastes, Windows certificate and file-lock issues, and more).

## 5.0.0
- First public version: MCP server with card data, deck checks, prices, combos and rules; collaborative deckbuilding skills; short `/mtg:*` commands; multi-commander vaults.
