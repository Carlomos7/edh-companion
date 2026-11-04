# Budgets, printings, brackets, alternatives and export

## Two budgets
Players often care about two different things:
- **Gameplay budget:** what the deck costs to play, judged on each card's cheapest paper printing.
- **Aesthetic budget:** what they'll pay on top for looks: foils, etched, showcase, borderless, extended art, Secret Lair, a cohesive art style, a "drippy" deck. Often a per-card max ("nothing over $30 a copy").
Ask money once, casually ("How do you wanna do cards?"):
- **Just build it, I'll see the price at the end** (Recommended)
- **Keep it cheap**
- **I've got a budget** → "About how much? Is that a hard limit or a rough target?"
- **Drip it out** (nicer printings, with a per-card max)
- **No expense spared: the ultimate blinged-out deck**: premium printings, rare art, collectible treatments (serialized, Secret Lair, foil-etched, borderless) and a cohesive look, no cap.
Only split it into the two budgets if they care about looks. Record it in PROJECT.md (Budget), including whether each limit is **hard** or a **flexible target**.

**Budgets guide; they don't hide options.** Unless the player says "hard limit", a budget is a target with some wiggle room (about 10 to 15%). Never silently go over a hard limit, and never trade away a strict theme to save money.

Present recommendations grouped, in this order, skipping empty groups:
1. **Within budget**: the picks that fit.
2. **Worth stretching for**: slightly over the target, each with the extra cost and what it buys.
3. **Best regardless of budget**: clearly better cards or upgrades at any price, kept separate so they're information, not pressure.
Keep **gameplay upgrades** (a better card) apart from **printing upgrades** (the same card, nicer). Judge on value: performance, theme fit, looks and price. Expensive doesn't mean better, and a $400 serialized printing plays exactly like the $1 one. For "no expense spared", say plainly which spend is collectibility and which is power.

Then:
- Pick the best card for the slot within the gameplay target, then the printing within the aesthetic one. Offer the cheaper printing or a cheaper card side by side when a pick runs over.
- Prices come from a source with a date (Scryfall's daily price per printing and finish via `deck_check.py`, or a vendor page). Anything else is an estimate and says so. Prices change daily.
- Check: `deck_check.py <list> --cheapest --budget <gameplay> --aesthetic-budget <extra> --per-card-max <max> [--hard-budget]` gives the cheapest total, the listed total and the premium for the chosen printings. Over a flexible target is a warning with the amount; with `--hard-budget` it fails.
- Drippy and cohesive looks: suggest printings that share a treatment or artist (`treatment`, `illustration_id`, artist in deck_check's JSON), and let them choose; it's their taste.

## Bracket targeting
- Building toward a bracket: keep its fixed limits (Game Changers, two-card combos counting the commander, mass land denial, extra turns) from the audit skill's brackets.md, checked by deck_check.py, and design the win turn to match the bracket's intent. Check Wizards' current bracket page when it may have changed.
- "What bracket is my deck?" is the audit skill's job; brew uses its result.

## Community-researched alternatives
After a build or review, proactively offer the worthwhile swaps, ordered by impact and grouped when there are many, each: add → cut, why (synergy, a weakness it fixes, theme fit), evidence (EDHREC inclusion with sample size, decklists, creator or community take), trade-off, price change if money matters. Save them as `proposed` recommendations. End with an offer, not a push: "Want a deeper comparison of any of these?" Rejected swaps stay rejected (DECISIONS.md).

## Export
Exact printings matter for art themes, looks and prices, so exports keep them:
```bash
uv run --script "${CLAUDE_SKILL_DIR}/scripts/export_deck.py" <project>/brew.json --format all --out <project>/decklists/export
```
| Format | Use | Keeps printing / finish |
|---|---|---|
| `deck.moxfield.txt` | Moxfield (and most sites): `1 Sol Ring (C21) 263 *F*`, commander first | yes / yes |
| `deck.archidekt.txt` | Archidekt: `1x Sol Ring (c21) 263 *F* [Commander]` (the tag sets the commander) | yes / yes |
| `deck.txt` | anything else, names only (Arena-style tools reject paper-only printings) | no |
| `deck.csv` | spreadsheets and CSV importers: quantity, name, set, collector_number, finish, section, scryfall_id | yes / yes |
Moxfield can't mark the commander from a paste: pick it in the New Deck dialog. Changing a deck on someone's Moxfield or Archidekt account directly needs an installed, authorized integration and the player's explicit yes; otherwise hand them the file.
