# Improve an existing deck

## 1. Get the deck
A Moxfield link (read it with a deck-reading tool if one works), a pasted export, or the project's latest decklists/ file. Never edit the player's original: the first version you save is `version: 1` of brew.json with every card `accepted`, exactly as given.

## 2. Profile before asking
Run deck_check.py at the bracket it seems to be and read the cards. Tell the player what you found **before** the questions, so the questions make sense. Lead with the finding that matters most (a legality problem, or "legal, plays like bracket 3"), then legality problems, Game Changers, combos, bracket signal, cost, theme lean (what share of printings are from one franchise) and obvious role gaps. Mention cost once here.

## 3. Ask (fast path first)
"Use your defaults (Recommended)": keep its bracket, light tune of 5 to 10 swaps, no new money concerns, keep its theme. Or set it up:
1. Target bracket (stay / push up / tune down).
2. Theme (only if it leans on one or they mention it): per themes.md.
3. How much change: light (5 to 10) · solid (15 to 25) · rebuild around the commander.
4. Money (the only money question).
Plus one optional line: "Any cards that must stay?"

## 4. Diagnose
With research.json (or EDHREC/decklist data gathered via the research skill): role gaps against construction.md, mana (sources vs pips), cards that underperform here (read each first, and say how: too slow, off-plan, redundant, fragile), missing commander payoffs, popular high-synergy cards it lacks, and bracket problems for the target.

## 5. Propose (never apply)
- Each swap is a `recommendations` entry: `rec-NNN`, add + cut, reason, evidence refs, theme status, trade-off, `status: proposed`.
- Respect the change budget, locked cards, and every decision in DECISIONS.md (rejected recommendations stay rejected).
- Theme on: every add stays inside the theme rules; an off-theme idea is only offered if they asked what the theme costs.
- Order by impact. Close calls become a multiple-choice question.

## 6. Apply what they accept
Accepted → change `deck`, bump `version`, new `deck_hash`, save a new decklists/<variant>-v<N>.txt and note what changed in STATE.md. Rejected → `status: rejected` plus a dated DECISIONS.md line with their reason. Then the boundary audit (brew workflow step 6).

## 7. Hand back
Brew's hand-back (SKILL.md step 7). For an existing deck the diff is the cuts, adds and printing changes, with before → after only for the numbers that moved (bracket signals, Game Changers, role counts, theme line), plus what wasn't checked.

## Edge cases
- Illegal deck: fixing legality comes first and doesn't count toward the change budget.
- Over the target bracket: removals to reach it come first.
- Proxies: ask once whether their table allows them; otherwise flag them.
- Already strong for the target: say so with evidence and offer side-grades instead of forcing changes.
