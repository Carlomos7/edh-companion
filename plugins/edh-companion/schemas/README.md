# Project files

All four skills work from one folder per project, outside the plugin. This file is the single description of that folder; skills link here instead of repeating it. How replies and file prose are written for the player: [references/writing.md](../references/writing.md).

## Where projects live
One persistent workspace, the same wherever Claude Code is started:
1. `$EDH_COMPANION_HOME`, if set.
2. `./EDHCompanion/` in the current folder **only if it contains `workspace.yaml`** (the player chose to keep a workspace there; setup creates the marker). A stray `EDHCompanion` folder without it is ignored and mentioned.
3. The `workspace:` in the config file, if set.
4. `~/Documents/EDHCompanion/`.

Config file: `~/.config/edh-companion/config.yaml` (optional; see the setup skill). `companion.py where` prints the resolved paths. Ask about the location only if the player wants it elsewhere or the default can't be written; otherwise just use it.

## Starting a session
- **Started inside a project?** If the current folder or one of its parents has a PROJECT.md (or sits directly under `<workspace>/projects/`), that's the project: read it and carry on, no questions.
- **Creating and resuming is conversational.** "Start a Spider-Man project" creates `<workspace>/projects/<slug>/` (writing the first file creates the folder); "let's get back to my Doom deck" finds it by name. Players never need to make or open folders themselves.
- Otherwise, when a request is about a deck, commander or report and no project is named, check what exists first: `uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/companion.py" projects` (without a shell: list the folders in `<workspace>/projects/` directly, using the workspace order above, and read each STATE.md first line; don't search by guessed names). If something matches, offer to resume it in one line ("You have a Spider-Gwen project from Nov 4, last step: upgrade pass. Continue that?"). Unrelated projects stay separate unless the player asks to combine them.

## Showcases (several projects in one report)
```text
EDHCompanion/showcases/<name>/
├── showcase.yaml   which projects, how they're grouped, the mode and the theme
└── report/         generated page (never edited by hand)
```
```yaml
title: Marvel Commander Showcase
mode: showcase          # summary | interactive | showcase
theme: null             # optional, see Report themes
projects:
  - project: spider-gwen
    group: Heroes
  - project: doom
    group: Villains
```
Projects keep their own files, decisions and audits; a showcase only points at them. When a new report is requested and a showcase already exists that fits (same theme, same player, related decks), offer to add the deck to it (as a new tab, a variant, or in a group) instead of a separate report; once the player agrees, that grouping is saved in showcase.yaml and reused without asking again. Regenerate reports from the source files; never edit generated HTML.

## Report themes
Pages take accent colors from each commander's color identity automatically. A saved theme overrides that: `<project>/report-theme.yaml` or `theme:` in showcase.yaml (whole report or per project), e.g.
```yaml
accent: "#c8102e"
accent2: "#1f3a93"
style: comic        # comic | gothic | flames | null
label: Spider-Man comic
```
Precedence: a theme the player asks for now > the saved theme > the commander's colors > neutral. Save a theme only when the player wants it kept.

## One project
```text
EDHCompanion/projects/<project>/     project = commander or idea slug, e.g. spider-man-marvel
├── PROJECT.md      goals and restrictions, in Markdown                  (any skill, when the player states them)
├── STATE.md        where things stand, open questions, next steps       (any skill, after meaningful progress)
├── DECISIONS.md    what the player accepted, rejected or allowed, why   (any skill, when the player decides)
├── RESEARCH.md     readable research summary with citations             (research)
├── research.json   sources and findings, for citations and checks       (research)
├── research.plan.json  expected parallel workers and their ID prefixes  (research, only when parallel)
├── research.part-<slug>.json  one worker's findings until merged         (researcher agents; merge-research files them in research.parts/)
├── candidates.json verified card candidates for brew, evidence kept     (candidates.py; regenerate, never edit)
├── brew.json       accepted deck, proposals, statistics                 (brew)   brew-<variant>.json for variants
├── audit.json      checks and verdict for one deck version              (audit)  audit-<variant>.json for variants
├── ACQUISITION.md  optional: how to get the cards, with dated prices   (brew, on request)
├── decklists/      main-v1.txt, main-v2.txt, b4-v1.txt ... importable lists, never overwritten
└── reports/        index.html + img/ and presentation-checks.md         (present)
```
Create only what the task needs. A research question writes RESEARCH.md and research.json and nothing else.

Markdown is the source of truth for goals and decisions; JSON is used where structure pays for itself (citations, decklists with printings, automated checks, pages). Schemas: `research.schema.json`, `research-plan.schema.json`, `candidates.schema.json`, `brew.schema.json`, `audit.schema.json`. Check a project with `uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/companion.py" validate <project>`: schemas, citation IDs (including rankings, disagreements and feasibility), EDHREC number consistency, duplicate source URLs, future dates, unmerged worker parts ("research incomplete"), stale candidates and stale audits.

## Card data and the cache
Scripts get card data through the shared core (`scripts/edhcore/`), never by hand: `card_lookup.py` for lookups and searches, `deck_check.py` for decks, `candidates.py` for research candidates. They share a cache in `~/.cache/edh-companion/` (outside the workspace; disposable; `EDHC_CACHE_DIR` moves it, `EDHC_NO_CACHE=1` turns it off), one rate limit across parallel processes, and retries per endpoint. Freshness: card text 7 days; legality, Game Changers, prices and searches 24 hours; `--fresh` re-reads everything (audits use it). Every result has a `data` block (`fresh`, `cached`, `stale` = an older copy used because the refresh failed, `unavailable`); anything that relied on stale or unavailable data is `unverified`. Providers excluded in the research preferences are never called; `--offline` uses the cache only.

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
- Gameplay: about $150, flexible target (hard limit: no)
- Aesthetics: up to $150 extra for premium printings; foils and borderless welcome, cohesive comic-art look
- Style: drippy (others: just build it, cheap, budget, no expense spared)
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
`src-001` sources and `fnd-001` findings (research.json), `rec-001` recommendations (brew.json), `chk-<area>-<n>` checks (audit.json). Parallel research workers use their slug: `src-yt-001`, `fnd-cards-003`, so parts never collide; merging keeps every existing ID. IDs are never reused; new items take the next number. brew.json `deck[].evidence` carries a card's IDs from candidates.json into the deck. Readable files cite them in brackets: "Gwenom wants cheap spells [fnd-004, src-012]". Chat replies name the source and moment instead, with the ID only as a pointer ([writing.md](../references/writing.md), "Facts, citations and money").

## Findings and checks
Optional fields that keep claims, locations and methods apart, so files and pages stay readable (older files without them stay valid):
- **research.json `findings[]`**: one claim per finding. `headline` is the conclusion in about 90 characters or fewer; `claim` says it in 1 to 3 sentences with no citation brackets or timestamps in the text; `locators` says where in each cited source this claim is supported: `[{"source": "src-101", "at": ["9:00", "9:40-10:40"]}]` (mm:ss or h:mm:ss, ranges allowed; videos mainly). Long card lists go in `cards`, reasoning in `explanation`, what weakens the claim in `limitations`. Method: research's [method.md](../skills/research/references/method.md), "Writing findings".
- **research.json `scope.deck`**: for research about an existing deck, the deck it was written for (`{version, deck_hash}`, the same shape as audit.json `subject.deck`). When brew.json has moved on, the research isn't silently current: say which version it describes and flag claims about cards or plans that changed.
- **research.json `methodology.stopped_because`**: why research stopped (questions answered, saturation, a limit, a tool failure).
- **audit.json `checks[].method`**: how the check was done (the deck_check command and its inputs, hashes, sources or images opened). `detail` then holds only the result. Checks done the same way share identical `method` text.

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

## When to ask (and when not to)
Three different things; don't mix them up:
1. **Research preferences**: which research tools are approved, how often to check in, how deep to go. Asked once, saved, reused (research's sources.md, "Research approval").
2. **Consequential actions**: the gates below, asked in the moment.
3. **Claude Code's tool permissions**: Claude Code's own prompts; separate, and never bypassed or worked around.

**Ask first** (one short, conversational question with a recommended answer):
- Changing the accepted deck (adding, cutting, swapping, changing printings), unless the player just asked for that exact change.
- Relaxing or reinterpreting a hard rule (theme, art, budget limit, bracket, hard lines, ownership).
- Moving, merging, renaming or deleting the player's files or projects.
- Publishing or sharing anything outside their machine (an Artifact link, a post), or putting private project data in it.
- Anything with real-world consequences (an account change on a deck site, a purchase-like action).
- **Unexpectedly expensive work**: a very large download, substantial research beyond what's approved (much deeper than their default, many long videos), or a costly API operation. Say what it's for, what it gains, roughly how long and how many tokens or what cost, and a cheaper recommended alternative.

**Don't ask** when the request or saved preferences already cover it:
- What the player explicitly asked for ("swap Sol Ring for Mind Stone", "make a page", "audit it") is the approval: do it (still keeping the old version).
- Approved research at the saved depth, including all the Scryfall searches that depth needs (exhaustive printing and theme searches count as part of comprehensive research).
- Ordinary lookups, audits, routine research, validation, and reports the player asked for.
- Using an approved equivalent tool when one fails (e.g. a second approved search tool). Ask before an unapproved or excluded one.

**Show progress without stopping:** announce substantial work, give progress updates at natural milestones and finish with what was done ([writing.md](../references/writing.md), "Multi-step work"). Don't pause for confirmation in the middle unless a gate above is hit.

**Never**, approved or not: overwrite an accepted decklist version (add a new one), erase research or decisions, or publish private project data silently.

## Missing values
Unknown is `null` or a listed gap, never a guess. A check that couldn't run is `unverified` with the reason.
