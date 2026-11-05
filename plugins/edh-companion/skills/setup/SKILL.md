---
name: setup
description: Optional first-time setup and reconfiguration for edh-companion. Reports which research and card-data capabilities are available, suggests optional integrations, and saves a few preferences (deck platform, default bracket, budget style, workspace folder) to a small config file.
disable-model-invocation: true
argument-hint: "[nothing, or what to change, e.g. 'workspace D:/MTG']"
---

# Setup (optional)

Nothing requires setup: every skill works without it, using defaults. This only saves preferences and tells the player what their tools can do. Replies follow [writing.md](../../references/writing.md).

Request: $ARGUMENTS

## 1. Show what's there
Check capabilities by calling, not by reading tool names (one cheap call each; list in [research's sources.md](../research/references/sources.md)): card data (Scryfall), EDHREC stats, combos (Commander Spellbook), deck links (Moxfield/Archidekt), web search, YouTube transcripts, a browser for page testing (Playwright/Chrome), Bash + uv (for the deck checker and page builder). Report answer-first: one line on what works and what's missing ("Card data, combos and web search work; no YouTube transcripts, so no creator deck techs"), then a table: capability · available or missing · what's lost without it.

For missing capabilities that would clearly help, suggest options in one line each (never install anything yourself):
- MTG data: j4th MTG MCP (`claude mcp add mtg --scope user -- uvx --with "selectolax<1.0" mtg-mcp-server`) or its hosted connector
- Search: Parallel (`claude mcp add parallel-search --scope user --transport http https://search.parallel.ai/mcp`) or Exa (`claude mcp add exa --scope user --transport http https://mcp.exa.ai/mcp`); built-in web search also works
- Video: jkawamoto YouTube transcripts (`claude mcp add youtube-transcript --scope user -- uvx --from git+https://github.com/jkawamoto/mcp-youtube-transcript mcp-youtube-transcript`)
- uv (`winget install astral-sh.uv` / `brew install uv`), needed for the deck checker and pages

## 2. Ask, one question at a time, only what they want to set
Any can be skipped.
1. Deck platform: Moxfield (Recommended) · Archidekt · other.
2. Defaults for new projects (optional): bracket, money style (no limit / cheap / budget, as a hard limit or a flexible target / drippy / no expense spared), and for looks: preferred treatments (foil, etched, borderless, showcase, Secret Lair) and an aesthetic budget or per-card max.
3. Shopping (optional): currency/region (USD default, EUR for Cardmarket) and preferred stores, used only when they ask how to get cards.
4. Research (optional): run research's two-step approval (tools approved, then how often to ask) and pick the default depth; or review and change saved choices (`companion.py research` shows them). Skip it and research asks once, on the first big research request.
5. Workspace folder: `~/Documents/EDHCompanion` (Recommended, used from any folder Claude Code starts in) · another path · this folder (creates `EDHCompanion/workspace.yaml` here so it's used when Claude Code starts here). Existing projects are never moved; if they live elsewhere, say where and let the player move them. Say plainly where the choice is saved (`workspace:` in the config file) and that every future session uses it, wherever Claude Code is started; a marked local folder (`workspace.yaml`) is the only thing that overrides it.

## 3. Save
Config file: `~/.config/edh-companion/config.yaml`. Read it first if it exists; show each change to an existing value as old → new and get a yes before overwriting it. Write only what was answered:
```yaml
platform: Moxfield
workspace: ~/Documents/EDHCompanion
defaults:
  bracket: 3
  budget: no_limit          # no_limit | cheap | budget | drippy | no_expense_spared
  budget_limit: flexible    # flexible (a target with wiggle room) | hard
  aesthetic:
    treatments: [foil, borderless]
    per_card_max_usd: 30
shopping:
  currency: USD
  stores: [TCGplayer]
research: …              # research's sources.md, "Saved form"
```
Step 1's check never calls an unapproved tool; once tools are approved, their test results go in `status` and `checked` ("Research approval").
Then confirm with `uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/companion.py" where` (or by reading the file back). Never store credentials or API keys here; MCP keys belong in Claude Code's own MCP config.

Project defaults from this file are suggestions for new projects only; a project's PROJECT.md always wins.
