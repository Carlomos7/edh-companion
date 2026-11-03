---
name: commander-vault
description: Orchestrates a full themed Commander deck vault published as an artifact (tier lists, bracketed decklists, cards to consider, price ladders, 3D card viewer), leading Sonnet subagents and an independent verifier.
argument-hint: "[theme | @request-file]"
disable-model-invocation: true
effort: high
---

# Commander Deck Vault (lead)

Request: $ARGUMENTS

Load now: `mtg-research` and `commander-deckbuilding` (the knowledge), then read [references/theme-rules.md](references/theme-rules.md).
Invoked as `/mtg:commander-vault` when installed as the plugin. Paths for briefs: `MTGDB=${CLAUDE_PLUGIN_ROOT}/scripts/mtgdb.py` (the same commands as the `mtgdb` MCP tools; subagents may use either). Page scripts: `PAGES=${CLAUDE_SKILL_DIR}/scripts` (see [references/pages.md](references/pages.md)). Run every script with `uv run`. Pass `--themes vault/themed-printings.json` (and `--reasons vault/<slug>/off-theme.json`) in vault runs that have a theme.

## Current state
```!
test -f vault/plan.md && { echo "RESUMING. plan.md:"; cat vault/plan.md; } || echo "Fresh run, no vault/ here."
```
Resuming: continue from the first unchecked gate. Don't redo a passed gate unless asked.

## Accuracy model (why the gates exist)
1. **Computed facts** (legality, printings, prices, Game Changers, counts): only from `mtgdb.py`. Agents may not state them otherwise.
2. **Sourced claims** (plans, must-plays, combos, cEDH): logged in `claims.jsonl`, audited by script.
3. **Independent verification**: `vault-verifier`, which didn't write the work, re-opens sources and re-runs checks.
4. **Lead adjudication**: you resolve every refuted or unverifiable high-impact claim.
5. **Disclosure**: the page shows data dates, checks run and what stayed unverified.

## Intake
The request usually follows the repo's `vault-request.md` (sections: what it's about, table and wallet, your cards, what goes on the page). Resolve: commanders, brackets + default, budget, price style, hard lines, collection and owned-card preference, must/never include, tab grouping, page extras, label style (default neutral verdicts: Play, Good, Situational, Binder, Bracket 4+; never "weak"), and theme (default none; if wanted, the themes.md intake question: mode, franchise, limits, premium).
Extras the page template can't render yet (alternative commanders, collection planner, splitting a pile between players) go out as Markdown files in `vault/` (`alternatives.md`, `collection-plan.md`): every placement passes `mtgdb.py validate` color identity for that deck, and cards that fit no commander are listed with their colors. Note the template gap in `plan.md`. Ask (AskUserQuestion, multiple choice) only for those; default the rest. If the user asks a question, answer it and don't build. Over 6 commanders or 18 decks: give the scale and confirm.
Write `vault/plan.md`: inputs, slugs, bracket matrix, defaults, the cost estimate, and the checklist `G0` to `G5`.

## G0 Setup (you)
- `mtgdb.py status --remote`, then `mtgdb.py sync` for anything stale (cards, tags, rulings, combos, rules; about a minute), then `mtgdb.py selftest`. A failure stops the run until explained.
- Read the latest Wizards bracket / Game Changers / ban announcement. If it is newer than `commander-deckbuilding/references/brackets.md`, note the changes in `plan.md` and include them in every brief.
- Check MCPs by calling them, not by reading names: `ping` on the MTG connector, one transcript fetch, one search. Report exactly which server answered. If one is missing, say which checks won't run.
- Theme (skip when mode is none): write `vault/theme-spec.json` and build `vault/themed-printings.json` with `theme-build` (theme-rules.md). For strict, run `theme-pool` per commander. Then check the map both ways:
  - **False positives**: `contact-sheet` of every mapped Secret Lair printing; look at it yourself and drop anything off theme.
  - **Gaps**: run `search` for the theme in names, art (`art:`) and flavor (`ft:`) across all sets and diff against the map.
  - Show the user the final drop/set list in one line.
- Set the recency cutoff `SINCE` = date of the latest bans/Game Changers update.
- Write `vault/config.json`: `{"since": SINCE, "budget": <number or null>, "commanders": {"<slug>": 1 or 2}}`. The plugin's hook reads it: every time anyone writes `vault/<slug>/b<N>.txt` or a `claims*.jsonl`, the hook validates it and feeds failures straight back to the writer. Hooks don't replace your gates; they stop bad files early.
- Data extras: `mtgdb.py sync prices` (once per run) for vendor prices on the price ladder; if the user has a collection, `collection show` and ask whether owned cards should be preferred.

