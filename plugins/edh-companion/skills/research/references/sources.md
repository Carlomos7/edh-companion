# Capabilities, tested tools and fallbacks

Find tools by capability. Names differ between installs (a claude.ai connector prefixes `mcp__claude_ai_…`, a local server doesn't), so read the tool list and pick by what a tool does. Confirm with one cheap call before depending on it. When a capability is missing or failing, use the fallback and record it.

## Research approval (first use, then remembered)
Three separate choices, each asked once and saved in the config file (`~/.config/edh-companion/config.yaml`, `research:` section; a project's PROJECT.md "Research preferences" overrides it for that project):
1. **Which tools are approved** (step 1).
2. **How often to ask** before research (step 2).
3. **How deep** to go (Quick / Comprehensive / Deep / Custom / Skip).
Claude Code's own tool permissions are separate: even approved tools may still show Claude Code's permission prompt, and nothing here can bypass it. To stop those prompts, the player allows the tools in Claude Code (`/permissions`). Trivial lookups (one card, one rule) never trigger this onboarding.

### Step 1: approve tools (before the first substantial research)
Detect without calling anything external: read the available tool list and group tools by capability. Show one table with the real tool or provider names:

| Capability | Tool found | Used for | Speed / cost | Notes |
|---|---|---|---|---|
| Card data, combos | e.g. MTG MCP (j4th, claude.ai connector) | facts, legality, printings, prices, combos | fast, light | primary source of truth |
| EDHREC stats | same MTG MCP | what decks play, with sample sizes | fast | some commanders return no data |
| Video transcripts | e.g. YouTube Transcript | creator deck techs, quoted with mm:ss | slower, uses more tokens (long transcripts) | YouTube sometimes blocks; one video at a time |
| Semantic discovery | e.g. Exa | finding deck techs, primers, articles | fast | may count against the provider's API quota/key |
| Web search + fetch | e.g. Parallel Search, or Claude Code's built-in web search | Reddit, forums, reading pages | medium | Reddit is reached through search |
| Scripts | uv | deck checks, exports, pages | fast, local | |

Add a status column once known: **detected** (listed, not tried) · **verified** (approved and a cheap test call gave a sensible answer) · **failed** (approved but the test or a real call failed; say the error) · **unavailable** (not installed). Then offer:
- **Recommended:** approve every relevant tool found, video transcripts first when available.
- **Customize:** pick tools or source categories (e.g. no videos, no Reddit, only MTG data).
- **Fast research:** MTG data and one search tool only; skip long transcripts and deep crawls.
- **No external research:** only card data the player supplies or what local scripts can check; say plainly that recommendations then rest on card data and Claude's judgment, without community or creator evidence, and that legality and prices can't be verified without a card-data source.
Use nothing external before this answer. After it, test each approved tool with one cheap call (the checks in the table below) and report detected → verified / failed. Save the approved tools (by capability, with the tool name) and anything excluded.

### Step 2: how future research should work (ask once, right after step 1)
- **Ask every time:** show the tools and a short plan before each substantial research task.
- **Ask when something changes (Recommended):** reuse approved tools without asking; confirm before using a new provider, a big change in plan (much deeper than usual, many videos), or a fallback to an unapproved tool.
- **Automatic:** use approved tools without a plan check; still never use an excluded or new provider without asking.

### Every substantial research task
- Announce it in one or two lines before starting: what you'll research, which tools you'll use (by name), how long it should take. With "ask every time", wait for a yes.
- Use only approved tools. If one fails, report it as failed, use an approved fallback, or ask before using an unapproved one (never silently).
- If a new research tool appears or an approved one disappears, mention it once and ask whether to approve it (any mode).

### Checks for "verified"
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

### Depth (independent of approval)
- **Comprehensive (Recommended):** every approved source: data, decklists, creator videos with timestamps, Reddit and forums, articles; about 5 to 15 minutes per commander.
- **Quick:** card data, EDHREC, one or two community threads, a video only if central; about 1 to 3 minutes.
- **Deep:** comprehensive plus tournament data, more decklists and smaller creators; for comparisons and contested questions; longer (often 15 to 30 minutes per subject).
- **Custom:** chosen source categories.
- **Skip:** no web research; card data and rules only, labelled as unresearched.

### Saved form
```yaml
research:
  approved:                     # capability: tool as named in Claude Code
    card_data: MTG MCP (j4th)
    edhrec: MTG MCP (j4th)
    combos: MTG MCP (j4th)
    transcripts: YouTube Transcript
    semantic_search: Exa
    web_search: Parallel Search
  excluded: [MTGGoldfish]       # tools or sources never to use
  approval: on_change           # every_time | on_change | automatic
  depth: comprehensive          # quick | comprehensive | deep | custom | skip
  prefer: [EDHREC, Reddit]
  status: {card_data: verified, transcripts: failed}
  checked: 2026-11-04
```
`companion.py research` prints the saved choices (and a project's overrides) so they can be reviewed; the player can change any of them by saying so or through setup.

## Reliability (lessons from real runs)
- **Card data in batches, once.** For cards you already know (from lists, transcripts, threads), look them up together: `uv run --script "${CLAUDE_PLUGIN_ROOT}/skills/audit/scripts/deck_check.py" names.txt --cards-only --json <project>/cards.json` (75 cards per request, bounded retries on 429 and 5xx). Reuse `cards.json` instead of looking the same card up again. Use Scryfall **search** only to discover new cards (theme pools, commander-text searches), with targeted queries.
- **Respect rate limits.** Scryfall search/named/collection allow about 2 requests a second; a 429 means a 30-second lockout, so wait (the helper does) rather than retry immediately. Never hammer an endpoint in a loop.
- **Check MCP results before trusting them.** Treat a result as unreliable when it contradicts itself or the authority: EDHREC numbers where a card's deck count exceeds the commander's total, `total_decks: 0` next to non-zero card counts, inclusion % that doesn't match count/total, generic staples returned for a specific commander, or card facts that differ from Scryfall. Cross-check with the source site (the EDHREC page itself, Scryfall) and record the conflict; never present the contradictory number as fact.
- **Failing endpoints.** On a 502/503 or timeout, retry at most once, then mark that tool or endpoint as failing for the rest of the session (`methodology.tools_failed`), switch to an approved fallback, and don't call it again until the player asks or a later session starts. Say what the failure cost (e.g. "no EDHREC numbers for Azula; lists and threads only").
- **No invented URLs.** Don't guess EDHREC (or any) page paths. Find the page through search, or build it only from a pattern you've just verified loads (e.g. the commander page `edhrec.com/commanders/<slug>` with the slug from that page or a search result), and record the URL actually opened.
- **Gaps are findings.** Every failure, fallback and the evidence it left missing goes in `methodology.tools_failed` and `gaps`, and into the reply.

## Parallel research (only when subjects are independent)
- One **card-data worker** owns Scryfall: theme pools, printings and art, commander checks, and the batched `cards.json`. It runs first or alongside, and the others read its file.
- The other workers own **YouTube deck techs, decklists, Reddit/forums and articles**, and add card names they find to the card-data list (or look them up in `cards.json`) instead of querying Scryfall themselves.
- Each worker writes its part file in the research.json format with its own ID range and a status (`complete` / `partial: <what's missing>`), recorded in `methodology.workers`.
- **Research isn't complete until every worker has finished and its part validates:** wait for all of them, merge, run `companion.py validate`, and resolve or list what failed. A worker that died or returned partial work is reported as a gap, not hidden.

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
