# MCP server design and existing MTG servers

Research for turning `mtgdb.py` into an MCP server shipped inside the `mtg` plugin.
All sources accessed 2026-11-03. Items marked **(unconfirmed)** were not verified against a primary source.

## Summary

- Two of our slow or fragile data paths now have official bulk files. Scryfall publishes `oracle_tags` (about 6 MB) as daily bulk data, so `tags-sync` no longer has to page `otag:` searches for 2 to 3 minutes. Commander Spellbook publishes every combo as `variants.json.gz`, so `combos` can run locally. Both changes remove most of the need for long-running MCP jobs.
- Keep the tool count small and shaped around workflows, such as "validate this deck", not one tool per CLI subcommand. Return concise output by default, let the caller ask for detail, and write error messages that tell the model what to do next.
- Claude Code caps MCP output at 25,000 tokens and saves text results over 50,000 characters to a file. A tool can raise that cap for itself with `_meta["anthropic/maxResultSizeChars"]`. A call that runs longer than 2 minutes moves to the background on its own.
- Build with the official Python SDK v2 (`MCPServer`, formerly `FastMCP`), run it over stdio with `uv run`, declare it in the plugin's `.mcp.json`, and keep data in `${CLAUDE_PLUGIN_DATA}`.
- Do not rebuild `j4th/mtg-mcp-server`. It already covers live lookups, EDHREC, Moxfield, 17Lands and rules. Our own server should hold only what nobody else offers: the local index with every printing, deterministic deck checks, the simulator and swap tests, and claim auditing.

---

## Part A. MCP server best practice

### A1. Tool design

**How many tools.** Agents get confused when tools overlap or have a vague purpose. Anthropic recommends a few well-chosen tools that match natural subdivisions of a task, over thin wrappers around every endpoint. Its examples: one `schedule_event` tool in place of `list_users` + `list_events` + `create_event`, one `search_logs` in place of `read_logs`, and one `get_customer_context` in place of three getters. https://www.anthropic.com/engineering/writing-tools-for-agents

**Context cost of definitions.** Every loaded tool definition costs context, and intermediate results pass back through the model each time. https://www.anthropic.com/engineering/code-execution-with-mcp. Claude Code softens this with tool search, which is on by default for recent models: only tool names and server instructions load at startup, and full definitions load when needed. Server instructions and upfront tool descriptions are capped at 4,096 characters each. Descriptions loaded through tool search are capped at 16,384 characters. A tool can ask to load upfront with `_meta["anthropic/alwaysLoad"]`. https://code.claude.com/docs/en/mcp. **Design effect:** the server `instructions` field is what tells Claude when to search for our tools, so it has to say plainly "card facts, legality, deck validation, Commander".

**Naming.** Tool names are 1 to 64 characters, case-sensitive, made of letters, digits, `_`, `-`, `.` and `/` (SEP-986, final). https://modelcontextprotocol.io/seps/986-specify-format-for-tool-names.md. Prefix names by service or resource (for example `asana_projects_search`). Prefix and suffix schemes score differently in evals, so pick one by testing. Name parameters without ambiguity, such as `user_id` and not `user`. https://www.anthropic.com/engineering/writing-tools-for-agents. Servers SHOULD return `tools/list` in a fixed order so clients and prompt caches can reuse it (2026-07-28 changelog). https://modelcontextprotocol.io/specification/2026-07-28/changelog

**Input schemas.** Write each description the way you would explain the tool to a new hire. Make niche formats, such as Scryfall query syntax, explicit, and enforce inputs with strict models. https://www.anthropic.com/engineering/writing-tools-for-agents. The Python SDK builds the input schema from type hints and the docstring. https://py.sdk.modelcontextprotocol.io/

