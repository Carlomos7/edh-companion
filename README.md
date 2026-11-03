# mtg-skills

[![test](https://github.com/Carlomos7/mtg-skills/actions/workflows/test.yml/badge.svg)](https://github.com/Carlomos7/mtg-skills/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Build Magic: The Gathering Commander decks together with Claude, the way you want them.**

A [Claude Code](https://code.claude.com) plugin. Claude asks what you enjoy, what your table plays and how you like to spend, shows you a plan before it fills 99 slots, and lets you choose wherever it comes down to taste. Every card fact (legality, colors, prices, Game Changers, combos, rules) is checked against current data, never typed from memory.

## Contents
- [Features](#features)
- [Quick start](#quick-start)
- [Your first deck](#your-first-deck)
- [Commands and examples](#commands-and-examples)
- [Build your own vault](#build-your-own-vault)
- [Optional add-ons](#optional-add-ons)
- [Keeping data current](#keeping-data-current)
- [Troubleshooting](#troubleshooting)
- [How it works](#how-it-works)
- [Contributing](#contributing)
- [Credits and license](#credits-and-license)

## Features
- **Built with you, not for you.** A few multiple-choice questions, a plan you approve, then options wherever it's a matter of taste.
- **Your budget, your way.** Every deck is priced three ways (cheapest, as listed, bling) with a direct store link for each card. Budget style offers cheaper cards that do the same job.
- **Always checked.** 100 cards, singleton, color identity, legality, bracket rules, Game Changers, combos, mana, and how often you'll have your commander out on time.
- **Current data, your call.** Card data, rules and combos come from Scryfall, Wizards and Commander Spellbook. Claude shows how fresh they are and offers to refresh.
- **Works with your tools.** Paste a list from Moxfield, Archidekt, MTG Arena or anywhere. Export back with exact printings, so Moxfield's and Archidekt's buy buttons pull the same copies.
- **Vaults.** Full decks for several commanders and power levels on one interactive page.

## Quick start
**You need:** Claude Code, [uv](https://docs.astral.sh/uv/) (a small helper that runs the card-data tools; it installs its own Python), and about 500 MB of disk for card data.

1. **Install uv** (one time):
   - Windows: `winget install astral-sh.uv`
   - macOS: `brew install uv`
   - Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. **Install the plugin** from inside Claude Code:
   ```
   /plugin marketplace add Carlomos7/mtg-skills
   /plugin install mtg@carlomos7-mtg-skills
   ```
3. **Restart Claude Code and type `/mtg:build`**, or just say "build me a Krenko deck". The first time, Claude offers to download the card data (about a minute).

## Your first deck
A build is a conversation, usually 10 to 20 minutes. You can stop, change your mind or say "you pick" at any point.

1. **Data check.** One line showing how fresh the card data and rules are, with an offer to refresh.
2. **A few questions, as options to click.** Usually three short rounds:
   - where you're starting (a commander, colors, a favorite card, a deck to upgrade)
   - your table's power level (bracket 1 to 5) and anything you don't want to see (infinite combos, extra turns, land destruction)
   - what's fun for you, how you like to win, how much interaction
   - your budget and price style: **budget** (cheapest copies), **balanced**, or **bling** (foils, borderless, Secret Lair, up to a per-card ceiling)
   - pet cards and cards you never want

   Your answers are saved to `deck-brief.md`, so you can edit them or pick up later.
3. **A plan before any list.** The deck's plan, roughly when it wins, how many lands, ramp, draw and removal, and 3 to 5 key cards. You say yes, or what to change.
4. **Filling the deck.** Claude picks the obvious parts (lands, basic ramp) and says what it picked. Where it's taste (win conditions, close calls, your pet-card slots) you get 2 to 4 options, each with its reason and price.
5. **Checks.** Every version of the list is checked. Problems come back to you as choices, not silent changes.
6. **Hand-back.**
   - the list and a short plan
   - a Rule 0 summary to read out at your table
   - the price three ways, with a store link for every card
   - an export for Moxfield, Archidekt, MTG Arena or a spreadsheet (import it into Moxfield or Archidekt for a page you can share)

## Commands and examples
| Type | To |
|---|---|
| `/mtg:build` | start a new deck together |
| `/mtg:check` | check a deck: legal? bracket? weak spots? cost? |
| `/mtg:upgrade` | improve a deck you have |
| `/mtg:cheaper` | see what a deck costs and make it cheaper |
| `/mtg:share` | get a list ready for Moxfield, Archidekt, Arena or a spreadsheet |
| `/mtg:update-data` | see how fresh the card data and rules are, and refresh |
| `/mtg:commander-vault` | build a vault (see below) |

You don't need the commands; plain requests work too:
- "Build me a bracket 3 Krenko deck, I like going wide, under $150"
- "Here's my list (paste). What bracket is it and what should I cut?"
- "Show me the bling version, nothing over $40 a card"
- "Is Teferi's Protection worth it in my Elesh Norn deck? What's cheaper?"
- "Give me this list for Moxfield with the exact printings"
- "Does deathtouch work with trample?"

## Build your own vault
A vault is one page with full decks for several commanders at the power levels you play, plus card rankings, cards to consider and price ladders. Any theme works, or none.

1. Open Claude Code in an empty folder (the vault's files go there).
2. Copy the block below, change the answers after each colon, and delete any line you don't need (its default is used).
3. Type `/mtg:commander-vault`, a space, paste your block, and press Enter.

```text
Commanders: Krenko, Mob Boss; Edgar Markov
Theme: none
Brackets: 2 and 3, open on 3
Budget per deck: $150
Price style: balanced
Hard lines: no infinite combos
Collection: none
Extras: alternative commanders
```

| Line | What to put | Default |
|---|---|---|
| Commanders | names, or "the 6 most-built Dragon commanders on EDHREC" | (required) |
| Theme | a franchise, tribe or art style, e.g. "Lord of the Rings", "vampires" | none |
| Brackets | which power levels to build, and which the page opens on | your bracket plus one above |
| Budget per deck | e.g. "$150" | no limit, price always shown |
| Price style | budget, balanced, or bling (with a per-card ceiling) | balanced |
| Hard lines | what you never want: infinite combos, extra turns, land destruction, stax | what the bracket allows |
| Collection | paste a list, or a CSV path from Moxfield, Archidekt or ManaBox | none |
| Extras | alternative commanders, collection planner, splitting a pile between players | none |

Claude asks about anything unclear, shows the plan and a cost estimate, then builds. Expect 30 minutes or more; if you stop, run the same thing again in the same folder and it resumes. The page is published privately to your claude.ai account when you're signed in, otherwise saved as files you open in a browser. Every option (theme strictness, must-include cards, card labels, look) is in the [full request template](vault-request.md).

## Optional add-ons
Everything above works on its own. These MCP servers make research richer: popularity numbers, deck links, creator videos and news. Claude uses them when they're installed and says when a check needed one that isn't. Card facts and deck checks always come from the plugin's own data, even when an add-on has a similar tool.

| Add-on | What it adds | Install in Claude Code |
|---|---|---|
| [MTG MCP server](https://github.com/j4th/mtg-mcp-server) (j4th) | EDHREC popularity numbers, Moxfield deck links, Commander Spellbook bracket estimates | `claude mcp add mtg --scope user -- uvx mtg-mcp-server` |
| [YouTube transcripts](https://github.com/jkawamoto/mcp-youtube-transcript) | Deck techs from creators like The Command Zone, quoted with timestamps | `claude mcp add youtube-transcript --scope user -- uvx --from git+https://github.com/jkawamoto/mcp-youtube-transcript mcp-youtube-transcript` |
| Web search, e.g. [Parallel](https://parallel.ai) | Wizards announcements, tournament results, articles | `claude mcp add parallel-search --scope user --transport http https://search.parallel.ai/mcp` (Claude Code's built-in web search also works) |

- **Install the MTG server one way, not both:** the command above, or (if you also use claude.ai or Claude Desktop) the hosted connector: Settings → Connectors → Add custom connector → `https://mtg-mcp-server.fastmcp.app/mcp`. Connectors appear in Claude Code when you're signed in with a Claude account (not an API key). Having both loads every tool twice.
- Restart Claude Code after adding one; `/mcp` shows whether it connected.

## Keeping data current
| What | Source | Refresh |
|---|---|---|
| Cards, legality, bans, Game Changers, prices | Scryfall daily bulk data | weekly is plenty |
| Card roles (ramp, draw, removal...) and rulings | Scryfall Tagger and rulings files | monthly |
| Combos | Commander Spellbook | weekly |
| Comprehensive Rules | Wizards' rules page | when a new set releases |
| Vendor prices (optional: Card Kingdom, Cardmarket, buylists) | MTGJSON | when you want them |

Claude checks these at the start of each deck and offers a refresh. To do it yourself: `/mtg:update-data`, or say "refresh the card data". Vendor prices: "sync vendor prices" (about 300 MB more disk).

**Update the plugin:** `/plugin marketplace update carlomos7-mtg-skills`, then restart Claude Code.
**Uninstall:** `/plugin uninstall mtg@carlomos7-mtg-skills`, then delete the data folder `~/.cache/mtg` (Windows: `%USERPROFILE%\.cache\mtg`).

**Privacy:** the plugin's tools only download public data (Scryfall, Commander Spellbook, Wizards, and MTGJSON if you ask) and keep your decks, answers and collection on your computer. Vault pages are published privately to your own claude.ai account, and add-ons you install follow their own terms.

## Troubleshooting
| Problem | Fix |
|---|---|
| Claude says the deck tools aren't available | Install uv (Quick start step 1), then restart Claude Code. `/mcp` should list `plugin:mtg:mtgdb` as connected. |
| "No card index yet" | Say "download the card data" or run `/mtg:update-data` (about a minute). |
| A brand-new card isn't found | Refresh the data. A card revealed in the last day or so may not be in Scryfall's daily file yet; Claude says so instead of guessing. |
| A pasted deck has unrecognized lines | Claude lists them and suggests the closest real card names. Check spelling, or paste the site's export instead of copying from a web page. |
| An add-on check "didn't run" | That add-on isn't installed or didn't connect; see [Optional add-ons](#optional-add-ons). Everything else still works. |
| Card images fail on a vault page (Windows) | Update the plugin; downloads use an up-to-date certificate bundle. |

## How it works
- **Skills** (`plugins/mtg/skills/`) hold the workflow: deckbuilding with intake and approval, research rules and sources, the multi-agent vault, and the short `/mtg:*` commands.
- **The `mtgdb` MCP server** (`plugins/mtg/scripts/server.py`) serves card facts and deck checks from a local SQLite index built from official bulk files. The same code runs as a command-line tool (`mtgdb.py`), so the tools, the hook and the tests can't disagree.
- **A hook** validates vault decks and research logs the moment they're written, and only runs for files in a `vault/` folder.
- **Accuracy:** card names from pastes and videos are matched to real cards before use; opinions need two independent dated sources; vault work is re-checked by a separate verifier; anything unchecked is labelled.

Design notes and sources are in [docs/research](docs/research).

## Contributing
Issues and pull requests are welcome.

```bash
claude --plugin-dir ./plugins/mtg              # try local changes
claude plugin validate --strict ./plugins/mtg  # check the plugin
uv run plugins/mtg/scripts/mtgdb.py --help     # the CLI behind the MCP tools
uv run plugins/mtg/scripts/mtgdb.py sync       # download all data sources
```
Tests (unit, MCP server over stdio, and a headless-browser test of the vault page):
```bash
uv run --with pillow --with ijson --with certifi --with playwright --with "mcp>=2.3" python -m unittest discover -s tests
```
Behavior evals use real Claude runs and cost usage: see [plugins/mtg/evals/README.md](plugins/mtg/evals/README.md). When something goes wrong in a real session, add an eval case for it.

## Credits and license
Card data from [Scryfall](https://scryfall.com) (cards, prices, rulings, Tagger tags), combos from [Commander Spellbook](https://commanderspellbook.com), rules from [Wizards of the Coast](https://magic.wizards.com/en/rules), optional vendor prices from [MTGJSON](https://mtgjson.com). Thanks to all of them for publishing open data.

This project is unofficial Fan Content permitted under the [Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy). Not approved or endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.

Code is [MIT](LICENSE) licensed. Made by [Carlomos7](https://github.com/Carlomos7).
