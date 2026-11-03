# mtg: Magic: The Gathering plugin for Claude Code

Accurate MTG research, Commander deckbuilding and optimizing, and tested deck pages. Every card fact is computed from a local Scryfall index; opinions are logged with sources, audited, and independently verified.

## Skills (`plugins/mtg/skills`)

| Skill | Job | Runs |
|---|---|---|
| `mtg-research` | Source authority, research loop, video and community protocol, claim ledger, `mtgdb.py` | Automatically on MTG questions |
| `commander-deckbuilding` | Build, review, optimize an existing deck, themes (optional), card picker | Automatically on deck requests |
| `mtg-pages` | Data contract + fixed tested template → interactive page / artifact | When a page is wanted |
| `commander-vault` | Orchestrates multi-commander vaults with agents and gates | `/mtg:commander-vault` only |

Agents: `vault-researcher`, `vault-deckbuilder`, `vault-merger`, `vault-verifier` (Sonnet, can't spawn agents or publish).
Hook: validates vault deck files and claim ledgers the moment they're written.

## Accuracy model
1. Computed facts (legality, identity, printings, prices, Game Changers, counts, roles via Scryfall Tagger) only from `mtgdb.py`.
2. Names from transcripts and pastes go through `normalize`; nothing unresolved reaches a deck.
3. Claims need dated sources, timestamps, 2 independent sources for opinions, sample sizes for stats, and a recency cutoff (`audit-claims`).
4. The hook bounces bad files back to the writer; an independent verifier re-opens sources; the lead adjudicates; leftovers are labelled on the page.
5. Measured, not guessed: `simulate` (commander on curve, matches exact math), `theme-pool` (strict theme feasibility), `diff` (what an optimization changed).
6. Pages are rendered from validated data by a fixed template, so no number on a page is typed by hand.

## Requirements
- [uv](https://docs.astral.sh/uv/) (every script runs with `uv run` and installs its own dependencies)
- Claude Code, with `claude --chrome` for page checks

## Install
In Claude Code:
```
/plugin marketplace add Carlomos7/mtg-skills
/plugin install mtg@carlomos7-mtg-skills
```
Local development: `claude --plugin-dir ./plugins/mtg` and `claude plugin validate ./plugins/mtg`.

MCP servers and connector:
```bash
claude mcp add parallel-search --scope user --transport http https://search.parallel.ai/mcp
claude mcp add youtube-transcript --scope user -- uvx --from git+https://github.com/jkawamoto/mcp-youtube-transcript mcp-youtube-transcript
```
- Add `j4th/mtg-mcp-server` at claude.ai Settings, Connectors (shows as `claude_ai_mtg-mcp`).
- Optional: a free TopDeck.gg API key in `TOPDECK_API_KEY`.

## One-time data setup
```bash
S=plugins/mtg/skills/mtg-research/scripts/mtgdb.py    # or the installed plugin path
uv run $S index && uv run $S selftest     # card index (~500 MB download) + golden facts
uv run $S tags-sync                       # role tags, a few minutes; monthly
uv run $S prices-sync                     # optional multi-vendor prices (--history = 90 days, large)
uv run $S collection import my.csv        # optional: Moxfield / Archidekt / ManaBox export
```
Re-run `index` weekly (prices, bans).

## Use
- "Is X good in my Y deck?" · "Build a B3 Vader deck" · "Optimize this list: <paste or Moxfield link>" · "Make a page for it"
- Vault: empty folder, `claude --chrome`, `/model opus`, copy `vault-request.md` into it and fill it in, then `/mtg:commander-vault @vault-request.md`. Re-run in the same folder to resume.

## Test
```bash
uv run --with pillow --with ijson --with playwright python -m unittest discover -s tests   # 44 tests incl. headless Chrome
cd plugins/mtg && claude plugin eval .                                                    # behavior evals (costs usage)
```
If cdnjs is blocked, set `CHARTJS=/path/to/chart.umd.js` for the browser test.
