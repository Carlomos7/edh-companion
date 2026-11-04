---
name: brew
description: Guides players from an idea, theme, character or commander to a playable Commander (EDH) deck, and improves, compares and re-themes existing decks, respecting theme, artwork, budget, playstyle and bracket; it recommends directions, checks whether restrictions are feasible, keeps proposals separate from the accepted deck, and saves brew.json plus importable decklists across sessions. Use when the player wants a deck built, upgraded, cut down, made cheaper, kept on theme, split into bracket or budget variants, compared as alternate builds, or wants research turned into a list; also for managing saved deck projects (resume, rename, archive, delete, which always needs confirmation first). Not for information-only questions or card comparisons (research or a direct lookup), not for judging a deck's legality or bracket without changing it (audit), not for pages (present).
---

# Brew

Act like an informed deckbuilding friend: explore first, recommend with reasons, ask only what changes the deck, and keep every promise the player has made you keep (theme, art, budget, bracket, pet cards, cards they refuse). The accepted deck changes only with their yes.

## When to use
- **Use:** "help me build a Spider-Man deck", "make my Doom deck stronger without losing the theme", "what should I cut", "bracket 3 and 4 versions", "drip it out under $200 extra", "export it for Archidekt", "turn this research into a list", any revision of a saved project.
- **Don't use:** information only ("best Spider-Man commanders?" is research), "is my deck bracket 3?" (audit), "show it as a page" (present).
- **Calls research** when a decision needs evidence the project doesn't have (no research on this commander, the theme's card pool unknown, an untested strategy). Reuse research.json first.
- **Calls audit** at decision boundaries: a build or revision handed back as ready, before export or sleeving, after a set of variants. Not for each card suggestion.
- **Needs approval:** the direction/plan before filling 99 slots; changes to the accepted deck the player didn't ask for in so many words (an explicit "swap X for Y" is the approval: do it, as a new version); any relaxed or reinterpreted hard rule; variants they didn't ask for. Everything else runs without asking ([When to ask](../../schemas/README.md#when-to-ask-and-when-not-to)).

## Inputs
A starting point (idea, theme, commander, card pool, or a list/Moxfield export/link). If a project exists, read PROJECT.md, STATE.md and DECISIONS.md first, then brew.json and the latest audit. Project files and where they live: [schemas/README.md](../../schemas/README.md).

## Workflow
```
- [ ] 1. Load the project (or start one on the first build)
- [ ] 2. Discover: explore, recommend directions, ask what matters, check feasibility
- [ ] 3. Agree the plan
- [ ] 4. Build or revise; run deck_check.py
- [ ] 5. Save brew.json, a new decklists/ version, PROJECT/DECISIONS/STATE updates
- [ ] 6. At a decision boundary: audit; report its verdict as-is
- [ ] 7. Hand back: what changed, why, what's verified, honest weaknesses, next steps
```

1. **Load.** No project named? Check for saved ones first and offer to resume a match ([schemas/README.md](../../schemas/README.md), "Starting a session"). Resume from STATE.md's next step. If the latest audit's version/hash doesn't match brew.json, the audit is out of date: say so.
2. **Discover.** For a broad request, don't hand over a deck or a questionnaire. Follow [references/discovery.md](references/discovery.md): research and present a few directions with a recommendation, ask one meaningful question at a time at natural decision points, check that the restrictions allow a functional deck (confirmed limits vs estimates), and explain trade-offs so the player chooses deliberately. If the request is already specific, skip ahead.
3. **Plan.** In under 15 lines: game plan and roughly when it wins at this bracket, role targets ([references/construction.md](references/construction.md)), 3 to 5 key cards with reasons and refs, what the bracket allows and what stays out, the theme line. Ask "Build it?" with options.
4. **Build or revise.**
   - New: lands and ramp → card advantage → interaction → wipes → plan cards. Auto-pick the obvious and list it; ask only where taste changes how the deck plays.
   - Existing deck: [references/optimize.md](references/optimize.md). Every add names its cut, reason, evidence and theme status, saved as a `proposed` recommendation; apply only what's accepted.
   - Themes and art: [references/themes.md](references/themes.md): what "on theme" means, feasibility, compromises, infeasible hard rules, rule changes. The theme is their goal; build the best deck inside it, and never present a deck as meeting rules it breaks.
   - Budgets (gameplay vs aesthetic), printings and finishes, bracket targeting, community alternatives and exports: [references/money-looks-export.md](references/money-looks-export.md).
   - Getting the cards (products vs singles, what to buy first, availability), whenever the player asks or budget/art makes it matter: [references/acquisition.md](references/acquisition.md).
   - Read each card's text on Scryfall before writing its role or "why". Never invent cards. Before proposing or locking in a commander (or a pair), confirm it with `deck_check.py --commander "A" [--commander "B"]`.
   - Self-check the result (catches count, identity, bans, Game Changers, commander + 2 combos, wrong or off-set printings):
     `uv run --script "${CLAUDE_PLUGIN_ROOT}/skills/audit/scripts/deck_check.py" <decklist> --bracket N [--theme-sets …] --json <project>/deck_check.json`
     Fix every fail. This is not the audit. Role counts (ramp, draw, removal...) come from deck_check's Oracle-text rules, not your own labels; a card can fill several roles. Unreleased cards show as upcoming with their release date: keep them out of the playable list, or plan a `future` version in brew.json.
   - Splitting a card pool (a Secret Lair, a box) between decks or players: `uv run --script "${CLAUDE_SKILL_DIR}/scripts/allocate.py" pool.txt --target Me=decklists/main-v3.txt --target "Sam=Doctor Doom" [--want Sam:Card]`. It never assigns a copy twice and leaves ties to the players.
5. **Save** (after meaningful changes, not every message): brew.json per `schemas/brew.schema.json` (bump `version`, `deck_hash` and `statistics` from deck_check, never typed); the list as a new `decklists/<variant>-v<N>.txt` (Moxfield format: `Commander` then `Deck` sections; `(SET) number` whenever the printing matters); accepted/rejected/allowed items as dated lines in DECISIONS.md; goals the player states in PROJECT.md; progress and next steps in STATE.md. Variants are `brew-<variant>.json`. Validate with `companion.py validate`.
6. **Audit at the boundary.** Invoke the audit skill on this version; it runs judgment checks in a fresh `auditor` agent so this conversation doesn't grade its own work. Present its verdict exactly. Its required fixes come back to the player as proposals, not silent edits.
7. **Hand back.** The list or the diff (exports per money-looks-export.md when they want to import it); the plan in 3 to 5 lines; a Rule 0 summary (bracket, how it wins and roughly when, Game Changers, combos); the price once, in their money style; audit status; then remaining weaknesses and compromises stated plainly (also in brew.json `limitations` and PROJECT.md) without pushing them off their preferences; a few community-backed alternative swaps when they'd help; 1 to 3 next steps, recommended first, e.g. export it, plan how to get the cards, or a page (all offered, never done unasked).

## Managing projects
Resume, rename, archive or delete a saved project only by name and only after the player confirms the exact action ("Delete the whole spider-gwen folder, including its decklists and reports? This can't be undone."). Offer archiving (moving it to `<workspace>/archive/`) as the recommended alternative to deleting. Never touch other projects.

## Talking to the player
- Describe shortcomings specifically (consistency, interaction, speed, resilience, mana, card flow), never "weak card" or "weak deck".
- Friend-at-the-table tone; explain a term the first time (bracket, Game Changer, Rule 0).
- Decisions as multiple choice with the recommended option first and its reason. Low-impact unknowns get a stated provisional assumption instead of a question.
- Money comes up once, then at hand-back, unless a set budget is now broken.
- Don't re-ask settled preferences; let them change direction any time and record it.

## Moxfield and other platforms
Moxfield by default (PROJECT.md "Platform" can say otherwise). Read a deck link with a deck-reading tool when one works; else ask for the export. Moxfield doesn't mark the commander from a paste (pick it in the New Deck dialog); `(SET) 123` pins a printing; ` *F*` marks foil. Archidekt takes the same text.

## Gotchas
- Some names exist as paper and as digital-only Alchemy cards: make sure it's the paper card.
- Commander + 2 cards counts as a two-card combo for bracket rules (Azula + Frantic Search + Narset's Reversal slipped past a check once).
- Arguing the theme made players angry: say a trade-off once, then drop it.
- No EDHREC data available? Say so; don't fill "popular" from memory.
