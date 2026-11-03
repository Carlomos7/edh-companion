# mtg-skills: Commander deckbuilding with Claude Code

Build, review, price and share Magic: The Gathering Commander decks **together with Claude**, the way you want them. Claude asks what you enjoy, what your table plays and how you like to spend, shows you a plan before it fills 99 slots, and lets you choose wherever it comes down to taste. Every card fact is checked against current data, never typed from memory.

## What you get

One plugin, `mtg`: deckbuilding, research and multi-deck vault skills, plus the `mtgdb` MCP server with the card data and deck checks.

**Working with you**
- **Intake first:** starting point, bracket and hard lines (combos, extra turns, land destruction), what's fun for you, budget, and price style.
- **Price style:**
  - *budget:* cheapest copies, with cheaper alternatives offered
  - *balanced:* normal copies
  - *bling:* foils, borderless, Secret Lair, up to a per-card ceiling you set
- **Skeleton before the list:** the plan, role targets and key cards for you to approve or change.
- **Choices where taste matters:** win conditions, pet cards and close calls come to you as options.
- **Hand-back:** a Rule 0 summary for your table, all three price totals, a direct store link for every card, and an export in the format you need.

**Accurate data**
- **Card facts:** legality, color identity, Game Changers, printings and prices come from Scryfall's daily bulk data.
- **Roles:** Scryfall Tagger tags (ramp, draw, removal and more), not guesses.
- **Combos:** Commander Spellbook's full combo database, checked locally.
- **Rules:** the current Comprehensive Rules from Wizards, with their effective date.
- **Always current, or your choice:** Claude shows the date of every source at the start and offers to refresh. One sync takes about a minute.
- **Checks on every list:** card count, singleton, color identity, legality, Game Changers per bracket, combos, curve, mana sources, and a goldfish simulation of when you cast your commander.

**Sharing**
- **Import:** paste from Moxfield, Archidekt, MTG Arena or a plain list (section headers, partners and sideboards are understood), or link a Moxfield or Archidekt deck through the companion connector below.
- **Export:**
  - Moxfield/Archidekt with exact printings and foil marks, so their buy buttons pull the same copies
  - MTG Arena sections
  - plain names
  - CSV

