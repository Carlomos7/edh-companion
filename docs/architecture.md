# Architecture

Hybrid: skills decide and talk to the player; a small shared Python core does the deterministic data work; project files are the record.

## Pieces
| Piece | Where | Why it exists |
|---|---|---|
| 4 skills + setup | `plugins/edh-companion/skills/` | The product. Interaction, research decisions, approvals, deckbuilding judgment, presentation. Each owns one job and its references (loaded only when needed). |
| Project files contract | `plugins/edh-companion/schemas/README.md` + JSON schemas | How skills share work: Markdown for goals and decisions, JSON for citations, candidates, decks and checks. |
| Shared data core `edhcore/` | `plugins/edh-companion/scripts/edhcore/` | One HTTP client, cache, rate limit and card model for every script (below). Exists because three scripts had three HTTP paths, nothing was cached, and parallel workers had no shared rate limit. |
| `card_lookup.py` | `scripts/` | Compact cached card lookups and searches for research and brew, replacing ad-hoc curl/Python (37 such calls in one real research session). |
| `companion.py` | `scripts/` | Workspace, project validation, and research coordination: `research-plan`, `merge-research`, `research-find`. |
| `candidates.py` | `scripts/` | Research findings → verified card candidates (`candidates.json`) for brew, citations kept. |
| `deck_check.py` | `skills/audit/scripts/` | Deterministic deck checks (Scryfall + Commander Spellbook): same deck, same answer. |
| Page pipeline | `skills/present/scripts/`, `assets/template.html` | Deck-browser template; image atlases because artifacts block hotlinked images. |
| 2 agents | `agents/` | `researcher` for independent research subjects; `auditor` so work made in a chat is judged in a fresh context. |
| Evals, tests, benchmarks | `plugins/edh-companion/evals/`, `tests/unit/`, `tests/bench/` | Skill behaviour, script behaviour, measured cost. |

Not included on purpose: MCP servers, a service, external databases, an agent framework, a collection manager, hooks. Optional MCPs (YouTube, Exa, Parallel, Moxfield, MTG data) are discovered at runtime by capability and stay the way research reaches the web.

## The data core
| Module | Responsibility |
|---|---|
| `http` | Retries by failure class, per endpoint (host + path): 429 = wait Retry-After and hold the bucket for every process; 5xx/timeouts = 1-2-4 s backoff, 3 tries; other 4xx = request error, not counted; 3 exhausted calls in a row = that endpoint's breaker opens (60 s doubling to 10 min, then one probe). Never a provider-wide lockout. |
| `cache` | Disposable SQLite in `~/.cache/edh-companion/` (`EDHC_CACHE_DIR`, `EDHC_NO_CACHE=1`): cards, searches, combos, the shared pacing clock and breaker state. Recovery from corruption deletes only its own three files and never in a workspace, project, repo or home dir. |
| `session` | Freshness per data category: oracle facts 7 days; legality, Game Changers, prices, searches, combos 24 h; `--fresh` re-reads everything (audits). A failed refresh falls back to a copy up to 30 days old marked `stale`; nothing usable is `unavailable`. Every result carries `data: {as_of, verification, endpoints_unavailable}`; checks that relied on stale or unavailable data are `unverified`. |
| `policy` | Providers excluded in the player's research preferences (config or PROJECT.md) get no requests; `--offline` / `EDHC_OFFLINE=1` uses the cache only. |
| `scryfall`, `spellbook` (in `session`) | Batched (75 per collection request), cached, paginated access. |
| `cards`, `decklist` | One normalized card record and helpers; one decklist parser. |

## Flow
Research → Brew → Audit → Present is the common path, not a pipeline: each skill runs on its own and calls another only when the request needs it.
- **Research** works inline, or for independent subjects plans workers (`research-plan`), lets each write `research.part-<slug>.json` with its own ID prefix, and merges with `merge-research`, which refuses until every planned worker finished and validated, dedupes sources by URL, keeps existing IDs and conflicting numbers, and is safe to rerun. Prior research is queried with `research-find` instead of reloaded.
- **Research → brew:** `candidates.py` verifies every candidate (exists, legal, in the combined identity, Game Changer vs bracket, upcoming, theme and printings, approved exceptions) and keeps its evidence; only hard rule breaks are `ineligible`, judgment calls are `needs_review`. Brew carries evidence IDs into `deck[].evidence`.
- brew calls audit at decision boundaries; audit runs `deck_check.py --fresh` and judgment in the fresh `auditor` agent; it never edits.
- present is opt-in and copies audit results as they are.

## Token use
Scripts print short summaries and write full data to files; agents reply in ≤10 lines and keep evidence in their part files; prior research is queried by card or topic. Full evidence and citations always stay in the project files.

## State
Per project: `PROJECT.md` (goals), `STATE.md` (progress), `DECISIONS.md` (append-only), `research.json` (+ `research.plan.json`, `research.parts/` history), `candidates.json`, `brew*.json`, `audit*.json`, `decklists/` (versioned), `reports/`. Audits record the deck version and hash they checked; a mismatch means the audit is out of date. Claude's automatic memory is never the record.

## Tested vs not
Unit tests cover the core (failure classes, breaker, freshness, cross-process pacing with real processes, cache safety, provider policy), parsing, deterministic checks, merging, candidates, validation and page building. `tests/bench/` measures script workloads (requests, duplicates, time) and real Claude Code sessions (tokens, context, tool calls) — see `docs/benchmarks.md`. Real-device mobile testing and long multi-session use are not automated.
