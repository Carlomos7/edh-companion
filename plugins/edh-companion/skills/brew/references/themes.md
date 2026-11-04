# Themes and artwork

**Default: no theme.** A theme applies only when the player asks for one. "I want Frodo as my commander" is a commander choice; ask once whether the other 99 should follow.

## The player's theme is the goal
Build the best deck *inside* the theme they chose; don't steer them back toward power.
- Say a real trade-off **once**, at the plan ("Strict Spider-Man is light on removal; I'll use the best on-theme removal there is"). Then drop it.
- No "a stronger option would be…", no off-theme suggestions, unless they ask ("what am I giving up?").
- A thin pool is a puzzle, not a refusal. Offer, recommended first: keep it strict and fill with the best on-theme cards (Recommended) · allow a few off-theme staples (they pick how many) · widen to the franchise.
- What still holds, theme or not: legality, color identity, the bracket rules they asked for. Say so plainly when one blocks a themed card and offer the closest themed card that fits.

## Questions (only the ones not answered yet)
1. **How strict?** No theme (best deck) · Themed printings when they exist (`printings`) · Mostly on theme, a few exceptions (`prefer`, with a limit) · Strictly on theme (`strict`).
2. **What counts as on theme?** In the player's words, e.g. "Spider-Man characters and Spider-Man set cards", "any Marvel", "only villains". Record it verbatim in PROJECT.md (Theme → Counts as on theme).
3. **Does artwork matter?** If yes, a card is on theme only in a printing whose art shows the theme, so every themed card needs a `printing_id` in brew.json and `(SET) number` in the decklist.
4. **Exceptions?** Basics, a few staples, specific cards. Record them in PROJECT.md (Theme → Allowed exceptions); anything else off theme needs the player's yes and a dated line in DECISIONS.md.

Unclear cases (a symbiote in a Spider-Man deck, a hero who later turns villain, a reprint with the original art) are questions for the player, recorded in brew.json `theme_policy.unresolved` and STATE.md until answered. Don't decide them silently either way.

## Finding on-theme cards and printings
- Set codes first: Scryfall `e:<set>` for the franchise's sets, `unique:prints` to see every printing of a card.
- Then art and flavor: `art:<tag>`, `ft:"<word>"`, character names in `o:` and type lines. Name or flavor matches are leads; the art (looked at, not assumed) decides.
- Secret Lair and promo printings carry many franchise arts; check each one's image.
- Unplayable printings (gold border, digital-only, oversized) never count as an available themed printing.

## Per card in brew.json
`deck[].theme`: `on_theme` (meets eligibility, printing recorded when art matters) · `exception` (an allowed exception in PROJECT.md or approved in DECISIONS.md) · `off_theme` (only in `printings`/`prefer` mode within the limit, with a one-line reason) · `n/a` (basics when exempt) · `unchecked` (not yet looked at: never in a build handed back as ready).

## Report
One theme line in brew.md: "84 on theme · 6 exceptions (basics excluded) · 2 off theme (limit 5)". Add the themed-printing price premium only if money matters to them.

## Edge cases
- Commanders are exempt from counts unless the player wants an on-theme commander.
- Budget vs theme: when both can't hold, ask. Never silently drop either.
- Owned plain copy vs a paid themed printing: ask once for the whole deck.
- Partners/backgrounds: both exempt, or both must match if the commander must be on theme.
