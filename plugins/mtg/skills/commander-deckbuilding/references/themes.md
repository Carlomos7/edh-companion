# Themes (optional)

**Default: no theme.** Only apply a theme when the user asks for one. "I want Frodo as my commander" is a commander choice, not a theme for the other 99 cards: ask once whether they also want the rest on theme.

## The player's theme is the goal, not a problem to fix
When someone wants a theme deck, the theme **is** what makes the deck good for them. Build the best deck *inside* the theme they chose; don't steer them back toward power.
- **Say the trade-off once, at most:** one short line at the skeleton, as information ("Strict Fellowship leaves the deck a bit light on removal; I'll use the best on-theme removal there is"). Then drop it.
- **Never re-argue it.** No "a stronger option would be...", no off-theme suggestions, no repeating the power cost, unless they ask ("what am I giving up?", "any stronger cards?").
- **Never slip in off-theme cards** in strict mode, and in prefer mode only within the limits they set.
- **A thin pool is a puzzle, not a refusal.** If `theme-pool` says strict is tight, tell them once and offer choices, recommended first: "Keep it strict; I'll fill the gaps with the best on-theme cards and themed lands (Recommended)" · "Allow a few off-theme staples (you pick how many)" · "Widen to the franchise".
- **What still holds, theme or not:** Commander legality, color identity and the bracket rules they asked for. Say so plainly if one blocks a themed card, and offer the closest themed card that fits.


## Intake question (one, multiple choice)
"How much should the rest of the deck follow <theme>?"
- **No theme**: just the best deck for this commander. → `mode: none` (or no theme file)
- **Theme when free**: best cards, but use themed printings of them. → `mode: power`
- **Mostly on theme**: on theme, with a few off-theme staples where they really help (you set how many). → `mode: prefer` (+ `max_off_theme`)
- **Strictly on theme**: nothing off theme. → `mode: strict` (run `theme-pool` first)

Also ask, only if relevant: is the wider franchise OK (`franchise_label`, `max_franchise`), and how much extra are they willing to pay for themed printings (`max_premium_per_card`).

## Factions and sub-themes (Fellowship vs Sauron's forces, Jedi vs Sith)
Factions aren't in card data, so they're a judgment the user confirms:
1. `theme-build` the franchise first (every Middle-earth printing).
2. Propose faction labels from card names, type lines, flavor text and art (`search` with `art:`/`ft:`/name terms), as separate labels in priority order, e.g. `["Fellowship", "Sauron", "Middle-earth"]` with `franchise_label: "Middle-earth"`.
3. Show a `contact-sheet` of everything assigned to the smaller faction plus anything ambiguous (characters who switch sides, like Gollum). Let the user move disputed cards (picker page or a list), then record them as `include`/`exclude` in the spec and rebuild.
4. "Only Sauron's side" is then `mode: strict` with labels `["Sauron"]`, or `prefer` with `franchise_label: "Middle-earth"` and `max_franchise` for "mostly Sauron's side".

## Kinds of theme (all handled the same way)
| Kind | Example | Spec queries |
|---|---|---|
| Printing / IP | Middle-earth, Final Fantasy, Doctor Who | `e:ltr`, `e:fin`, `e:sld art:hobbit`, `e:sld ft:"shire"` |
| Flavor / tribe | Vampires, Dinosaurs, Pirates | `t:vampire`, `o:vampire`, `art:vampire` |
| Art style | Showcase frames, borderless anime | `frame:showcase`, `is:borderless` |
| Commander only | "Frodo, rest anything" | `mode: none` (+ `commander_must_match` only if they want it checked) |

## Spec → map
Write `theme-spec.json`, then `uv run "${CLAUDE_PLUGIN_ROOT}/scripts/mtgdb.py" theme-build theme-spec.json --out themed-printings.json`.
```json
{"mode": "prefer", "franchise_label": "Middle-earth", "max_off_theme": 8, "max_franchise": null,
 "max_premium_per_card": 15, "count_basics": false, "exempt_commanders": true, "commander_must_match": true,
 "labels": [
  {"label": "Fellowship", "queries": ["e:ltr t:legendary (frodo or sam or gandalf or aragorn)"], "include": [], "exclude": []},
  {"label": "Middle-earth", "queries": ["e:ltr", "e:ltc", "e:sld (art:hobbit or ft:shire)"], "exclude": []}]}
```
- Labels are in **priority order**. A printing matched by several labels gets the first.
- `include` / `exclude` keys: Scryfall printing id, `set#cn`, `set:code`, `oracle:<oracle id>`, or `name:<card name>` (any printing of that card counts).
- **Secret Lair is one set (`sld`)** for every drop, so never use `set:sld`. Use queries plus includes and excludes.
- Then verify the map before trusting it:
  - False positives: `contact-sheet` of the matched Secret Lair and promo printings, and look at it.
  - Gaps: `search` the theme by name, art and flavor across all sets, then diff against the map.
  - Disputed art goes in `exclude` or `include` with a note.

## What validate does per mode
| | none | power | prefer | strict |
|---|---|---|---|---|
| Theme tags and counts | no | yes | yes | yes |
| Missed themed printing of the same card (free swap) | no | warn | warn | warn |
| Off-theme card | – | fine | warn if no reason | **error** |
| `max_off_theme` / `max_franchise` | – | error if set and exceeded | same | same |
| `commander_must_match` | – | error if set | same | same |

Always reported: `on_theme_pct`, off-theme list, franchise list, `theme_premium_usd` (extra cost of themed printings over the cheapest playable one).

## Edge cases (handled by the script)
- **Commanders** are exempt from counts and limits by default (`exempt_commanders`), so any commander works. Set `commander_must_match` to require an on-theme one.
- **Basic lands** don't count toward limits (`count_basics: false`), but a missed themed basic is still flagged.
- **Unplayable themed printings** (gold border, digital-only, oversized, memorabilia) never count as an available themed printing.
- **Price**: themed printings can cost 10x. `max_premium_per_card` warns per card; tell the user the total premium and offer the cheaper themed printing or the plain one.
- **Budget vs theme**: when both can't hold, ask. Don't silently drop either.
- **Collection vs theme**: if the user owns a plain copy and the themed one costs money, ask which they prefer (once, for the whole deck).
- **Reasons** (bookkeeping, not a debate with the player): in prefer mode, every off-theme card needs a one-line reason (`--reasons file.json`, or `off-theme.json` next to vault decks). Missing reasons are warnings.
- **Stale map**: maps older than `max_map_age_days` (45) warn; rebuild after new sets or Secret Lair drops.
- **Strict feasibility**: run `theme-pool <commander>` before a strict build. If the pool is thin, say so once with the choices in "The player's theme is the goal" above; keeping it strict is a fine answer.
- **Partners / backgrounds**: both commanders are exempt and both must match if `commander_must_match`.

## Report to the user
Show the theme line ("82% on theme: 71 Fellowship · 11 Middle-earth · 7 off-theme"; add the themed-printing premium only if money matters to them). List off-theme cards that were left out only if they ask what the theme costs.
