# mtg-skills: Commander deckbuilding with Claude Code

Build, review, price and share Magic: The Gathering Commander decks **together with Claude**, the way you want them. Claude asks what you enjoy, what your table plays and how you like to spend, shows you a plan before it fills 99 slots, and lets you choose wherever it comes down to taste. Every card fact is checked against current data, never typed from memory.

## What you get

| Plugin | What it does |
|---|---|
| `mtg` | Skills for deckbuilding, research and multi-deck vaults, plus the `mtgdb` MCP server with the card data and deck checks |
| `mtg-pages` (optional) | Turns decks into an interactive page (3D card viewer, charts, filters), published as an artifact or saved as HTML |

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
   Optional deck pages: `/plugin install mtg-pages@carlomos7-mtg-skills`
3. **Type `/mtg:build`** (or just say "build me a Krenko deck"). The first time, Claude offers to download the card data: about a minute and 400 MB of disk.

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

**Recommended companion:** [j4th/mtg-mcp-server](https://github.com/j4th/mtg-mcp-server) for EDHREC data, Moxfield and Archidekt links, and Commander Spellbook bracket estimates.

## Use
- "Build me a B3 Krenko deck, I like going wide, under $150"
- "Here's my list (paste). What bracket is it and what should I cut?"
- "Make this deck cheaper" / "Show me the bling version, nothing over $40 a card"
- "Is Teferi's Protection worth it in my Elesh Norn deck? What's cheaper?"
- "Give me this list for Moxfield with the exact printings"
- "Does deathtouch work with trample?"
- `/mtg:commander-vault @vault-request.md` builds several commanders and brackets at once with research agents and an independent verifier (copy `vault-request.md` into an empty folder and fill it in).

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
claude --plugin-dir ./plugins/mtg --plugin-dir ./plugins/mtg-pages   # try local changes
claude plugin validate ./plugins/mtg
uv run plugins/mtg/scripts/mtgdb.py --help                           # the CLI behind the MCP tools
uv run plugins/mtg/scripts/mtgdb.py sync                             # all data sources
```
Tests (unit, MCP server over stdio, and a headless-browser page test):
```bash
uv run --with pillow --with ijson --with playwright --with "mcp>=2.3" python -m unittest discover -s tests
```
Behavior evals (cost real usage): see [plugins/mtg/evals/README.md](plugins/mtg/evals/README.md).

Research notes behind the design are in [docs/research](docs/research).

## License
[MIT](LICENSE)
