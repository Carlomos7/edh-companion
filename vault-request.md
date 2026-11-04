# Commander vault request (full version)

A vault is one page with full decks for several commanders, at the power levels you play, plus card rankings, cards to consider and price ladders. It works for any theme, or none.

**How to use it**
1. Copy the block below (the copy button is in its top-right corner on GitHub).
2. Replace the text after each colon with your answer. Anything in parentheses is a hint. Delete any line you don't care about: its default is used.
3. In Claude Code, type `/mtg:commander-vault`, a space, then paste your filled-in block and press Enter.

Claude asks about anything unclear, shows you the plan and cost estimate, then builds. Expect 30 minutes or more. If you stop, run the same thing again in the same folder and it resumes.

The short version in the [README](README.md#build-your-own-vault) covers most people. This one has every option.

```text
WHAT IT'S ABOUT
Commanders: (names, or a description like "the 6 most-built Dragon commanders on EDHREC")
Theme: none (or a franchise, set, tribe or art style, e.g. "Lord of the Rings", "vampires", "Secret Lair art")
Theme strictness: prefer (none = theme only picks the commanders | power = best cards, themed printings where they exist | prefer = on theme unless an off-theme card is clearly better | strict = nothing off theme)
Theme limits: (optional, e.g. "at most 8 off-theme cards", "wider franchise is fine", "pay up to $15 extra for a themed printing")

YOUR TABLE AND WALLET
Brackets: (e.g. "2 and 3, open on 3"; default: the bracket you play plus one above; bracket 5 only for commanders with real tournament results)
Budget per deck: no limit (or e.g. "$150"; the price is always shown)
Copies: normal (or "cheapest" = cheapest copies and cheaper swaps where it matters | "drippy" = foil, borderless, Secret Lair, with a per-card max like "nothing over $30 a copy")
Hard lines: (anything you never want, even if the bracket allows it: infinite combos, extra turns, land destruction, stax)

YOUR CARDS
Collection: none (or paste a list here, or give the path to a CSV export from Moxfield, Archidekt or ManaBox)
Prefer owned cards: yes, when close in quality (or "owned only where possible", or "ignore")
Must include: (pet cards)
Never include: (cards or effects you refuse to play)

WHAT GOES ON THE PAGE
Extras: (any of: alternative commanders | collection planner | split a pile between players, e.g. "split this Secret Lair between Sam and me; Sam wants every Gandalf card")
Card labels: neutral (Play, Good, Situational, Binder, Bracket 4+; never "weak")
Look and writing: (optional, e.g. "dark theme by default", "keep summaries to 3 lines")
```

## What's always on the page
- one tab per commander group, with a commander picker and a bracket switcher
- per deck: a short summary (the plan, how it wins, key cards, strengths, weaknesses, how to play it, a tournament note at bracket 5), the mana curve, card types, colors needed vs. color sources, role counts, and the decklist with prices and a copy-for-Moxfield button
- one shared "cards to consider" list per tab: each card shows which decks it fits and what it would replace
- card rankings for the theme or colors, with how many decks each number comes from
- a card viewer: click to enlarge, arrow keys or swipe to browse, flip double-faced cards
- a sources page with data dates, what was checked, and anything left unverified

The extras arrive as files next to the page when the page can't show them yet.

## What you get back
- the page (published privately to your claude.ai account if you're signed in, otherwise as files you open in a browser)
- every deck as a `.txt` file in Moxfield format, ready to import
- research notes with sources
- a short list of anything that couldn't be verified

You don't need to ask for accuracy: every card is checked against current Scryfall data for legality, color identity and Game Changer limits; combos come from Commander Spellbook; opinions need two independent sources; and a separate reviewer re-checks the work before the page is built.
