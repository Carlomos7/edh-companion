# The research pass (every new deck)

A deck is only as good as what it was checked against. Before the skeleton, research the commander across every source type below, write it down, and cite it on the page. `mtg_research_plan` returns this checklist with ready-made queries. Run it as the `vault-researcher` agent in the background (see commander-deckbuilding step 4) so the player isn't waiting; run it inline if agents aren't available. Log every source with `mtg_research_log`; `mtg_research_report` shows what's still short.

## Coverage minimums
Report a shortfall in one line rather than skipping silently ("no Command Zone video on this commander yet").

| Type (`kind`) | Minimum | Tools (use what's installed) | Used for |
|---|---|---|---|
| Card data (`card-data`) | every card named anywhere | `mtgdb`: `mtg_card`, `mtg_resolve_names`, `mtg_deck_check` | text, legality, identity, Game Changers, prices, printings, Tagger roles |
| Stats (`stats`) | commander staples + synergy, with deck counts | `mtg_edhrec` (built in); add-ons for card-to-card synergy | what real decks play, high-synergy cards the deck lacks |
| Combos (`combos`) | the final list, plus "one card away" | `mtg_deck_check`; add-on Spellbook tools (`spellbook_find_decklist_combos`, `spellbook_estimate_bracket`, `get_edhrec_combos`) | keeping combos out of brackets 1 to 3, bracket second opinion |
| Real decklists (`decklist`) | 6+ recent public lists, mixed brackets | `mtg_decklists` (Archidekt, built in); add-ons for Moxfield (`moxfield_search_decks`, `search_moxfield_decks`) | cards in 4+ lists the deck lacks; deck cards nobody plays |
| Videos (`video`) | 3+ channels, last 12 months | web search for the video, then `get_transcript`; blocked → web fetch of the video URL; `get_video_info` for title, channel, date | plan, traps, must-plays, with mm:ss |
| Community (`community`) | 4+ threads or primers | web search + fetch: r/EDH, r/EDHBrews, r/CompetitiveEDH, Moxfield/Archidekt primers | play tips, table reactions, "too strong for bracket N?" |
| Articles (`article`) | 3+ | EDHREC articles, Card Kingdom, Commander's Herald, Draftsim, Cardsrealm, Wargamer | builds, key cards, bracket takes |
| Prices (`price`) | the 10 priciest cards | `mtg_price_plan`, then a live check (`goldfish_deck_price`, `price_comparison`, `get_card_price`, TCGplayer) | flag gaps over 20% |
| Official (`official`) | current bracket article, Game Changers date | magic.wizards.com | bracket rules, Game Changer status |
| cEDH (`cedh`) | bracket 4 and 5 only | EDHTop16, cedh-db, TopDeck.gg | "is this a real cEDH commander" |

Channel weight: The Command Zone, EDHRECast, Commander's Quarters, Tolarian Community College and MTGGoldfish Commander first; smaller channels when the big ones haven't covered the commander, weighted lower. Sponsored or precon-promo videos support, never decide.

Cross-check: when two MTG servers are installed (e.g. `mtg-mcp` and `mtg-commander`), use the second for decklists and EDHREC numbers as a check, and note disagreements.

## Best tool first, then fall back
For each source type, use the first option that's installed and answers; drop to the next only when it's missing, errors or comes back empty. Tool names are examples: judge installed tools by what they do. Log which one answered (`kind: tool` in the ledger), and say in one line when a type only got the last resort.

| Type | 1. Best | 2. Next | 3. Last resort |
|---|---|---|---|
| Card data | `mtgdb` (`mtg_card`, `mtg_resolve_names`) | `mtg_data_sync`, then retry | an add-on's live Scryfall lookup, labelled "not in the local index" |
| Stats | `mtg_edhrec` | an EDHREC add-on (`edhrec_commander_staples`, `get_edhrec_recommendations`) | web fetch of the commander's edhrec.com page |
| Combos | `mtg_deck_check` / `mtg_deck_swap` (local Spellbook) | a Spellbook add-on (`spellbook_find_decklist_combos`, `get_edhrec_combos`) | `mtgdb.py combos --live` (Spellbook API) |
| Bracket estimate | a Spellbook add-on (`spellbook_estimate_bracket`) | `mtg_deck_check` against references/brackets.md | (none: say it didn't run) |
| Real decklists | `mtg_decklists` (Archidekt) **and** a Moxfield add-on (`moxfield_search_decks`, `search_moxfield_decks`, `search_archidekt_decks`) together | whichever of those is installed | web search `site:moxfield.com <commander>` / `site:archidekt.com <commander>`, then fetch the lists |
| Videos | web search to find them, then a transcript tool (`get_transcript`) | web fetch of the video URL (returns the transcript when the transcript tool is blocked) | `get_video_info` or the page description: cite as "watch", don't quote |
| Community (Reddit, primers) | a search MCP (e.g. `parallel-search` `web_search` + `web_fetch`), whole threads | built-in WebSearch + WebFetch | (none: shortfall) |
| Articles | a search MCP | built-in WebSearch + WebFetch | (none: shortfall) |
| Prices | `mtg_price_plan` (Scryfall daily, plus MTGJSON vendors after `prices-sync`) | a live price add-on (`goldfish_deck_price`, `price_comparison`, `get_card_price`) to cross-check | web fetch of the TCGplayer product page |
| Official | web fetch of the magic.wizards.com announcement | web search for it | the local Game Changers flag, with its date |
| cEDH (B4, B5) | EDHTop16 GraphQL (`https://edhtop16.com/api/graphql`) | a tournament add-on (`spicerack_*`) or TopDeck.gg (with `TOPDECK_API_KEY`) | cedh-db or web search |

Run independent rows in parallel (videos one at a time). Never fill a row from memory.

## Rules
- Every card name goes through `mtg_resolve_names`. Card facts come from `mtgdb`, never from a video or thread.
- A community "combo alert" is a hard check: run it against the bracket before any swap that completes it.
- Opinions that disagree (with each other or with the player's theme) are shown, not acted on.
- Every suggested swap from the research passes `mtg_deck_swap` at the deck's bracket.

## Outputs (in `research/` next to the deck)
- `research.md`: one section per type above with findings and links, "Takes worth showing" (8 to 15), "Possible swaps" (each tested), "Shortfalls".
- `claims.jsonl`: one line per claim, `{"claim","subject","status","sources":[{"title","url","kind","date","locator","used_for"}]}`, `kind` from the table. The page's Sources tab groups by `kind` and shows `used_for`.
- `takes.json`: `[{"text","source","url","date","kind"}]`, which becomes `community` in notes.json.
- `swaps.json`: the tested swaps, in the `add-swaps` format.
