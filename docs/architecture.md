# Architecture

## Pieces
| Piece | Where | Why it exists |
|---|---|---|
| 4 skills + setup | `plugins/edh-companion/skills/` | The product. Each owns one job and its references (loaded only when needed). |
| Project files contract | `plugins/edh-companion/schemas/README.md` + 3 JSON schemas | How skills share work: Markdown for goals and decisions, JSON for citations, decks and checks. |
| `companion.py` | `plugins/edh-companion/scripts/` | Finds the workspace; validates a project (schemas, citation IDs, stale audits). |
| `deck_check.py` | `skills/audit/scripts/` | Deterministic deck checks from Scryfall + Commander Spellbook APIs. Exists because a tested MCP validator was down and its bracket estimator missed Game Changers and a banned card; same deck, same answer, every time. |
| Page pipeline | `skills/present/scripts/`, `skills/present/assets/template.html` | Reuses the established deck-browser template; builds image atlases because claude.ai artifacts block hotlinked images. |
| 2 agents | `plugins/edh-companion/agents/` | `researcher` for parallel research of independent subjects; `auditor` so work made in a chat is judged in a fresh context. |
| Evals | `plugins/edh-companion/evals/` | `claude plugin eval` cases: activation, persistence, theme drift, art, claims. Inside the plugin because the eval runner reads them there. |

Not included on purpose: MCP servers, databases, a collection manager, hooks, a web app. Optional MCPs are discovered at runtime by capability.

## Flow
Research → Brew → Audit → Present is the common path, not a pipeline: each skill runs on its own and calls another only when the request needs it.
- brew calls research when a decision lacks evidence, and audit at decision boundaries (a finished version, export).
- audit never edits; its fixes go back to the player as proposals.
- present is opt-in and copies audit results as they are.

## State
Per project: `PROJECT.md` (goals), `STATE.md` (progress, next steps), `DECISIONS.md` (append-only), `research.json`, `brew*.json`, `audit*.json`, `decklists/` (versioned), `reports/`. Audits record the deck version and hash they checked; a mismatch means the audit is out of date. Claude's automatic memory is never the record.

## Tested vs not
See the latest CHANGELOG entry and `tests/`. Unit tests cover parsing, hashing, deterministic checks, project validation and page building; evals cover skill activation and key behaviours. Real-device mobile testing and long multi-session use are not automated.
