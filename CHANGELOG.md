# Changelog

Players get a new version with `/plugin marketplace update carlomos7-mtg-skills` and a restart.

## 5.1.0
- **Fast path:** one click to use the recommended setup and skip the questions; the upgrade flow has it too.
- **Collection:** import from Moxfield, Archidekt or ManaBox, add and remove cards, undo, value, search, what a deck still needs, what fits a commander, export (`/mtg:collection`).
- **Money is asked once:** no limit (default), keep it cheap, a set budget, or drippy (fancy printings up to a per-card max). "Bling" is now "drippy".
- **Recommended next steps** at every stage, with the recommended option marked.
- **Decks are saved as you build** (`deck-brief.md` and `<commander>.txt`), and `/mtg:commander-vault` with nothing after it builds a vault from that deck.
- **Page offer:** once a deck passes every check, Claude offers to show it as a commander vault page.
- Optional add-ons are found by what they do; deck links work with any add-on that reads that site.
- Fixes from two independent reviews (foil marks on export, Arena and Archidekt pastes, Windows certificate and file-lock issues, and more).

## 5.0.0
- First public version: MCP server with card data, deck checks, prices, combos and rules; collaborative deckbuilding skills; short `/mtg:*` commands; multi-commander vaults.
