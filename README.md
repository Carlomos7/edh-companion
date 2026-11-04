# mtg-skills

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Build Magic: The Gathering Commander decks together with Claude, the way you want them.**

By [Carlomos7](https://github.com/Carlomos7).

A [Claude Code](https://code.claude.com) plugin. Claude asks what you enjoy, what your table plays and how you like to spend, shows you a plan before it fills 99 slots, and lets you choose wherever it comes down to taste. Every card fact (legality, colors, prices, Game Changers, combos, rules) is checked against current data, never typed from memory.

## Contents
- [Features](#features)
- [Quick start](#quick-start)
- [Your first deck](#your-first-deck)
- [Commands and examples](#commands-and-examples)
- [Build your own vault](#build-your-own-vault)
- [Optional add-ons](#optional-add-ons)
- [Updating](#updating)
- [Troubleshooting](#troubleshooting)
- [How it works](#how-it-works)
- [Contributing](#contributing)
- [Credits and license](#credits-and-license)

## Features
- **Built with you, not for you.** A few multiple-choice questions, a plan you approve, then options wherever it's a matter of taste.
- **Your money, asked once.** No limit, keep it cheap, a set budget, or drippy (foils, borderless, Secret Lair up to a per-card max). Claude asks once and shows the price at the end: cheapest, as listed and drippy, with a store link for each card if you want one.
- **Researched like a person would.** Before proposing a plan, Claude researches your commander: EDHREC numbers, real public decklists, combos, creator videos, Reddit threads, articles, live prices and the current Wizards rules. Every source is logged and cited on the deck page, grouped by type, and takes that disagree with each other (or with your theme) are shown, not hidden.
- **Always checked.** 100 cards, singleton, color identity, legality, bracket rules, Game Changers, combos, mana, and how often you'll have your commander out on time.
- **Works with your tools.** Paste a list from Moxfield, Archidekt, MTG Arena or anywhere. Export back with exact printings, so Moxfield's and Archidekt's buy buttons pull the same copies.
- **Your collection.** Import it from Moxfield, Archidekt or ManaBox, keep it current as you open packs or trade, see what it's worth, what a deck still needs and what fits a commander. Decks then prefer cards you own.
- **Deck pages, your way.** A finished deck can become a page: **Fancy** (card images, charts, cards to consider, a 3D card viewer you can spin) or **Basic** (just the deck and numbers, ready in seconds), or pick the sections yourself. Fancy pages can be a shareable link, or a local page that loads images from Scryfall with nothing to download.
- **Vaults.** Full decks for several commanders and power levels on one page.

## Quick start
**You need:** Claude Code.

1. **Install the plugin** from inside Claude Code:
   ```
   /plugin marketplace add Carlomos7/mtg-skills
   /plugin install mtg@carlomos7-mtg-skills
   ```
2. **Restart Claude Code and type `/mtg:build`**, or just say "build me a Krenko deck".

## Your first deck
A build is a conversation: quick by default (take the recommended setup and it's about three clicks), customizable whenever you want (say "let me pick" or "change X" at any point).

1. **One click, or a few questions.** Claude first offers its recommended setup (bracket 3, best cards with normal copies, medium interaction, no theme). Take it and you're at the plan within a minute. Or pick everything yourself, in about three short rounds:
   - where you're starting (a commander, colors, a favorite card, a deck to upgrade)
   - your table's power level (bracket 1 to 5) and anything you don't want to see (infinite combos, extra turns, land destruction)
   - what's fun for you, how you like to win, how much interaction
   - money, once: **no limit** (the default), **keep it cheap**, **a set budget**, or **drippy** (fancy printings up to a per-card max)
   - pet cards and cards you never want

   Your answers are saved to `deck-brief.md`, so you can edit them or pick up later.
2. **A plan before any list.** The deck's plan, roughly when it wins, how many lands, ramp, draw and removal, and 3 to 5 key cards. You say yes, or what to change.
3. **Filling the deck.** Claude picks the obvious parts (lands, basic ramp) and says what it picked. Where it's taste (win conditions, close calls, your pet-card slots) you get 2 to 4 options, each with its reason (and its price, if you asked to keep it cheap or set a budget).
4. **Checks.** Every version of the list is checked. Problems come back to you as choices, not silent changes.
5. **Hand-back.**
   - the list and a short plan
   - a Rule 0 summary to read out at your table
   - the price in one line (cheapest, as listed, drippy); store links if you want them
   - an export for Moxfield, Archidekt, MTG Arena or a spreadsheet (import it into Moxfield or Archidekt for a page you can share)
   - once the deck passes every check: "Want to see it as a page?" Fancy (shareable or just on your computer), Basic, or Customize

## Commands and examples
| Type | To |
|---|---|
| `/mtg:build` | start a new deck together |
| `/mtg:check` | check a deck: legal? bracket? weak spots? cost? |
| `/mtg:upgrade` | improve a deck you have |
| `/mtg:cheaper` | see what a deck costs and make it cheaper |
| `/mtg:share` | get a list ready for Moxfield, Archidekt, Arena or a spreadsheet |
| `/mtg:collection` | import, update, value or search your card collection |
| `/mtg:commander-vault` | build a vault (see below) |

You don't need the commands; plain requests work too:
- "Build me a bracket 3 Krenko deck, I like going wide, under $150"
- "Here's my list (paste). What bracket is it and what should I cut?"
- "Show me the drippy version, nothing over $40 a card"
- "Is Teferi's Protection worth it in my Elesh Norn deck? What's cheaper?"
- "Give me this list for Moxfield with the exact printings"
- "Does deathtouch work with trample?"
- "Here's my ManaBox export, import my collection" / "I opened these: (paste)" / "What do I still need for this deck?"

## Build your own vault
A vault is one page with full decks for several commanders at the power levels you play, plus card rankings, cards to consider and price ladders. Any theme works, or none.

**Already building a deck?** Type `/mtg:commander-vault` with nothing after it, in the same folder. It picks up that deck and asks one question: add neighbouring brackets, add other commanders, or just make a page for this deck.

1. Open Claude Code in an empty folder (the vault's files go there).
2. Copy the block below, change the answers after each colon, and delete any line you don't need (its default is used).
3. Type `/mtg:commander-vault`, a space, paste your block, and press Enter.

```text
Commanders: Krenko, Mob Boss; Edgar Markov
Theme: none
Brackets: 2 and 3, open on 3
Budget per deck: $150
Copies: normal
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
| Copies | normal, cheapest (keep it cheap), or drippy with a per-card max | normal |
| Hard lines | what you never want: infinite combos, extra turns, land destruction, stax | what the bracket allows |
| Collection | paste a list, or a CSV path from Moxfield, Archidekt or ManaBox | none |
| Extras | alternative commanders, collection planner, splitting a pile between players | none |
| Page style | fancy (images, charts, rankings, 3D cards) or basic (decks and numbers, no images) | fancy |
| Images | downloaded into the page (shareable link), or Scryfall links (local page, no download) | downloaded |

Claude asks about anything unclear, shows the plan and a cost estimate, then builds. Expect 30 minutes or more; if you stop, run the same thing again in the same folder and it resumes. The page is published privately to your claude.ai account when you're signed in, otherwise saved as files you open in a browser. Every option (theme strictness, must-include cards, card labels, look) is in the [full request template](vault-request.md).

## Optional add-ons
Everything above works on its own. These MCP servers make research richer: EDHREC numbers, Moxfield and Archidekt decklists, bracket estimates, creator videos, Reddit and articles. When they're installed Claude uses them automatically, with no setup questions: EDHREC data shapes your deck's plan and picks. Without them Claude says once what wasn't available.

| Add-on | What it adds | Install in Claude Code |
|---|---|---|
| [MTG MCP server](https://github.com/j4th/mtg-mcp-server) (j4th) | EDHREC popularity numbers, Moxfield deck links, Commander Spellbook bracket estimates | `claude mcp add mtg --scope user -- uvx mtg-mcp-server` |
| [YouTube transcripts](https://github.com/jkawamoto/mcp-youtube-transcript) | Deck techs from creators like The Command Zone, quoted with timestamps | `claude mcp add youtube-transcript --scope user -- uvx --from git+https://github.com/jkawamoto/mcp-youtube-transcript mcp-youtube-transcript` |
| Web search, e.g. [Parallel](https://parallel.ai) | Reddit threads, articles, Wizards announcements, tournament results; also reads video transcripts when YouTube blocks the transcript server | `claude mcp add parallel-search --scope user --transport http https://search.parallel.ai/mcp` (Claude Code's built-in web search also works) |

- **Install the MTG server one way, not both:** the command above, or (if you also use claude.ai or Claude Desktop) the hosted connector: Settings → Connectors → Add custom connector → `https://mtg-mcp-server.fastmcp.app/mcp`. Connectors appear in Claude Code when you're signed in with a Claude account (not an API key). Having both loads every tool twice.
- A second MTG server (e.g. `mtg-commander`) is used to cross-check decklists and EDHREC numbers when present.
- Restart Claude Code after adding one; `/mcp` shows whether it connected.

## Updating
**Update the plugin:** in Claude Code run `/plugin marketplace update carlomos7-mtg-skills`, then restart Claude Code. `/plugin` shows the installed version; [CHANGELOG.md](CHANGELOG.md) says what changed.
**Uninstall:** `/plugin uninstall mtg@carlomos7-mtg-skills`.

**Store links** on deck pages go straight to the store's product page (no affiliate redirects).
**Privacy:** the plugin keeps your decks, answers and collection on your computer. Vault pages are published privately to your own claude.ai account, and add-ons you install follow their own terms.

## Troubleshooting
| Problem | Fix |
|---|---|
| A brand-new card isn't found | A card revealed in the last day or so may not be on Scryfall yet; Claude says so instead of guessing. |
| A pasted deck has unrecognized lines | Claude lists them and suggests the closest real card names. Check spelling, or paste the site's export instead of copying from a web page. |
| An add-on check "didn't run" | That add-on isn't installed or didn't connect; see [Optional add-ons](#optional-add-ons). Everything else still works. |
| Card images fail on a vault page (Windows) | Update the plugin; downloads use an up-to-date certificate bundle. |

## How it works
- **Skills** (`plugins/mtg/skills/`) hold the workflow: deckbuilding with intake and approval, research rules and sources, the multi-agent vault, and the short `/mtg:*` commands.
- **The research pass** runs on every new deck, usually as a background research agent: every source type has a minimum, every source is logged with what it was used for, and shortfalls are said out loud.
- **Accuracy:** card names from pastes and videos are matched to real cards before use; opinions need two independent dated sources; vault work is re-checked by a separate verifier; anything unchecked is labelled.

Design notes and sources are in [docs/research](docs/research).

## Contributing
Issues and pull requests are welcome.

```bash
claude --plugin-dir ./plugins/mtg              # try local changes
claude plugin validate --strict ./plugins/mtg  # check the plugin
```
**Releasing:** bump `version` in `plugins/mtg/.claude-plugin/plugin.json` and add a CHANGELOG entry in the same commit. Players only receive an update when the version changes.

Behavior evals use real Claude runs and cost usage: see [plugins/mtg/evals/README.md](plugins/mtg/evals/README.md). When something goes wrong in a real session, add an eval case for it.

## Credits and license
Card data from [Scryfall](https://scryfall.com), combos from [Commander Spellbook](https://commanderspellbook.com), rules from [Wizards of the Coast](https://magic.wizards.com/en/rules). Thanks to all of them for publishing open data.

This project is unofficial Fan Content permitted under the [Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy). Not approved or endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.

Code is [MIT](LICENSE) licensed. Made by [Carlomos7](https://github.com/Carlomos7).
