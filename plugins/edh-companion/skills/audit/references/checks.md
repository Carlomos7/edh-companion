# Check protocol

Every check in audit.json has `kind`: **deterministic** (script/tool result with fixed rules), **sourced** (compared with a cited authority), or **judgment** (an assessment; shown as such, never as proof). Status meanings:
- `pass`: the requirement is met and you have the evidence.
- `warning`: met, but with a caveat the player should know (bracket 3 combo that's late-game, an exception near its limit).
- `fail`: not met.
- `unverified`: couldn't be checked (tool down, image not inspectable, source unreachable, rule ambiguous). Say why.

## Theme eligibility
1. Read the Theme section of PROJECT.md (mode, what counts as on theme, whether artwork matters, allowed exceptions and limits) and the exceptions in DECISIONS.md. The player's words define eligibility; don't widen or narrow them.
2. For each non-exempt card, decide on-theme by the rule that applies:
   - Set-based rule ("Spider-Man set cards"): the printing's set code. deck_check.py `--theme-sets` lists printings outside the sets.
   - Character/franchise rule ("Spider-Man characters"): the card's name/type/text identifies the character (sourced: Scryfall) or the art shows them (see below).
   - Art rule (`art_required`): the specific printing's art must show the theme.
3. Count exceptions and off-theme cards against the limits. Over the limit or not approved → `theme_violations` + a fail.
4. Ambiguous cases from `theme_policy.unresolved` are `unverified` with the question, not decided by the auditor.
5. Judge by the theme's **basis** in PROJECT.md (official / visual-story / mechanical / inspired) and its hard rules; flexible preferences can't fail a deck, hard rules can.

## Commander eligibility (CR 903.3, 702.124; rules effective 2026-09-25)
- A commander is a legendary creature, legendary Vehicle, or legendary Spacecraft with power/toughness, or a card that says it can be your commander. Not banned in Commander.
- Two commanders only through one shared partner ability; abilities can't be mixed: both **partner**; both the **same "partner—[text]"** (Character select, Father & son, Friends forever (old cards printed "Friends forever" alone), Survivors); **partner with** each other by name; **choose a Background** + a legendary Background enchantment; **Doctor's companion** + a legendary creature that is only a Time Lord Doctor. Never more than two.
- A Background is never a commander on its own.
- Color identity is the two commanders' combined identity.
- `deck_check.py` checks all of this (chk-legality-2, chk-legality-3) and cross-checks Scryfall's `is:commander`. A rules tool that predates 2026 gets partners wrong; trust the current rules text.

## Feasibility claims
- Re-run the searches behind `research.json.feasibility` (or a brew claim like "no official cards exist", "only 6 eligible removal spells"). Same result: pass with the queries in evidence. Different result: fail. Couldn't run: unverified.
- `infeasible` needs a confirmed count (for example no eligible commander); an estimate can only support `unknown` or `constrained`.
- A deck presented as meeting a theme it can't meet is a fail, whatever else passes.

## Custom and proxy cards
Entries with `custom: true` (or names Scryfall can't find) are never legal Magic cards. A list containing them fails legality, even if the playgroup allows them; the audit says "casual/Rule 0 only" and checks the rest normally.

## Budgets and prices
When PROJECT.md sets budgets: run deck_check with `--cheapest --budget --aesthetic-budget --per-card-max`, adding `--hard-budget` only when PROJECT.md calls the limit hard. Over a hard limit fails; over a flexible target is a warning with the amount; unpriced cards make the check unverified. "No expense spared" has no limit to check; just report what the premium buys (looks vs gameplay). Prices are Scryfall's daily price for that printing and finish, dated; any other figure is an estimate and is labelled so.

## Acquisition claims
When an acquisition plan is checked: products really contain the cards claimed (Scryfall `e:` search or the official list), prices have a source and date and match that printing and finish, availability claims (out of print, reprint announced, sold out) are cited, owned cards are excluded only if the player listed them. Unsupported claims are warnings; a wrong product content or price is a fail.

## Artwork and printings
- When the theme depends on art, every themed card must have a `printing_id` (or set + collector number). Missing → `fail` ("printing not specified, art can't be verified").
- Open the image (`art_crop` from deck_check.py JSON, or the Scryfall card page) and describe what it shows in `detail` ("Spider-Man swinging past a skyline"). A name or set alone doesn't prove the art.
- Universes Beyond and Secret Lair reprints: the same card often has both franchise art and plain art; check the listed printing, not the card in general.
- Can't view images in this environment → `unverified` with the image URLs for the player.
- Printing playability: gold border, digital-only and oversized printings fail (deck_check.py chk-printing-1).

## Combos
- Copy Commander Spellbook's included combos from deck_check.py with their ids/URLs.
- Interactions the research or brew mentions that Spellbook doesn't list: walk them step by step with Comprehensive Rules citations, listing every piece; if you can't, `unverified`.
- Bracket relevance: two-card (commander + up to 2 cards) at B1–B2 fail; at B3 warning, judged on whether it's an early or held win.

## Composition and mana (judgment on calculated data)
Compare deck_check stats with the plan and [construction defaults](../../brew/references/construction.md): lands vs curve, ramp, draw, interaction, wipes, color sources vs pips. Report numbers as calculated and the verdict as judgment.

## Research completeness
- Coverage: does `methodology.coverage` include data, decklists, creators and community for a standard pass? Missing types → research_gaps.
- Recency: power/legality claims from before the latest bans/Game Changers update can't decide anything.
- Sources: open every high-impact source (must-play, combo, ban, theme/printing, cEDH) and at least a fifth of the rest. "Source exists but says something else" is a fail. Unreachable is unverified.
- Statistics: sample size present; under ~50 decks flagged low confidence.
- Class inflation: a `community_opinion` or `model_assessment` worded as fact is a warning.
- Blind spots: an obvious commander, strategy, or high-synergy card missing; disagreements smoothed over.

## Recommendations
For each `rec-`: the cut is in the accepted deck; the add exists, is legal, in identity, within bracket and theme; evidence IDs resolve and support the reason; it doesn't contradict a decision (re-proposing a rejected card is a fail unless the reason changed and is stated).

## Verdict wording
- Lead with the verdict and the count of fails/unverified.
- Separate "what's objectively wrong" from "what I'd judge differently".
- Never write "verified" for something that was assumed.
