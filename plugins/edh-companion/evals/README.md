# Evals

`claude plugin eval` cases (prompt.md + graders/, or case.yaml). Run from `plugins/edh-companion`:

```bash
claude plugin eval . --scaffold --mocks off --ablation none --runs 1 --tag activation
claude plugin eval . --scaffold --mocks off --ablation none --runs 1 --allow-tools Write Edit WebSearch WebFetch   # everything
```
- `--scaffold` runs each case's `scaffold.sh`, which creates a saved Spider-Gwen project in `./EDHCompanion` (the skills look there first).
- MCP tools are denied unless `--allow-tools` lists them, so by default these runs also test the "integrations missing" fallbacks.
- Bash can't be granted in the Windows eval sandbox; `deck_check.py` is covered by `tests/unit` instead.
- The sandbox also refuses reads of the plugin's `references/` and `schemas/` files (the runner has no flag for allowing a path), so evals test SKILL.md text alone: rules that live only in references aren't visible to them, and script speed is measured by `tests/bench/` instead (see `docs/benchmarks.md`).
- Every run costs real usage. Add a case for every real mistake.

| Tag | Cases |
|---|---|
| activation | lookup-lifelink, research-anti-venom, ambiguous-best-commanders, audit-bracket, present-not-for-text |
| routing / negative | act-lookup-banned, not-mtg |
| persistence, theme, art | persist-rejected-decisions, theme-drift-removal, art-mismatch-audit |
| accuracy, research | unsupported-claim, conflicting-sources, card-facts, cedh-realism, transcript-names, alchemy-name, rules-current |
| theme, feasibility | theme-official-feasible, theme-stardew-infeasible, theme-refuses-exceptions, theme-loosen-midway, theme-weak-honest |
| aesthetics, export | aesthetic-budget, export-archidekt |
| deckbuilding | asks-before-building, b3-combo-trap, budget-alternatives, curve-check, export-exact, moxfield-sections, no-theme-default, review-planted-errors |
