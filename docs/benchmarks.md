# Benchmarks: 7.8.0 → 8.0.0

What we optimise is the cost and time of a task that ends well: a correct lookup, a legal and honest deck, an audit that catches every real problem. Smaller tool output or fewer requests only count if the whole task gets cheaper or faster without getting worse. So every number here is a whole run, failures included, and quality is measured next to cost.

Everything below was measured on 2026-11-04. Nothing is estimated or extrapolated: where a number couldn't be measured, it says so.

## Method

### Versions
- **Before:** commit `718ada9` (7.8.0).
- **After:** commit `d7d5ecb` (8.0.0).
- **Not measured:** 8.1.0 (`bdb0c73`, the report redesign), which landed after these runs.

Each version ran from its own clean git worktree, so no file was being edited while it was measured. The harness and the fixtures came from the same place for both, so both started from the same files.

### Machine
Windows 11 Pro (10.0.26200), 16 logical CPUs, home internet connection. Python 3.12 through uv 0.13.1. Claude Code 2.1.318; eval runs used `claude-opus-5-5`, graded by the default judge (haiku). Other work was running on the same machine at the same time (the Tier 2 evals during part of Tier 1, and other agents' unit tests), which adds noise to local times on both sides.

### Tier 1: the scripts, paired
`tests/bench/bench.py` runs the plugin's scripts exactly as the skills call them (`uv run --script …`) on both versions, interleaved: in each repeat, every scenario runs on 7.8.0 and then on 8.0.0, so changes in network conditions hit both. 3 repeats, with a 20 s pause between runs so the benchmark doesn't trip Scryfall's rate limit itself.

Each scenario runs twice in a row in a fresh temp folder with an empty cache:
- **Cold:** empty cache (a first session).
- **Warm:** the same commands again (a re-check, a second page build, a resumed session). 7.8.0 has no cache, so its warm run repeats the cold one.

uv's script environments were prepared before timing, so "cold" means an empty data cache, not a cold uv.

| Scenario | What runs (same inputs on both) | Notes on equivalence |
|---|---|---|
| lookup-1, lookup-10 | Look up 1 card (Sol Ring) or 10 cards | 8.0: `card_lookup.py names --file`, which prints one line per card. 7.8 had no lookup script; its research skill used `deck_check.py --cards-only --json cards.json`, which prints a pass line and writes the card data to a file Claude then has to read. Same request (one batched collection call); different output. |
| research | Commander check (Krenko) + card data for 61 names | Same commands on both. |
| candidates | `candidates.py` on the Krenko project | New in 8.0; no 7.8 equivalent, so not compared. |
| build | `deck_check` full with `--cheapest`, 2-variant page data (`site_data.py --images cdn`), export to every format | Same commands on both. |
| atlas | Page data with `--images atlas`, then `build_site.py` packing the card images | Image cache in the temp folder (`--raw-cache`), never the player's `~/.cache`. |
| optimize | `deck_check` before and after 5 real swaps, then `companion.py validate` | Same commands on both. |
| audit-planted | `deck_check` on 13 decklists with planted problems (below) | Each version runs what its audit skill runs: 8.0 adds `--fresh` (audits re-read all card data), 7.8 has no cache. |

Per step, `tests/bench/sitecustomize.py` logs every HTTP request (time to headers and time to read the body) and every `time.sleep` with the line of code that slept. Wall time is then split into:
- **Network:** time inside requests, body reads included.
- **Waiting:** sleeps outside network time (pacing, 429 holds, retry backoff).
- **Local:** everything else (Python, uv start-up, disk, page building).

### Planted-error audit (correctness)
`tests/fixtures/planted-errors/` holds `clean.txt` (the Krenko test deck with Skirk Prospector swapped for a Mountain, so it has no commander + 2 combo) and one deck per planted problem. `expected.json` lists, for each deck, the check that must report the problem, its status and the card it must name:

| Deck | Planted problem | Must be reported as |
|---|---|---|
| clean, clean-b2 | none (bracket 3 and 2) | every check passes |
| banned | Jeweled Lotus | `chk-legality-1` fail |
| off-identity | Counterspell in a mono-red deck | `chk-identity-1` fail |
| duplicate | two Goblin Matron | `chk-singleton-1` fail |
| wrong-printing | Sol Ring (CMR) 1, which is The Prismatic Piper | `chk-printing-2` fail |
| count-99 | 99 cards | `chk-count-1` fail |
| fake-card | a made-up name | `chk-cards-1` fail |
| game-changers-4 | Jeska's Will, Gamble, Ancient Tomb, Mana Vault at bracket 3 | `chk-game-changers-1` fail |
| combo-b2 | Krenko + Skirk Prospector + Goblin Warchief (Spellbook 38-659-1288) at bracket 2 | `chk-combos-1` fail |
| unreleased | Rise from the Nether (releases 2027-04-09) | `chk-legality-4` warning |
| foil-finish | Sol Ring (C21) 263 foil, which exists only nonfoil | `chk-printing-3` fail |
| all-in-one | the nine bracket-3 problems in one deck | all nine, as above |

Detection rate = planted problems reported with the right check id, status and card. Any other non-passing check is listed as a possible false alarm. The facts were checked against Scryfall and Commander Spellbook on 2026-11-04. The "unreleased" plant stops working on 2027-04-09; replace it with a newer card then.

### Tier 2: Claude end to end, paired
`claude plugin eval` with the same flags on both versions, run from each worktree's `plugins/edh-companion`:

```
claude plugin eval . --case <case> --scaffold --mocks off --ablation none --runs 2 -j 2 --keep-temp --no-publish --trust-plugin \
  --allow-tools Write Edit WebSearch WebFetch --max-cost-usd 4
```

Two rounds of 2 runs, so 4 runs per case per version, 48 runs in all. The eval case files are identical in both commits.

| Case | Task |
|---|---|
| act-lookup-banned | quick lookup ("Is Sol Ring banned in Commander?") |
| review-planted-errors | audit a pasted deck with 5 planted problems |
| act-research-anti-venom | research ("What are people saying about Anti-Venom as a commander?") |
| asks-before-building | brew ("Build me a Krenko, Mob Boss deck.") |
| gate-explicit-change | brew, explicit swap on a saved project |
| act-present-not-for-text | present routing: a plain-text list must not build a page |

Quality is the case's graders (pass/fail). Cost and duration are the eval's own `costUsd` and `durationSeconds` per run (the judge's cost is reported separately and is not included). Tokens, tool calls, errors and permission denials come from each run's `trace.jsonl`, read by `tests/bench/session_stats.py --eval`; token totals are the CLI's own per-model totals for the run, by kind.

## Tier 1 results

Median over 3 repeats, [min–max] when they differ. "Printed bytes" is what the scripts print to the terminal, which is what Claude reads unless it opens the output files.

| Scenario | Phase | Version | n | Wall s | Network s | Waiting s | Local s | Requests | Dup | Failed | 429 / 5xx | Slowest request ms | Printed bytes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lookup-1 | cold | 7.8.0 | 3 | 1.4 [1.3–1.8] | 0.2 [0.2–0.3] | 0.5 | 0.7 [0.6–1.1] | 1 | 0 | 0 | 0 / 0 | 226 [212–261] | 130 |
| lookup-1 | cold | 8.0.0 | 3 | 1.4 [0.8–1.8] | 0.2 [0.2–0.5] | 0.0 | 0.9 [0.6–1.5] | 1 | 0 | 0 | 0 / 0 | 233 [219–485] | 79 |
| lookup-1 | warm | 7.8.0 | 3 | 1.4 [1.3–4.0] | 0.2 [0.2–0.5] | 0.5 | 0.6 [0.5–2.9] | 1 | 0 | 0 | 0 / 0 | 233 [229–538] | 130 |
| lookup-1 | warm | 8.0.0 | 3 | 1.8 [0.7–1.9] | 0.0 | 0.0 | 1.8 [0.7–1.9] | 0 | 0 | 0 | 0 / 0 | 0 | 80 |
| lookup-10 | cold | 7.8.0 | 3 | 1.8 [1.6–1.8] | 0.3 [0.3–0.3] | 0.5 | 1.0 [0.7–1.0] | 1 | 0 | 0 | 0 / 0 | 301 [295–310] | 130 |
| lookup-10 | cold | 8.0.0 | 3 | 1.4 [1.0–2.9] | 0.3 [0.3–0.3] | 0.0 | 1.1 [0.7–2.6] | 1 | 0 | 0 | 0 / 0 | 275 [267–299] | 822 |
| lookup-10 | warm | 7.8.0 | 3 | 1.4 [1.3–1.8] | 0.3 [0.2–0.6] | 0.5 | 0.6 [0.5–0.7] | 1 | 0 | 0 | 0 / 0 | 338 [245–590] | 130 |
| lookup-10 | warm | 8.0.0 | 3 | 0.9 [0.6–2.5] | 0.0 | 0.0 | 0.9 [0.6–2.5] | 0 | 0 | 0 | 0 / 0 | 0 | 823 |
| research | cold | 7.8.0 | 3 | 5.5 [5.3–7.2] | 2.3 [2.1–2.5] | 1.0 | 2.0 [2.0–4.1] | 4 | 0 | 0 | 0 / 0 | 1545 [1364–1592] | 691 |
| research | cold | 8.0.0 | 3 | 3.8 [3.3–6.2] | 1.4 [1.4–1.6] | 0.4 [0.4–0.4] | 2.0 [1.4–4.4] | 3 | 0 | 0 | 0 / 0 | 1297 [1262–1433] | 714 |
| research | warm | 7.8.0 | 3 | 6.8 [4.5–10.0] | 2.6 [2.5–2.6] | 1.0 | 3.2 [1.1–6.3] | 4 | 0 | 0 | 0 / 0 | 1663 [1463–1764] | 691 |
| research | warm | 8.0.0 | 3 | 1.5 [1.3–2.7] | 0.0 | 0.0 | 1.5 [1.3–2.7] | 0 | 0 | 0 | 0 / 0 | 0 | 715 |
| candidates | cold | 8.0.0 | 3 | 1.9 [0.7–2.6] | 0.1 [0.1–0.1] | 0.0 | 1.7 [0.6–2.4] | 1 | 0 | 0 | 0 / 0 | 132 [120–154] | 413 |
| candidates | warm | 8.0.0 | 3 | 1.0 [0.5–1.0] | 0.0 | 0.0 | 1.0 [0.5–1.0] | 0 | 0 | 0 | 0 / 0 | 0 | 414 |
| build | cold | 7.8.0 | 3 | 32.1 [31.5–38.6] | 8.9 [8.7–9.6] | 16.1 [16.1–16.1] | 7.1 [6.7–12.9] | 37 | 14 | 0 | 0 / 0 | 1921 [1731–2289] | 5159 |
| build | cold | 8.0.0 | 3 | 14.4 [13.2–17.7] | 3.6 [3.5–3.9] | 3.0 [2.7–3.1] | 7.4 [6.5–11.5] | 15 | 0 | 0 | 0 / 0 | 1730 [1598–2042] | 5209 |
| build | warm | 7.8.0 | 3 | 36.4 [31.0–39.5] | 9.6 [8.5–10.0] | 16.1 | 10.7 [6.4–13.3] | 37 | 14 | 0 | 0 / 0 | 2427 [1758–2477] | 5159 |
| build | warm | 8.0.0 | 3 | 6.0 [5.9–13.9] | 0.0 | 0.0 | 6.0 [5.9–13.9] | 0 | 0 | 0 | 0 / 0 | 0 | 5209 |
| atlas | cold | 7.8.0 | 3 | 36.1 [33.7–43.1] | 7.5 [7.2–7.7] | 11.1 | 17.6 [15.4–24.3] | 103 | 3 | 0 | 0 / 0 | 2131 [1883–2487] | 2664 |
| atlas | cold | 8.0.0 | 3 | 24.4 [23.4–27.0] | 4.3 [4.3–4.6] | 3.0 [2.9–3.0] | 17.1 [16.1–19.6] | 92 | 0 | 0 | 0 / 0 | 1575 [1514–1815] | 2664 |
| atlas | warm | 7.8.0 | 3 | 34.1 [31.3–90.9] | 5.4 [5.4–5.8] | 11.1 [11.1–70.1] | 15.4 [14.8–17.3] | 25 [25–26] | 3 [3–4] | 1 | 1 / 0 | 1728 [1711–2000] | 2664 |
| atlas | warm | 8.0.0 | 3 | 14.7 [14.7–18.8] | 0.0 | 0.0 | 14.7 [14.7–18.8] | 0 | 0 | 0 | 0 / 0 | 0 | 2664 |
| optimize | cold | 7.8.0 | 3 | 11.2 [10.3–13.5] | 5.6 [5.2–5.9] | 1.0 | 4.3 [4.1–6.9] | 6 | 1 | 0 | 0 / 0 | 2047 [1891–2146] | 2490 |
| optimize | cold | 8.0.0 | 3 | 9.9 [7.4–13.3] | 3.5 [3.4–3.7] | 0.0 | 6.5 [3.7–9.9] | 5 | 0 | 0 | 0 / 0 | 1772 [1613–1804] | 2589 |
| optimize | warm | 7.8.0 | 3 | 11.4 [9.8–12.1] | 5.5 [5.0–5.8] | 1.0 | 4.9 [3.7–5.3] | 6 | 1 | 0 | 0 / 0 | 2042 [1844–2273] | 2490 |
| optimize | warm | 8.0.0 | 3 | 4.9 [2.9–5.5] | 0.0 | 0.0 | 4.9 [2.9–5.5] | 0 | 0 | 0 | 0 / 0 | 0 | 2590 |
| audit-planted | cold | 7.8.0 | 3 | 63.6 [54.3–64.1] | 31.9 [31.2–32.9] | 7.5 | 23.7 [15.6–24.1] | 41 | 17 | 0 | 0 / 0 | 2083 [2014–2228] | 11930 |
| audit-planted | cold | 8.0.0 | 3 | 54.3 [54.2–70.3] | 32.8 [31.6–33.2] | 0.7 [0.7–0.7] | 21.9 [20.3–36.8] | 41 | 17 | 0 | 0 / 0 | 1906 [1898–2700] | 12567 |
| audit-planted | warm | 7.8.0 | 3 | 58.3 [58.2–65.7] | 33.8 [33.2–34.3] | 7.5 | 16.9 [16.4–25.0] | 41 | 17 | 0 | 0 / 0 | 2463 [2196–2842] | 11930 |
| audit-planted | warm | 8.0.0 | 3 | 54.1 [51.4–72.5] | 32.6 [31.8–33.0] | 0.7 [0.6–0.7] | 20.3 [18.8–39.2] | 41 | 17 | 0 | 0 / 0 | 2148 [1993–2486] | 12567 |

Over all Tier 1 runs, 7.8.0 made 925 requests and got one 429 (no 5xx). 8.0.0 made 600 requests and got none.

### Planted-error detection

| | 7.8.0 | 8.0.0 |
|---|---|---|
| Planted problems found | 114 / 114 (38 per run × 3 repeats) | 114 / 114 |
| Missed | none | none |
| Other non-passing checks (false alarms) | none | none |
| Clean decks (bracket 3 and 2) | every check passed | every check passed |

Both versions found every planted problem in every run, with the right check id, status and card. That includes all nine in the combined deck, so there is no regression.

The 17 duplicate requests in this scenario are the same lookups repeated across the 13 decks, such as the commander check, which is identical for every deck. 8.0 audits run with `--fresh`, which re-reads all card data on purpose, so the cache doesn't help them. A single real audit has no duplicates.

## Tier 2 results

Median over 4 runs per case and version, [min–max] when they differ. Tokens are per run. "Denied" counts tool calls the eval sandbox refused; every tool error in these runs was such a denial.

| Case | Version | Runs | Passed | Cost USD | Duration s | Turns | Uncached in | Cache write | Cache read | Output | Tool calls | Dup | Errors | Denied | Subagents |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| act-lookup-banned | 7.8.0 | 4 | 4/4 | 0.178 [0.101–0.181] | 29 [26–36] | 3 [3–5] | 13700 [13332–13730] | 8421 [8280–8444] | 32934 [32929–61021] | 2066 [1931–2365] | 2 [2–4] | 0 | 0 | 0 | 0 |
| act-lookup-banned | 8.0.0 | 4 | 4/4 | 0.176 [0.173–0.179] | 31 [25–33] | 3 | 13326 [13170–13565] | 8364 [8331–8434] | 33000 [32956–33012] | 1894 [1798–2077] | 2 | 0 | 0 | 0 | 0 |
| act-present-not-for-text | 7.8.0 | 4 | 2/4 | 0.112 [0.099–0.128] | 23 [19–25] | 6 [6–7] | 11 [10–12] | 9868 [8472–11612] | 62642 [60505–67285] | 1001 [977–1118] | 5 [4–5] | 0 | 2 [1–4] | 2 [1–4] | 0 |
| act-present-not-for-text | 8.0.0 | 4 | 1/4 | 0.127 [0.099–0.133] | 22 [18–25] | 6 [6–7] | 11 [8–12] | 11796 [8513–12147] | 59525 [46562–65216] | 1074 [968–1132] | 4 [4–5] | 0 | 3 [1–4] | 3 [1–4] | 0 |
| act-research-anti-venom | 7.8.0 | 4 | 0/4 | 0.125 [0.123–0.131] | 25 [23–30] | 5 [5–6] | 10 [10–12] | 11034 [10970–11525] | 53181 [53066–53441] | 1298 [1190–1400] | 3 [3–4] | 0 | 2 | 2 | 0 |
| act-research-anti-venom | 8.0.0 | 4 | 0/4 | 0.131 [0.125–0.137] | 28 [24–30] | 5 [5–6] | 8 [8–12] | 11684 [11616–12540] | 36711 [36699–54791] | 1348 [1203–1565] | 3 [3–4] | 0 | 2 | 2 | 0 |
| asks-before-building | 7.8.0 | 4 | 4/4 | 0.137 [0.133–0.139] | 38 [34–44] | 6 [5–6] | 9 [8–10] | 10874 [10872–10897] | 44484 [35866–53126] | 1994 [1903–2014] | 4 [3–4] | 0 | 2 | 2 | 0 |
| asks-before-building | 8.0.0 | 4 | 1/4 | 0.149 [0.141–0.155] | 36 [32–41] | 7 [6–7] | 10 [8–10] | 11860 [11831–11896] | 54677 [36461–54729] | 2130 [1936–2445] | 5 [4–5] | 0 | 3 | 3 | 0 |
| gate-explicit-change | 7.8.0 | 4 | 1/4 | 0.124 [0.121–0.252] | 28 [21–51] | 6 [6–18] | 12 [10–22] | 11123 [11095–16587] | 70012 [53183–153025] | 1052 [986–4431] | 4 [4–16] | 0 | 3 [2–3] | 3 [2–3] | 0 |
| gate-explicit-change | 8.0.0 | 4 | 1/4 | 0.123 [0.122–0.213] | 25 [24–42] | 6 [6–14] | 10 [10–12] | 11718 [11697–15727] | 54373 [54331–73830] | 906 [829–3587] | 4 [4–12] | 0 | 3 [1–3] | 3 [1–3] | 0 |
| review-planted-errors | 7.8.0 | 4 | 4/4 | 0.179 [0.157–0.214] | 60 [45–75] | 10 [7–12] | 14338 [12–38616] | 12459 [11385–14234] | 80065 [52439–108244] | 4426 [2548–6967] | 8 [5–10] | 0 | 1 [0–2] | 1 [0–2] | 0 |
| review-planted-errors | 8.0.0 | 4 | 4/4 | 0.194 [0.158–0.268] | 62 [43–84] | 12 [8–14] | 37692 [14–41781] | 14004 [11777–16776] | 101032 [71091–136001] | 6084 [2414–8994] | 10 [6–12] | 0 | 2 [2–3] | 2 [2–3] | 0 |

Totals over the 24 runs per version:

| | 7.8.0 | 8.0.0 |
|---|---|---|
| Runs passed | 15 / 24 | 11 / 24 |
| Agent cost (eval `costUsd`) | $3.49 | $3.70 |
| Judge cost | $0.013 | $0.009 |
| Duration, summed | 832 s | 829 s |
| Tokens: uncached input | 121,943 | 170,726 |
| Tokens: cache creation | 261,929 | 280,136 |
| Tokens: cache read | 1,470,767 | 1,374,314 |
| Tokens: output | 51,505 | 55,819 |
| Tool calls | 115 | 119 |
| Permission denials | 40 | 50 |
| Subagents | 0 | 0 |

The whole benchmark, Tier 2 included, cost about $7.40 of model usage (48 paired runs plus one format check).

## What improved

### Building a themed deck and its report (build)
- **Cold:** 32.1 s → 14.4 s median. Requests 37 → 15, duplicates 14 → 0.
- **Warm:** 36.4 s → 6.0 s. Requests 37 → 0.
- **Why:**
  - 7.8's `deck_check` slept a fixed 0.5 s after every Scryfall call. The probe logged each sleep and its code line: 13.5 s of them came from `--cheapest`'s printing searches alone. 8.0 waits only when its shared pacing clock requires it, 3.0 s in total.
  - 7.8's page builder fetched card data that `deck_check` had already fetched (the 14 duplicates). 8.0 reads it from the cache.
  - As a result, network time fell from 8.9 s to 3.6 s. Local time stayed the same (7.1 s vs 7.4 s).

### Page with packed card images (atlas)
- **Cold:** 36.1 s → 24.4 s. Requests 103 → 92, duplicates 3 → 0, waiting 11.1 s → 3.0 s.
- **Warm:** 34.1 s → 14.7 s. Requests 25 → 0.
- **Why:** both versions keep downloaded images, so neither downloads any on a warm run. 7.8 still re-requested its card data.

### Re-checks and resumed work (every warm run)
- **Warm:** 8.0 made no requests in any warm run. Optimisation (check, 5 swaps, re-check, validate) went from 11.4 s to 4.9 s, and the research card-data step from 6.8 s to 1.5 s.
- **Cold:** optimisation 11.2 s → 9.9 s (6 → 5 requests, 1 → 0 duplicates). Research 5.5 s → 3.8 s (4 → 3 requests).

### Quick lookups
- **Time:** about the same on a cold cache: 1.4 s for one card on both. With ten cards, 1.8 s → 1.4 s cold and 1.4 s → 0.9 s warm. The difference is 7.8's fixed 0.5 s sleep.
- **What Claude has to read:**
  - 8.0 prints the facts, one line per card: 79 bytes for one card, 822 bytes for ten.
  - 7.8 printed a 130-byte pass line and wrote the data to a JSON file that Claude then had to open: 1,477 bytes for one card, 11,678 bytes for ten.
  - That is about 19× (one card) and 14× (ten cards) fewer bytes to read. Whether this lowers tokens or cost in a real session wasn't measured, because the eval sandbox can't run scripts (see Limitations).

### Audits
- **Correctness:** unchanged and complete, 114 / 114 on both versions.
- **Time:** 13 audits took 63.6 s → 54.3 s cold. Both made the same 41 requests with the same network time (about 32 s). The difference is 7.8's fixed sleeps: waiting fell from 7.5 s to 0.7 s.

### Rate limits
- **8.0:** no 429 or 5xx in 600 requests, with its shared pacing.
- **7.8:** one 429 in 925 requests. That single 429 made one 7.8 run take 90.9 s instead of about 34 s. The probe shows a 59 s sleep in `deck_check.py`'s retry (`sleep(min(wait, MAX_WAIT))`), honouring Scryfall's Retry-After.
- **Caveat:** one 429 in 45 runs is consistent with 8.0's pacing being safer, but not enough to show it.

## What didn't improve, or is inconclusive

### Claude end to end (Tier 2): no measured saving, and one possible regression
- **Cost and time:**
  - Total agent cost went from $3.49 to $3.70 (+6%) over 24 runs each. Summed duration went from 832 s to 829 s.
  - Median cost per case changed by between −1% (lookup) and +13% (present). Every range overlaps.
- **Cache writes:**
  - They were 5–20% higher in every case that loaded a skill, for example asks-before-building 10,874 → 11,860 tokens. They were unchanged in the one case that loaded no skill (the lookup).
  - That matches the skill instructions growing by 7–15%: each SKILL.md is 0.5–1.4 KB larger.
  - Each skill now also tells Claude to read the new shared `references/writing.md` (7.8 KB) before its first reply. The eval sandbox refused those reads (see Limitations), so their real token cost wasn't measured.
- **Quality:**
  - Runs passed went from 15/24 to 11/24. Most failing runs failed for reasons outside the plugin (see the next item).
  - One difference may be real: **asks-before-building passed 4/4 on 7.8 and 1/4 on 8.0.** In both versions the reply recommends a bracket and asks one main question. The grader requires asking about at least two things (bracket, budget, fun, cards). 8.0's replies mention budget only in passing.
  - The judges split on several of these runs (FAIL FAIL PASS, FAIL PASS FAIL), as they did on two of 7.8's passes. The brew skill itself also says "ask one meaningful question at a time", which partly conflicts with this grader. Treat it as a possible regression to check, not a proven one.
- **Cases that couldn't pass on either version:**
  - **act-research-anti-venom:** 0/4 on both. Since 7.7, research asks which tools to use before its first search. A one-turn eval can't answer, so no sources are ever cited.
  - **gate-explicit-change** (1/4 on both) and **act-present-not-for-text** (2/4 → 1/4): in the failing runs, Claude looked for the saved project in the sandbox's home folder, was refused, and said it couldn't open the project. This happened on both versions.

### Local time
Local work didn't get faster: Python start-up through uv, page building, image packing and the cast-by-turn simulation. It is now most of what's left: 7.4 s of the 14.4 s cold build, and all of every warm run. See the opportunities below.

### The earlier slow cold builds (26 s, 77 s and 85 s)
- **Not reproduced:** in the 3 paired runs on the committed 8.0.0 code, the cold build took 13.2–17.7 s, with no failed request, no 429 and no 5xx.
- **Why the earlier runs can't be explained after the fact:**
  - They ran on a working tree that other agents were editing.
  - The old probe timed requests only until the headers arrived, so a slow body read was invisible.
  - It didn't log sleeps.
- **What fits the evidence:**
  - **The 85 s run** (a 69 s `deck_check` step with one failed request) fits the 429 pattern measured above: one 429 with a Retry-After of about 60 s. 8.0 honours Retry-After up to 60 s and holds that endpoint's bucket for every process, so one 429 still costs up to a minute.
  - **The 77 s run** (65 s for 9 requests, none failed) fits either a stalled body read or work the probe can't see. 8.0 allows 60 s per attempt for a read. Uv rebuilding a script environment after a file changed would also be invisible to the probe.
- **Next time:** the probe now records slow body reads and every sleep, so a repeat would show which.

## Limitations
- **Network noise:** one home connection and 3 repeats. Requests took up to 2.8 s, and there was one 429 in 1,525 requests. The retry and breaker paths for 5xx and timeouts were never exercised here; the unit tests cover them.
- **Machine load:** repeat 1 ran while the Tier 2 evals ran, so its local times are higher on both sides. For example, the 8.0 audits had 37 s of local time in repeat 1 against 20–22 s later. The medians absorb this; the max values show it.
- **Discarded data:**
  - The first attempt at repeat 2 crashed halfway. The probe tore a log line when the atlas step's 8 download threads wrote at the same time.
  - The partial repeat was discarded and repeats 2–3 were run again in full.
  - The probe now locks its writes, and the harness counts any unreadable line. There have been none since.
- **The eval sandbox can't run scripts:**
  - Bash can't be granted to evals on Windows, so Tier 2 never runs `deck_check`, `card_lookup` or any other script.
  - The planted-errors case passed on both versions by checking cards with WebFetch instead.
  - Tier 1's gains therefore don't show up in Tier 2, and Tier 2 can't show them.
- **The eval sandbox also refused file reads outside its working folder:**
  - 40 denials on 7.8 and 50 on 8.0, over 24 runs each.
  - They hit the plugin's own `references/*.md` and `schemas/README.md`, and the sandbox's home folder.
  - So Tier 2 measured the SKILL.md bodies without their references, and 8.0's new `writing.md` was never read.
- **Small N and judging:** 4 runs per case. The LLM graders are haiku with 3 votes each, and several verdicts were split.
- **Tokens:** taken from the CLI's per-model totals in each trace. Per-message usage in the stream is partial, so it isn't summed.
- **Not measured:**
  - Real sessions on 8.0. Only the 7.7 Azula session exists, in `results/session-azula-7.7.json`.
  - Research quality end to end, mobile, and long multi-session use.

## Remaining opportunities, ranked by measured cost
These are what the parts cost now in the runs above, not predicted savings.

1. **Image packing (`build_site.py` with atlas images):** about 10 s of local work on every page build, cold or warm. It is the same in both versions (10.0 s → 9.9 s warm) and is the largest single script cost left.
2. **Page data step:** 4.4 s warm and 5.3 s cold, nearly all local.
   - It starts `deck_check` through uv once per variant, plus once per group of loose card names (research commanders, rankings, adds). Each start costs about 0.75 s (measured separately).
   - It runs the 20,000-game cast-by-turn simulation once per variant, at about 0.6 s each (measured separately).
   - The build has usually just run `deck_check` on the same deck.
3. **Cache writes commit one at a time:**
   - In a profiled 8.0 `deck_check` run, 238 SQLite statements took 0.58 s of 6.2 s.
   - Each card is stored twice, each in its own commit.
   - This happens on every script call. That includes `--fresh` audits, where the cache can't speed up the run itself.
4. **Let Tier 2 see the plugin:**
   - The sandbox refused 90 file tool calls (Read, Glob, Grep) in 48 runs, and two cases fail on both versions for environment reasons.
   - Tier 2 can't measure the main 8.0 changes until evals can read references and run scripts, or a research case has saved tool preferences.
   - This blocks measurement rather than costing time directly.
5. **Re-check asks-before-building:**
   - Run it more times.
   - Decide which behaviour is intended: the grader's "at least two" questions or the skill's "one question at a time" rule.

## Files and how to reproduce
- `tests/bench/bench.py`: Tier 1 harness. `--table FILE…` prints the Markdown table above.
- `tests/bench/sitecustomize.py`: request and sleep probe. It loads only when `EDHC_BENCH_LOG` is set.
- `tests/bench/session_stats.py`: reads session transcripts, and eval results with `--eval`.
- `tests/fixtures/planted-errors/`: the planted-error decks and `expected.json`.
- Results (aggregates only, no paths or message content):
  - `tests/bench/results/tier1-7.8.0-vs-8.0.0.json` (repeat 1) and `tier1-7.8.0-vs-8.0.0-r2r3.json` (repeats 2–3).
  - `tests/bench/results/tier2-evals-7.8.0-vs-8.0.0.json` (48 eval runs).
  - The other files in `results/` come from earlier, unpaired runs with the old probe on a working tree under edit. They are superseded.

```
git worktree add --detach <tmp>/base 718ada9
git worktree add --detach <tmp>/after d7d5ecb
uv run --python 3.12 python tests/bench/bench.py LABEL --root base=<tmp>/base --root after=<tmp>/after --repeat 3 --pause 20
python tests/bench/bench.py --table tests/bench/results/LABEL.json
# Tier 2, from each worktree's plugins/edh-companion (flags above), then:
python tests/bench/session_stats.py --eval <aggregate-result.json or --json output> ... --json OUT
```
