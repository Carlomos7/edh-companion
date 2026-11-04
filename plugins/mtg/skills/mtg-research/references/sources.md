# Sources and tools

## Local (preferred for every card fact)
The plugin's `mtgdb` MCP server: `mtg_card`, `mtg_resolve_names`, `mtg_deck_check`, `mtg_deck_swap`, `mtg_deck_profile`, `mtg_simulate`, `mtg_price_plan`, `mtg_cheaper_alternatives`, `mtg_export`, `mtg_rules`, `mtg_data_status`, `mtg_data_sync`. The same commands (plus `search`, `audit-claims`, `selftest`, `theme-build`, `contact-sheet`, `collection`) run as `uv run "${CLAUDE_PLUGIN_ROOT}/scripts/mtgdb.py" <command>`. Built from official bulk files, so no rate limits.

## Optional MCP servers (find them by what they do)
Players install add-ons under their own names, and different servers name their tools differently. Look at the tools you actually have and judge by what each one does; tool names below are examples, not requirements.

| Capability | Examples | Use for |
|---|---|---|
| EDHREC data | j4th `mtg-mcp-server`: `edhrec_commander_staples`, `edhrec_card_synergy`; other servers: `get_edhrec_recommendations` | inclusion %, synergy, popular cards (with deck counts) |
| Read a deck from a link | `moxfield_decklist` (j4th), `get_moxfield_deck`, `get_archidekt_deck` (other servers) | importing a deck the player linked |
| Bracket estimate | `spellbook_estimate_bracket` (j4th) | a second opinion on the bracket |
| Video transcripts | `get_transcript` (`youtube-transcript`) | creator deck techs, see youtube.md |
| Web search and fetch | any search server (e.g. `parallel-search`), or the built-in WebSearch / WebFetch | Wizards announcements, articles, tournament pages |

Rules:
- **Card facts and deck checks always come from `mtgdb`** (legality, color identity, prices, printings, Game Changers, validation), even when an add-on has a similar tool (`scryfall_*`, `deck_validate`): add-ons are live, rate limited and can disagree with the index.
- **One exception:** a card that isn't in the index yet (spoiled after the last sync). Offer `mtg_data_sync` first; if it's still missing, an add-on's Scryfall lookup may be used, labelled "live Scryfall, not in the local index".
- **Checking what's there:** call one cheap tool per capability (any read-only lookup) rather than trusting names. Report which capabilities answered.
- **Present add-on:** use it by default for what it's good at (no need to ask the player first).
- **Missing add-on:** say which check didn't run and carry on with the rest. Never fill the gap from memory.
- **No link reader for a site:** ask the player to paste the site's export instead.

## Optional local data (all in `~/.cache/mtg/`, survives re-index)
- **Scryfall Tagger tags**: part of `sync`, from Scryfall's daily oracle-tags bulk file. Role counts in `stats` use `ROLE_TAGS` in mtgdb.py (a role tag with 0 cards was probably renamed; check tagger.scryfall.com). Every tag is also stored for `alternatives`.
- **Rulings, combos, Comprehensive Rules**: also part of `sync`, from Scryfall's rulings file, Commander Spellbook's combo file and Wizards' rules page.
- **Art tags**: `search "e:sld art:<thing>"` finds printings by what their art shows. Good for building theme maps; still eyeball disputed ones.
- **MTGJSON prices**: `prices-sync` maps MTGJSON's daily prices (paper vendors: TCGplayer, Card Kingdom, Cardmarket, Cardsphere; retail and buylist) to Scryfall printings. `--history` loads 90 days. Needs `pip install ijson` for the large files. Quote the vendor and date with any price.
- **Collection**: `mtg_collection` / `mtg_collection_edit` (the `collection` skill): import from Moxfield, Archidekt or ManaBox CSV or a list, add, remove, value, find, have vs. a deck, fits a commander, export. Validate and price-plan report owned cards and cost to buy.

## Web sources (no MCP)
- **EDHTop16**: public GraphQL at `https://edhtop16.com/api/graphql`, no auth, introspection enabled, regenerated nightly. Commander meta share, conversion rate, top cuts, decklists, card play rates. Introspect the schema first; keep queries small. Best evidence for "is this a real cEDH commander".
- **TopDeck.gg** (advanced, only if the player set `TOPDECK_API_KEY` before starting Claude Code): tournament platform API with an `Authorization` header. Read the key from the environment inside the command (e.g. `curl -H "Authorization: $TOPDECK_API_KEY" ...`); never print, echo or log it, and to check it exists test only whether it's non-empty. Tournaments, standings with win rates, decklists after events end, and the `leader` field for commanders. Limits: 50/min on single-tournament endpoints, 100/min elsewhere. Read `https://topdeck.gg/openapi.json` before the first call. Use when EDHTop16 lacks the detail (specific events, recent results). Key goes in `TOPDECK_API_KEY`; never write it into files.
- **cEDH Decklist Database** (cedh-db): curated competitive lists per commander. If a commander isn't there, say so.
- **Wizards announcements** (magic.wizards.com): only authority for bans, Game Changers and bracket rule changes.
- **Commander Spellbook**: `mtg_deck_check` lists every combo from the local copy of Spellbook's combo file. `combos --live` asks the API instead. Bracket estimates come from an add-on's bracket-estimate tool, when one is installed.

## Community sources (supporting only)
- r/EDH, r/CompetitiveEDH, Moxfield/Archidekt primers and comments, Discord write-ups.
- Use them to find questions (missing roles, bad interactions, overrated cards), then confirm with data, Spellbook or the rules.
- Cite them like any source (url + date). They never count as one of the 2 independent sources for a must-play on their own.

## Data caveats to state when relevant
- **Scryfall**: `/cards/search`, `/named`, `/random`, `/collection` allow 2 req/s, other endpoints 10/s. A 429 locks you out for 30s and repeated overload can ban you. That's why the index exists. Images on `*.scryfall.io` are unlimited.
- **EDHREC**:
  - Inclusion % is popularity among user-uploaded decks, not strength.
  - Since Dec 2025, card-to-card pages use **lift** (1 = independent, above 1 = played together more than chance); commander pages still show synergy.
  - Salt score is a 0 to 4 survey average.
  - Their FAQ doesn't cover automated access, and at least one tool author avoids it over the terms. Keep queries light (one staples pull per commander, cached in your notes), and prefer the MCP over scraping.
- **Prices**: Scryfall bulk is daily; quote the `prices_as_of` date.
- **Brackets**: read the latest Wizards bracket article before a build; the local Game Changers list is only as fresh as the index.
