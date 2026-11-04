# Plugin evals

Run from the plugin root (`plugins/mtg`):

```bash
claude plugin eval . --mocks off --allow-tools Read Write WebSearch WebFetch
# add --case card-facts --runs 1 --ablation none for a quick single check while editing
claude plugin eval . --judge-model sonnet    # steadier judging
```

| Case | Checks |
|---|---|
| card-facts | mtg-research fires, ban / Game Changer / price facts correct with a source date |
| review-planted-errors | deckbuilding fires, all 5 planted errors found |
| b3-combo-trap | no Kinnan two-card infinite at B3, Game Changer limit |
| cedh-realism | answer uses tournament data, not EDHREC popularity |
| transcript-names | garbled names resolved to real cards |
| curve-check | states assumptions about the curve, still catches an illegal list |
| no-theme-default | a themed commander alone doesn't add theme checks |
| not-mtg | no MTG skill fires on an unrelated coding request |
| alchemy-name | a paper card is not confused with its digital Alchemy namesake (real bug, fixed in 5.0) |
| moxfield-sections | Moxfield export headers, partners and sideboard are read correctly (real bug, fixed in 5.0) |
| asks-before-building | asks about bracket, price style and fun before handing over a list |
| budget-alternatives | cheaper mono-white options with dated prices |
| export-exact | import-ready list with exact printings, commander first |
| rules-current | trample + deathtouch answered from the current Comprehensive Rules with rule numbers and date |
| route-collection | "I opened packs, track them" routes to the collection skill and adds the cards |
| route-research | "Is Sol Ring banned?" routes to mtg-research, not deckbuilding (near-miss) |

Notes:
- Eval runs deny MCP tools unless `--allow-tools` lists them.
- Each run starts in an empty workspace.
- Every run and judge call costs real usage. b3-combo-trap is the expensive one.
- Add a case for every real mistake you find.