**Output.**
- Return only high-signal fields. Prefer names the model can read over opaque IDs, because resolving UUIDs to readable names reduced hallucinations in Anthropic's evals. https://www.anthropic.com/engineering/writing-tools-for-agents
- Offer a `response_format` enum (`concise` or `detailed`). In Anthropic's example the concise form used about a third of the tokens. Concise output leaves IDs out, and detailed output includes the IDs that later calls need. Same source.
- Use structured content: a tool can declare an `outputSchema`, return `structuredContent`, and SHOULD also return the same JSON as a text block for backwards compatibility. If an output schema is declared, results MUST conform to it. https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- From 2026-07-28 on, every result carries a `resultType` (`complete` or `input_required`). The SDK fills this in for us. https://modelcontextprotocol.io/specification/2026-07-28/changelog

**Errors that help recovery.** The protocol has two error channels. Use JSON-RPC protocol errors for an unknown tool or malformed arguments. Use `isError: true` inside the result for API failures, bad input data and business-logic failures, because only the second kind reaches the model so it can correct itself. https://modelcontextprotocol.io/specification/2025-06-18/server/tools. Error text should name the specific fix, for example "card 'Sol Rng' not found; did you mean 'Sol Ring'? Call normalize first", and not an opaque code or a traceback. https://www.anthropic.com/engineering/writing-tools-for-agents. Claude Code keeps only the first and last 5,000 characters of error text longer than about 11,000 characters, so keep errors short. https://code.claude.com/docs/en/mcp

**Pagination and token limits.**
- Use pagination, range selection, filtering or truncation with sensible defaults. If you truncate, tell the agent how to narrow the query. https://www.anthropic.com/engineering/writing-tools-for-agents
- Claude Code warns above 10,000 tokens and caps output at 25,000 tokens by default (`MAX_MCP_OUTPUT_TOKENS`). It saves text results over 50,000 characters to a file. A tool can raise its own threshold, up to 500,000 characters, with `_meta["anthropic/maxResultSizeChars"]`. https://code.claude.com/docs/en/mcp
- **Design effect:** a resolved 100-card deck with full Oracle text can exceed 10k tokens. Default to returning counts, problems and card names, and give full card text only on request.

**Write-up of evaluations.** Anthropic recommends building realistic eval tasks with verifiable answers and tracking how many calls, tokens and errors each tool causes. Many redundant calls point to a pagination problem, and many invalid-parameter errors point to unclear descriptions. https://www.anthropic.com/engineering/writing-tools-for-agents. Our `selftest` golden facts are a starting point for this.

### A2. Tools, resources and prompts

| Primitive | Who controls it | Use it for | Source |
|---|---|---|---|
| Tool | The model decides when to call it | Anything the model must act on or compute: card lookup, validate, simulate, sync | https://modelcontextprotocol.io/specification/2025-06-18/server/tools |
| Resource | The host app decides what to include, often through a picker | Read-only context addressed by URI, such as the banned list, Game Changers list, bracket rules, or a saved deck | https://modelcontextprotocol.io/specification/2025-06-18/server/resources |
| Prompt | The user picks it, usually as a slash command | Reusable workflow starters, such as "review this deck" | https://modelcontextprotocol.io/specification/2025-06-18/server/prompts |

How this applies here:
- Claude does not read resources by itself the way it calls tools, so anything the agent must fetch on its own has to be a tool. Resources fit reference data the user attaches, and a tool can return a `resource_link` that points to one. https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- The plugin already ships skills and slash commands, so MCP prompts would duplicate them. Skip prompts. (This is a judgement call, not a sourced rule.)

### A3. Python stack, packaging and long jobs

**SDK choice.**
- The official `mcp` Python SDK v2 is stable. v2.0.0 shipped on 2026-07-28 and v2.3.0 is current. `pip install mcp` now installs 2.x. The old `FastMCP` class is now `MCPServer` (`from mcp.server import MCPServer`), with the same decorator API. It speaks the 2026-07-28 protocol and still serves 2025-era clients. Its stdio transport sends stray `print` output to stderr, which protects the JSON-RPC stream. Python 3.11+. https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0, https://py.sdk.modelcontextprotocol.io/
- The standalone FastMCP (PrefectHQ/fastmcp, Apache-2.0, about 28k stars, v3.x) is a separate, more feature-rich framework, and `j4th/mtg-mcp-server` uses it. https://github.com/PrefectHQ/fastmcp
- **Recommendation:** use the official SDK. One fewer dependency, and it tracks the spec first. Pin `mcp>=2.3,<3`.

