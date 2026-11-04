# Plugin evals

Run from the plugin root (`plugins/mtg`):

```bash
EVAL_MTG_CACHE=~/.cache/mtg claude plugin eval . --mocks off --allow-tools "mcp__plugin_mtg_mtgdb__*" Read Write WebSearch WebFetch
# add --case card-facts --runs 1 --ablation none for a quick single check while editing
claude plugin eval . --judge-model sonnet    # steadier judging
```

| Case | Checks |
|---|---|
| card-facts | mtg-research fires, mtgdb.py is used, ban / Game Changer / price facts correct with a data date |
| review-planted-errors | deckbuilding fires, validate runs, all 5 planted errors found |
| b3-combo-trap | no Kinnan two-card infinite at B3, Game Changer limit, checks reported |
| cedh-realism | answer uses tournament data, not EDHREC popularity |
| transcript-names | garbled names normalized to real cards via the index |
| curve-check | runs the goldfish simulation, states assumptions, still catches an illegal list |
| no-theme-default | a themed commander alone doesn't add theme checks |
| not-mtg | no MTG skill fires on an unrelated coding request |
| alchemy-name | a paper card is not confused with its digital Alchemy namesake (real bug, fixed in 5.0) |
| moxfield-sections | Moxfield export headers, partners and sideboard are read correctly (real bug, fixed in 5.0) |
| asks-before-building | asks about bracket, price style and fun before handing over a list |
| budget-alternatives | cheaper mono-white options with dated prices from mtg_cheaper_alternatives |
| export-exact | import-ready list with exact printings, commander first |
| rules-current | trample + deathtouch answered from the current Comprehensive Rules with rule numbers and date |
| route-collection | "I opened packs, track them" routes to the collection skill and adds the cards |
| route-research | "Is Sol Ring banned?" routes to mtg-research, not deckbuilding (near-miss) |

Notes:
- `--mocks off` starts the plugin's real `mtgdb` MCP server (local, reads only the card cache). `--allow-tools` lets runs use it; eval runs deny MCP tools otherwise.
- `EVAL_MTG_CACHE`: each eval run gets an empty home folder and only `EVAL_*` variables pass through, so this points the server at your synced data.
- Granting `Bash` makes the eval sandbox Bash; on some Windows setups that sandbox can't start, so the cases are written to work without Bash.
- Each run starts in an empty workspace. Sync the data first (`uv run scripts/mtgdb.py sync`); runs read it from `~/.cache/mtg/`.
- Every run and judge call costs real usage. b3-combo-trap is the expensive one.
- Add a case for every real mistake you find.
- Script and server logic are unit tested separately (see the repo README).