## Quick start
1. **Install uv**, a small helper that runs the card-data tools (one time):
   - Windows: `winget install astral-sh.uv`
   - macOS: `brew install uv`
   - Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. **Install the plugin** in [Claude Code](https://code.claude.com):
   ```
   /plugin marketplace add Carlomos7/mtg-skills
   /plugin install mtg@carlomos7-mtg-skills
   ```
3. **Type `/mtg:build`** (or just say "build me a Krenko deck"). The first time, Claude offers to download the card data: about a minute and 400 MB of disk.

### Your first deck, step by step
A build is a conversation, usually 10 to 20 minutes. You can stop, change your mind or say "you pick" at any point.

1. **Data check.** Claude shows how fresh its card data and rules are and offers to refresh (one line; about a minute the first time).
2. **A few questions, as options to click.** Usually three short rounds:
   - where you're starting (a commander, colors, a favorite card, a deck to upgrade)
   - your table's power level (bracket 1 to 5) and anything you don't want to see (infinite combos, extra turns, land destruction)
   - what's fun for you, how you like to win, how much interaction
   - your budget, and your price style: budget, balanced, or bling
   - pet cards and cards you never want

   Your answers are saved to `deck-brief.md`, so you can edit them or pick up later.
3. **A plan before any list.** The deck's plan, roughly when it wins, how many lands, ramp, draw and removal, and 3 to 5 key cards. You say yes, or what to change.
4. **Filling the deck.** Claude picks the obvious parts (lands, basic ramp) and tells you what it picked. Where it comes down to taste, like win conditions, close calls and your pet-card slots, you get 2 to 4 options with the reason and price for each. In budget style you also get cheaper swaps for expensive cards.
5. **Checks.** Every version of the list is checked: 100 cards, singleton, colors, legality, bracket rules, combos, mana, and how often you'll have your commander out on time. Problems come back to you as choices, not silent changes.
6. **Hand-back.**
   - the list
   - a short plan
   - a Rule 0 summary to read out at your table
   - the price three ways (cheapest, as listed, bling), with a store link for every card
   - an export for Moxfield, Archidekt, Arena or a spreadsheet; import it into Moxfield or Archidekt to get a page you can share

### Commands
| Type | To |
|---|---|
| `/mtg:build` | start a new deck together |
| `/mtg:check` | check a deck: legal? bracket? weak spots? cost? |
| `/mtg:upgrade` | improve a deck you have |
| `/mtg:cheaper` | see what a deck costs and make it cheaper |
| `/mtg:share` | get a list ready for Moxfield, Archidekt, Arena or a spreadsheet |
| `/mtg:update-data` | see how fresh the card data and rules are, and refresh |

You don't need the commands: plain questions work too.

### Optional add-ons (recommended)
Everything above works on its own. These extra MCP servers make research richer. Claude uses them when they're installed and tells you when a check needed one that isn't. They run alongside the plugin with no conflicts.

| Add-on | What it adds | Install in Claude Code |
|---|---|---|
| [MTG MCP server](https://github.com/j4th/mtg-mcp-server) (j4th) | EDHREC popularity numbers, Moxfield and Archidekt deck links, Commander Spellbook bracket estimates | `claude mcp add mtg --scope user -- uvx mtg-mcp-server` |
| [YouTube transcripts](https://github.com/jkawamoto/mcp-youtube-transcript) | Deck techs from creators like The Command Zone, quoted with timestamps | `claude mcp add youtube-transcript --scope user -- uvx --from git+https://github.com/jkawamoto/mcp-youtube-transcript mcp-youtube-transcript` |
| Web search, e.g. [Parallel](https://parallel.ai) | Wizards announcements, tournament results, articles | `claude mcp add parallel-search --scope user --transport http https://search.parallel.ai/mcp` (Claude Code's built-in web search also works) |
| [TopDeck.gg](https://topdeck.gg) API key | Tournament standings for cEDH questions | free key from TopDeck.gg, set as the `TOPDECK_API_KEY` environment variable |

Using claude.ai or Claude Desktop too? The MTG server is also hosted: Settings → Connectors → Add custom connector → `https://mtg-mcp-server.fastmcp.app/mcp`. Connectors added there show up in Claude Code when you're signed in.

Restart Claude Code after adding one, then `/mcp` shows whether it connected.

## Use
- "Build me a B3 Krenko deck, I like going wide, under $150"
- "Here's my list (paste). What bracket is it and what should I cut?"
- "Make this deck cheaper" / "Show me the bling version, nothing over $40 a card"
- "Is Teferi's Protection worth it in my Elesh Norn deck? What's cheaper?"
- "Give me this list for Moxfield with the exact printings"
- "Does deathtouch work with trample?"
- `/mtg:commander-vault @vault-request.md` builds several commanders and brackets at once with research agents and an independent verifier, and renders them as one interactive page (copy `vault-request.md` into an empty folder and fill it in). Takes 30 minutes or more.

## How accuracy works
1. Computed facts only come from the local index (`mtgdb`), never from memory.
2. Names from pastes and videos are resolved to real cards before use.
3. Opinions (must-plays, traps) are logged with dated sources; vault runs audit and independently verify them.
4. Every suggested swap is re-checked before it's shown.
5. Anything that couldn't be checked is labelled as unverified.

## Data sources
- [Scryfall](https://scryfall.com) bulk data: cards, prices, rulings, Tagger tags
- [Commander Spellbook](https://commanderspellbook.com) combo data
- [Wizards of the Coast](https://magic.wizards.com/en/rules): Comprehensive Rules
- [MTGJSON](https://mtgjson.com) (optional): multi-vendor prices

This project is unofficial Fan Content permitted under the [Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy). Not approved or endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.

## Development
```bash
claude --plugin-dir ./plugins/mtg                                    # try local changes
claude plugin validate ./plugins/mtg
uv run plugins/mtg/scripts/mtgdb.py --help                           # the CLI behind the MCP tools
uv run plugins/mtg/scripts/mtgdb.py sync                             # all data sources
```
Tests (unit, MCP server over stdio, and a headless-browser test of the vault page):
```bash
uv run --with pillow --with ijson --with playwright --with "mcp>=2.3" python -m unittest discover -s tests
```
Behavior evals (cost real usage): see [plugins/mtg/evals/README.md](plugins/mtg/evals/README.md).

Research notes behind the design are in [docs/research](docs/research).

## License
[MIT](LICENSE)
