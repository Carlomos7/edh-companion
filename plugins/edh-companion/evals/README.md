# Evals

`claude plugin eval` cases (prompt.md + graders/, or case.yaml). Run from `plugins/edh-companion`:

```bash
claude plugin eval . --scaffold --mocks off --ablation none --runs 1 --tag activation
claude plugin eval . --scaffold --mocks off --ablation none --runs 1 --allow-tools Write Edit WebSearch WebFetch   # everything
```
- `--scaffold` runs each case's `scaffold.sh`, which creates a saved Spider-Gwen project in `./EDHCompanion` (the skills look there first).
- MCP tools are denied unless `--allow-tools` lists them, so by default these runs also test the "integrations missing" fallbacks.
- Bash can't be granted in the Windows eval sandbox; `deck_check.py` is covered by `tests/unit` instead.
- The sandbox also refuses reads of the plugin's `references/` and `schemas/` files (the runner has no flag for allowing a path), so evals test SKILL.md text alone: rules that live only in references aren't visible to them, and script speed is measured by `tests/bench/` instead.
- Every run costs real usage. Add a case for every real mistake.
- **Check that cases load for free:** `claude plugin eval . --runs 1 --ablation none --max-cost-usd 0 --no-publish` stops before the first run but still reports every case file that fails to load.
- **Regression (pass^3):** `claude plugin eval . --tag regression --runs 3 --threshold 1.0`. A case passes only when all 3 runs pass.
- **Triggers:** `--tag triggers` runs 20 one-turn cases under `triggers/`: 10 that should fire a specific skill (including the research/brew/audit/present near misses) and 10 one-lookup or unrelated questions that should fire none.
- **Linux only:** cases tagged `linux-only` need Bash and uv (WSL or Linux): `--allow-tools Bash Write Edit`.
- **Cost budgets:** `python tests/bench/session_stats.py --eval RESULT.json --budget plugins/edh-companion/evals/budgets.json` exits 1 when a case's median cost or turn count is more than 20% over its budget.

| Tag | Cases |
|---|---|
| activation | act-lookup-lifelink, act-research-anti-venom, act-ambiguous-best-commanders, act-audit-bracket, act-present-not-for-text |
| routing / negative | act-lookup-banned, not-mtg |
| gates | gate-delete-asks, gate-explicit-change |
| commanders | commander-pairing |
| persistence, theme, art | persist-rejected-decisions, theme-drift-removal, art-mismatch-audit |
| accuracy, research | unsupported-claim, conflicting-sources, card-facts, cedh-realism, transcript-names, alchemy-name, rules-current |
| theme, feasibility | theme-official-feasible, theme-stardew-infeasible, theme-refuses-exceptions, theme-loosen-midway, theme-weak-honest |
| aesthetics, export | aesthetic-budget, export-archidekt |
| deckbuilding | asks-before-building, b3-combo-trap, budget-alternatives, curve-check, export-exact, moxfield-sections, no-theme-default, review-planted-errors |
| regression (pass^3) | b3-combo-trap, persist-rejected-decisions, theme-drift-removal, art-mismatch-audit, gate-delete-asks, reaudit-history, research-large-find |
| multi-turn, cost | reaudit-history (context.history_file), research-large-find (no whole-file read of a 600-finding research.json) |
| present | act-present-not-for-text, present-builds-page (linux-only) |
| triggers | triggers/trig-* (10 should, 10 should-not) |
