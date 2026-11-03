# Sources and tools

## Local (preferred for every card fact)
`mtgdb.py`: card, printings, normalize, gamechangers, validate, stats, swaptest, audit-claims, selftest. Built from Scryfall bulk data, so no rate limits.

## MCP servers
| Server | Use for | Notes |
|---|---|---|
| `claude_ai_mtg-mcp` (j4th connector) | `edhrec_commander_staples`, `edhrec_card_synergy`, `commander_overview`, `spellbook_find_combos`, `spellbook_find_decklist_combos`, `spellbook_estimate_bracket`, `spellbook_combo_details`, `rules_*`, `scryfall_card_rulings`, `moxfield_*` | EDHREC tools are beta. Scryfall tools only for rulings or cards missing from the index. |
| `youtube-transcript` | Deck-tech transcripts | Auto captions mangle names; see youtube.md |
| `parallel-search` | Web search and page reads (Wizards announcements, articles, cEDH DB, Secret Lair drop pages) | |

## Optional local data (all in `~/.cache/mtg/`, survives re-index)
- **Scryfall Tagger tags**: `tags-sync` pulls `otag:` role tags (ramp, card-advantage, removal, board-wipe, tutor, ...) once; `stats` then counts real roles. Tag names live in `ROLE_TAGS` in mtgdb.py; a tag that returns 0 cards is probably misnamed (check tagger.scryfall.com). Refresh monthly.
- **Art tags**: `search "e:sld art:<thing>"` finds printings by what their art shows. Good for building theme maps; still eyeball disputed ones.
- **MTGJSON prices**: `prices-sync` maps MTGJSON's daily prices (paper vendors: TCGplayer, Card Kingdom, Cardmarket, Cardsphere; retail and buylist) to Scryfall printings. `--history` loads 90 days. Needs `pip install ijson` for the large files. Quote the vendor and date with any price.
- **Collection**: `collection import <csv or list>` (Moxfield, Archidekt, ManaBox CSV exports, or `1 Card Name` lines). Validate then reports owned cards and cost to buy.

## Web sources (no MCP)
- **EDHTop16**: public GraphQL at `https://edhtop16.com/api/graphql`, no auth, introspection enabled, regenerated nightly. Commander meta share, conversion rate, top cuts, decklists, card play rates. Introspect the schema first; keep queries small. Best evidence for "is this a real cEDH commander".
- **TopDeck.gg**: tournament platform API (free key from their developer portal, `Authorization` header). Tournaments, standings with win rates, decklists after events end, and the `leader` field for commanders. Limits: 50/min on single-tournament endpoints, 100/min elsewhere. Read `https://topdeck.gg/openapi.json` before the first call. Use when EDHTop16 lacks the detail (specific events, recent results). Key goes in `TOPDECK_API_KEY`; never write it into files.
- **cEDH Decklist Database** (cedh-db): curated competitive lists per commander. If a commander isn't there, say so.
- **Wizards announcements** (magic.wizards.com): only authority for bans, Game Changers and bracket rule changes.
- **Commander Spellbook**: MCP first; if it's down, `mtgdb.py combos deck.txt` calls the public find-my-combos API directly and lists included combos (two-card ones separately) with links.

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
