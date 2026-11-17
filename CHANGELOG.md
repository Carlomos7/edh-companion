# Changelog

Players get a new version with `/plugin marketplace update edh-companion` and a restart.

## 8.15.0
- **Build picker is a dropdown:** every build sits in one select, each option labelled with its bracket first and then its name ("Bracket 2 · Core", "Bracket 3 · Upgraded", "Bracket 3 · Budget list"), grouped by build group when there are several. "Compare with" and the Differences heading use the same naming. Switching still redraws in place and keeps the `#build=` link. On phones both selects are full width.
- 272 unit tests.

## 8.14.0
One page for every build: a build bar replaces per-group tabs, and two-commander decks show both commanders.
- **Build bar:** every build of every group and commander sits in one bar on the Decks view, one segmented control per group, with label, bracket name, price and audit verdict on each button. Past 12 builds it becomes a grouped select.
  - Picking a build redraws the page in place.
  - `#build=<commander>/<build>` links reopen that build.
- **Compare with:** pick another build to add a Differences section listing the cards only in each build and any changed counts (e.g. B2 → B4).
- **At most four views:** Decks, Research, Rankings and Sources & accuracy. The view bar appears only with two or more views.
  - Every rankings group sits behind one in-page switch with short labels ("All decks", "Bracket 2"...), instead of one tab each.
  - The Overview tab is gone; the build bar does its job.
