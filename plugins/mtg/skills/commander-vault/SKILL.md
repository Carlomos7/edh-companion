---
name: commander-vault
description: Orchestrates a Commander deck vault for several commanders (any theme or none) rendered as one page (tier lists, bracketed decklists, cards to consider, price ladders, card viewer), leading Sonnet subagents and an independent verifier. Can start from the deck currently being built in this folder.
argument-hint: "[pasted request | @vault-request.md | nothing, to use the deck you're working on]"
disable-model-invocation: true
effort: high
---

# Commander Deck Vault (lead)

Request: $ARGUMENTS

Load now: `mtg-research` and `commander-deckbuilding` (the knowledge), then read [references/theme-rules.md](references/theme-rules.md).
Invoked as `/mtg:commander-vault` when installed as the plugin. Paths for briefs: `MTGDB=${CLAUDE_PLUGIN_ROOT}/scripts/mtgdb.py` (the same commands as the `mtgdb` MCP tools; subagents may use either). Page scripts: `PAGES=${CLAUDE_SKILL_DIR}/scripts` (see [references/pages.md](references/pages.md)). Run every script with `uv run`. Pass `--themes vault/themed-printings.json` (and `--reasons vault/<slug>/off-theme.json`) in vault runs that have a theme.

## Current state
Before anything else, check this folder: if `vault/plan.md` exists, read it (a run to resume); if `deck-brief.md` exists, read it and note the deck `.txt` next to it (a deck in progress).
Resuming: continue from the first unchecked gate. Don't redo a passed gate unless asked.

**Starting from the deck you're working on.** If the request is empty or says "this deck" (or names a deck file), and there is a deck in progress (a `deck-brief.md` and its `<commander-slug>.txt` from the deckbuilding skill, in this folder or earlier in this conversation), build the vault around it instead of asking for a paste:
- The brief prefills the request: commander, bracket, hard lines, money answer, collection preference, must/never include, theme.
- The existing list becomes that commander's deck at its bracket: copy it to `vault/<slug>/b<N>.txt`, run the G2 checks on it, and don't rebuild it unless a check fails.
- Ask one question (AskUserQuestion): "What should the vault add?" with "Neighbouring brackets for this commander (Recommended)" · "Other commanders too (name them)" · "Just a page for this deck" (that last one: render it per references/pages.md and stop; no agents needed).
- Then the page question, as one AskUserQuestion with the same four options as the deckbuilding skill's page offer: "Fancy, shareable link (Recommended)" · "Fancy, just on my computer" · "Basic" · "Customize".

## Accuracy model (why the gates exist)
1. **Computed facts** (legality, printings, prices, Game Changers, counts): only from `mtgdb.py`. Agents may not state them otherwise.
2. **Sourced claims** (plans, must-plays, combos, cEDH): logged in `claims.jsonl`, audited by script.
3. **Independent verification**: `vault-verifier`, which didn't write the work, re-opens sources and re-runs checks.
4. **Lead adjudication**: you resolve every refuted or unverifiable high-impact claim.
5. **Disclosure**: the page shows data dates, checks run and what stayed unverified.

## Intake
**Quick by default, customizable whenever they want:** take the request as given, default everything it doesn't say (and list the defaults once in `plan.md` and in one line to the user), and ask only what can't be defaulted (usually just the commanders). Deeper options come from "Customize" or the full `vault-request.md`.

The request is pasted after the command or passed as a file, and usually follows the repo's `vault-request.md` template (lines like `Brackets: 2 and 3`; text in parentheses is a hint, not an answer) (sections: what it's about, table and wallet, your cards, what goes on the page). Resolve: commanders, brackets + default, budget, price style, hard lines, collection and owned-card preference, must/never include, tab grouping, page style (Fancy by default: images, charts, cards to consider, card rankings, 3D viewer; Basic: decks and numbers only, no images; or a custom set of sections), images for Fancy (downloaded into the page so it can be shared, by default; or Scryfall links for a local-only page with no download), label style (default neutral verdicts: Play, Good, Situational, Binder, Bracket 4+; never "weak"), and theme (default none; if wanted, the themes.md intake question: mode, franchise, limits, premium).
Extras the page template can't render yet (alternative commanders, collection planner, splitting a pile between players) go out as Markdown files in `vault/` (`alternatives.md`, `collection-plan.md`): every placement passes `mtgdb.py validate` color identity for that deck, and cards that fit no commander are listed with their colors. Note the template gap in `plan.md`. Ask (AskUserQuestion, multiple choice) only for those; default the rest. If the user asks a question, answer it and don't build. Over 6 commanders or 18 decks: give the scale and confirm.
Write `vault/plan.md`: inputs, slugs, bracket matrix, defaults, the cost estimate, and the checklist `G0` to `G5`.

## G0 Setup (you)
- `mtgdb.py status --remote`, then `mtgdb.py sync` for anything stale (cards, tags, rulings, combos, rules; about a minute), then `mtgdb.py selftest`. A failure stops the run until explained.
- Read the latest Wizards bracket / Game Changers / ban announcement. If it is newer than `commander-deckbuilding/references/brackets.md`, note the changes in `plan.md` and include them in every brief.
- Check add-ons by calling them, not by reading names, per the add-on rules in the `mtg-research` skill (references/sources.md, "Optional MCP servers"): one cheap call per capability (EDHREC data, deck links, bracket estimate, transcripts, web search). Write which capabilities answered into `plan.md`; for each missing one, say which checks won't run.
- Theme (skip when mode is none): write `vault/theme-spec.json` and build `vault/themed-printings.json` with `theme-build` (theme-rules.md). For strict, run `theme-pool` per commander. Then check the map both ways:
  - **False positives**: `contact-sheet` of every mapped Secret Lair printing; look at it yourself and drop anything off theme.
  - **Gaps**: run `search` for the theme in names, art (`art:`) and flavor (`ft:`) across all sets and diff against the map.
  - Show the user the final drop/set list in one line.
