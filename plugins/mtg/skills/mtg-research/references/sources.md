# Sources and tools

Reddit and YouTube block direct requests from some networks; reach them through a web search or fetch tool.

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
- **Card facts always come from Scryfall** (legality, color identity, prices, printings, Game Changers), through an add-on's Scryfall tools (`scryfall_*`) or the web. Never from memory, videos or EDHREC.
- **Brand-new cards** can lag a day in Scryfall's data. Say so if one is missing.
- **Checking what's there:** call one cheap tool per capability (any read-only lookup) rather than trusting names. Report which capabilities answered.
- **Present add-on:** use it by default for what it's good at (no need to ask the player first). The per-source order (best tool, next, last resort) is in research-pass.md.
- **Missing add-on:** say which check didn't run and carry on with the rest. Never fill the gap from memory.
- **No link reader for a site:** ask the player to paste the site's export instead.

## Web sources (no MCP)
- **EDHTop16**: public GraphQL at `https://edhtop16.com/api/graphql`, no auth, introspection enabled, regenerated nightly. Commander meta share, conversion rate, top cuts, decklists, card play rates. Introspect the schema first; keep queries small. Best evidence for "is this a real cEDH commander".
- **TopDeck.gg** (advanced, only if the player set `TOPDECK_API_KEY` before starting Claude Code): tournament platform API with an `Authorization` header. Read the key from the environment inside the command (e.g. `curl -H "Authorization: $TOPDECK_API_KEY" ...`); never print, echo or log it, and to check it exists test only whether it's non-empty. Tournaments, standings with win rates, decklists after events end, and the `leader` field for commanders. Limits: 50/min on single-tournament endpoints, 100/min elsewhere. Read `https://topdeck.gg/openapi.json` before the first call. Use when EDHTop16 lacks the detail (specific events, recent results). Key goes in `TOPDECK_API_KEY`; never write it into files.
- **cEDH Decklist Database** (cedh-db): curated competitive lists per commander. If a commander isn't there, say so.
- **Wizards announcements** (magic.wizards.com): only authority for bans, Game Changers and bracket rule changes.
- **Commander Spellbook**: combos and their pieces. Bracket estimates come from an add-on's bracket-estimate tool, when one is installed.

## Community sources (supporting only)
- r/EDH, r/CompetitiveEDH, Moxfield/Archidekt primers and comments, Discord write-ups.
- Use them to find questions (missing roles, bad interactions, overrated cards), then confirm with data, Spellbook or the rules.
- Cite them like any source (url + date). They never count as one of the 2 independent sources for a must-play on their own.

## Data caveats to state when relevant
- **Scryfall**: `/cards/search`, `/named`, `/random`, `/collection` allow 2 req/s, other endpoints 10/s. A 429 locks you out for 30s and repeated overload can ban you. Space out calls. Images on `*.scryfall.io` are unlimited.
- **EDHREC**:
  - Inclusion % is popularity among user-uploaded decks, not strength.
  - Since Dec 2025, card-to-card pages use **lift** (1 = independent, above 1 = played together more than chance); commander pages still show synergy.
  - Salt score is a 0 to 4 survey average.
  - Their FAQ doesn't cover automated access, and at least one tool author avoids it over the terms. Keep queries light (one staples pull per commander, saved in your notes), and prefer an MCP add-on over scraping.
- **Prices**: Scryfall bulk is daily; quote the `prices_as_of` date.
- **Brackets**: read the latest Wizards bracket article before a build; check the Game Changers list's date.