- **Two commanders** (Partner, Background, Doctor's companion): both cards side by side in the hero, named "A + B", each opening the card viewer.
- **One commander across several projects:** the hero carries the page title, so the masthead no longer repeats it.
- **Phones:** each build group is one swipeable row, so the commander stays near the top.
- **Tests:**
  - a two-commander fixture (`tests/fixtures/partners`)
  - browser tests for the build bar (all builds, grouped, one selected, at most four views) and for the two-commander hero
- 272 unit tests.

## 8.13.0
The page template is a swappable folder, and pages (plus autobuild and upgrade_path) follow each project's own conventions.
- **Template folder:** `skills/present/assets/template/` is now `index.html`, `page.css` and `page.js`.
  - `build_site.py` puts them together into one self-contained page through four placeholders (`__TITLE__`, `/*__CSS__*/`, `/*__JS__*/`, `/*__DATA__*/`). With the default folder the output is byte-for-byte the same as 8.12.
  - `--template DIR` swaps in another folder that has the same files and placeholders. A folder missing a file or a placeholder is refused.
- **Template checks:** tests run `node --check page.js` and load the built page in a real browser, and fail on any uncaught JS error. A deliberately broken page.js was caught.
- **Your role targets:** brew.json `role_targets` sets lands plus per-role `{min, max}`, with `max` null for "10+".
  - Roles: ramp, draw, removal, counter, wipe, protection, recursion, tutor.
  - The page's role check becomes "Against your targets", and the lands tile shows "your target 36–37".
  - autobuild.py and upgrade_path.py use the targets instead of `roles.json`; autobuild then also fills a protection floor.
- **Theme tiers:** `theme_policy.tiers` and `deck[].theme_tier` (e.g. Spider-Verse first, then other Marvel) add a sub-label on on-theme cards, in the list and grid views, and a count per tier in the theme line. The on-theme % and filters don't change.
- **Docs:** page-spec (template folder contract, conventions on the page), construction.md (role_targets), themes.md (tiers).
- 270 unit tests.

## 8.12.0
Fixes from an independent review of 8.9–8.11, plus the features 8.11 left out.
- **Ranking:** a lift under 1 now counts as 1, so staples with high baselines (Sol Ring, Command Tower) are no longer ranked below cards nobody has measured. Impossible counts (decks > total decks) give no score instead of crashing candidates.py.
- **autobuild.py:**
  - Fixes:
    - Counts a commander that is a Game Changer, and warns when locks push past the bracket.
    - Includes the commanders in the budget.
    - Keeps a strict or prefer theme (off-theme or unchecked candidates are left out, and it says how many).
    - Matches locks and bans on the front-face name, and reports every lock that didn't make it in.
    - No longer crashes when nothing is priced.
    - Keeps 100 cards with many locked lands.
    - Keeps totals right after the mana check.
  - New swap step: when a color is short, an unused candidate land that makes it replaces a basic.
- **upgrade_path.py:**
  - Cutting a measured card for an unmeasured one makes no lift claim, so Command Tower is no longer cut for a card with no numbers.
  - Basic lands can be cut, so it can suggest a dual land for a basic. A land that makes more of the deck's colors is worth 0.5 per extra color.
  - The commander's Game Changers count.
  - Commander Spellbook combos: a piece of a combo the deck already has is never cut; an add that completes a combo gains 1; two or more missing pieces come as one package step. Two-card combos aren't promoted at brackets 1–3.
- **collection.py:** reads "Edition Code" before "Edition" (Deckbox), and finds a card by name when its set and number don't match.
- **validate:** the lift check allows for EDHREC rounding the baseline, so merge-research no longer refuses good data.
- **Pages:** the card viewer names the artist ("Illustrated by"). Your own copy (`--include-notes --collection`) shows owned or missing per card and a "Missing cards" tile; shared pages never show it.
- **Docs:**
  - brew: how an autobuild draft becomes brew.json v1, and the budget is in USD.
  - research: compute `content_sha256` from the saved file, and use `authorship: unknown` when unsure.
  - The low-confidence cutoff is 100 decks everywhere.
- 265 unit tests.

## 8.11.0
Ranking, a first-draft deck builder, collections and upgrade paths, plus machine-readable page exports.
- **Ranking (`edhcore/scoring.py`, candidates.py):** cards with EDHREC counts get a `score` (95% Wilson lower bound of inclusion, and lift = that ÷ baseline, capped at 8, only with 100+ decks and 10%+ inclusion) and a `rank`. `ranking.coverage` says how many top picks are niche; `--surprise N` marks high-lift picks most lists miss. The thresholds are untuned starting points.
- **`autobuild.py` (brew):** a first-draft 100-card deck from candidates.json.
  - Hard limits are filters: verdict, upcoming cards, singleton, Game Changers per bracket, and the budget as a true total from cheapest printings. A card with no price is left out under a budget, and no single card may take more than 8× the average share left per slot.
  - Order: locks, then role floors from the new `references/roles.json` (ramp 12 for 4+ mana commanders), then rank without passing role caps.
  - Lands: Karsten's formula (33–40), then candidate lands and basics split by pips.
  - A mana check reruns the simulation and moves basics to the bottleneck color, at most 3 times.
  - Output: why for every pick, binding limits, the rank cutoff, weak spots, and adds/cuts against brew.json.
- **`collection.py`:** ManaBox, Moxfield, Deckbox and Archidekt CSV (read by header) or text lists → `<workspace>/collection.json`. Exact printings are kept when the export names them, duplicates are added up, and every row that didn't resolve is listed in `unmatched`.
- **`upgrade_path.py` (brew):** one-for-one swaps ordered by value per dollar.
  - Value = role floors filled plus lift gained; price = cheapest printing.
  - Owned swaps ($0) come first, and the order is recomputed after each step. The budget is a running total.
  - It cuts the least-played card (EDHREC inclusion, then Scryfall's overall EDHREC rank). Spells swap for spells and lands for lands. A strict or prefer theme only adds on-theme cards.
- **Pages:** `build_site.py` writes `llms.txt` and one `export-<project>-<build>.json` per build (decklist, version, date, audit verdict and the attribution), adds Open Graph tags and an alternate link, and the footer names EDHREC, Commander Spellbook and the Fan Content Policy.
- **Rules and docs:**
  - research sources.md: site-terms rules, including EDHREC JSON only when the player asks, in small volumes, never republished. `methodology.excluded` records hosts not used.
  - Acquisition and optimize docs cover owned / other printing / missing cards and upgrade paths.
  - Audit checks cover ownership and upgrade totals.
  - README credits Karsten, Chart.js and three.js.
- **Fixes:**
  - `companion.py card` now lists candidates.json entries (it read the wrong key).
  - Blinking your own creature (Ephemerate) no longer counts as removal.
- 258 unit tests.

## 8.10.0
Honest numbers and honest sources: EDHREC statistics are stored with their sample and baseline, generated lists are labelled as generated, and a few mana-count bugs are fixed.
- **EDHREC stats:** `card_candidates` and `rankings` cards take `lift` (preferred; EDHREC replaced synergy with lift on 2025-12-15), `baseline_pct`, `synergy_pct`, `window`, `as_of` and `trend_zscore` next to `decks`/`total_decks`/`inclusion_pct`. `validate` warns when lift doesn't match inclusion / baseline.
- **candidates.py:**
  - Keeps the stats, and computes inclusion from decks / total decks when it's missing.
  - New `data_strength` per card: `ok`, `thin` (under 100 decks, needs review) or `none`.
  - EDHREC conflicts use 95% intervals instead of a fixed 2-point gap (2 points still when counts are missing).
- **Source provenance:** sources take `origin` (fetched, pasted, file, generated_by_us), `authorship`, `generator`, `derived_from`, `path` and `content_sha256`. Pasted and file sources need no URL and are saved to `sources/pasted/<id>.txt`.
  - `validate` warns when a pasted file is missing or its hash differs, and when a `verified_fact`, `community_opinion` or `popularity_metric` finding rests only on machine-generated sources.
  - `research-find --summary` counts independent roots (a copy counts as its original) and shows generated sources apart.
- **Skills:** research asks whether a pasted list was played or generated and labels it; method.md gets the field list, an explanation template ("association, not strength") and the too-new-for-statistics rule; audit checks popularity numbers for sample, date and baseline.
- **Mana fixes (analytics):**
  - Fetch lands count only the colors of the land types they find (Bloodstained Mire: B and R). True fetches used to count as no color at all, and color-source checks ignored them.
  - A spell with a land back face (Valakut Awakening) no longer counts as ramp.
- **Moxfield lines** on the deck page (whole deck, Copy, Copy shown, Copy for Moxfield) carry `*F*` / `*E*` for foil and etched printings, like export_deck.py.
- 243 unit tests.

## 8.9.0
Build names on pages and copy buttons for card lists.
- **Build labels:** brew.json takes an optional `label` (up to 40 characters, e.g. "B3 Upgraded"). The page's build switch shows it; without one it shows the bracket (B3) as before, and the page no longer repeats the bracket name next to it.
- **Copy buttons on the deck page:**
  - **Copy** on every section heading copies the cards that section shows right now.
  - **Copy shown** copies every card the current filters show.
  - **Copy for Moxfield** in the card viewer copies one import line for that card.
- **Docs:** research notes and benchmark write-ups moved out of the repo; only `docs/architecture.md` stays. README, CLAUDE.md and the eval notes no longer link to them.
- 235 unit tests.

## 8.8.0
Hooks, cost measurement and a wider eval suite, plus tools so findings and cards don't have to be read in full.
- **Hooks (`hooks/hooks.json`, `scripts/hook.py`, stdlib only):**
  - After Claude writes a research.json, brew*.json or audit*.json, the project is validated, and any errors go back to Claude in the same turn.
  - At startup or resume inside a project, a one-line status is added: STATE.md's first line and the builds.
  - The auditor can't finish while an audit.json it wrote in the last 30 minutes fails validation.
  - Unrelated writes cost about 1 s (uv startup).
- **Findings:** a new `facet` field (strategy, combo, card, power, table-feel). `research-find --summary` groups findings by facet and evidence class and counts creators, not videos, in place of a hand-written brief. A replaced finding gets `status: superseded`, and `archive-findings` moves uncited ones to research.archive.json.
- **`companion.py card <project> NAME`:** every place a card appears: builds (with printing), recommendations, candidates, findings, rankings, audit checks and DECISIONS lines.
- **Measurement:** a "Tier 3: real sessions" section in docs/benchmarks.md (method, OTEL per-skill attributes, a baseline from 3 sessions before 8.3.0). `session_stats.py --eval … --budget evals/budgets.json` exits 1 when a case's median cost or turn count is more than 20% over budget.
- **Evals:**
  - reaudit-history: a multi-turn case via `context.history_file`.
  - research-large-find: a 600-finding research.json, which must not be read whole.
  - present-builds-page: Linux/WSL only.
  - 20 trigger cases (10 should, 10 should-not).
  - A `regression` tag for pass^3 runs.
  - `--max-cost-usd 0` checks that every case loads, for free.
- 234 unit tests.

## 8.7.0
The cast-by-turn simulation now sees colors. It used to count only the amount of mana, so a five-color commander looked castable whenever five lands were out.
- **Color-aware cast-by-turn:** lands and cheap mana producers carry the colors they make (Scryfall `produced_mana`; fetch lands count as any needed color), and the commander's pips have to be paid. It uses Karsten's 2022 Commander model: London mulligan with the first one free, his keep rules, bottoming toward three lands, and a turn-1 draw. It also reports `mulligans_per_game`, the share of games where colors (not mana) were the problem, which color was short, and the `bottleneck`. In the Spider-Man deck, Cosmic Spider-Man is castable by turn 5 in 53% of games; in a quarter of games the mana was there but a color wasn't, most often red.
- **`stats.sources_check`:** each color's effective sources (lands 1, cheap mana producers ¾) against the most demanding card's need in Karsten's 99-card table (gold cards +1, his rule), naming that card.
- **`stats.land_count`:** Karsten's formula, 31.42 + 3.13 × average mana value − 0.28 × cheap ramp and draw, with a warning when the deck is 2 or more lands off.
- deck_check prints all three. Prose that quotes the old percentages will get validate's prose-lint warning after the next deck_check.
- 228 unit tests.

## 8.6.0
Rules versus preferences, one plan for a swap across variants, and a short STATE.md.
- **PROJECT.md `## Rules` (R1…) and `## Guidance` (G1…):**
  - Rules are hashed one by one; `[b2]` after an id limits a rule to that variant. Guidance is never hashed, so it can only ever produce audit warnings.
  - Audits record `subject.rule_hashes`, and checks cite the rules they verify (`checks[].rules`). A changed rule makes only its checks out of date, and audit-scope re-checks just those. A new or changed rule that no check covers makes the audit stale.
  - A rule that leaves Rules needs a DECISIONS line naming it.
  - PROJECT.md files without rule ids still hash as a whole.
- **`plan.py`:** PLAN.json holds one pending change across variants, pinned to their deck hashes. `new` shows a dry-run; `apply` applies exactly that plan and reports a result per variant. It refuses a variant whose deck changed, or one where an add is a Game Changer at bracket 1–2, is off identity or is banned. Each applied variant gets one version bump, a new decklist and its hash; `revert` undoes the apply. Adds may name a printing: `"+Sol Ring (SLD) 908 *F*@ramp"`.
- **DECISIONS ids:** `D-n` ids, with "(superseded by D-n)" instead of edits. validate checks the ids are unique and that each reference points at a real decision.
- **STATE.md is a short snapshot;** history is appended to HISTORY.md, which sessions don't read by default.
- **Precedence:** plugin defaults < Rules < variant rules < a one-off instruction from the player.
- 226 unit tests.

## 8.5.0
A franchise theme's card pool becomes a reviewed lockfile instead of a fresh search every session. In the Spider-Man project, 29 Marvel Secret Lair bonus cards had no drop name anywhere and were found only by reading their footers.
- **`pool.py sweep <project>`:** discovers printings through several channels: set names from Scryfall's default_cards bulk file, which is fetched only when Scryfall's `updated_at` changes (bulk hosts have no rate limit); MTGJSON Secret Lair drop names; Secret Lair cards with no drop name; and a `date>now` search for cards newer than the bulk file. It writes `sources/pool.lock.json`, keyed by Scryfall id, with the evidence and a status (accepted, pending, rejected or removed) for each card, plus `pool.diff.md` listing what changed. Brew and audit use only accepted entries.
- **`sources/theme-rule.json`:** the theme rule as data. It holds the patterns, which evidence is strong, weak or rejecting, and which evidence wins a conflict (the player's call, then the footer).
- **Footers and art:** `art_sheet.py` builds contact sheets of footer strips or art crops for the cards that are still unchecked. `pool.py footer` and `pool.py art` record what was read. `sources/art_notes.json` is keyed by `illustration_id`; `art-seed` adds Scryfall Art Tags as unverified hints, and a note is marked stale when Scryfall gets a better scan.
- **`pool.py freshness <project>`:** reports the bulk and MTGJSON dates, changes to the Game Changers and banned lists (by hash), theme sets that grew, Scryfall ID migrations (merges re-key the entry, deletes mark it removed), stale art notes and the pool's age against `sources/freshness.json`. It exits with 2 on an error, which makes theme checks unverified.
- **Conditional downloads:** `Client.snapshot` sends If-None-Match / If-Modified-Since and records the sha256 of each snapshot.
- 221 unit tests, plus a live regression (`EDHC_LIVE=1`): the 29 bonus Secret Lair cards and the Marvel: Darkhold Destiny card are in the pool.

## 8.4.0
Fixes from a review of every skill: instructions that contradicted each other, a scoped re-audit that left its bookkeeping to the model, and paths that might not resolve.
- **Contradictions resolved:**
  - brew asks direction, bracket and budget in one message (discovery.md used to ask them third and fourth).
  - present publishes an Artifact link only on the player's yes.
  - setup detects tools from the tool list and tests only approved ones, as research does.
  - audit reports validate's prose warnings as brew fixes instead of fixing them.
  - A bracket 3 two-card combo fails when it can win early or is held for later; it is a warning only when incidental and late-game.
  - Palette precedence lives only in pages.md; research depth only in method.md.
  - Research in "ask every time" mode waits for a yes.
- **`companion.py audit-scope --write-carry`:** writes `carry-audit[-<variant>].json` with the new subject (deck, goals_hash, sections, mode, based_on) and the carried checks, each keeping its oldest `carried_from` date. The audit checklist starts with "earlier audit exists → audit-scope"; audits before export or sleeving stay full.
- **Paths:** every script runs as `uv run --script "${CLAUDE_PLUGIN_ROOT}/..."`, and each SKILL.md states the plugin root, so reference files with an unexpanded variable still resolve.
- **Descriptions:** trimmed to about 90 words, with routing split (exploring before building is research; exporting is brew; a comparison in chat is brew, a comparison page is present). "When to use" sections that repeated the description are gone.
- **Pages:** the build switch is in bracket order and labels the main build by its bracket ("B3"); pages still open on the main build. Research written for the main deck no longer marks variants as out of date (ported from a lost 8.1.3 local patch).
- **Network and output:** TLS uses the OS certificate store (`truststore`) first, then certifi, then Python's default. The User-Agent reads the version from plugin.json. Every edhcore script prints UTF-8.
- **Housekeeping:** setup's install commands moved to `setup/references/integrations.md`; the view-model and palette detail moved into the views.py and palette.py docstrings; the template-change note is in page-spec.md, marked maintainer-only; duplicate rate-limit text merged; tool table has a re-test date; brackets.md re-checked against Wizards on 2026-11-16; stale skill names fixed in evals and schemas; eval tag table completed; deck_check usage lists `--no-tags` and `--cards-only`.

## 8.3.0
Cheaper re-audits and fewer audit failures on stale wording. In one project, a full audit after three card swaps cost about 300k tokens and 20 minutes, and most failures were prose that no longer matched the deck.
- **Scoped re-audits:** `companion.py sections <brew.json>` fingerprints each deck line, recommendation and prose block; audits store them in `subject.sections`. `companion.py audit-scope <project> [brew-<variant>.json]` then lists what a re-audit must re-check (changed cards, recommendations and prose, deck-wide checks, earlier non-pass checks, two random spot checks) and what carries over, or says why it must be full (no baseline, PROJECT.md changed). New optional audit fields: `subject.mode`, `subject.based_on`, `checks[].carried_from`. The audit skill and auditor agent describe when to scope and when to stay full.
- **Prose lint in `validate`:** warns when a brew's strategy or limitations still name a cut card, or state a land count, cast-by-turn percentage or listed price that differs from its deck_check.json. Mentions that say the card is gone ("no Teferi's Protection") and numbers about other decks ("community lists run 34 to 36 lands") are skipped.
- **Role second opinion from Scryfall Tagger tags:** deck_check adds `stats.roles_tag_only`, the roles that community tags (otag:removal, tapper, recursion, sweeper, ...) give a card but the Oracle-text rules don't, such as Auras that neutralize a creature and tappers. Not counted (tags over-include: Path to Exile is tagged ramp); the auditor judges just those cards instead of recounting. A failed tag lookup never changes the data status. `--no-tags` skips it; page builds skip it.
- **Compact research-find:** evidence shows IDs only (first three, then "+N more"); `--detail` restores source titles.
- **Raw decklists:** research saves each fetched list to `sources/decklists/<source-id>.json`, so counts in findings can be recomputed.
- 213 unit tests.

## 8.2.0
- **Set filter:** the deck list has a "Set" chip group (most-played set first), labelled with the full set name and code, e.g. "Marvel's Spider-Man (SPM)". The card viewer's price row also names the set. Site data now carries each card's `set_name`.
- **Filters wrap from 600 px:** chip groups wrap instead of scrolling sideways on tablets and desktops (was 1280 px); phones keep swipe rows.
- **Contrast and targets:** gold theme tags use a dedicated ink (`--gold-ink`) so they pass in dark mode; status icons, Game Changer and theme tags are 1 px larger; timestamp links are at least 24 px tall and source footnote links 28 px.

## 8.1.3
- **Privacy, precise:** quotes of DECISIONS.md and PROJECT.md text inside audit or research files stay hidden on shared pages; STATE.md is no longer scanned for quotes, because it restates the audit and research (hiding those overlaps hid the audit's own public facts). STATE.md itself is still never on the page.
- **Recommendations link their video moments:** a time after a named creator in a recommendation's reason or trade-offs (e.g. "MTG Bear … (1:13)") links that video at that moment, like findings and disagreements.
- **Hero contrast with any artwork:** below 960 px the hero text sits on a near-opaque wash, so the art behind it can shift contrast by at most ~5%; measured on Azula: title 10.1:1, meta text 5.5:1 or more, light and dark, 390 to 1440 px.
- **Evals README:** documents that the eval sandbox can't read references or run scripts (no runner flag for it) and where those are measured instead.
- 205 unit tests.

## 8.1.2
- **MTG MCP install fix:** the recommended command now pins `selectolax<1.0` (`uvx --with "selectolax<1.0" mtg-mcp-server`). mtg-mcp-server 3.0.0 leaves selectolax uncapped and selectolax 1.0 breaks its import, so fresh installs crashed on startup. Reproduced and verified both ways; README and setup updated.

## 8.1.1
Fixes from an independent review of the redesign, plus leaner skills.
- **Reports:** switching builds or commanders no longer removes the theme button (focus returns to the switch); finding headlines state the conclusion (no label-only or mid-quote cuts) with a one-line summary visible collapsed; finding and source links are scoped per project, so showcase "Cited in" links land on the right tab; citing a finding brings only the sources it actually cites, and bare times after a named video link to that moment; filter chips match the groups (commander excluded, "Has type"); theme percentage states its denominator and exempt cards; Sources and Stats no longer leave large empty areas at 1440 px; mana pips show their letter; each build shows its own hero stats; Rule 0 is a short labelled table (bracket, Game Changers with their limit, restrictions, win turn).
- **Privacy:** quotes of DECISIONS.md, STATE.md or PROJECT.md text inside audit or research files are hidden on shared pages ("N quoted private notes were hidden"); `--include-notes` shows them.
- **Contrast:** palette `border` fitted to 3:1, off-theme text and hero meta text to 4.5:1 or more in every palette; textures behind text toned down. axe-core: 0 violations on every tab.
- **Summary mode:** includes the plan sections, theme counts and how the research was done.
- **Staleness notice:** compares the decklist files research names with the newest list (Azula: "names main-v3.txt; the newest list is main-v5.txt").
- **Skills:** trimmed back to 7.8.0 size or smaller (detail moved to references read when needed; four reply rules inline instead of a mandatory writing.md read); brew asks or states bracket and budget before the plan again. Evals: asks-before-building 4/4 (grader aligned with "one question at a time"; under the old grader 2/4 vs 1/4 on 8.0.0), cost per run $0.149 → $0.131.
- **Tests:** 204 unit tests.

## 8.1.0
Reports redesigned: one component system for Interactive Report and Showcase, built from a deterministic view layer.
- **Answer first, evidence on demand:** findings show a headline and a short body, with numbered citations that link to the exact video moment for that claim; evidence, quotes and every source stay one click away (nothing truncated or dropped). Disagreements are shown open. The audit leads with counts, fails and warnings first, passes collapsed ("27 checks passed"), the shared method shown once, plain labels (no `pass_with_warnings`).
- **Design system:** type scale, spacing, two shadows, colour roles derived from the commander's artwork (contrast enforced: text 4.5:1, UI 3:1; explicit themes still win), light and dark, sticky section nav, card grid with a density toggle, list view and all filters kept, charts with a takeaway and a data table. Showcase adds the artwork-led hero and restrained motion; reduced motion respected.
- **Card types, one rule:** `edhcore/types.py` classifies every card for deck_check's stats and the page (multi-type cards match every type filter, front face decides double-faced cards, split cards count every half, MDFC lands shown as "36 lands + 1 MDFC", basics once with ×N); each build and showcase group has its own counts.
- **Honest content:** accepted recommendations show as applied, not "cards to consider"; research written for an older deck version gets a notice; private notes (DECISIONS.md, PROJECT.md text, STATE.md) are left out of shared pages unless `--include-notes`.
- **Writing:** Summary mode (Markdown) is complete (audit, disagreements, all findings and sources, numbered).
- **Breaking for generated pages only:** page-data drops the legacy fields (`tiers`, the `sources`/`used_for` dump, per-build `validation`/`errors`, `swaps`, video lists, the old accent pair). Rebuild old pages; project files are unaffected.
- **Measured on the real Azula project:** page height 50,459 → 31,222 px on a phone (390 px) in Interactive mode, 20,040 → 20,647 px at 1440 (more content now shown: disagreements, candidates, next steps). axe-core: 0 violations; no console errors or horizontal overflow at 390/768/1440, light and dark.

## 8.0.0
A shared data core, deterministic research coordination and a verified research → deck handoff. Existing projects, decklists and audits work unchanged (all new fields are optional).
- **Shared data core (`scripts/edhcore/`):** one HTTP client, cache and card model for every script. Failures are handled per endpoint, never per provider: a 429 waits for Retry-After and makes every process wait; 5xx and timeouts back off and retry 3 times; other 4xx aren't held against the endpoint; three exhausted calls in a row open that endpoint's breaker (60 s doubling to 10 min, then a probe). Rate limits are shared across parallel processes through a disposable SQLite cache in `~/.cache/edh-companion/` (`EDHC_CACHE_DIR`, `EDHC_NO_CACHE=1`); recovery never deletes anything but its own files and never inside a workspace, project, repo or home folder.
- **Freshness you can see:** card text 7 days; legality, Game Changers, prices, searches and combos 24 hours; `--fresh` re-reads everything and audits use it. A failed refresh falls back to an older copy marked stale; every result carries a `data` block (fresh / cached / stale / unavailable), and checks that relied on stale or unavailable data are `unverified`, never pass.
- **Provider preferences respected by scripts:** Scryfall or Spellbook excluded in the research preferences (config or PROJECT.md) get no requests; `--offline` uses the cache only.
- **New commands:** `card_lookup.py` (compact cached lookups and searches instead of ad-hoc curl), `companion.py research-plan` / `merge-research` / `research-find`, `candidates.py` (verified candidates for brew).
- **Research merging is deterministic:** planned workers with their own ID prefixes; merge refuses until every planned worker finished and validated (or records gaps with `--allow-partial`), dedupes sources by URL, keeps existing IDs, keeps conflicting worker conclusions and EDHREC numbers as disagreements, and is safe to rerun or resume after an interruption.
- **Research → deck:** `candidates.json` gives every candidate a verdict; only hard rule breaks (not a real card, banned, outside the identity) are ineligible; Game Changers, upcoming cards, theme questions and missing evidence are judgment calls; a set filter alone never rejects a card; printing choices are tracked separately. Evidence IDs carry into `deck[].evidence`.
- **Validation:** EDHREC number consistency, duplicate source URLs, future dates and refs in rankings/disagreements/feasibility are reported as warnings (existing projects keep passing); unmerged worker parts make research "incomplete".
- **Writing standard:** one shared `references/writing.md` (answer first, plain labels, group instead of truncating, missing ≠ zero, citations to the exact moment); reply-length caps removed from skills and agents; findings get an optional `headline` and `locators` (timestamps per claim), audit checks an optional `method`.
- **Fixes:** a single Scryfall error no longer aborts a page build; back faces only for real double-faced cards; atlas images written atomically and corrupt ones refetched; `--commander` alone no longer runs the 100-card count or Spellbook; card names with accents or curly apostrophes resolve; banned/upcoming labels kept for research cards.
- **Measured (paired, 3 interleaved runs per version, medians; `docs/benchmarks.md`):** themed build + 2-variant page 32.1 → 14.4 s cold (37 → 15 requests, 14 → 0 duplicates) and 36.4 → 6.0 s warm (37 → 0); research card data 6.8 → 1.5 s warm; optimisation 11.4 → 4.9 s warm; audits of 13 planted-error decks 63.6 → 54.3 s with 114/114 problems found by both versions. End-to-end Claude (eval runner, 6 cases × 4 runs): cost $3.49 → $3.70 (+6%, larger skill files), time unchanged; one brew case (asks-before-building) dropped 4/4 → 1/4, possibly real. The eval sandbox can't run scripts, so it doesn't see the script gains.
- **Tests:** 176 unit tests (core failure classes, breaker, freshness, real cross-process pacing, cache safety, provider policy, merge recovery, candidates, page pipeline).

## 7.8.0
- **Approval gates, not prompts everywhere:** one shared "When to ask" rule set in the project contract. Ask before changing an accepted deck the player didn't ask for in so many words, relaxing hard rules, moving or deleting files, publishing or sharing, real-world actions, and unexpectedly expensive work (with purpose, cost and a cheaper alternative). Don't re-ask for what the request or saved preferences already cover (an explicit swap is the approval; comprehensive research includes its Scryfall searches). Announce big work and give progress updates without stopping. Research preferences, these gates and Claude Code's own permissions are kept apart. brew now also manages saved projects; deleting always asks first, with archiving offered.
- **Adaptive research depth:** Quick, Comprehensive and Deep with source ranges as guidelines, not quotas; research continues until the important questions are covered and corroborated, disagreements explained and gaps named, or new sources stop adding anything, and research.json records sources reviewed and why it stopped.
- **Research reliability (from the Azula run):** card data looked up in batches once (`deck_check.py --cards-only` → `cards.json`) and reused; bounded retries honouring Retry-After for 429 and 5xx; MCP numbers sanity-checked (contradictory EDHREC counts aren't trusted); a failing endpoint is dropped after one retry for the session with an approved fallback; no guessed URLs; in parallel research one worker owns Scryfall, the others videos, lists and community, and research isn't complete until every worker finished and validated.
- **Tests:** 83 unit tests (retry and batching regressions added); evals for an explicit change applied without re-asking and a delete that asks first.

## 7.7.0
Research approval, asked once.
- **Step 1, approve tools:** before the first substantial research, research lists the tools it found by name (read from the tool list, nothing external called yet) with what each would be used for and its speed, token and API-cost trade-offs, and offers Recommended (all relevant tools, video transcripts first), Customize, Fast research, or No external research (with its limits explained). Approved tools are then tested and shown as detected, verified, failed or unavailable.
- **Step 2, how often to ask:** ask every time, ask when something changes (Recommended: new providers, much bigger plans or unapproved fallbacks), or automatic (never for excluded or new providers).
- Depth (Comprehensive / Quick / Custom / Skip) stays a separate choice. Substantial research is announced with the tools it will actually use and roughly how long. Trivial lookups never trigger onboarding.
- Choices persist in the config, with per-project overrides in PROJECT.md; `companion.py research` shows them; change them in conversation or setup. Claude Code's own permission prompts are separate and can't be bypassed (`/permissions` to allow tools there).

## 7.6.0
- **Research onboarding:** on the first substantial research request, research checks each capability with a cheap call (card data, EDHREC, combos, decklists, web and semantic search, video transcripts, scripts), judges the results rather than trusting that a tool is installed, shows a short working / missing table, and offers Comprehensive (Recommended, 5 to 15 min per commander), Quick (1 to 3 min), Custom or Skip. The choice and the capabilities seen are saved in the config and reused in every session and project; it only asks again when a capability appears, disappears or starts failing.
- **Smarter tool use:** each job goes to the tool that does it best (MTG data for facts, semantic search for deck techs and articles, web search for Reddit and forums, transcripts for what creators said), no duplicate searches unless the first failed, no re-reading pages, fallbacks noted. Comprehensive research includes creator deck techs with timestamps when transcripts work.
- **Setup:** can save default research depth, preferred and excluded sources, and which tool to use when several can do a job.

## 7.5.0
Reports, built on the existing deck-browser template.
- **Three modes:** Deck Summary (clean Markdown, export to Word/PDF with installed skills), Interactive Report (images, decklists, filters, comparisons, prices, essential charts; no 3D viewer or card fan) and Showcase (the full template). `--mode summary|interactive|showcase`.
- **Theme rankings tabs** from research.json `rankings` (rank, tier, card image, inclusion % with deck counts labelled as popularity, why, sources, status pills), with each ranking's method and date shown.
- **Research-only reports:** commanders compared, findings, disagreements, rankings and sources before any deck exists.
- **Navigation:** builds grouped into tabs (brew `group`, e.g. Heroes / Villains), a commander picker inside a group, bracket/variant switches, alternative commanders compared.
- **Multi-project Showcases:** `site_data.py from-showcase` combines projects listed in showcase.yaml into one report; each project keeps its own files, decisions and audits, and the grouping is saved for next time.
- **Charts from deck_check data only:** rule-based role counts (builder labels shown separately where they differ), price ladder, mana sources vs color requirements, cast-by-turn with its assumptions; each hidden with a note when the data isn't there.
- **Commander color theming:** accents from each commander's color identity (at most two hues, muted gold for 3+, neutral for colorless and multi-commander views), updated live when switching tabs, commanders or builds; saved custom themes (comic, gothic, flames or your own colors) in report-theme.yaml or showcase.yaml; precedence explicit > saved > commander colors > neutral; every accent kept at 4.5:1 contrast; reduced motion respected.
- **Tests:** 75 unit tests; browser checks of showcase and interactive modes at 390 and 1440 px, light and dark, 0 axe-core violations.

## 7.4.0
- **Reliable deck statistics:** `deck_check.py` counts roles (ramp, draw, removal, counters, wipes, tutors, protection, recursion) from fixed Oracle-text rules in `analytics.py`, cards can fill several roles, and each role names the rule that matched. Claude's own labels no longer drive the numbers.
- **Analytics:** mana sources vs color requirements (Scryfall produced_mana, the deck's colors only); a seeded, reproducible cast-by-turn simulation with its assumptions stated; price ladders (affordable / as listed / premium printings) with dates.
- **Upcoming cards:** unreleased cards show as upcoming with their Scryfall release date, separate from banned and not-legal cards; brew can plan a `future` version.
- **Card pools:** `allocate.py` divides a pool (a Secret Lair, a box) between decks or players: wishes, then decks that list the card, then commanders whose colors fit; never assigns a copy twice; ties go to the players.
- **Research:** theme rankings (`rankings` in research.json, per group, with method, date and sample sizes) and verified commander checks recorded per candidate.
- **Workspace:** one persistent workspace wherever Claude Code starts; a local `EDHCompanion` folder is used only when marked with `workspace.yaml`; starting inside a project picks it up; `companion.py projects` lists projects to resume; projects are created and resumed conversationally. README "Working with your decks".
- **Wording:** shortcomings are named specifically (consistency, interaction, speed, resilience, mana), never "weak".
- **Tests:** 62 unit tests (role rules, mana, simulation, allocation, workspace and project detection).
- Coming next: report modes (summary / interactive / showcase), ranking tabs, multi-project showcases and commander color theming on the page.

## 7.3.0
- **Commander eligibility, current rules (effective 2026-09-25):** a commander is a legendary creature, legendary Vehicle, or legendary Spacecraft with power/toughness, or a card that says it can be your commander; never banned; never more than two. Pairings follow CR 702.124 exactly: partner, the same partner—[text] (Character select, Father & son, Friends forever, Survivors; old "Friends forever" wording still pairs), partner with each other, choose a Background + a Background, Doctor's companion + a pure Time Lord Doctor; abilities can't be mixed and a Background is never a commander alone. `deck_check.py --commander A [--commander B]` checks a commander without a deck and cross-checks Scryfall's `is:commander`. research and brew only recommend commanders that pass. Found while testing: the installed rules tool returns pre-2026 partner rules.
- **Budgets:** new "No expense spared: the ultimate blinged-out deck" option (collectibility called out separately from power). Budgets are flexible targets by default (over is a warning with the amount) unless the player says hard (`--hard-budget`, over fails). Recommendations come in small groups: within budget, worth stretching for (with the extra cost), and best regardless of budget; gameplay upgrades apart from printing upgrades.
- **Tests:** 46 unit tests (commander eligibility and pairings offline and against Scryfall, flexible vs hard budgets).

## 7.2.0
- **Getting the cards, on demand:** ask any time (before, during or after a build, or about one card or product) how to get cards. research checks real product contents (precons, Secret Lairs) against Scryfall, dated prices per printing, and availability (out of print, reprints, Reserved List); brew turns it into a short ranked plan (best path, buy-first cards, products vs singles, printing choices within the aesthetic budget, totals without owned cards), saved to ACQUISITION.md only if wanted. Offered after a finished deck, never forced. audit can check product contents and price claims. setup can save currency and preferred stores.

## 7.1.0
Themes that might not work, money and looks, exports.
- **Theme feasibility:** research checks whether a franchise really has Magic cards (no assuming either way), finds eligible commanders, counts the pool per color identity and role, and records a verdict (feasible, constrained, infeasible, unknown) with confirmed counts vs estimates. brew explains the compromises with numbers and offers real paths (a thematic commander, a broader visual/story or mechanical theme, approved exceptions, or casual custom/proxy cards clearly marked as not legal), recommends one, and never presents a deck as meeting rules it breaks. Themes now record their basis (official, visual/story, mechanical, inspired) and hard rules vs flexible preferences.
- **Rule changes:** loosening or tightening a theme updates PROJECT.md and DECISIONS.md, re-checks affected cards, and makes earlier audits stale (`companion.py goals-hash`; audits record it).
- **Two budgets:** gameplay (cheapest printings) and aesthetic (extra for foils, borderless, showcase, Secret Lair), plus a per-card max. `deck_check.py` reads `*F*`/`*E*` finishes, prices each printing and finish with a date, finds each card's cheapest printing (`--cheapest`), and checks `--budget`, `--aesthetic-budget` and `--per-card-max`. It fails finishes that don't exist and, when a set number points at another card, keeps checking the named card.
- **Card vs printing:** schemas separate a card's game identity (name, oracle_id) from its printing (set, number, finish, illustration, treatment, price with source, date and verified flag). Custom cards are flagged and never legal.
- **Exports:** `export_deck.py` writes Moxfield, Archidekt (commander tagged), plain text and CSV, keeping printings and finishes.
- **Alternatives and preferences:** brew offers community-backed swaps with trade-offs; research honours preferred and excluded sources (PROJECT.md or the setup config); setup can save looks and source defaults.
- **Tests:** 27 unit tests (finishes, budgets, exports, stale rules); evals for an official franchise, Stardew Valley, refusing exceptions, loosening midway, an honest weak-deck review, a drippy budget and an Archidekt export.

## 7.0.0
**The plugin is now EDH Companion** (`edh-companion`): four skills that research, build, verify and present Commander decks, with projects saved outside the plugin.

Moving from `mtg`: run `/plugin uninstall mtg@carlomos7-mtg-skills`, `/plugin marketplace remove carlomos7-mtg-skills`, then the install steps in the README. Old `/mtg:...` commands are gone; plain requests trigger the skills.
- **Skills:** `research` (cited community research and recommendations), `brew` (guided discovery, feasibility checks, builds and revisions inside your theme, art, budget and bracket), `audit` (independent pass / warning / fail / unverified checks, in a fresh agent for work made in the same chat), `present` (the existing deck-browser page, now built from project files), and an optional `setup`.
- **Projects:** `~/Documents/EDHCompanion/projects/<project>/` (or `./EDHCompanion`, or a folder you set) with PROJECT.md, STATE.md and DECISIONS.md in Markdown, plus research.json, brew.json and audit.json where structure helps (citations, decklists, checks, pages). Decklist versions are kept, never overwritten. Audits record the deck version they checked, so an out-of-date audit is detected.
- **`deck_check.py`:** deterministic Commander checks from Scryfall and Commander Spellbook's public APIs (real cards, printings matching their names, count, singleton, commander, identity, bans, Game Changers per bracket, commander + 2 combos, off-set printings, stats). Added because the tested MCP deck validator was down and its bracket estimator missed Game Changers and a banned card.
- **MCP-agnostic:** skills look for capabilities (card data, EDHREC, combos, decklists, search, transcripts), confirm them with one call, and fall back to the web; tested tool behaviour is documented.
- **Removed:** the commander-deckbuilding, commander-vault, collection and wrapper command skills (`build`, `check`, `cheaper`, `share`, `upgrade`), the vault agents (replaced by `researcher` and `auditor`), `vault-request.md`.
- **Tests:** unit tests for the deck checker, project validation and the page pipeline; evals for skill activation (positive, negative, ambiguous), persistence of rejected recommendations, theme drift, art mismatches, unsupported claims and conflicting sources.

## 6.0.0
The plugin moves to skills only. The in-house tooling is gone.
Removed:
- **The `mtgdb` MCP server and the `mtgdb.py` data CLI** (card index, deck checks, swap tests, simulation, price plans, exports, research logging, collection tools).
- **The deck and claims file-check hook** and its `vault/config.json`.
- **The `update-data` skill.**
- **The tests and the CI workflow.**
- **Eval graders** that checked in-house tool use.

Note: the page scripts (`site_data.py`, `build_site.py`) still call `mtgdb.py` and need rewiring. The page template is kept.

## 5.6.0
Page redesign: mobile first, one design system, accessible.
- **One set of tokens:** spacing (4 to 48px), type sizes, corner radii and card corners come from shared variables, so every panel, control and card lines up. Layout is written phone first and widens at 641, 821 and 1025px.
- **Card images:** the decklist has a List / Cards switch; Cards shows every card as an image grid (2 across on phones), with quantity, Game Changer and swap badges. Swap suggestions show a card thumbnail. All cards share one fixed 63x88 box with real card corners and a placeholder, so nothing jumps while images load. The viewer sizes the card to the screen so its buttons never fall off it, and the hover preview sits beside the pointer instead of over the next names.
- **Accessibility:** no automated WCAG 2.2 AA failures in light or dark mode (was about 300). Every target is at least 24px, 44px on touch screens. Theme tags pick a text color that passes contrast. Headings are in order, the tabs are a labelled nav, there's a footer, and pressed states read as pressed. No sideways scroll at 320px.
- **Also:** sticky tabs no longer hide focused items, safe-area insets for notched phones, and a print style that prints the decklist as text.

## 5.5.6
- **Better page filters:** the decklist filters are now chips you can combine: card type, mana value, role, theme and tags (Game Changers, cards with swap options, flagged cards). Chips in one row widen the list (Instant or Sorcery); rows narrow it (and Removal). Each chip shows how many cards it would leave, empty ones grey out, and Clear filters resets everything. Search also matches type and role. The card-rankings tab gets tier, price and theme chips in place of the max-price box. Filters are remembered and scroll sideways on phones. A browser test covers them.

## 5.5.5
- **Hover preview fix:** 5.5.4 hid the preview on scroll, which hid it as soon as it showed. It now shows on hover and hides on click, key press, tab change and when the viewer opens. A browser test covers it.

## 5.5.4
Fixes from an independent review against every requirement:
- **Privacy:** deck pages no longer contain local file paths (a ledger path with the Windows username was leaking), and `build_site.py` refuses to build a page that contains one.
- **Honest claim counts:** logged sources are `sourced`, not `verified`; only the vault's second reviewer marks a claim verified. The page shows re-checked, sourced and unverified counts separately.
- **Theme cap holds for swaps:** `mtg_deck_check` and `mtg_deck_swap` take the theme map (`themes`, `reasons`), so a swap that breaks the player's off-theme limit fails instead of being offered.
- **Deck page:** the hover preview no longer sticks after a click, tab change or opening the viewer; the template check marks "above range" as fine instead of red (card tags count a card in every role); plain-language check labels; the three price styles (cheapest, as listed, drippy) under the numbers; store links go straight to the store (no affiliate redirect); the faded card fan behind the title on phones is gone.
- **Research tools:** `mtg_decklists` keeps only finished lists (98+ cards) and dates them by creation; `mtg_edhrec` supports partners; both return ready-made log entries; the "no videos" warning is per commander.
- **Docs agree:** Fancy uses the three.js viewer by default everywhere; pages.md covers single-deck pages; one data-refresh rule (refresh during deck work, offer for one-off questions); research starts once bracket and theme are known; must-include cards ride along with the defaults question; bracket estimates run on the final 100; the hook's coverage is described accurately; page-spec matches the template.

## 5.5.3
- **Every vault page comes out the same shape:** `build_site.py` prints an `incomplete:` warning for each missing part (deck summary parts, community takes, videos, cards to consider, 10+ grouped sources), and the vault fixes each one or explains it in `plan.md`. pages.md lists what every page has.
- **The vault uses the research pass:** G1 follows research-pass.md (minimums, best tool first, logged sources, takes.json); a deck from the build skill brings its research along; notes carry community takes and videos; cards to consider cite their evidence.
- **Vault checks:** commander + 2 combos count as two-card combos at brackets 1 to 3; bracket-estimate add-ons are a second opinion; the render check covers snap-back, ⇄ swap options, card links and the Sources tab.
- **vault-request.md** describes the community section, swap marks, card links, grouped sources and the research pass.

## 5.5.2
- **Edge cases fixed in the research tools:**
  - `mtg_edhrec` and `mtg_decklists` fall back to the last cached copy (flagged stale) when offline.
  - Cache files are written atomically.
  - Archidekt cards without card data no longer crash the comparison.
- **The research log:**
  - accepts a JSON list, one object, or a JSONL file (including its own ledger), with a clear error for bad JSON
  - writes the full claims format, so `audit-claims` passes
  - the report lists sources missing a date or a video timestamp
- **`mtg_research_log`** needs a full folder path and passes entries through a file, so large logs work on Windows.
- **`mtg_deck_swap`** now reports every combo a swap completes. Ones needing only the commander plus two cards still fail brackets 1 to 3; bigger ones are a Rule 0 warning.

## 5.5.1
- **Best tool first, then fall back:** the research pass now has an explicit order per source type (card data, stats, combos, bracket estimate, decklists, videos, community, articles, prices, official, cEDH): installed add-ons first for the best results, then the built-in tools, then web search or fetch, never memory. Which tool answered is logged, and a row that only got the last resort is said out loud. `mtg_research_plan` returns the order too.

## 5.5.0
- **Research pass built into the MCP server:** `mtg_research_plan` (every source type, its minimum, the tool and ready-made queries), `mtg_edhrec` (EDHREC numbers built in, no add-on needed; with a deck, what it lacks), `mtg_decklists` (recent public Archidekt lists by bracket; cards most lists play that you don't, and your cards nobody plays), and `mtg_research_log` / `mtg_research_report` (a cited source ledger with coverage and shortfalls).
- **Every new deck runs it**, usually as the background research agent while you answer the intake: EDHREC, 6+ real decklists, combos, 3+ creator videos, 4+ Reddit threads, 3+ articles, live prices, the Wizards bracket page, and cEDH results at bracket 4 and 5.
- **Combo fix:** a combo that needs only the commander plus two cards now counts as a two-card combo for brackets 1 to 3 (before, Azula + Frantic Search + Narset's Reversal slipped through), and `mtg_deck_swap` blocks swaps that complete one.
- **Deck pages:** "researched from N sources" in the deck header, and a Sources tab grouped by type (decklists, videos, community, articles...) with what each source was used for.

## 5.4.0
- **Community research on every build:** before the plan, the build checks Reddit (r/EDH, r/EDHBrews, r/CompetitiveEDH), articles and primers, and 2 or 3 recent creator videos, then keeps 6 to 10 takes with their sources. Combos the community mentions are checked against your bracket.
- **"What the community says" on the page:** each take links to its thread, article or video, with a Watch list and every source in Sources & accuracy.
- **YouTube fallback:** when the transcript tool is blocked, the video page is fetched with a web fetch tool instead, which usually returns the transcript.
- **Responsive pass:** phone and tablet layouts tidied (stacked overview, two-up filters, readable rows, viewer controls no longer overlap the card name), checked at 390, 768, 1024 and 1440 px.

## 5.3.0
- **Links on every card:** the card viewer has Scryfall, EDHREC, TCGplayer and Cardmarket buttons; in the decklist the price opens the exact printing on TCGplayer and ↗ opens it on Scryfall. Basic pages (no viewer) link card names to Scryfall.
- **Page layout reordered:** deck header with Copy for Moxfield up top, then the plan next to the numbers, the decklist, cards to consider, the game plan, and the charts last in a 2 by 2 grid. The bracket switch only shows when there's more than one bracket.
- **Card viewer:** the card leans toward the mouse on hover, shows a grab cursor, and snaps back to the nearest face when you let go of a drag.

## 5.2.0
- **New page design for Fancy (and Basic):** bold display type, a 3D card fan in the header (filled from the deck's key cards on one-deck pages), big-number stat tiles, a 3-column decklist with mana symbols, rarity dots and Game Changer marks, card previews on hover and a darker card viewer.
- **Swap options:** after a build you're asked if you want them (best few, or cheaper ones). Each swap is tested at the deck's bracket and shows in Cards to consider, as a ⇄ mark in the decklist, and under the card in the viewer.
- Readable price dates, one three.js load per page. Card data now includes rarity: run `/mtg:update-data` (or it refreshes on your next build) to get rarity dots.

## 5.1.0
- **Skills reviewed against Anthropic's skill-authoring guidance** (docs/research/skill-authoring.md): descriptions say where each skill stops, trigger text moved out of Claude Code-only fields, gotchas sections from real failures, rules explain their reasons, no shell blocks that can abort a skill, and routing evals with near-misses.
- **Add-ons are used by default when installed:** EDHREC staples and synergy shape the plan, the picks, reviews and upgrades (quoted with deck counts); bracket estimates and deck links too. Without them the build still works and says once what wasn't available.
- **Quick by default, customizable whenever you want:** data refreshes without asking, the default path keeps picks to the 2 or 3 that matter, and the page choice (including images) is one question.
- **Page styles:** Fancy (images, charts, rankings, cards to consider, 3D viewer) or Basic (deck and numbers, no images), or customize sections; Fancy pages can download images (shareable) or use Scryfall's image links (local, no download). Basic loads no libraries.
- **Themes are respected:** the trade-off is mentioned once at most; no re-arguing, no off-theme suggestions unless asked; a thin strict pool becomes choices, not pushback.
- **3D card viewer option:** vault pages can use a three.js viewer (spin cards freely, pointer-lit foil shine) instead of the default simple one; it loads only when chosen and falls back on devices without 3D.
- **Fast path:** one click to use the recommended setup and skip the questions; the upgrade flow has it too.
- **Collection:** import from Moxfield, Archidekt or ManaBox, add and remove cards, undo, value, search, what a deck still needs, what fits a commander, export (`/mtg:collection`).
- **Money is asked once:** no limit (default), keep it cheap, a set budget, or drippy (fancy printings up to a per-card max). "Bling" is now "drippy".
- **Recommended next steps** at every stage, with the recommended option marked.
- **Decks are saved as you build** (`deck-brief.md` and `<commander>.txt`), and `/mtg:commander-vault` with nothing after it builds a vault from that deck.
- **Page offer:** once a deck passes every check, Claude offers to show it as a commander vault page.
- Optional add-ons are found by what they do; deck links work with any add-on that reads that site.
- Fixes from two independent reviews (foil marks on export, Arena and Archidekt pastes, Windows certificate and file-lock issues, and more).

## 5.0.0
- First public version: MCP server with card data, deck checks, prices, combos and rules; collaborative deckbuilding skills; short `/mtg:*` commands; multi-commander vaults.
