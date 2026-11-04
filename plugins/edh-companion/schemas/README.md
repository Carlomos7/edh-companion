# Project files

All four skills work from one folder per project, outside the plugin. This file is the single description of that folder; skills link here instead of repeating it.

## Where projects live
1. `./EDHCompanion/` in the current folder, if it exists (keeps a project next to other work; also used by tests).
2. Otherwise the `workspace:` in the config file, if set (the `setup` skill writes it).
3. Otherwise `~/Documents/EDHCompanion/`.

Config file: `~/.config/edh-companion/config.yaml` (optional; see the setup skill). `python scripts/companion.py where` prints the resolved paths.

## One project
```text
EDHCompanion/projects/<project>/     project = commander or idea slug, e.g. spider-man-marvel
├── PROJECT.md      goals and restrictions, in Markdown                  (any skill, when the player states them)
├── STATE.md        where things stand, open questions, next steps       (any skill, after meaningful progress)
├── DECISIONS.md    what the player accepted, rejected or allowed, why   (any skill, when the player decides)
├── RESEARCH.md     readable research summary with citations             (research)
├── research.json   sources and findings, for citations and checks       (research)
├── brew.json       accepted deck, proposals, statistics                 (brew)   brew-<variant>.json for variants
├── audit.json      checks and verdict for one deck version              (audit)  audit-<variant>.json for variants
├── ACQUISITION.md  optional: how to get the cards, with dated prices   (brew, on request)
├── decklists/      main-v1.txt, main-v2.txt, b4-v1.txt ... importable lists, never overwritten
└── reports/        index.html + img/ and presentation-checks.md         (present)
```
Create only what the task needs. A research question writes RESEARCH.md and research.json and nothing else.

Markdown is the source of truth for goals and decisions; JSON is used where structure pays for itself (citations, decklists with printings, automated checks, pages). Schemas: `research.schema.json`, `brew.schema.json`, `audit.schema.json`. Check a project with `python scripts/companion.py validate <project-dir>`.

## Reading and writing
- Start by reading PROJECT.md, STATE.md and DECISIONS.md (short), then load research.json / brew.json only when needed.
- Update files after meaningful changes (a decision, a new deck version, finished research or audit), not every message.
- Never overwrite an accepted decklist version or erase research: add a new decklist file and bump `version`; extend research.json and keep its IDs.
- A skill writes its own files; any skill may record what the player says in PROJECT.md, DECISIONS.md and STATE.md.
- Don't use Claude's automatic memory for project data; these files are the record.

## PROJECT.md
Plain Markdown with these headings (omit what's unknown):
```markdown
# Spider-Man / Marvel deck
## Goal
A powerful Spider-Man deck that stays true to Marvel.
## Commander
Undecided (candidates in RESEARCH.md)
## Table and power
Bracket 3. Hard lines: no infinite combos, no extra turns.
## Budget
- Gameplay: no limit; show the price at the end
- Aesthetics: up to $150 extra for premium printings; foils and borderless welcome, cohesive comic-art look
## Theme
- Mode: prefer (on theme unless an exception is approved)
- Basis: official franchise cards and art
- Counts as on theme: Spider-Man characters and cards from Spider-Man sets; other Marvel cards when clearly better
- Artwork matters: yes (the printing must show Marvel art)
- Hard rules: no non-Marvel creatures
- Flexible: lands and mana rocks may be off theme if no Marvel version exists
- Allowed exceptions: basic lands, Sol Ring; at most 5 off-theme cards
## Feasibility
Feasible: 140+ eligible nonland cards in Jeskai; removal is thin (6 eligible). Evidence: research.json feasibility.
## Known limitations
Light on board wipes because of the theme (accepted 2026-11-04).
## Research preferences
Prefer EDHREC and Reddit; skip MTGGoldfish.
## Must include / never include
## Platform
Moxfield
```
Theme modes: **none** (best deck) · **printings** (best cards, themed printings when they exist) · **prefer** (on theme unless an approved exception) · **strict** (nothing off theme).
Theme basis (what "on theme" is judged by): **official** (cards or printings from the franchise's own Magic products) · **visual/story** (art and flavor that clearly depict the theme, any set) · **mechanical** (cards that play like the theme, e.g. farming = landfall, food, plants) · **inspired** (a mix, judged case by case with the player).
Hard rules are never bent without the player changing them; flexible preferences can be traded off with a stated reason.

## DECISIONS.md
Append-only, dated, in the player's words where possible:
```markdown
- 2026-11-04 Theme is strict Spider-Man; basics exempt.
- 2026-11-04 Rejected Cyclonic Rift (rec-004): "no off-theme blue staples".
- 2026-11-05 Allowed exception: Sol Ring, any printing.
```
A later request that conflicts with a decision is a question to the player, never a silent override. A rejected card isn't proposed again unless the player asks or the reason no longer applies (say why).

## Versions and stale audits
- `brew.json.version` goes up on every accepted change, with the new `deck_hash` from `deck_check.py` and a new file in `decklists/`.
- `audit.json.subject.deck` records the version and hash it checked, and `subject.goals_hash` (from `companion.py goals-hash <project>`) records PROJECT.md's rules at the time. If either differs now, the audit is **stale**: say so and don't call the deck verified. `companion.py validate` reports stale audits.
- When the player changes a restriction, update PROJECT.md, add a dated DECISIONS.md line, re-check the cards the change affects, and treat earlier audits as stale.

## Card vs printing
A card's **game identity** (name, `oracle_id`) decides rules, legality and color identity. Its **printing** (`printing_id`, set, collector number, finish, `illustration_id`, treatment, price) decides art, theme-by-art, looks, exports and cost. Keep both: a strict art theme, a drippy budget and an exact Moxfield import all depend on the printing, not the card. Prices are per printing and finish, with a date and `verified: true` only when read for that exact printing; anything else is an estimate.

## IDs (citations and checks only)
`src-001` sources and `fnd-001` findings (research.json), `rec-001` recommendations (brew.json), `chk-<area>-<n>` checks (audit.json). IDs are never reused; new items take the next number. Readable files cite them in brackets: "Gwenom wants cheap spells [fnd-004, src-012]".

## Evidence classes
| class | meaning |
|---|---|
| `verified_fact` | read from the authority for that fact (Scryfall, Wizards, Spellbook, Comprehensive Rules) |
| `calculated` | computed from verified data by a script or tool |
| `popularity_metric` | usage statistics with a sample size |
| `community_opinion` | what players or creators say |
| `model_assessment` | Claude's own judgment |
| `unresolved` | not established |

## Recommendations, next steps, questions
research.json, brew.json and audit.json may carry `recommendations`, `recommended_next_steps` and `follow_up_questions` (empty when there's nothing worth saying). STATE.md lists the current next steps and open questions for the player.

## Approval
Changing the accepted deck, relaxing any goal (theme, art, budget, bracket, ownership, hard lines), or starting big work nobody asked for (deep research, several builds, a page) needs the player's yes. Research and audits that serve the current request don't; they never change the deck.

## Missing values
Unknown is `null` or a listed gap, never a guess. A check that couldn't run is `unverified` with the reason.