- Set the recency cutoff `SINCE` = date of the latest bans/Game Changers update.
- Write `vault/config.json`: `{"since": SINCE, "budget": <number or null>, "commanders": {"<slug>": 1 or 2}}`. The plugin's hook reads it: every time a deck `vault/<slug>/b<N>.txt` or a `claims*.jsonl` is written with Write or Edit, the hook validates it and feeds failures straight back to the writer. Files copied with Bash or written by `mtg_research_log` (which validates entries itself) don't trigger it, so the gates below re-check everything. Hooks don't replace your gates; they stop bad files early.
- Data extras: `mtgdb.py sync prices` (once per run) for vendor prices on the price ladder; if the user has a collection, `collection show` and ask whether owned cards should be preferred.

## G1 Research (vault-researcher, parallel, 2 to 3 commanders each)
Brief: [references/briefs.md](references/briefs.md) §1. Every commander gets the full research pass (mtg-research references/research-pass.md: coverage minimums, best tool first, every source logged with `mtg_research_log`). A deck brought in from the deckbuilding skill already has it in `research/`: copy it to `vault/<slug>/` instead of redoing it.
Gate: for each commander, `mtgdb.py audit-claims vault/<slug>/claims.jsonl --since SINCE` passes; `mtgdb.py research report vault/<slug> --bracket <highest>` shows no shortfalls (or each is explained in `plan.md`); `research.md` has every section; `takes.json` has 8 to 15 linked takes.

## G2 Pilot, then decks (vault-deckbuilder)
Build the default bracket for one commander first (§2). Run the G2 checks on it. Fix the brief if the agent misread anything. Then fan out.
Gate, every deck, run by you (never trust the agent's report):
- `mtgdb.py --themes vault/themed-printings.json validate <deck> --bracket N [--budget X]`
- `mtgdb.py combos <deck>` (local Spellbook data; B1 to B3: nothing in `two_card`, which counts the commander plus two cards as a two-card combo) and, if an add-on offers one, a bracket estimate (treat it as a second opinion: it has missed Game Changers and combos the local data finds)
- `themed_printing_available` warnings fixed or justified
- every `consider.json` pairing passes `swaptest`

## G3 Merge (vault-merger, one per tab)
§3. Gate: every card in `merged.json` appears in at least one of that tab's `consider.json` files; count matches; every pairing passes `swaptest` (re-run a 25% sample yourself, all of them for B3 and below).

## G4 Verify (vault-verifier, fresh context, one per 3 to 4 commanders)
§4. It verifies 100% of high-impact claims and a 20% sample of the rest, re-runs every deck check, and checks disputed printings by looking at the art.
Gate: `mtgdb.py audit-claims vault/<slug>/claims.verified.jsonl --since SINCE --require-verified` passes, and every `refuted` / `unverifiable` item in `verification.md` is resolved by you: fixed, removed, or kept with a visible "unverified" label.

## G5 Page (you, following [references/pages.md](references/pages.md))
1. `site_data.py init vault/site-data.json` with the page choice (`--style fancy|basic`, `--images cdn` for local-only, `--show`/`--hide`/`--viewer` for custom; `--themes` if themed), then for each deck `add-deck` with its `b<N>.notes.json` (plan, key cards, strengths, weaknesses, tips, plus `community` from `takes.json` and `youtube` from the research's videos), `add-tier` per tier tab (EDHREC numbers with `n`), `add-swaps` per tab, `add-claims` with every `claims.verified.jsonl`.
2. `build_site.py vault/site-data.json --out vault/site`. Fix every error, and every `incomplete:` warning or explain it in `plan.md` (pages.md "Every page has"). This is what keeps every vault page the same shape.
3. Follow pages.md steps 4 and 5: look at it at desktop and 390 px, spot-check 10 random cards against `mtgdb.py`, then publish (or, for a local-only page with Scryfall images, hand over the file).
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

## Gotchas (from real runs)
- **Theme maps are wrong both ways at first:** searches pull in unrelated Secret Lair drops and miss real ones. Always run both G0 checks (contact sheet and gap search).
- **Merged "cards to consider" lists leak** cards no deck suggested. The G3 gate (every merged card appears in a `consider.json`) exists because of that.
- **YouTube blocks parallel transcript fetches.** One video at a time.
- **Card images can fail to download** (network or certificates); `build_site.py` lists failures, so read its output before publishing.
- **Agents report success optimistically.** Re-run every gate yourself; never trust an agent's summary.
- **Commander + 2 combos slip through a two-card check.** Azula + Frantic Search + Narset's Reversal did, until `combos` counted the commander as always present. `mtg_deck_swap` now blocks swaps that complete one at B1 to B3.
- **YouTube blocks the transcript tool on some networks**; a web fetch of the video URL often returns the transcript instead. If neither works, cite the video as "watch" and don't quote it.
