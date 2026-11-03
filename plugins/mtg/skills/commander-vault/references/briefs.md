# Brief templates

Each brief is self-contained (the agent hasn't seen this chat). Replace every `<...>`. Give objective, inputs, output files and format, tools, boundaries.

## §0 Header (every brief)
```
Commander deck vault. THEME: <none | label list + mode (power/prefer/strict) + limits>. BUDGET: <none | $X/deck>.
If THEME is none, ignore every theme instruction below.
Skills preloaded: mtg-research, commander-deckbuilding. Follow their accuracy rules exactly.
Card tool: uv run <abs MTGDB> [--themes <abs>/vault/themed-printings.json] <cmd>
Recency cutoff (SINCE): <date> because <latest WotC update>. Rule changes since the reference files: <none | list>.
Commanders: <name (slug)>, ...
Write only to: <abs folders>. Read anything under vault/.
Collection: <none | prefer owned cards; mtgdb.py collection show>
A hook validates your deck and claim files when you write them; if it reports errors, fix them before moving on.
User notes: <...>
Finish with a short report: files written, check results, **tools used and tools that failed (with the error)**, flags, open questions. No file contents.
```

## §1 vault-researcher
```
Objective: an evidence-backed profile of each commander that a deckbuilder can rely on.
For each commander:
1. Data first: EDHREC staples + themes (note deck count n), Spellbook combos with the commander,
   EDHTop16 / cEDH DB presence (entries, top cuts, dates).
2. Creators: 2 to 5 recent deck techs or articles, different channels, per mtg-research youtube.md.
   Transcripts one at a time. Normalize every card name. Prefer linked decklists.
2b. Commander-text search (mtg-research): cards that scale the commander's own ability. List each with a verdict.
2c. Community pass: r/EDH, primers, comments. Log what they say is missing or overrated as `community` claims.
2d. Every combo not in Spellbook: `rules` claim with rule numbers and the full piece list.
3. Write vault/<slug>/research.md: Plan, Must-plays, Traps, Combos, cEDH evidence, Conflicts, Sources.
4. Log every opinion/external claim in vault/<slug>/claims.jsonl (mtg-research claims.md).
5. Run: mtgdb.py audit-claims vault/<slug>/claims.jsonl --since <SINCE>. Fix every problem before reporting.
Don't build decks.
```

## §2 vault-deckbuilder
```
Objective: bracket-correct, themed 100-card decks for <brackets>, built from vault/<slug>/research.md.
For each bracket: follow commander-deckbuilding "Build" including the full validate loop with
--themes and --bracket. Pick printings with `printings` (themed first, then price).
Save vault/<slug>/b<N>.txt.
Then:
- vault/<slug>/deck-notes.md: per bracket plan, intended win turn, combos (Spellbook ids), off-theme reasons,
  B5 cEDH realism with evidence.
- vault/<slug>/off-theme.json (themed runs): {"Card": "one-line reason"} for every off-theme card.
- vault/<slug>/b<N>.notes.json for the page: pitch, wins, key_cards, strengths, weaknesses, tips, youtube, checks (format: mtg-pages site_data.py --help).
- vault/<slug>/consider.json: 10 to 15 per deck,
  [{"card","why","bracket","swap_out","theme","claim_ids":[]}], every pairing passes swaptest.
- Append any new claims to vault/<slug>/claims.jsonl.
Report per deck: validate pass, price, theme_counts, game_changers, Spellbook bracket estimate.
```

## §3 vault-merger
```
Objective: one cards-to-consider list for tab <tab> (decks: <list>).
Merge consider.json files, dedupe by card. For every card x deck pair (not just where it was suggested),
find a sensible swap_out and test with swaptest at that deck's bracket. Keep passing pairs only.
Before saving, check every merged card came from one of this tab's consider.json files and report the count.
Save vault/tabs/<tab>/merged.json: [{"card","theme","why","fits":[{"deck":"<slug>/b<N>","swap_out","note"}]}].
Report: cards, pairs kept, pairs dropped by reason.
```

## §4 vault-verifier
```
Objective: independently confirm or refute the work for <slugs>. You did not write it; assume nothing.
1. Claims: copy vault/<slug>/claims.jsonl to claims.verified.jsonl. For every high-impact claim and a
   random 20% of the rest: re-open each source (video at the timestamp, EDHREC page, Spellbook combo,
   EDHTop16 query) and set status verified | refuted | unverifiable with a verifier_note saying what you saw.
   Verify the claim, not the source's existence.
2. Decks: re-run validate (with --themes, --bracket, budget), stats, Spellbook combos + bracket estimate for every
   b<N>.txt. Check every Must-play in research.md is in the matching decks or explained in deck-notes.md.
3. Printings: build a `contact-sheet` of every disputed printing plus 20 random themed ones per commander and
   check each tag against the art. Re-run validate's printing check (gold border, digital, oversized).
3b. Simulate: re-run `simulate` per deck and compare with the deckbuilder's reported numbers.
4. Write vault/<slug>/verification.md: summary counts, every refuted/unverifiable item with evidence, every
   failed check. Do not edit decks, research or claims.jsonl.
```

## §5 Correction (SendMessage, same agent)
```
Fix in <file>: <exact problem>. Evidence: <check output or verifier note>. Change only that, re-run the
relevant check, reply with the diff and new result.
```
