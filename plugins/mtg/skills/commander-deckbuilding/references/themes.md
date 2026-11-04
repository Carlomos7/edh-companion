# Themes (optional)

**Default: no theme.** Only apply a theme when the user asks for one. "I want Frodo as my commander" is a commander choice, not a theme for the other 99 cards: ask once whether they also want the rest on theme.

## The player's theme is the goal, not a problem to fix
When someone wants a theme deck, the theme **is** what makes the deck good for them. Build the best deck *inside* the theme they chose; don't steer them back toward power.
- **Say the trade-off once, at most:** one short line at the skeleton, as information ("Strict Fellowship leaves the deck a bit light on removal; I'll use the best on-theme removal there is"). Then drop it.
- **Never re-argue it.** No "a stronger option would be...", no off-theme suggestions, no repeating the power cost, unless they ask ("what am I giving up?", "any stronger cards?").
- **Never slip in off-theme cards** in strict mode, and in prefer mode only within the limits they set.
- **A thin pool is a puzzle, not a refusal.** If strict is tight, tell them once and offer choices, recommended first: "Keep it strict; I'll fill the gaps with the best on-theme cards and themed lands (Recommended)" · "Allow a few off-theme staples (you pick how many)" · "Widen to the franchise".
- **What still holds, theme or not:** Commander legality, color identity and the bracket rules they asked for. Say so plainly if one blocks a themed card, and offer the closest themed card that fits.


## Intake question (one, multiple choice)
"How much should the rest of the deck follow <theme>?"
- **No theme**: just the best deck for this commander.
- **Theme when free**: best cards, but use themed printings of them.
- **Mostly on theme**: on theme, with a few off-theme staples where they really help (you set how many).
- **Strictly on theme**: nothing off theme.

Also ask, only if relevant: is the wider franchise OK, and how much extra are they willing to pay for themed printings.

## Factions and sub-themes (Fellowship vs Sauron's forces, Jedi vs Sith)
Factions aren't in card data, so they're a judgment the user confirms:
1. Start with the whole franchise (every Middle-earth printing).
2. Propose faction groups from card names, type lines, flavor text and art, in priority order, e.g. Fellowship, Sauron, Middle-earth.
3. Show everything assigned to the smaller faction plus anything ambiguous (characters who switch sides, like Gollum). Let the user move disputed cards (picker page or a list).
4. "Only Sauron's side" is then strict with the Sauron group, or prefer with a limit on the wider franchise for "mostly Sauron's side".

## Kinds of theme (all handled the same way)
| Kind | Example | Scryfall queries |
|---|---|---|
| Printing / IP | Middle-earth, Final Fantasy, Doctor Who | `e:ltr`, `e:fin`, `e:sld art:hobbit`, `e:sld ft:"shire"` |
| Flavor / tribe | Vampires, Dinosaurs, Pirates | `t:vampire`, `o:vampire`, `art:vampire` |
| Art style | Showcase frames, borderless anime | `frame:showcase`, `is:borderless` |
| Commander only | "Frodo, rest anything" | (only check the commander is on theme if they want it) |

## Edge cases
- **Commanders** are exempt from counts and limits by default, so any commander works. Require an on-theme one only if they ask.
- **Basic lands** don't count toward limits but a missed themed basic is still flagged.
- **Unplayable themed printings** (gold border, digital-only, oversized, memorabilia) never count as an available themed printing.
- **Price**: themed printings can cost 10x. warn per card above their max; tell the user the total premium and offer the cheaper themed printing or the plain one.
- **Budget vs theme**: when both can't hold, ask. Don't silently drop either.
- **Collection vs theme**: if the user owns a plain copy and the themed one costs money, ask which they prefer (once, for the whole deck).
- **Reasons** (bookkeeping, not a debate with the player): in prefer mode, every off-theme card needs a one-line reason.
- **Strict feasibility**: check the pool before a strict build. If the pool is thin, say so once with the choices in "The player's theme is the goal" above; keeping it strict is a fine answer.
- **Partners / backgrounds**: both commanders are exempt and both must match if the commander has to be on theme.

## Report to the user
Show the theme line ("82% on theme: 71 Fellowship · 11 Middle-earth · 7 off-theme"; add the themed-printing premium only if money matters to them). List off-theme cards that were left out only if they ask what the theme costs.
