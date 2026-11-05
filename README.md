# EDH Companion

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**A research-driven Commander (EDH) companion for Claude Code.** Start with anything (a character, a theme, a commander, a strategy, a decklist, a vague idea) and Claude researches what real players know, recommends directions, builds the deck with you inside your theme, budget and power level, checks it independently, and can turn it into an interactive page.

By [Carlomos7](https://github.com/Carlomos7). Not a card database or a deckbuilding site: decks live on Moxfield or Archidekt; this is the advisor next to them.

## What it does
- **Researches like a person would.** EDHREC numbers (with sample sizes), real decklists and primers, Reddit threads, articles and YouTube deck techs (quoted with timestamps), tournament results when power matters. Every claim is cited and labelled: fact, statistic, community opinion, Claude's judgment, or unresolved.
- **Guides, then builds.** For a broad idea it shows a few directions with a recommendation, asks one question at a time when the answer matters, checks whether your restrictions allow a working deck, and explains the trade-offs before you commit.
- **Keeps your rules.** Strict themes, specific artwork, approved exceptions, budget, bracket, pet cards and cards you refuse stay in force across sessions. Suggestions are proposals until you say yes.
- **Knows when a theme won't work.** "Strictly Stardew Valley" gets researched, not assumed: if there's no legal way to do it, you hear why and get real options, never a fake-compliant list.
- **Money and looks.** A gameplay budget and a separate budget for foils, borderless and Secret Lair printings, with dated prices.
- **Exports.** Moxfield, Archidekt, plain text and CSV, with exact printings and foils.
- **Checks honestly.** A separate audit verifies legality, color identity, Game Changers and bracket limits, combos, printings and art, and whether recommendations are supported. Anything it couldn't check says "unverified".
- **Shows it.** On request, an interactive deck browser: card images and viewer, variants side by side, charts, filters, swaps, theme and audit status, and every source linked.

## Requirements
| | What | Why |
|---|---|---|
| Required | [Claude Code](https://code.claude.com) (CLI, desktop app or IDE extension) | runs the plugin |
| Required | [uv](https://docs.astral.sh/uv/) | runs the deck checker, exports and page builder; it fetches Python itself, so there's no separate Python install |
| Required | internet access | card data from Scryfall, combos from Commander Spellbook, research sources |
| Optional | a claude.ai account on a paid plan | publishing pages as private shareable links; without it, pages are saved as files |
| Optional | Git | only for installing the YouTube transcript add-on |
| Optional | Chrome or Edge | lets Claude test pages in a real browser before handing them over |
| Optional | MCP add-ons ([below](#optional-integrations)) | richer, faster research; everything works without them |

Install uv:

| Shell | Command |
|---|---|
| bash | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| PowerShell | `winget install astral-sh.uv` |
| Command Prompt | `winget install astral-sh.uv` |

## Install
In Claude Code (the same everywhere):
```
/plugin marketplace add Carlomos7/edh-companion
/plugin install edh-companion@edh-companion
```
Restart Claude Code, then just talk: "I want to build a powerful Spider-Man Commander deck that stays true to Marvel."

## Working with your decks
EDH Companion keeps your decks, research and reports in one workspace. By default that's the `EDHCompanion` folder inside `Documents` in your home folder.

**Recommended:** open Claude Code in your main workspace.

bash:
```bash
cd ~/Documents/EDHCompanion
claude
```
PowerShell:
```powershell
cd "$HOME\Documents\EDHCompanion"
claude
```
Command Prompt:
```bat
cd /d "%USERPROFILE%\Documents\EDHCompanion"
claude
```
From there you can create decks, continue existing projects and manage Showcases just by talking to Claude.

**Working on one specific deck?**

bash:
```bash
cd ~/Documents/EDHCompanion/projects/spider-man
claude
```
PowerShell:
```powershell
cd "$HOME\Documents\EDHCompanion\projects\spider-man"
claude
```
Command Prompt:
```bat
cd /d "%USERPROFILE%\Documents\EDHCompanion\projects\spider-man"
claude
```
Useful for focused sessions.

**Already opened Claude somewhere else?** No problem. EDH Companion finds your configured workspace and works with its projects without restarting Claude.

The optional `/edh-companion:setup` lets you choose a different storage location.

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
EDHCompanion/projects/spider-man-marvel/
├── PROJECT.md     your goals and rules (theme, art, bracket, budget)
├── STATE.md       where things stand and what's next
├── DECISIONS.md   what you accepted, rejected or allowed, and why
├── RESEARCH.md    findings with sources            (+ research.json)
├── brew.json      the accepted deck and proposals
├── audit.json     the latest checks
├── decklists/     every version, ready to import into Moxfield
└── reports/       pages
```
Come back any time ("let's keep working on my Spider-Man deck") and Claude picks up from STATE.md with your decisions intact. Several projects can share one interactive page (a showcase) while keeping their own files and decisions. Details: [project files](plugins/edh-companion/schemas/README.md).

## Optional integrations
Everything works with Claude Code's built-in web search. These make research richer and faster; the skills find them by what they can do, so similar tools work too. Nothing is installed for you.

| Add-on | Adds | Install |
|---|---|---|
| [j4th MTG MCP](https://github.com/j4th/mtg-mcp-server) | Scryfall, EDHREC, Commander Spellbook, Moxfield | `claude mcp add mtg --scope user -- uvx --with "selectolax<1.0" mtg-mcp-server` |
| [Parallel Search](https://parallel.ai) | web, Reddit and article search | `claude mcp add parallel-search --scope user --transport http https://search.parallel.ai/mcp` |
| [Exa](https://exa.ai) | semantic search and discovery | `claude mcp add exa --scope user --transport http https://mcp.exa.ai/mcp` |
| [YouTube transcripts](https://github.com/jkawamoto/mcp-youtube-transcript) | creator deck techs with timestamps | `claude mcp add youtube-transcript --scope user -- uvx --from git+https://github.com/jkawamoto/mcp-youtube-transcript mcp-youtube-transcript` |

The MTG MCP command pins `selectolax<1.0`: mtg-mcp-server 3.0.0 doesn't cap that dependency, and selectolax 1.0 (Oct 2026) breaks its import, so an unpinned install crashes on startup. Drop the pin once mtg-mcp-server supports selectolax 1.x. Already added it without the pin? Run `claude mcp remove mtg --scope user`, then the command above.

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
