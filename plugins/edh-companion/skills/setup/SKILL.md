---
name: setup
description: Optional first-time setup and reconfiguration for edh-companion. Reports which research and card-data capabilities are available, suggests optional integrations, and saves a few preferences (deck platform, default bracket, budget style, workspace folder) to a small config file.
disable-model-invocation: true
argument-hint: "[nothing, or what to change, e.g. 'workspace D:/MTG']"
---

# Setup (optional)

Nothing requires setup: every skill works without it, using defaults. This only saves preferences and tells the player what their tools can do.

Request: $ARGUMENTS

## 1. Show what's there
Check capabilities by calling, not by reading tool names (one cheap call each; list in [research's sources.md](../research/references/sources.md)): card data (Scryfall), EDHREC stats, combos (Commander Spellbook), deck links (Moxfield/Archidekt), web search, YouTube transcripts, a browser for page testing (Playwright/Chrome), Bash + uv (for the deck checker and page builder). Report in a short table: available / missing / what's lost without it.

For missing capabilities that would clearly help, suggest options in one line each (never install anything yourself):
- MTG data: j4th MTG MCP (`claude mcp add mtg --scope user -- uvx mtg-mcp-server`) or its hosted connector
- Search: Parallel (`claude mcp add parallel-search --scope user --transport http https://search.parallel.ai/mcp`) or Exa (`claude mcp add exa --scope user --transport http https://mcp.exa.ai/mcp`); built-in web search also works
- Video: jkawamoto YouTube transcripts (`claude mcp add youtube-transcript --scope user -- uvx --from git+https://github.com/jkawamoto/mcp-youtube-transcript mcp-youtube-transcript`)
- uv (`winget install astral-sh.uv` / `brew install uv`), needed for the deck checker and pages

## 2. Ask, one question at a time, only what they want to set
1. Deck platform: Moxfield (Recommended) · Archidekt · other.
2. Defaults for new projects (optional): bracket, money style (no limit / cheap / budget / drippy), and for looks: preferred treatments (foil, etched, borderless, showcase, Secret Lair) and an aesthetic budget or per-card max.
3. Research sources (optional): any to prefer (e.g. EDHREC, Reddit, a favourite creator) or to never use. Skip it and research uses everything available.
4. Workspace folder: `~/Documents/EDHCompanion` (Recommended) or another path.

## 3. Save
Config file: `~/.config/edh-companion/config.yaml`. Read it first if it exists; show the changes and get a yes before overwriting any existing value. Write only what was answered:
```yaml
platform: Moxfield
workspace: ~/Documents/EDHCompanion
defaults:
  bracket: 3
  budget: no_limit          # no_limit | cheap | budget | drippy
  aesthetic:
    treatments: [foil, borderless]
    per_card_max_usd: 30
research:
  prefer: [EDHREC, Reddit]
  exclude: []
```
Then confirm with `uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/companion.py" where` (or by reading the file back). Never store credentials or API keys here; MCP keys belong in Claude Code's own MCP config.

Project defaults from this file are suggestions for new projects only; a project's PROJECT.md always wins.