**Launch over stdio with uv.** Plugins declare servers in `.mcp.json` at the plugin root or inline in `plugin.json`, and Claude Code starts them when the plugin is enabled. `${CLAUDE_PLUGIN_ROOT}` (install path, which changes on update) and `${CLAUDE_PLUGIN_DATA}` (`~/.claude/plugins/data/<id>/`, kept across updates, deleted on uninstall unless `--keep-data`) are substituted in `command`, `args` and `env`, and exported to stdio servers. https://code.claude.com/docs/en/plugins-reference, https://code.claude.com/docs/en/mcp. A sketch:

```json
{ "mcpServers": { "mtgdb": {
    "command": "uv",
    "args": ["run", "--project", "${CLAUDE_PLUGIN_ROOT}/server", "mtgdb-mcp"],
    "env": { "MTG_CACHE": "${CLAUDE_PLUGIN_DATA}" },
    "timeout": 600000 } } }
```

**Where data lives.** Today the default is `~/.cache/mtg/cards.sqlite`. `${CLAUDE_PLUGIN_DATA}` is the documented home for caches, but it is deleted on uninstall. **Decision needed:** keep the user cache (it survives reinstalls and is shared with the CLI) or move to plugin data. Keep `MTG_CACHE` as the override either way. Never write under `${CLAUDE_PLUGIN_ROOT}`. https://code.claude.com/docs/en/plugins-reference

**MCPB.** A plugin's `mcpServers` can point at a `.mcpb` bundle, which Claude Code extracts into `.mcpb-cache/`. https://code.claude.com/docs/en/plugins-reference. MCPB manifest 0.4 adds a `uv` server type: dependencies go in `pyproject.toml`, the host installs them, and the bundle is about 100 KB. https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md, https://github.com/modelcontextprotocol/mcpb/blob/main/examples/hello-world-uv/manifest.json. One mirror of the manifest docs labels `uv` as experimental. **(unconfirmed which label is current)** MCPB only matters if we also want a one-click Claude Desktop install. For Claude Code, a plain `.mcp.json` is simpler.

**Long-running jobs (index download, price sync).**
- Progress: the client sends a `progressToken`, and the server MAY send `notifications/progress` with `progress`, an optional `total` and a `message`. https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/progress. In the SDK this is `await ctx.report_progress(done, total)` with a `ctx: Context` parameter. https://py.sdk.modelcontextprotocol.io/v2/migration/
- Claude Code moves any main-conversation MCP call still running after 2 minutes into a background task. Claude gets a task ID and keeps working, `/tasks` shows the latest progress the server reported, and the result comes back as a notification (`CLAUDE_CODE_MCP_AUTO_BACKGROUND_MS` changes the threshold). Progress notifications do not extend the per-server `timeout`. https://code.claude.com/docs/en/mcp
- Server-side tasks are now an official extension, `io.modelcontextprotocol/tasks`. They were experimental core in 2025-11-25 and moved out in 2026-07-28. Claude Code supports them only on 2026-07-28 connections, only from the main conversation and not from subagents. https://modelcontextprotocol.io/specification/2026-07-28/changelog, https://code.claude.com/docs/en/mcp
- **Design effect:** with tags and combos moving to bulk files (Part B), the remaining long jobs are `index` (about 80 MB `default_cards`) and `prices-sync`. A plain tool with `report_progress` plus Claude Code's automatic backgrounding is enough. Skip the tasks extension. It adds a state machine, and our vault subagents could not use it anyway. Keep `index` available as a CLI command so a first-time setup does not depend on an MCP call.

### A4. Security and anti-patterns