## G1 Research (vault-researcher, parallel, 2 to 3 commanders each)
Brief: [references/briefs.md](references/briefs.md) §1.
Gate: for each commander, `mtgdb.py audit-claims vault/<slug>/claims.jsonl --since SINCE` passes; `research.md` has every section.

## G2 Pilot, then decks (vault-deckbuilder)
Build the default bracket for one commander first (§2). Run the G2 checks on it. Fix the brief if the agent misread anything. Then fan out.
Gate, every deck, run by you (never trust the agent's report):
- `mtgdb.py --themes vault/themed-printings.json validate <deck> --bracket N [--budget X]`
- `mtgdb.py combos <deck>` (local Spellbook data; B1 to B3: no 2-card combos) and, if the j4th connector is up, `spellbook_estimate_bracket`
- `themed_printing_available` warnings fixed or justified
- every `consider.json` pairing passes `swaptest`

## G3 Merge (vault-merger, one per tab)
§3. Gate: every card in `merged.json` appears in at least one of that tab's `consider.json` files; count matches; every pairing passes `swaptest` (re-run a 25% sample yourself, all of them for B3 and below).

## G4 Verify (vault-verifier, fresh context, one per 3 to 4 commanders)
§4. It verifies 100% of high-impact claims and a 20% sample of the rest, re-runs every deck check, and checks disputed printings by looking at the art.
Gate: `mtgdb.py audit-claims vault/<slug>/claims.verified.jsonl --since SINCE --require-verified` passes, and every `refuted` / `unverifiable` item in `verification.md` is resolved by you: fixed, removed, or kept with a visible "unverified" label.

## G5 Page (you, following [references/pages.md](references/pages.md))
1. `site_data.py init vault/site-data.json` (with `--themes` if themed), then for each deck `add-deck` (agents' `deck-notes.md` condensed into `notes.json` per deck), `add-tier` per tier tab (EDHREC numbers with `n`), `add-swaps` per tab, `add-claims` with every `claims.verified.jsonl`.
2. `build_site.py vault/site-data.json --out vault/site`. Fix every error.
3. Follow pages.md steps 4 and 5: look at it at desktop and 390 px, spot-check 10 random cards against `mtgdb.py`, publish.
4. Reply in a few lines: what's in it, theme counts (themed vaults), accuracy summary (claims verified / labelled unverified, data dates), accepted exceptions.

Don't hand-build or restyle the page. If the template is missing something every vault needs, note it in `plan.md` as a template change for later.

## When things change mid-run
- **User redirects** (new bracket focus, theme rule, budget): update `plan.md` and `config.json` first, then SendMessage every running agent the exact change, then re-gate anything already built under the old rule.
- **Agents die** (session restart, crash): check which files exist, restart only the missing work, or do it yourself if it's small. Never wait on an agent that isn't running.
- **A tool is down**: say which check didn't run and mark affected items unverified. Never fill the gap by hand.

## Scale and cost (decide at intake, write into plan.md)
Rough agent time: about 10 to 20 minutes per commander for research, about 10 per deck to build, and verification about half the build time again. A 12-commander, 40-deck vault ran for several hours.
- **Default scope**: the user's bracket plus one above. B5 only when asked, and only for commanders with real cEDH evidence (EDHTop16 entries). For others, say "not a real cEDH commander" instead of building a B5 list nobody will play.
- **Default size**: up to 6 commanders. Above that, confirm the estimate first, or split into several vaults.
- **Verifier scope**: 100% of high-impact claims, but cap at 40 per commander. If there are more, verify the 40 that appear on the page (must-plays, combos, cEDH) and label the rest unverified.
- **Optional heavy data**: `prices-sync --history` (a large download) only if the page shows price trends.
- **Skip what's cheap to skip**: no community pass for B5 (tournament data decides), no YouTube research for commanders with fewer than about 200 EDHREC decks (little content exists; data and Spellbook only).
- **Never cut**: validate, Spellbook combo checks, the hook, the theme map checks, the G5 render check.

## Cost and context
- Agents write files and return short reports. Read their files only at gates.
- No live per-card Scryfall calls; the index covers it.
- Log every fix you make in `plan.md` so a resumed run knows.
