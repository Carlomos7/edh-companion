# EDH Companion

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**A research-driven Commander (EDH) companion for Claude Code.** Start with anything (a character, a theme, a commander, a strategy, a decklist, a vague idea) and Claude researches what real players know, recommends directions, builds the deck with you inside your theme, budget and power level, checks it independently, and can turn it into an interactive page.

By [Carlomos7](https://github.com/Carlomos7). Not a card database or a deckbuilding site: decks live on Moxfield or Archidekt; this is the advisor next to them.

## What it does
- **Researches like a person would.** EDHREC numbers (with sample sizes), real decklists and primers, Reddit threads, articles and YouTube deck techs (quoted with timestamps), tournament results when power matters. Every claim is cited and labelled: fact, statistic, community opinion, Claude's judgment, or unresolved.
- **Guides, then builds.** For a broad idea it shows a few directions with a recommendation, asks one question at a time when the answer matters, checks whether your restrictions allow a working deck, and explains the trade-offs before you commit.
- **Keeps your rules.** Strict themes, specific artwork, approved exceptions, budget, bracket, pet cards and cards you refuse stay in force across sessions. Suggestions are proposals until you say yes.
- **Checks honestly.** A separate audit verifies legality, color identity, Game Changers and bracket limits, combos, printings and art, and whether recommendations are supported. Anything it couldn't check says "unverified".
- **Shows it.** On request, an interactive deck browser: card images and viewer, variants side by side, charts, filters, swaps, theme and audit status, and every source linked.

## Install
In Claude Code:
```
/plugin marketplace add Carlomos7/edh-companion
/plugin install edh-companion@edh-companion
```
Restart Claude Code. Needs [uv](https://docs.astral.sh/uv/) for the deck checker and pages (`winget install astral-sh.uv` on Windows, `brew install uv` on macOS).

Then just talk: "I want to build a powerful Spider-Man Commander deck that stays true to Marvel."

**Coming from the old `mtg` plugin?** `/plugin uninstall mtg@carlomos7-mtg-skills`, `/plugin marketplace remove carlomos7-mtg-skills`, then install as above. Old `/mtg:...` commands are replaced by plain requests.

## Skills
You rarely call these by name; Claude picks one from what you ask.

| Skill | Use it for | Example |
|---|---|---|
| `research` | exploring ideas, commanders, strategies; what players say; comparisons | "What are people saying about Anti-Venom?" |
| `brew` | building, upgrading, re-theming, variants | "Make my Doom deck stronger without losing the theme" |
| `audit` | legality, bracket, theme and art checks; second opinions | "Is my deck really bracket 3?" |
| `present` | interactive pages and comparisons | "Show both versions side by side" |
| `setup` | optional: preferences and a tool check | `/edh-companion:setup` |

Simple questions ("what does lifelink do?") get a direct answer, no workflow.

## Your projects
Each deck idea gets a folder, outside the plugin:
```text
~/Documents/EDHCompanion/projects/spider-man-marvel/
├── PROJECT.md     your goals and rules (theme, art, bracket, budget)
├── STATE.md       where things stand and what's next
├── DECISIONS.md   what you accepted, rejected or allowed, and why
├── RESEARCH.md    findings with sources            (+ research.json)
├── brew.json      the accepted deck and proposals
├── audit.json     the latest checks
├── decklists/     every version, ready to import into Moxfield
└── reports/       pages
```
Come back any time ("let's keep working on my Spider-Man deck") and Claude picks up from STATE.md with your decisions intact. A folder named `EDHCompanion` in the current directory is used instead, if there is one; `setup` can point somewhere else. Details: [project files](plugins/edh-companion/schemas/README.md).

## Optional integrations
Everything works with Claude Code's built-in web search. These make research richer and faster; the skills find them by what they can do, so similar tools work too. Nothing is installed for you.

| Add-on | Adds | Install |
|---|---|---|
| [j4th MTG MCP](https://github.com/j4th/mtg-mcp-server) | Scryfall, EDHREC, Commander Spellbook, Moxfield | `claude mcp add mtg --scope user -- uvx mtg-mcp-server` |
| [Parallel Search](https://parallel.ai) | web, Reddit and article search | `claude mcp add parallel-search --scope user --transport http https://search.parallel.ai/mcp` |
| [Exa](https://exa.ai) | semantic search and discovery | `claude mcp add exa --scope user --transport http https://mcp.exa.ai/mcp` |
| [YouTube transcripts](https://github.com/jkawamoto/mcp-youtube-transcript) | creator deck techs with timestamps | `claude mcp add youtube-transcript --scope user -- uvx --from git+https://github.com/jkawamoto/mcp-youtube-transcript mcp-youtube-transcript` |

Known limits we hit while testing (Nov 2026): the MTG MCP's deck validator was down and its bracket estimator missed Game Changers, so decks are checked with the plugin's own `deck_check.py` against Scryfall and Commander Spellbook. YouTube sometimes blocks transcripts; a web fetch of the video often works instead.

## Updating
`/plugin marketplace update edh-companion`, then restart. [CHANGELOG.md](CHANGELOG.md) lists changes.

## Troubleshooting
| Problem | Fix |
|---|---|
| "deck_check.py didn't run" | Install uv and restart Claude Code. Without it, checks are done by hand and labelled as such. |
| A brand-new card isn't found | Scryfall can lag a day behind reveals; Claude says so instead of guessing. |
| An integration "didn't answer" | Check `/mcp`. Research falls back to web search and says what it couldn't reach. |
| Pages can't show images when opened from disk | Use the published link, or serve the `reports/` folder; local pages load images from Scryfall. |

## How it works
- [Architecture](docs/architecture.md): skills, project files, scripts and why each exists.
- [Research notes](docs/research/): the conventions and sources the design is based on.

## Contributing
See [CLAUDE.md](CLAUDE.md) for layout, tests and release rules. Try local changes with `claude --plugin-dir ./plugins/edh-companion`.

## Credits and license
Card data from [Scryfall](https://scryfall.com), combos from [Commander Spellbook](https://commanderspellbook.com), statistics from [EDHREC](https://edhrec.com), rules from [Wizards of the Coast](https://magic.wizards.com/en/rules).

Unofficial Fan Content permitted under the [Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy). Not approved or endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.

Code is [MIT](LICENSE) licensed.
