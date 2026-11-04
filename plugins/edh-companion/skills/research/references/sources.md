# Capabilities, tested tools and fallbacks

Find tools by capability. Names differ between installs (a claude.ai connector prefixes `mcp__claude_ai_…`, a local server doesn't), so read the tool list and pick by what a tool does. Confirm with one cheap call before depending on it. When a capability is missing or failing, use the fallback and record it.

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
