# Themes, feasibility and compromises

**Default: no theme.** A theme applies only when the player asks for one. "I want Frodo as my commander" is a commander choice; ask once whether the other 99 should follow.

## The player's theme is the goal
Build the best deck *inside* the theme they chose; don't steer them back toward power.
- Say a real trade-off **once**, when it matters, then drop it. No "a stronger option would be…" unless they ask.
- A thin pool is a puzzle, not a refusal. But an impossible deck is never presented as possible.
- Always true, theme or not: legality, color identity, 100 cards, the bracket rules they chose.

## 1. Pin down what "on theme" means
Ask only what isn't clear from their words, one question at a time:
- **Basis:** official franchise cards or art · visual/story match from any set · mechanically thematic (plays like the theme) · inspired (mix, case by case). "Strictly on theme" for a franchise usually means *official*; confirm when it matters.
- **Strictness:** strict · prefer (a few approved exceptions) · themed printings when they exist · none.
- **Artwork:** does the printing's art have to show the theme?
- **Hard rules vs flexible preferences:** which parts can bend with a reason (lands, mana rocks) and which never can.
Record all of it in PROJECT.md (Theme section). Unclear cases (a symbiote in a Spider-Man deck, a reprint with original art) go to the player as a question and sit in STATE.md until answered.

## 2. Check feasibility before committing (research owns the evidence)
Don't assume a franchise has Magic cards, and don't assume it doesn't. research checks and writes `research.json.feasibility`:
- **Official pool:** search Scryfall for the franchise (set names, `e:`, `art:`, `ft:`, `name:`, Secret Lair drops, promos) and official product pages. Zero hits after a real search is a finding, not a guess; say which searches were run.
- **Commanders:** eligible legal commanders (legendary creatures or "can be your commander") in the pool. No eligible commander means a strict deck can't be legal.
- **Count by color identity and role:** nonland cards per identity, then ramp, draw, removal, wipes, threats, lands. Compare with construction.md's targets.
- **Verdict:** `feasible` · `constrained` (legal, with real gameplay costs) · `infeasible` (no legal 100-card deck under these rules, confirmed) · `unknown` (research incomplete). Say which parts are counted (confirmed) and which are estimated.

### The pool lockfile (franchise themes)
For an official franchise theme, keep the pool as a reviewed lockfile instead of re-searching each session: `uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/pool.py" sweep <project>` writes `sources/pool.lock.json` (every printing, keyed by Scryfall id, with the evidence for it and a status) and `sources/pool.diff.md` (what changed). The rule for what counts lives in `sources/theme-rule.json` (set-name and Secret Lair drop patterns, which evidence is strong, weak or rejecting, which wins a conflict); edit it for a theme other than Marvel.
- **Only `accepted` entries are the pool.** `pending` ones (one weak channel, e.g. a Secret Lair card with no drop name) are candidates: read their footers with `art_sheet.py <project> --footer` and record them (`pool.py footer <project> --marvel ID … --not ID …`), or ask the player (`pool.py accept|reject`).
- **Art:** `sources/art_notes.json`, keyed by `illustration_id` (stable across reprints), says who the art shows. Look only at what it lacks: `art_sheet.py <project>` makes contact sheets of unchecked art; record with `pool.py art <project> ID --characters "…"`. `pool.py art-seed` adds Scryfall Art Tags as unverified hints.
- **Freshness first:** brew and audit run `pool.py freshness <project>` before relying on the pool. Warnings (Game Changers or bans changed, theme sets grew, ID migrations, stale art notes) are reported; an error (data unreachable, pool older than its error age in `sources/freshness.json`) makes theme checks `unverified` until a new sweep.
- Deck usage is never stored in the lockfile; derive it from the brew files.

## 3. When it's constrained or infeasible, offer real paths
Explain with the numbers ("Scryfall has 0 official Stardew Valley cards; a strict build can't have a legal commander"). Then 2 to 4 options, recommended first, each with what it costs:
- **A thematic commander from elsewhere** whose art or story fits (visual/story basis).
- **Broaden the basis:** visual/story match, or mechanically thematic ("farming" → landfall, Food, Plants, seasons).
- **Approved exceptions:** a stated number of off-theme staples, or lands/rocks only.
- **Casual custom or proxy cards**, clearly labelled: custom cards aren't legal Magic cards; they're only for a playgroup that agrees (Rule 0). Never mix them into a list presented as legal; mark them `custom: true` in brew.json.
Recommend one, explain why, and let the player choose. One question, not a questionnaire.

## 4. Hard constraints that can't be met
If the player keeps an infeasible hard rule, don't fabricate a compliant deck. Offer what can honestly exist: the partial pool as an incomplete concept (marked "not a legal deck: N cards, no commander"), a casual custom-card version clearly labelled, or a path that bends a different rule. Record their choice and the rejected compromises in DECISIONS.md.

## 5. Build inside the approved rules
- Every card in `deck` has `theme`: `on_theme` (meets the basis; printing recorded when art matters) · `exception` (allowed in PROJECT.md or approved in DECISIONS.md) · `off_theme` (only in prefer/printings mode, within the limit, with a reason) · `n/a` (exempt basics) · `unchecked` (never in a list handed back as ready).
- Art-based themes need a `printing_id` and `(SET) number` for every themed card; the art is looked at, not assumed from the name or set.
- Finding printings: Scryfall `unique:prints` with `e:`, `art:`, `ft:`; Secret Lair and promos carry many franchise arts. Unplayable printings (gold border, digital, oversized) never count.

Preference inside the theme (e.g. "Spider-Verse first, other Marvel when stronger"): list it as `theme_policy.tiers` in order (`[{id, label}]`) and tag each on-theme card's `deck[].theme_tier`. It's shown on pages and counted; it never makes a card off theme.

## 6. When the rules change
"Actually, let's loosen it" (or tighten it): update PROJECT.md and add a dated DECISIONS.md line; re-check the cards the change affects (newly allowed upgrades become *proposals*; newly forbidden cards become required fixes); treat earlier audits as stale; tell the player what changed.

## 7. Report honestly
A theme line ("84 on theme · 6 exceptions · 2 off theme, limit 5") and the deck's theme-driven weaknesses in brew.json `limitations` and PROJECT.md "Known limitations": consistency, interaction, mana, win conditions, realistic bracket. Offer improvements that stay inside the rules first; ones needing a new exception are offered, never pushed.

## Edge cases
- Commanders are exempt from counts unless the player wants an on-theme commander.
- Budget vs theme: when both can't hold, ask; never silently drop either.
- Partners/backgrounds: both exempt, or both must match if the commander must be on theme.