- Servers MUST validate all tool inputs, apply access control, rate-limit invocations, and sanitize outputs. https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- Tool names and descriptions are instructions the model reads. Keep them strictly about the tool, because hidden directives are "tool poisoning". Do not change tool definitions after install without reason. https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/local-server-security
- Treat fetched third-party text (Moxfield deck descriptions, EDHREC pages, transcripts) as untrusted data in tool results. Return it as data fields and never echo it into instructions. Same source, under the "prompt injection in untrusted content" threat.
- Do not shell out with user-supplied strings, such as deck URLs or file paths. Command injection through URLs is a listed attack. https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices
- File-path inputs (`collection import`, deck files): restrict them to the project dir or plugin data, and refuse path traversal. (Inferred from the "overcollecting server" guidance above.)
- Mark destructive or slow tools honestly with annotations (`readOnlyHint`, `destructiveHint`, `openWorldHint`). Clients must treat annotations as untrusted unless the server is trusted, so they help but do not enforce anything. https://modelcontextprotocol.io/specification/2025-06-18/server/tools. Claude Code can force an approval on every call with `_meta["anthropic/requiresUserInteraction"]: true`. https://code.claude.com/docs/en/mcp. Use it on nothing except perhaps a full re-index.
- Never print to stdout in a stdio server. SDK v2 redirects it, but subprocesses we spawn should still log to stderr. https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0
- Anti-patterns from the sources above: one tool per REST endpoint, unbounded list output, UUIDs in place of names, tracebacks as errors, and the same feature exposed under two names.

---

> **Correction (2026-11-03):** j4th's `config.py` and `.env.example` turn EDHREC, Moxfield, Rules, bulk data and 17Lands on by default. "Behind a flag" below means they *can* be switched off, not that they start off.

## Part B. Existing MTG MCP servers and data sources

### B1. Survey of existing servers

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

I found no standalone, maintained Commander Spellbook MCP or MTGJSON MCP. Both are covered inside j4th's server (Spellbook) or not at all (MTGJSON). The `gh search` queries were "mtg mcp", "scryfall mcp", "edhrec mcp", "commander spellbook mcp", "mtgjson mcp" and "magic the gathering mcp". Many other repos have 0 stars and are omitted.

