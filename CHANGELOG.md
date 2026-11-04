# Changelog

Players get a new version with `/plugin marketplace update edh-companion` and a restart.

## 7.1.0
Themes that might not work, money and looks, exports.
- **Theme feasibility:** research checks whether a franchise really has Magic cards (no assuming either way), finds eligible commanders, counts the pool per color identity and role, and records a verdict (feasible, constrained, infeasible, unknown) with confirmed counts vs estimates. brew explains the compromises with numbers and offers real paths (a thematic commander, a broader visual/story or mechanical theme, approved exceptions, or casual custom/proxy cards clearly marked as not legal), recommends one, and never presents a deck as meeting rules it breaks. Themes now record their basis (official, visual/story, mechanical, inspired) and hard rules vs flexible preferences.
- **Rule changes:** loosening or tightening a theme updates PROJECT.md and DECISIONS.md, re-checks affected cards, and makes earlier audits stale (`companion.py goals-hash`; audits record it).
- **Two budgets:** gameplay (cheapest printings) and aesthetic (extra for foils, borderless, showcase, Secret Lair), plus a per-card max. `deck_check.py` reads `*F*`/`*E*` finishes, prices each printing and finish with a date, finds each card's cheapest printing (`--cheapest`), and checks `--budget`, `--aesthetic-budget` and `--per-card-max`. It fails finishes that don't exist and, when a set number points at another card, keeps checking the named card.
- **Card vs printing:** schemas separate a card's game identity (name, oracle_id) from its printing (set, number, finish, illustration, treatment, price with source, date and verified flag). Custom cards are flagged and never legal.
- **Exports:** `export_deck.py` writes Moxfield, Archidekt (commander tagged), plain text and CSV, keeping printings and finishes.
- **Alternatives and preferences:** brew offers community-backed swaps with trade-offs; research honours preferred and excluded sources (PROJECT.md or the setup config); setup can save looks and source defaults.
- **Tests:** 27 unit tests (finishes, budgets, exports, stale rules); evals for an official franchise, Stardew Valley, refusing exceptions, loosening midway, an honest weak-deck review, a drippy budget and an Archidekt export.

## 7.0.0
**The plugin is now EDH Companion** (`edh-companion`): four skills that research, build, verify and present Commander decks, with projects saved outside the plugin.

Moving from `mtg`: run `/plugin uninstall mtg@carlomos7-mtg-skills`, `/plugin marketplace remove carlomos7-mtg-skills`, then the install steps in the README. Old `/mtg:...` commands are gone; plain requests trigger the skills.
- **Skills:** `research` (cited community research and recommendations), `brew` (guided discovery, feasibility checks, builds and revisions inside your theme, art, budget and bracket), `audit` (independent pass / warning / fail / unverified checks, in a fresh agent for work made in the same chat), `present` (the existing deck-browser page, now built from project files), and an optional `setup`.
- **Projects:** `~/Documents/EDHCompanion/projects/<project>/` (or `./EDHCompanion`, or a folder you set) with PROJECT.md, STATE.md and DECISIONS.md in Markdown, plus research.json, brew.json and audit.json where structure helps (citations, decklists, checks, pages). Decklist versions are kept, never overwritten. Audits record the deck version they checked, so an out-of-date audit is detected.
- **`deck_check.py`:** deterministic Commander checks from Scryfall and Commander Spellbook's public APIs (real cards, printings matching their names, count, singleton, commander, identity, bans, Game Changers per bracket, commander + 2 combos, off-set printings, stats). Added because the tested MCP deck validator was down and its bracket estimator missed Game Changers and a banned card.
- **MCP-agnostic:** skills look for capabilities (card data, EDHREC, combos, decklists, search, transcripts), confirm them with one call, and fall back to the web; tested tool behaviour is documented.
- **Removed:** the commander-deckbuilding, commander-vault, collection and wrapper command skills (`build`, `check`, `cheaper`, `share`, `upgrade`), the vault agents (replaced by `researcher` and `auditor`), `vault-request.md`.
- **Tests:** unit tests for the deck checker, project validation and the page pipeline; evals for skill activation (positive, negative, ambiguous), persistence of rejected recommendations, theme drift, art mismatches, unsupported claims and conflicting sources.

## 6.0.0
The plugin moves to skills only. The in-house tooling is gone.
Removed:
- **The `mtgdb` MCP server and the `mtgdb.py` data CLI** (card index, deck checks, swap tests, simulation, price plans, exports, research logging, collection tools).
- **The deck and claims file-check hook** and its `vault/config.json`.
- **The `update-data` skill.**
- **The tests and the CI workflow.**
- **Eval graders** that checked in-house tool use.

Note: the page scripts (`site_data.py`, `build_site.py`) still call `mtgdb.py` and need rewiring. The page template is kept.

