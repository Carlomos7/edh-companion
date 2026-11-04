# Capabilities, tested tools and fallbacks

Find tools by capability. Names differ between installs (a claude.ai connector prefixes `mcp__claude_ai_…`, a local server doesn't), so read the tool list and pick by what a tool does. Confirm with one cheap call before depending on it. When a capability is missing or failing, use the fallback and record it.

## First research: capabilities and depth
Check each capability with one cheap call and judge the answer, not just that something came back (an empty, generic or wrong result is a failure):

| Capability | Cheap check | Working means |
|---|---|---|
| Card data | look up Sol Ring | text and Commander legality come back |
| EDHREC stats | staples for a popular commander (e.g. Atraxa, Praetors' Voice) | a deck count above 0 and real cards |
| Combos | combos for a known pair (commander + 2 cards) | the known combo is found |
| Decklists | read one known public deck link, or a site search | real 100-card lists for that commander |
| Web / community search | search a Reddit EDH thread about a commander | relevant threads with URLs |
| Semantic discovery | "deck tech article for <commander>" | relevant articles |
| Video transcripts | transcript of one short MTG video | timestamped text |
| Scripts (uv) | `companion.py where` | paths print |

Show the result as one short table (working / not working / missing, and what each missing one costs), then offer:
- **Comprehensive (Recommended)**: every working source: data, decklists, creator videos with timestamps, Reddit and forums, articles; about 5 to 15 minutes per commander. Best recommendations, best citations.
- **Quick**: card data, EDHREC, one or two community threads, a video only if one is clearly central; about 1 to 3 minutes. Good for a first look.
- **Custom**: the player picks sources to include or exclude (and can name preferred tools).
- **Skip**: no web research; answers from verified card data and rules only, clearly labelled as unresearched.
Save to the config file (`~/.config/edh-companion/config.yaml`), keeping everything else in it:
```yaml
research:
  depth: comprehensive        # comprehensive | quick | custom | skip
  prefer: []                  # sources to favour, e.g. [EDHREC, Reddit, The Command Zone]
  exclude: []                 # sources never to use
  tools: {}                   # optional, e.g. {semantic_search: Exa, web_search: Parallel}
  capabilities_seen: [card_data, edhrec, combos, web_search, semantic_search, transcripts, scripts]
  checked: 2026-11-04
```
Ask again only when a capability appears, disappears or starts failing compared with `capabilities_seen`, or when the player asks.

## Which tool for which job
Use the strongest tool for each job, not every tool for every job:
- **Card facts, legality, printings, prices, combos:** the MTG data tool (Scryfall- and Spellbook-backed), or Scryfall/Spellbook directly. Never a search engine.
- **Finding deck techs, primers and articles by description:** semantic search (e.g. Exa).
- **Reddit, forums and keyword searches, reading pages:** web search + fetch (e.g. Parallel, or the built-in tools).
- **What a creator actually said:** transcripts, quoted with mm:ss.
- **Real lists:** read known deck links; find links with web search when the deck tool's search doesn't filter.
Don't repeat a search with a second engine unless the first came back empty or wrong, and don't refetch a page already read this session. When a tool fails mid-research, switch to its fallback, note it in `methodology.tools_failed`, and keep going.

Tested 2026-11-04 with the j4th MTG MCP (claude.ai connector), Parallel Search, Exa and jkawamoto YouTube Transcript:

| Capability | Typical tool | Tested result | Fallback |
|---|---|---|---|
| Card facts (text, legality, identity, Game Changer, image, printings) | `scryfall_card_details`, `scryfall_search_cards` | Works. Search supports `is:gamechanger`, `e:`, `art:`, `unique:prints`. | Scryfall API via web fetch (`https://api.scryfall.com/cards/named?exact=…`) |
| Deck validation | `deck_validate` | **Down (502 twice).** | the audit skill's `deck_check.py` (Scryfall API, deterministic) |
| Combos in a list | `spellbook_find_decklist_combos` | Works; counts the commander as a piece. Output is very large: pass only the list you need. | `deck_check.py` (Spellbook API), or commanderspellbook.com search |
| Bracket estimate | `spellbook_estimate_bracket` | **Unreliable:** returned no Game Changers and no banned cards for a list with Rhystic Study, Smothering Tithe and Mana Crypt. Never use it as evidence. | Count Game Changers and combos with `deck_check.py`; judge the rest |
| EDHREC commander stats | `edhrec_commander_staples` | Works for exact front-face names; a double-faced name failed. Returned `total_decks: 0` with generic staples for a new commander: treat as no data. | edhrec.com/commanders/<slug> via web fetch; report a gap |
| Public decklists | `moxfield_search_decks`, `moxfield_decklist` | Search **ignored its query text** (returned unrelated decks). Reading a known deck link is the reliable part. | Web search `site:moxfield.com <commander>` or `site:archidekt.com`, then read each list |
| Web/community search | Parallel `web_search` + `web_fetch` | Works; good for Reddit threads and articles. | Built-in WebSearch/WebFetch |
| Semantic discovery | Exa `web_search_exa`, `web_fetch_exa` | Works; good at finding articles and deck techs by description. | Parallel or built-in search |
| Video transcripts | `get_transcript`, `get_video_info` | Works (timestamped). YouTube sometimes blocks by IP. | Web fetch of the video URL; else cite the video as "watch" without quoting |
| Prices and vendors | Scryfall prices (USD/EUR/TIX per printing, daily); a price tool such as `price_comparison` if installed (not retested) | Scryfall works | Vendor product pages via web fetch (TCGplayer, Card Kingdom, Cardmarket) |
| Product contents (precons, Secret Lairs) | Scryfall `e:<set>` search | Works | Official Wizards product/decklist pages |
| Comprehensive Rules | a rules lookup tool (`rules_lookup`) | **Outdated:** returned pre-2026 partner rules (no "Partner—[text]", friends forever as its own ability). Check the date of the rules it uses. | Wizards' current Comprehensive Rules (magic.wizards.com/en/rules); state the effective date |
| Commander eligibility | Scryfall `is:commander` search | Works and matches current rules (includes Vehicles and Spacecraft) | `deck_check.py --commander` |
| Tournament results (cEDH) | EDHTop16 GraphQL `https://edhtop16.com/api/graphql`; a tournament tool if installed | Not retested | cedh-db, web search |
| Wizards rules and announcements | web fetch of magic.wizards.com | Works via any fetch tool | none needed |

Re-test a capability whenever a result looks odd (empty, generic, or contradicting Scryfall). A tool answering is not the same as a tool being right.

## Authority per question
| Question | Authority | Never from |
|---|---|---|
| Card text, legality, identity, Game Changer, printings, art | Scryfall | memory, videos, EDHREC |
| Bans, Game Changer list changes, bracket rules | Wizards announcements | creators |
| What people play (inclusion, synergy, lift) | EDHREC with deck counts; real decklists | videos |
| Combos and their pieces | Commander Spellbook | memory, videos |
| What wins competitively | EDHTop16, TopDeck.gg, cEDH decklist database | EDHREC, casual creators |
| Why a card or plan is good, traps, lines | creators and primers, cross-checked | a single source |
| How it plays at real tables | Reddit and forum threads, primer comments | as proof of power |
| Rules interactions | Comprehensive Rules (with effective date), Scryfall rulings | memory |

## Rate limits and access
- Scryfall: search/named/collection 2 requests/s, others 10/s; a 429 locks you out for 30 s. Batch (the collection endpoint takes 75 cards).
- EDHREC: one staples pull per commander, reused.
- YouTube: one transcript at a time.
- Reddit and YouTube block some direct requests; go through a search/fetch tool.