**What nobody offers.** None of the surveyed servers offers any of the following: a full local index with every printing (j4th's bulk mode uses `oracle_cards`, one printing per card; its README says the bulk download is about 30 MB, which matches `oracle_cards`), printing selection by theme or price, Game Changers and bracket checks run against a local list, budget validation, `simulate` (on-curve probability), `swaptest`, `theme-pool`, `diff`, claim-ledger auditing, or collection-aware builds. This is from the READMEs only; I did not read the code. **(unconfirmed beyond the READMEs)**

### B2. Data source terms

**Scryfall**
- Every request to `api.scryfall.com` MUST send an accurate `User-Agent` (app name and version, not the library default) and an `Accept` header. https://scryfall.com/docs/api
- Hard rate limits: `/cards/search`, `/cards/named`, `/cards/random` and `/cards/collection` allow 2 per second. `/cards/manifest` allows 10 per minute. Everything else allows 10 per second. `*.scryfall.io` file hosts have no limit. A 429 locks you out for 30 seconds, and ignoring 429s can get the app banned. https://scryfall.com/docs/api/rate-limits
- Cache data for at least 24 hours. For fast lookups of many names, prices or images you MUST use bulk data. Prices change once a day. Gameplay data rarely changes, so a weekly download is enough. https://scryfall.com/docs/api/rate-limits
- Bulk files are gzipped JSONL. Bulk prices are "dangerously stale after 24 hours". https://scryfall.com/docs/api/bulk-data
- **New since our design:** Tagger tags are official bulk files, `oracle_tags` and `art_tags`, updated daily. https://scryfall.com/docs/api/tags. I confirmed both in `GET /bulk-data` today: `oracle_tags` is 6.1 MB and `default_cards` is 80.8 MB. Our `tags-sync` currently pages `otag:` searches through `/cards/search` at 2 per second, which is the 2 to 3 minute job. Switching to the bulk file makes it a few seconds and stops loading the API.
- Data and images are free to use for building Magic software under the Fan Content Policy. Image rules: do not crop off or cover the artist or copyright, do not distort or recolour, do not watermark, and do not imply the card is not from Wizards. If you show `art_crop`, list the artist and copyright alongside it. https://scryfall.com/docs/api
- New image formats `display`, `crop` and `art` (WEBP) replace `large`, `border_crop` and `art_crop`. https://scryfall.com/docs/api/images. Check whether `contact-sheet` and the pages use the old names.

**EDHREC**
- EDHREC has no public or documented API. Its JSON endpoints (`json.edhrec.com`) are the ones the website itself uses, found by inspecting network traffic. https://github.com/sigiltenebrae/edhrec_scraper/issues/1. nathanmartins' README calls them "unofficial JSON endpoints". https://github.com/nathanmartins/mtg-mcp
- The terms grant a licence "solely for your own personal, noncommercial use". The acceptable-use policy forbids using "software or automated agents or scripts … to generate automated searches, requests, or queries to the Site". https://edhrec.com/terms
- EDHREC's 429 page says "Please limit your requests to 1 per second … Implement caching. Contact us to lift the ban". https://beta.edhrec.com/429
- **Position:** any automated EDHREC access breaks the literal terms. Both existing servers do it anyway, and j4th puts it behind a flag. We should not build our own EDHREC client. If the user wants EDHREC data, they can enable it in j4th's or nathanmartins' server, and the risk stays with that choice.

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
- The usual disclaimer, used by EDHREC, Spellbook and j4th, reads: "unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC." https://edhrec.com/terms, https://github.com/j4th/mtg-mcp-server. Put it in our README and server `instructions`.

### B3. Recommendation: combine

**Build our own small MCP server, and keep j4th's server as the companion for live and community data.** Do not fork it and do not take it as a dependency.

Reasons:
1. **Our value is the local deterministic layer, and no existing server has it.** That layer is the full printings index, the hard deck checks (legality, identity, Game Changers, bracket, budget), `simulate`, `swaptest`, `diff`, `theme-pool` and `audit-claims`. Those are the accuracy guarantees in our README. Wrapping them as MCP tools is new work, not duplicated work.
2. **j4th already covers the breadth, and it is maintained.** It covers EDHREC, Moxfield, 17Lands, Goldfish, rules and live Scryfall, with MIT licence, CI and active releases. It is already connected here. Rebuilding that means taking on the scraping risk (EDHREC terms, Moxfield's reverse-engineered API) for no gain.
3. **Taking it as a dependency would cost more than it saves.** It brings FastMCP 3.x and 69 tools. Its bulk mode keeps one printing per card, which our printing logic cannot use. Forking would make us maintain seven upstream integrations.
4. **Drop overlap on our side.** Remove `search` (live Scryfall search) and the live `combos` call from the MCP surface, or keep them CLI-only. Route those questions to j4th, or answer combos from the local Spellbook bulk file. Two tools that answer the same question confuse agents. https://www.anthropic.com/engineering/writing-tools-for-agents
5. **Keep the CLI.** The hook, vault subagents and `selftest` already call `mtgdb.py`. The MCP server should import the same functions, so the CLI stays the test surface and the fallback when MCP is not connected.

Suggested first tool set (about 8 tools, each a workflow and not a subcommand):

| Tool | Wraps |
|---|---|
| `mtg_card` | `card` + `printings` + tags, with `response_format` |
| `mtg_resolve_names` | `normalize` (batch) |
| `mtg_deck_check` | `resolve` + `validate` + `stats` + local combos |
| `mtg_deck_swap` | `swaptest` + `diff` |
| `mtg_deck_profile` | `profile` |
| `mtg_simulate` | `simulate` |
| `mtg_theme_pool` | `theme-build` + `theme-pool` |
| `mtg_data_status` / `mtg_data_sync` | `info`, `selftest`, and `index` / tags / prices / spellbook bulk refresh with progress |

`audit-claims` and `hook` should stay CLI-only, because the PostToolUse hook calls them.

### Unconfirmed items

- Whether MCPB's `uv` server type is still labelled experimental (sources disagree).
- The licence of Commander Spellbook's combo data, separate from its MIT code, and how often `variants.json.gz` refreshes.
- Whether price vendors attach terms to MTGJSON price data beyond its MIT licence.
- What existing servers lack (B1) is based on READMEs, not code review.
- j4th's tool, prompt and resource counts are taken from its README.