## 5.6.0
Page redesign: mobile first, one design system, accessible.
- **One set of tokens:** spacing (4 to 48px), type sizes, corner radii and card corners come from shared variables, so every panel, control and card lines up. Layout is written phone first and widens at 641, 821 and 1025px.
- **Card images:** the decklist has a List / Cards switch; Cards shows every card as an image grid (2 across on phones), with quantity, Game Changer and swap badges. Swap suggestions show a card thumbnail. All cards share one fixed 63x88 box with real card corners and a placeholder, so nothing jumps while images load. The viewer sizes the card to the screen so its buttons never fall off it, and the hover preview sits beside the pointer instead of over the next names.
- **Accessibility:** no automated WCAG 2.2 AA failures in light or dark mode (was about 300). Every target is at least 24px, 44px on touch screens. Theme tags pick a text color that passes contrast. Headings are in order, the tabs are a labelled nav, there's a footer, and pressed states read as pressed. No sideways scroll at 320px.
- **Also:** sticky tabs no longer hide focused items, safe-area insets for notched phones, and a print style that prints the decklist as text.

## 5.5.6
- **Better page filters:** the decklist filters are now chips you can combine: card type, mana value, role, theme and tags (Game Changers, cards with swap options, flagged cards). Chips in one row widen the list (Instant or Sorcery); rows narrow it (and Removal). Each chip shows how many cards it would leave, empty ones grey out, and Clear filters resets everything. Search also matches type and role. The card-rankings tab gets tier, price and theme chips in place of the max-price box. Filters are remembered and scroll sideways on phones. A browser test covers them.

## 5.5.5
- **Hover preview fix:** 5.5.4 hid the preview on scroll, which hid it as soon as it showed. It now shows on hover and hides on click, key press, tab change and when the viewer opens. A browser test covers it.

## 5.5.4
Fixes from an independent review against every requirement:
- **Privacy:** deck pages no longer contain local file paths (a ledger path with the Windows username was leaking), and `build_site.py` refuses to build a page that contains one.
- **Honest claim counts:** logged sources are `sourced`, not `verified`; only the vault's second reviewer marks a claim verified. The page shows re-checked, sourced and unverified counts separately.
- **Theme cap holds for swaps:** `mtg_deck_check` and `mtg_deck_swap` take the theme map (`themes`, `reasons`), so a swap that breaks the player's off-theme limit fails instead of being offered.
- **Deck page:** the hover preview no longer sticks after a click, tab change or opening the viewer; the template check marks "above range" as fine instead of red (card tags count a card in every role); plain-language check labels; the three price styles (cheapest, as listed, drippy) under the numbers; store links go straight to the store (no affiliate redirect); the faded card fan behind the title on phones is gone.
- **Research tools:** `mtg_decklists` keeps only finished lists (98+ cards) and dates them by creation; `mtg_edhrec` supports partners; both return ready-made log entries; the "no videos" warning is per commander.
- **Docs agree:** Fancy uses the three.js viewer by default everywhere; pages.md covers single-deck pages; one data-refresh rule (refresh during deck work, offer for one-off questions); research starts once bracket and theme are known; must-include cards ride along with the defaults question; bracket estimates run on the final 100; the hook's coverage is described accurately; page-spec matches the template.

## 5.5.3
- **Every vault page comes out the same shape:** `build_site.py` prints an `incomplete:` warning for each missing part (deck summary parts, community takes, videos, cards to consider, 10+ grouped sources), and the vault fixes each one or explains it in `plan.md`. pages.md lists what every page has.
- **The vault uses the research pass:** G1 follows research-pass.md (minimums, best tool first, logged sources, takes.json); a deck from the build skill brings its research along; notes carry community takes and videos; cards to consider cite their evidence.
- **Vault checks:** commander + 2 combos count as two-card combos at brackets 1 to 3; bracket-estimate add-ons are a second opinion; the render check covers snap-back, ⇄ swap options, card links and the Sources tab.
- **vault-request.md** describes the community section, swap marks, card links, grouped sources and the research pass.

## 5.5.2
- **Edge cases fixed in the research tools:**
  - `mtg_edhrec` and `mtg_decklists` fall back to the last cached copy (flagged stale) when offline.
  - Cache files are written atomically.
  - Archidekt cards without card data no longer crash the comparison.
- **The research log:**
  - accepts a JSON list, one object, or a JSONL file (including its own ledger), with a clear error for bad JSON
  - writes the full claims format, so `audit-claims` passes
  - the report lists sources missing a date or a video timestamp
- **`mtg_research_log`** needs a full folder path and passes entries through a file, so large logs work on Windows.
- **`mtg_deck_swap`** now reports every combo a swap completes. Ones needing only the commander plus two cards still fail brackets 1 to 3; bigger ones are a Rule 0 warning.

## 5.5.1
- **Best tool first, then fall back:** the research pass now has an explicit order per source type (card data, stats, combos, bracket estimate, decklists, videos, community, articles, prices, official, cEDH): installed add-ons first for the best results, then the built-in tools, then web search or fetch, never memory. Which tool answered is logged, and a row that only got the last resort is said out loud. `mtg_research_plan` returns the order too.

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
