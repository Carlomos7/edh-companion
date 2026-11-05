---
name: audit
description: Independently verifies Commander decks, research and recommendations and records each check as pass, warning, fail or unverified in audit.json: real cards, legality, color identity, counts, Game Changers and bracket limits, known combos, theme eligibility, exact printings and artwork, mana and composition, research completeness, and whether recommendations are supported. Use when the player asks whether a deck is legal, on theme, balanced, strong enough or really a given bracket, wants a fact-check or second opinion, is finalizing or exporting a deck, or when another skill's consequential claims (legality, art, combos, brackets, proposed changes) need checking. Not for a single lookup ("is X banned?"), brainstorming, building or fixing decks (brew), or new research (research).
---

# Audit

An audit is worth something only if it can say "fail" and "couldn't check". Each check states the requirement, how it was checked, and the evidence. Nothing passes on reasoning alone.

**Replies:** answer first, reasons next, limits once, next step last (a choice as options, recommended first with why). Read [writing.md](../../references/writing.md) before writing a verdict reply, `verdict.summary` or audit.md.

## When to use
- **Use:** "is my deck really bracket 3?", "is this legal?", "are these all Marvel art?", "fact-check this research", "second opinion before I sleeve it", brew's boundary check on a finished version.
- **Don't use:** one direct lookup ("does this card have Marvel art?" → open the printing and answer; offer a full audit only if they want the deck checked), brainstorming, anything that edits the deck.
- **Independence:** deterministic checks come from `scripts/deck_check.py`. Judgment and source checks on work **produced in this conversation** run in the `auditor` agent, which starts fresh with only the files. A deck the player brought can be audited inline. Record which in `auditor`. Claude re-reading its own reasoning is not verification.
- **Calls research** only when a completeness gap is material and the player wants it filled; otherwise the gap is reported.
- **Needs approval:** nothing; it never edits the deck, research, goals or decisions; run it when asked ([When to ask](../../schemas/README.md#when-to-ask-and-when-not-to)).

## Inputs
The subject: a pasted list, a decklist file, a brew.json, research.json, or a set of recommendations. Optionally the project's PROJECT.md (bracket, theme, budget, hard lines) and DECISIONS.md (approved exceptions). Project files: [schemas/README.md](../../schemas/README.md).

## Workflow
```
- [ ] 1. Identify the subject and its version/deck_hash; list what the goals require
- [ ] 2. Deterministic checks (deck_check.py)
- [ ] 3. Theme and printing checks; look at the art when the theme depends on it
- [ ] 4. Bracket: fixed limits, indicators, then a labelled judgment
- [ ] 5. Composition and mana
- [ ] 6. Research and recommendation checks
- [ ] 7. Verdict and required fixes; write audit.json (+ audit.md for big audits); validate
```

1. **Subject.** Record the brew file, `version`, `deck_hash`, and `goals_hash` (`companion.py goals-hash <project>`). The audit applies to that version and those rules only; a later change to either makes it out of date.
2. **Deterministic checks:**
   `uv run --script "${CLAUDE_SKILL_DIR}/scripts/deck_check.py" <list|brew.json> --bracket N [--commander NAME] [--theme-sets set,set] --fresh --project <project> --json deck_check.json`
   Always `--fresh`; stale or unavailable data makes the affected checks `unverified`. Copy its checks unchanged (command and inputs in `method`, result in `detail`). What it covers, the `data` block and budget flags: [references/checks.md](references/checks.md), "Deterministic checks". If Bash or the network isn't available, do the same checks by hand from Scryfall (count every line, each card's legality and identity, Game Changers via `is:gamechanger`), mark them `sourced`, and say so. Unreachable sources make checks `unverified`, never skipped.
3. **Theme and printings** per [references/checks.md](references/checks.md): eligibility against PROJECT.md's theme basis and hard rules, exceptions against DECISIONS.md; when art matters, open each themed printing's image and describe what it shows (doubtful art is `unverified`, never assumed); re-run the searches behind feasibility claims. Custom or proxy cards are never legal.
4. **Bracket** (for "what bracket is this?" and for checking a target): limits from [references/brackets.md](references/brackets.md) (check Wizards' page if it may be newer). Give the likely bracket with confidence and the reasons. Keep apart: `deterministic` (Game Changer count, bans, two-card combos), `indicators` (extra turns, MLD, tutors, fast mana: read in context), `assessment` (where it really plays: labelled judgment with uncertainty). Never cite an automatic bracket estimator as evidence; one tested tool missed Game Changers and a banned card.
5. **Composition:** lands, ramp, draw, interaction, wipes and win conditions vs the plan; role counts from deck_check's Oracle-text rules (`calculated`, multi-role), the verdict `judgment`. Name each shortcoming specifically (too slow, fragile, light on interaction). Unreleased cards are `upcoming` with their release date (a warning), not illegal; banned is a fail.
6. **Research and recommendations** per checks.md: open all high-impact sources (must-plays, combos, bans, theme/printing claims) and a sample of the rest; "source exists but says something else" fails. Then sample sizes, claims worded above their evidence class, missing perspectives, and each recommendation's cut, add and evidence.
7. **Verdict.** `pass` only when no required check is `fail` or `unverified`; otherwise `pass_with_warnings`, `fail` or `incomplete`. `verdict.summary` per [references/checks.md](references/checks.md), "Writing checks and the verdict". `required_fixes` tied to check IDs, `limitations`, `recommended_next_steps`. Write audit.json (or `audit-<variant>.json`) per `schemas/audit.schema.json`; add audit.md only when the audit is long enough to need a readable report. Validate with `companion.py validate`.

Reply in the shape of `verdict.summary` with the version checked ("Audit status" in writing.md), what to do next last. Fixes are suggestions; brew applies them only with the player's yes.
