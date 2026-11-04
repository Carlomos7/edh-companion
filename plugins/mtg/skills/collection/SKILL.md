---
name: collection
description: Manage the player's own Magic card collection: import it from Moxfield, Archidekt or ManaBox, add opened packs or trades, remove cards, undo, see what it's worth, find cards they own, check what a deck still needs, find what fits a commander, and export it. Use for "import my collection", "I opened these", "I traded away...", "what's my collection worth", "do I own X", "what do I still need for this deck", "what can I build with my cards". Not for building or changing the deck itself (commander-deckbuilding uses the collection automatically).
argument-hint: "[what you want to do, or paste cards]"
---

# Card collection

The collection lives on the player's computer (`~/.cache/mtg/collection.json`) and the deckbuilding skill uses it automatically to prefer owned cards and show "cost to buy". Use the `mtgdb` MCP server's tools (full names `mcp__plugin_mtg_mtgdb__<tool>`):
- `mtg_collection` (read only): `show`, `find`, `have`, `fits`, `export`
- `mtg_collection_edit`: `import`, `add`, `remove`, `restore`

Request: $ARGUMENTS

## Getting the collection in
Ask where they track cards, then tell them exactly how to export (one line):
- **Moxfield:** Collection → Export → CSV
- **Archidekt:** Collection → Export → CSV
- **ManaBox:** Collection → share or export as CSV
- **Nothing yet:** paste a list (`2 Sol Ring`, one card per line; set codes and `*F*` for foil are optional)

They can paste the CSV text or give the file path. `import` **replaces** the collection: if one already exists (`mtg_collection` `show` succeeds), ask first whether to replace it or merge (`merge: true`).

## Keeping it up to date
- Opened packs, trades in, a new precon: `add` with the list.
- Traded, sold, or a card moved to a friend: `remove`. If they had fewer copies than they asked to remove, say so.
- Every change makes a backup first; `restore` undoes the last change. Mention this after any big import.
- Unrecognised names come back in `unresolved` with suggestions: ask which card they meant, then `add` it. Never guess.

## Answering questions
- **What's it worth?** `show`: total, most valuable cards, prices date. Owned printings and foils are priced as such; cards without a known printing at the cheapest copy, so say it's an estimate.
- **Do I own X?** `show` with `card`, or `find` with `query`.
- **Find by colors, type or role:** `find` (e.g. identity "Gruul", role "ramp").
- **What do I need for this deck?** `have` with the decklist: owned cards, what's missing, and the cheapest cost to buy the rest. Basic lands are assumed owned.
- **What fits this commander?** `fits` with the commander (both, for partners). It lists legal, on-color cards they own, most popular first; read a card before recommending it for the deck.
- **What could I build?** Ask which commanders they're considering (or offer to suggest some with `mtg-research`), run `fits` for each and compare counts, roles and value.
- **Export:** `export` as a Moxfield list or CSV (keeps printings and foil marks) for Moxfield/Archidekt collection import or a spreadsheet.

## Splitting a pile between players
For "split this box/Secret Lair between Sam and me": add nothing to the collection; take the pasted pile, ask each player's commanders and wishes ("Sam wants every Gandalf card"), check color identity per commander with `mtg_card`, and propose a split as a table (card → who → why). Cards that fit nobody's colors are listed as "trade or binder", not hidden. Only change the collection if they ask.

## Gotchas
- **Replacing by accident.** `import` replaces the whole collection; confirm first when one exists. An import that finds no cards is refused, and every change keeps one backup (`restore`).
- **Site CSVs differ** (quantity, set, foil columns). The tool reads Moxfield, Archidekt and ManaBox exports; don't hand-edit `collection.json`.
- **Junk quantities** like `x` are reported, not guessed: ask the player.
- **Basic lands** are assumed owned in `have`, so "need" lists aren't padded with 30 Mountains.
