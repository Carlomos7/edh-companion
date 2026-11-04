# The research pass (every new deck)

A deck is only as good as what it was checked against. Before the skeleton, research the commander across every source type below, write it down, and cite it on the page. Run it as the `vault-researcher` agent in the background (see commander-deckbuilding step 3) so the player isn't waiting; run it inline if agents aren't available. Log every source in `claims.jsonl` (see claims.md) and note what's still short.

## Coverage minimums
Report a shortfall in one line rather than skipping silently ("no Command Zone video on this commander yet").

| Type (`kind`) | Minimum | Tools (use what's installed) | Used for |
|---|---|---|---|
| Card data (`card-data`) | every card named anywhere | Scryfall, through an add-on (`scryfall_card_details`, `get_card_details`) or the web | text, legality, identity, Game Changers, prices, printings |
| Stats (`stats`) | commander staples + synergy, with deck counts | EDHREC add-ons (`edhrec_commander_staples`, `edhrec_card_synergy`) | what real decks play, high-synergy cards the deck lacks |
| Combos (`combos`) | the final list, plus "one card away" | add-on Spellbook tools (`spellbook_find_decklist_combos`, `spellbook_estimate_bracket`, `get_edhrec_combos`) | keeping combos out of brackets 1 to 3, bracket second opinion |
| Real decklists (`decklist`) | 6+ recent public lists, mixed brackets | add-ons for Moxfield and Archidekt (`moxfield_search_decks`, `search_moxfield_decks`, `search_archidekt_decks`) | cards in 4+ lists the deck lacks; deck cards nobody plays |
| Videos (`video`) | 3+ channels, last 12 months | web search for the video, then `get_transcript`; blocked → web fetch of the video URL; `get_video_info` for title, channel, date | plan, traps, must-plays, with mm:ss |
| Community (`community`) | 4+ threads or primers | web search + fetch: r/EDH, r/EDHBrews, r/CompetitiveEDH, Moxfield/Archidekt primers | play tips, table reactions, "too strong for bracket N?" |
| Articles (`article`) | 3+ | EDHREC articles, Card Kingdom, Commander's Herald, Draftsim, Cardsrealm, Wargamer | builds, key cards, bracket takes |
| Prices (`price`) | the 10 priciest cards | a live check (`goldfish_deck_price`, `price_comparison`, `get_card_price`, TCGplayer) | flag gaps over 20% |
| Official (`official`) | current bracket article, Game Changers date | magic.wizards.com | bracket rules, Game Changer status |
| cEDH (`cedh`) | bracket 4 and 5 only | EDHTop16, cedh-db, TopDeck.gg | "is this a real cEDH commander" |

Channel weight: The Command Zone, EDHRECast, Commander's Quarters, Tolarian Community College and MTGGoldfish Commander first; smaller channels when the big ones haven't covered the commander, weighted lower. Sponsored or precon-promo videos support, never decide.

Cross-check: when two MTG servers are installed (e.g. `mtg-mcp` and `mtg-commander`), use the second for decklists and EDHREC numbers as a check, and note disagreements.

## Best tool first, then fall back
For each source type, use the first option that's installed and answers; drop to the next only when it's missing, errors or comes back empty. Tool names are examples: judge installed tools by what they do. Say in one line when a type only got the last resort.

| Type | 1. Best | 2. Next | 3. Last resort |
|---|---|---|---|
| Card data | a Scryfall add-on (`scryfall_card_details`, `get_card_details`) | Scryfall's website or API through web fetch | (none: shortfall) |
| Stats | an EDHREC add-on (`edhrec_commander_staples`, `get_edhrec_recommendations`) | web fetch of the commander's edhrec.com page | (none: shortfall) |
| Combos | a Spellbook add-on (`spellbook_find_decklist_combos`, `get_edhrec_combos`) | web fetch of commanderspellbook.com | (none: say it didn't run) |
| Bracket estimate | a Spellbook add-on (`spellbook_estimate_bracket`) | the bracket rules in the commander-deckbuilding references | (none: say it didn't run) |
| Real decklists | a Moxfield add-on and an Archidekt add-on (`moxfield_search_decks`, `search_moxfield_decks`, `search_archidekt_decks`) together | whichever of those is installed | web search `site:moxfield.com <commander>` / `site:archidekt.com <commander>`, then fetch the lists |
| Videos | web search to find them, then a transcript tool (`get_transcript`) | web fetch of the video URL (returns the transcript when the transcript tool is blocked) | `get_video_info` or the page description: cite as "watch", don't quote |
| Community (Reddit, primers) | a search MCP (e.g. `parallel-search` `web_search` + `web_fetch`), whole threads | built-in WebSearch + WebFetch | (none: shortfall) |
| Articles | a search MCP | built-in WebSearch + WebFetch | (none: shortfall) |
| Prices | a live price add-on (`goldfish_deck_price`, `price_comparison`, `get_card_price`) | Scryfall prices, cross-checked on a vendor page | web fetch of the TCGplayer product page |
| Official | web fetch of the magic.wizards.com announcement | web search for it | Scryfall's Game Changers flag, with its date |
| cEDH (B4, B5) | EDHTop16 GraphQL (`https://edhtop16.com/api/graphql`) | a tournament add-on (`spicerack_*`) or TopDeck.gg (with `TOPDECK_API_KEY`) | cedh-db or web search |

Run independent rows in parallel (videos one at a time). Never fill a row from memory.

## Rules
- `title`, `used_for` and `locator` are shown to players on the page: plain English ("how many decks play each card"), no tool names, field names or API notes.
- Logged sources are `sourced`; only the vault's verifier marks a claim `verified` after re-opening it.
- Every card name is checked against Scryfall. Card facts come from Scryfall, never from a video or thread.
- A community "combo alert" is a hard check: run it against the bracket before any swap that completes it.
- Opinions that disagree (with each other or with the player's theme) are shown, not acted on.
- Every suggested swap from the research is checked for legality, color identity and the deck's bracket before it is offered.

## Outputs (in `research/` next to the deck)
- `research.md`: one section per type above with findings and links, "Takes worth showing" (8 to 15), "Possible swaps" (each checked), "Shortfalls".
- `claims.jsonl`: one line per claim, `{"claim","subject","status","sources":[{"title","url","kind","date","locator","used_for"}]}`, `kind` from the table. The page's Sources tab groups by `kind` and shows `used_for`.
- `takes.json`: `[{"text","source","url","date","kind"}]`, which becomes `community` in notes.json.
- `swaps.json`: the checked swaps.
