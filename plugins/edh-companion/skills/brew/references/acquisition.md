# Getting the cards

Acquisition help is on demand: before a build ("what's the cheapest way into Spider-Man?"), during it ("is this printing still in print?"), after it ("how do I get all this?"), or on its own ("which precon has the most of these?"). After a finished deck, offer it in one line; never make it a required step. Buying itself is out of scope: give the plan and links, the player buys.

## What to find out (only what's missing)
- What they already own: a collection export (ManaBox, Moxfield, Deckbox, Archidekt CSV, or a pasted list) through `collection.py FILE --out <workspace>/collection.json`. Report its `unmatched` rows; never guess them. Don't ask if they haven't mentioned owning cards; say the plan assumes they own nothing.
- Card states against the collection: **owned** (that card, the listed printing or any when none is listed), **owned in another printing** (playable now; the chosen art still costs money) and **missing**. Lead with "Missing N cards"; owned cards cost $0 and come first.
- Their money rules from PROJECT.md (gameplay vs aesthetic budget, per-card max) and the platform/region if prices differ (USD default; Cardmarket EUR for Europe).

## Research (the research skill's sources and rules apply)
- **Products that cover many cards:** precons, Secret Lair drops, bundles, starter kits. Check what's actually in them: Scryfall `e:<set>` searches against the deck's card names (`(!"Sol Ring" or !"Arcane Signet") e:cmm`), or the official decklist page. Count how many of the needed cards each product covers and what it costs per needed card.
- **Singles:** the cheapest acceptable printing per card (`deck_check.py --cheapest`) and the chosen aesthetic printing, with vendor prices where available (Scryfall's TCGplayer/Cardmarket/Card Kingdom prices, or a price tool). Every price has a source and date; anything else is labelled an estimate.
- **Availability:** in print or not, recent or announced reprints that may drop the price, Secret Lairs sold out (secondary market only), cards on the Reserved List (never reprinted). Cite the source for each claim.

## Upgrade paths
For an existing deck with a budget ("what should I buy next with $50?"): `upgrade_path.py <project> --budget 50` (`skills/brew/scripts/`). It orders one-for-one swaps by value per dollar (role floors filled plus lift gained, over the cheapest printing's price), puts **swaps you can make today ($0, owned)** first, recomputes after every step and keeps the budget as a running total ("13 swaps, about $44, prices as of <date>"). Each step says why and what the cut costs the deck. Check every cut yourself before proposing it (a card with no numbers is the script's guess), group swaps that only work together, then propose them as recommendations per optimize.md.

## The plan (ranked, best path first)
1. **Best path in one line** ("Buy the X precon ($45, covers 31 cards), then ~$60 of singles").
2. **Buy first:** the commander and the cards the plan can't work without; then upgrades by impact.
3. **Products vs singles:** each product worth it, with how many needed cards it covers and the leftover value; when singles are cheaper, say so.
4. **Printing choices** within the aesthetic budget, separately from gameplay cost.
5. **Watch or wait:** cards likely to get cheaper (announced reprints), very volatile prices.
6. **Totals:** gameplay cost, aesthetic premium, total; owned cards excluded; date of the prices.
Proxies only if the player brings them up, and only for a playgroup that agrees (Rule 0).

## Saving
If there's a project and they want it kept, write the plan to `ACQUISITION.md` in the project (prices dated) and note it in STATE.md. Prices go stale: re-check before relying on an old plan.

## Integrating into building
When budget or artwork matters, acquisition shapes picks during the build: prefer cards in a product they're buying anyway, flag cards that are expensive only because they're out of print, and show the cheaper-printing option next to an expensive themed one. Without money or art constraints, don't bring it up until hand-back.
