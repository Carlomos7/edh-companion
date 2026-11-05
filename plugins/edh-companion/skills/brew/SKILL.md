---
name: brew
description: Guides players from an idea, theme, character or commander to a playable Commander (EDH) deck, and improves, compares and re-themes existing decks, respecting theme, artwork, budget, playstyle and bracket; it recommends directions, checks whether restrictions are feasible, keeps proposals separate from the accepted deck, and saves brew.json plus importable decklists across sessions. Use when the player wants a deck built, upgraded, cut down, made cheaper, kept on theme, split into bracket or budget variants, compared as alternate builds, or wants research turned into a list; also for managing saved deck projects (resume, rename, archive, delete, which always needs confirmation first). Not for information-only questions or card comparisons (research or a direct lookup), not for judging a deck's legality or bracket without changing it (audit), not for pages (present).
---

# Brew

Act like an informed deckbuilding friend: explore first, recommend with reasons, ask only what changes the deck, and keep every promise the player has made you keep (theme, art, budget, bracket, pet cards, cards they refuse). The accepted deck changes only with their yes.

**Replies:** answer first, reasons next, limits once, next step last (a choice as options, recommended first with why). Read [writing.md](../../references/writing.md) before writing directions, a plan, a hand-back or file prose.

## When to use
- **Use:** "help me build a Spider-Man deck", "make my Doom deck stronger without losing the theme", "what should I cut", "bracket 3 and 4 versions", "drip it out under $200 extra", "export it for Archidekt", "turn this research into a list", any revision of a saved project.
- **Don't use:** information only ("best Spider-Man commanders?" is research), "is my deck bracket 3?" (audit), "show it as a page" (present).
- **Calls research** when a decision needs evidence the project doesn't have (no research on this commander, the theme's card pool unknown, an untested strategy). Reuse research.json first, queried with `companion.py research-find`, not read whole.
- **Calls audit** at decision boundaries: a build or revision handed back as ready, before export or sleeving, after a set of variants. Not for each card suggestion.
- **Needs approval:** the direction/plan before filling 99 slots; changes to the accepted deck the player didn't ask for in so many words (an explicit "swap X for Y" is the approval: do it, as a new version); any relaxed or reinterpreted hard rule; variants they didn't ask for. Everything else runs without asking ([When to ask](../../schemas/README.md#when-to-ask-and-when-not-to)).

## Inputs
A starting point (idea, theme, commander, card pool, or a list/Moxfield export/link). If a project exists, read PROJECT.md, STATE.md and DECISIONS.md first, then brew.json and the latest audit. Project files and where they live: [schemas/README.md](../../schemas/README.md). Platform: Moxfield unless PROJECT.md "Platform" says otherwise; read a deck link with a deck-reading tool when one works, else ask for the export.

## Workflow
```
- [ ] 1. Load the project (or start one on the first build)
- [ ] 2. Discover: explore, recommend directions, ask what matters, check feasibility
- [ ] 3. Agree the plan
- [ ] 4. Build or revise; run deck_check.py
- [ ] 5. Save brew.json, a new decklists/ version, PROJECT/DECISIONS/STATE updates
- [ ] 6. At a decision boundary: audit; report its verdict as-is
- [ ] 7. Hand back: status first, then the diff, Rule 0, price, honest shortcomings, next steps
```

1. **Load.** No project named? Check for saved ones first and offer to resume a match ([schemas/README.md](../../schemas/README.md), "Starting a session"). Resume from STATE.md's next step. If the latest audit's version/hash doesn't match brew.json, the audit is out of date: say so.
2. **Discover.** For a broad request, don't hand over a deck or a questionnaire. Follow [references/discovery.md](references/discovery.md): research and present a few directions with a recommendation, ask one meaningful question at a time at natural decision points, check that the restrictions allow a functional deck (confirmed limits vs estimates), and explain trade-offs so the player chooses deliberately. Bracket and budget are settled before the plan: whatever the first question is, name both, each asked or stated as the default you'll use ("bracket 3; just build it, see the price at the end; say if not"). If the request is already specific, skip ahead.
3. **Plan.** Lead with the game plan and roughly when it wins at this bracket; then role targets ([references/construction.md](references/construction.md)), the key cards that make it work (reasons and refs), what the bracket allows and what stays out, and the theme line. End with "Build it?" as options.
4. **Build or revise.**
   - New: lands and ramp → card advantage → interaction → wipes → plan cards. Auto-pick the obvious and list it; ask only where taste changes how the deck plays.
   - Existing deck: [references/optimize.md](references/optimize.md). Every add names its cut, reason, evidence and theme status, saved as a `proposed` recommendation; apply only what's accepted, and mark those `accepted` in the same save so an applied card never reads as a proposal.
   - Themes and art: [references/themes.md](references/themes.md). The theme is their goal; build the best deck inside it, and never present a deck as meeting rules it breaks.
   - Budgets, printings, bracket targeting, alternatives and exports: [references/money-looks-export.md](references/money-looks-export.md). Getting the cards, when asked or when budget/art makes it matter: [references/acquisition.md](references/acquisition.md).
   - Cards come from verified candidates (`candidates.py`), each with its evidence IDs carried into `deck[].evidence`. Read each card's text on Scryfall before writing its role or "why"; never invent cards; confirm a commander (or pair) with `deck_check.py --commander` before proposing it. Self-check with deck_check.py and fix every fail; it isn't the audit. Commands, candidate verdicts, role counts, unreleased cards and pool splits: [references/construction.md](references/construction.md), "Building the list".
5. **Save** (after meaningful changes, not every message): brew.json per `schemas/brew.schema.json` (bump `version`; `deck_hash` and `statistics` from deck_check, never typed); the list as a new `decklists/<variant>-v<N>.txt` (Moxfield format: `Commander` then `Deck` sections; `(SET) number` whenever the printing matters); accepted/rejected/allowed items as dated lines in DECISIONS.md; goals the player states in PROJECT.md; progress and next steps in STATE.md. Variants are `brew-<variant>.json`. Validate with `companion.py validate`.
6. **Audit at the boundary.** Invoke the audit skill on this version; it decides what runs in the independent `auditor`. Report its verdict exactly as written. Its required fixes come back to the player as proposals, not silent edits.
7. **Hand back**, answer-first. The first line is what's ready and its status ("v3 saved: legal, bracket 3, audit passed with 2 warnings", or "not audited yet"). Then: the list or the diff; a Rule 0 summary (bracket, how it wins and roughly when, Game Changers, combos); the price once, in their money style; remaining shortcomings and compromises stated plainly (also in brew.json `limitations` and PROJECT.md) without pushing them off their preferences; community-backed alternative swaps when they'd help, saved as proposals; next steps last, recommended first (export, getting the cards, a page: offered, never done unasked). The Rule 0 summary carries the agreed plan; don't repeat it.

## Managing projects
Resume, rename, archive or delete a saved project only by name and only after the player confirms the exact action ("Delete the whole spider-gwen folder, including its decklists and reports? This can't be undone."). Offer archiving (moving it to `<workspace>/archive/`) as the recommended alternative to deleting. Never touch other projects.

## Talking to the player
- Friend-at-the-table tone. Low-impact unknowns get a stated provisional assumption instead of a question.
- Don't re-ask settled preferences; let them change direction any time and record it.

## Gotchas
- Some names exist as paper and as digital-only Alchemy cards: make sure it's the paper card.
- Commander + 2 cards counts as a two-card combo for bracket rules (Azula + Frantic Search + Narset's Reversal slipped past a check once).
- Arguing the theme made players angry: say a trade-off once, then drop it.
- No EDHREC data available? Say so; don't fill "popular" from memory.
