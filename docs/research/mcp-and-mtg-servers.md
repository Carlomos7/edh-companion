# Existing MTG MCP servers and data source terms

All sources accessed 2026-11-03. Items marked **(unconfirmed)** were not verified against a primary source.

> **Correction (2026-11-03):** j4th's `config.py` and `.env.example` turn EDHREC, Moxfield, Rules, bulk data and 17Lands on by default. "Behind a flag" below means they *can* be switched off, not that they start off.

## Existing MTG MCP servers

### Survey

Stars and dates come from `gh repo view` / `gh search repos` on 2026-11-03.

| Repo | Stars | Last push | Lang | License | What it offers | Maintained? |
|---|---|---|---|---|---|---|
| [j4th/mtg-mcp-server](https://github.com/j4th/mtg-mcp-server) | 20 | 2026-10-21 (release v3.2.1) | Python, FastMCP ≥3.2 | MIT | 69 tools, 19 prompts, 21 resources. Scryfall live and bulk (`oracle_cards` only, behind a flag), Spellbook (find combos, estimate bracket), 17Lands, EDHREC (behind a flag), Moxfield (behind a flag), Spicerack, MTGGoldfish (scraped, behind a flag), rules engine. Workflow tools: `commander_overview`, `deck_analysis`, `deck_validate`, `budget_upgrade`, `suggest_cuts`, `suggest_mana_base`. Hosted at `mtg-mcp-server.fastmcp.app/mcp` and on PyPI (`uvx mtg-mcp-server`). We already use it as the `claude_ai_mtg-mcp` connector. | Yes, active, with CI, codecov and Dependabot |
| [nathanmartins/mtg-mcp](https://github.com/nathanmartins/mtg-mcp) | 25 | 2026-11-02 | Go | MIT | About 20 tools: Scryfall (search, details, legality, rulings, price incl. BRL, banned list, `validate_deck` in batches of 75, card image with an MCP Apps widget), Moxfield (3), Archidekt (3, incl. bracket filter), EDHREC (recommendations with theme and price tier, combos, set cards), Comprehensive Rules. Resources: commander rules, banned list, comp rules. Installed here as `mtg-commander`. | Yes, active, 92.8% coverage |
| [cryppadotta/scryfall-mcp](https://github.com/cryppadotta/scryfall-mcp) | 36 | 2025-02-12 | JS | none listed | Scryfall API wrapper | No (stale) |
| [artillect/mtg-mcp-servers](https://github.com/artillect/mtg-mcp-servers) | 15 | 2025-03-18 | Python | none listed | Scryfall search plus deck and hand state for play | No |
| [gregario/mtg-oracle](https://github.com/gregario/mtg-oracle) | 5 | 2026-05-02 | TS | MIT | Card search, rules, deck analysis, Commander | Low activity |
| [pato/mtg-mcp](https://github.com/pato/mtg-mcp) | 5 | 2025-07-21 | Rust | none listed | Card data | No |
| [bmurdock/scryfall-mcp](https://github.com/bmurdock/scryfall-mcp) | 1 | 2026-10-29 | TS | MIT | Scryfall search, rules, deckbuilding workflows | Active, tiny |
| [elliotchun/edhrec-mcp](https://github.com/elliotchun/edhrec-mcp) | 1 | 2025-09-30 | Python | none listed | EDHREC data | No |
| [dreliq9/urza](https://github.com/dreliq9/urza) | 1 | 2026-05-21 | Python | not checked | Commander brewing app built on top of j4th's server | Low |

I found no standalone, maintained Commander Spellbook MCP or MTGJSON MCP. Spellbook is covered inside j4th's server; MTGJSON is not covered at all. The `gh search` queries were "mtg mcp", "scryfall mcp", "edhrec mcp", "commander spellbook mcp", "mtgjson mcp" and "magic the gathering mcp". Many other repos have 0 stars and are omitted.

### Data source terms

**Scryfall**
- Every request to `api.scryfall.com` MUST send an accurate `User-Agent` (app name and version, not the library default) and an `Accept` header. https://scryfall.com/docs/api
- Hard rate limits: `/cards/search`, `/cards/named`, `/cards/random` and `/cards/collection` allow 2 per second. `/cards/manifest` allows 10 per minute. Everything else allows 10 per second. `*.scryfall.io` file hosts have no limit. A 429 locks you out for 30 seconds, and ignoring 429s can get the app banned. https://scryfall.com/docs/api/rate-limits
- Cache data for at least 24 hours. For fast lookups of many names, prices or images you MUST use bulk data. Prices change once a day. Gameplay data rarely changes, so a weekly download is enough. https://scryfall.com/docs/api/rate-limits
- Bulk files are gzipped JSONL. Bulk prices are "dangerously stale after 24 hours". https://scryfall.com/docs/api/bulk-data
- Tagger tags are official bulk files, `oracle_tags` and `art_tags`, updated daily. https://scryfall.com/docs/api/tags. I confirmed both in `GET /bulk-data` today: `oracle_tags` is 6.1 MB and `default_cards` is 80.8 MB. Paging `otag:` searches through `/cards/search` at 2 per second takes 2 to 3 minutes; the bulk file takes a few seconds.
- Data and images are free to use for building Magic software under the Fan Content Policy. Image rules: do not crop off or cover the artist or copyright, do not distort or recolour, do not watermark, and do not imply the card is not from Wizards. If you show `art_crop`, list the artist and copyright alongside it. https://scryfall.com/docs/api
- New image formats `display`, `crop` and `art` (WEBP) replace `large`, `border_crop` and `art_crop`. https://scryfall.com/docs/api/images.

**EDHREC**
- EDHREC has no public or documented API. Its JSON endpoints (`json.edhrec.com`) are the ones the website itself uses, found by inspecting network traffic. https://github.com/sigiltenebrae/edhrec_scraper/issues/1. nathanmartins' README calls them "unofficial JSON endpoints". https://github.com/nathanmartins/mtg-mcp
- The terms grant a licence "solely for your own personal, noncommercial use". The acceptable-use policy forbids using "software or automated agents or scripts … to generate automated searches, requests, or queries to the Site". https://edhrec.com/terms
- EDHREC's 429 page says "Please limit your requests to 1 per second … Implement caching. Contact us to lift the ban". https://beta.edhrec.com/429
- **Position:** any automated EDHREC access breaks the literal terms. Both existing servers do it anyway, and j4th puts it behind a flag. If the user wants EDHREC data, they can enable it in j4th's or nathanmartins' server, and the risk stays with that choice.

**Commander Spellbook**
- The API is public and needs no login. Guidelines: make sparse requests ("a few HTTP calls per user interaction"), name your service in `User-Agent`, stay at about 80 requests per minute or less, always handle 429, and credit and link commanderspellbook.com. https://backend.commanderspellbook.com/, https://spacecowmedia.github.io/commander-spellbook-backend/api.html
- Do not export the whole dataset through the API. Instead use `https://json.commanderspellbook.com/variants.json.gz`, which holds all variants and aliases and is "refreshed periodically". The refresh interval is not stated. https://spacecowmedia.github.io/commander-spellbook-backend/api.html
- Endpoints include `POST /find-my-combos` and `POST /estimate-bracket`. Same source.
- The backend code is MIT (checked with `gh repo view SpaceCowMedia/commander-spellbook-backend`). The licence of the combo data itself is not stated. **(unconfirmed)**

**MTGJSON**
- MIT licence ("Copyright © 2018 – Present, Zach Halpern"), applied to the website and its content. https://mtgjson.com/license
- Rebuilt daily, and `Meta.json` shows the last build. https://github.com/mtgjson/mtgjson
- Price data comes from vendors such as TCGplayer and Cardmarket. Whether those vendors add terms beyond MTGJSON's MIT licence is not stated on the licence page. **(unconfirmed)**

**Wizards Fan Content Policy** (last updated 2017-11-15)
- Fan content must be free: no payments, surveys, required downloads, subscriptions or email sign-ups to access it. Donations and ad revenue are allowed. No Wizards logos or trademarks without written consent. https://company.wizards.com/en/legal/fancontentpolicy
- The usual disclaimer, used by EDHREC, Spellbook and j4th, reads: "unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC." https://edhrec.com/terms, https://github.com/j4th/mtg-mcp-server. Put it in the README.

### Unconfirmed items

- The licence of Commander Spellbook's combo data, separate from its MIT code, and how often `variants.json.gz` refreshes.
- Whether price vendors attach terms to MTGJSON price data beyond its MIT licence.
- j4th's tool, prompt and resource counts are taken from its README.
