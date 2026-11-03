# Commander vault request

Use this to get your own Commander "vault": one page with full decks for several commanders, at the power levels you play, plus card rankings, cards to consider and price ladders. It works for any theme, or none.

**How to use it**
1. Copy this file into an empty folder and fill in the parts you care about. Anything you leave out uses the default shown.
2. Open Claude Code in that folder and type `/mtg:commander-vault @vault-request.md`.
3. Claude asks about anything unclear, shows you the plan and cost estimate, then builds. Expect 30 minutes or more; it resumes if you stop and run the same command again.

A minimal request is fine, for example:

> Commanders: Krenko, Mob Boss and Edgar Markov. Brackets 2 and 3. Under $150 a deck.

---

## 1. What the vault is about

**Commanders:** <!-- names, or a description like "the 6 most-built Dragon commanders on EDHREC" -->

**Theme (optional):** <!-- e.g. "Lord of the Rings", "vampires", "pirates", "Secret Lair art". Default: none (just the best decks) -->

If you set a theme, how strict should it be? <!-- pick one -->
- none: theme is only why these commanders were picked
- power: best cards, but use themed printings of them where they exist
- prefer: on theme unless an off-theme card is clearly better (you'll see why) *(default when a theme is set)*
- strict: nothing off theme (Claude checks first whether that leaves enough playable cards)

Optional theme limits: <!-- e.g. "at most 8 off-theme cards", "wider franchise is fine", "pay up to $15 extra for a themed printing" -->

## 2. Your table and your wallet

**Brackets:** <!-- e.g. "2 and 3, open on 3". Default: the bracket you play plus one above; bracket 5 only for commanders with real tournament results -->

**Budget per deck:** <!-- e.g. "$150", "no limit". Default: no limit, price always shown -->

**Price style:** <!-- budget (cheapest copies, cheaper swaps offered) | balanced (default) | bling (foil, borderless, Secret Lair) with a per-card ceiling, e.g. "nothing over $30 a copy" -->

**Hard lines:** <!-- anything you never want, even if the bracket allows it: infinite combos, extra turns, land destruction, stax. Default: what the bracket allows -->

## 3. Your cards (optional)

**Collection:** <!-- paste a list, or the path to a CSV export from Moxfield, Archidekt or ManaBox, or "none" -->

**Prefer owned cards?** <!-- yes, when close in quality | owned only where possible | ignore. Default: yes -->

**Must include / never include:** <!-- pet cards, cards you refuse to play -->

## 4. What goes on the page

Included by default:
- one tab per commander group, with a commander picker and a bracket switcher
- per deck: a short summary (the plan, how it wins, key cards, strengths, weaknesses, how to play it, and a tournament note at bracket 5), the mana curve, card types, colors needed vs. color sources, role counts, and the decklist with prices and a copy-for-Moxfield button
- one shared "cards to consider" list per tab: each card shows which decks it fits and what it would replace
- card rankings for the theme or color pair, with how many decks each number comes from
- a card viewer: click to enlarge, arrow keys or swipe to browse, flip double-faced cards
- a sources page with data dates, what was checked, and anything left unverified

Extras (say which you want; delivered as files next to the page where the page can't show them yet):
- [ ] **Alternative commanders:** others worth building for this theme, one line each on why
- [ ] **Collection planner:** for each card you own, which decks can legally play it and where it's strongest; cards that fit none of the commanders' colors are listed, not hidden
- [ ] **Split a pile between players:** e.g. "split this Secret Lair between Sam and me; Sam wants every card with Gandalf art"

**How cards are labelled:** <!-- default: neutral verdicts (Play, Good, Situational, Binder, Bracket 4+), never "weak" -->

**Anything else about the look or the writing:** <!-- e.g. "dark theme by default", "keep summaries to 3 lines" -->

## 5. What you get back

- the page (published privately to your claude.ai account if available, otherwise as files you can open in a browser)
- every deck as a `.txt` file in Moxfield format, ready to import
- research notes with sources
- a short list of anything that couldn't be verified

You don't need to ask for accuracy: every card is checked against current Scryfall data for legality, color identity and Game Changer limits; combos come from Commander Spellbook; opinions need two independent sources; and a separate reviewer re-checks the work before the page is built.
