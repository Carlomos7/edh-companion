# Plugin evals

Run from the plugin root (`plugins/mtg`):

```bash
claude plugin eval .                         # every case, 3 runs each, with and without the plugin
claude plugin eval . --case card-facts --runs 1 --ablation none   # quick single check while editing
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
| deck-page | uses the page pipeline, not hand-written HTML, and catches a bad list first |
| not-mtg | no MTG skill fires on an unrelated coding request |

Notes:
- Each run starts in an empty workspace. Build the index first (`mtgdb.py index`); runs read it from `~/.cache/mtg/`. If your eval runs can't see your home directory, set `MTGDB` in each prompt's `env` frontmatter.
- Every run and judge call costs real usage. b3-combo-trap is the expensive one.
- Add a case for every real mistake you find.
- Script logic is unit tested separately: `python3 -m unittest discover -s tests` from the repo root.
