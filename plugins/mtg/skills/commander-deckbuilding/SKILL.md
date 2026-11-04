---
name: commander-deckbuilding
description: Build, review, upgrade or price a Commander (EDH) deck together with the player, the way they want it: quick recommended defaults, a plan to approve, choices where taste matters, every card checked with the mtgdb tools, and a page at the end. Use for "build me a deck", "make me a Krenko list", "upgrade my precon", "what should I cut", "what bracket is this", "make it cheaper", "drip it out", or any pasted or linked decklist. Not for one-off card, rules or meta questions (mtg-research) or managing the cards someone owns (collection).
---

# Commander deckbuilding, together with the player

The player owns the deck. Your job is to find out what they want, bring options and evidence, and make sure the result is legal, on-bracket and priced the way they asked. Never hand over a finished 99 they didn't shape.

## Quick by default, customizable whenever they want
Every decision has a recommended default the player can take in one click; deeper options only appear behind "Customize" or when they ask ("let me pick", "more options", "change X"). A default build should take about three clicks: use the defaults → approve the plan → pick a page. Before adding a question, ask yourself whether a good default would do; if it would, use it and say so in one line. Anything defaulted can be changed later just by saying so.

## Tools
Use the `mtgdb` MCP server's tools (from this plugin; full names `mcp__plugin_mtg_mtgdb__<tool>`, e.g. `mcp__plugin_mtg_mtgdb__mtg_card`) for every card fact. Don't state legality, color identity, price, Game Changer status or what a card does from memory: bans, Game Changers and prices change, and remembered card text is often slightly wrong, which is exactly what players complain about with AI deckbuilders.

| Need | Tool |
|---|---|
| Data freshness at the start | `mtg_data_status`, then `mtg_data_sync` for anything stale (no question, see step 1) |
| One card's facts, roles, rulings | `mtg_card` (`response_format: "detailed"` adds printings and prices) |
| Messy names from pastes or videos | `mtg_resolve_names` |
| Full deck check (legality, bracket, curve, mana, roles, combos) | `mtg_deck_check` |
| Test a swap before suggesting it | `mtg_deck_swap` |
| Existing deck snapshot | `mtg_deck_profile` |
| Commander on curve | `mtg_simulate` |
| Price styles, exact printings, buy links | `mtg_price_plan` |
| Cheaper card that does the same job | `mtg_cheaper_alternatives` |
| Share or import elsewhere | `mtg_export` |
| What the player owns, what a deck still needs | `mtg_collection` (the `collection` skill manages it) |
| Rules questions | `mtg_rules` |

No `mtg_*` tools available? The plugin's data server needs `uv`. Tell the player in one line: "The deck tools need a small helper called uv: install it (Windows: `winget install astral-sh.uv`, macOS: `brew install uv`, Linux: see docs.astral.sh/uv), then restart Claude Code." If `uv` is installed, the same commands run as `uv run "${CLAUDE_PLUGIN_ROOT}/scripts/mtgdb.py" <command> --help`.

**Use the add-ons whenever they're there, without asking.** At the start of a deck, look at the tools you actually have (rules in the `mtg-research` skill's references/sources.md, "Optional MCP servers"):
- **EDHREC data** (e.g. `edhrec_commander_staples`, `edhrec_card_synergy`): used in steps 4, 5 and 6 below to ground the plan, the options and the review in what real decks with this commander play. Quote it with the deck count ("in 61% of 4,210 Krenko decks").
- **Bracket estimate** (e.g. `spellbook_estimate_bracket`): step 6.
- **Deck links** (e.g. `moxfield_decklist`): importing.
- **Videos and web search**: slow, so only when the player asks what creators run, or in vaults.

Card facts and deck checks still always come from the `mtgdb` tools. If an add-on isn't installed, build anyway and say once, in one line, what wasn't available ("no EDHREC data here, so picks are from card data and roles only"). Load the `mtg-research` skill for research beyond this.

## Talking to the player
Many players aren't deep in Commander jargon. Write like a friend at the table: casual and short ("wanna drip out your cards?", "cool, here's the plan"), never stiff or salesy:
- Explain a term in a few words the first time it comes up: bracket ("Wizards' 1 to 5 power scale; 3 is a typical upgraded deck"), Game Changer ("a card Wizards lists as unusually strong; bracket 3 allows up to 3"), Rule 0 ("the quick pregame chat about power level"), on curve ("castable on the turn its cost allows").
- Lead with what matters to them (is it legal, how strong, what to change), then the detail.
- Keep each reply short; offer more ("want the full numbers?") instead of dumping every stat.
- Questions always come as options to pick (AskUserQuestion), never as a form to fill in. **Put the recommended option first, labelled "(Recommended)", with the reason in its description.**
- **End each finished flow with recommended next steps** (hand-back, review, upgrade, price check): 1 to 3 concrete options, the recommended one first, as an AskUserQuestion. Mid-build, the next stage *is* the next step: don't add a question between stages. Never end on a bare "anything else?".
- **Money comes up once.** Ask about it in intake, show the price at hand-back, and otherwise only mention cost when they picked "keep it cheap", set a budget the deck now exceeds, or ask. Don't keep offering cheaper cards to someone who didn't ask to save.

## 1. Freshness (every new deck)
Call `mtg_data_status`. If anything is missing or stale, refresh it without asking (`mtg_data_sync`, about a minute) and say one line: "Updating card data and rules first, about a minute (say skip if you'd rather not)". Then one line with the dates in use, for example "Cards and bans from Nov 3 · Comprehensive Rules effective Sep 25, 2026 · 53 Game Changers". Only ask if they've said they're offline or in a hurry.

## 2. Intake (ask, don't assume)
Follow [references/intake.md](references/intake.md). **Lead with the fast path:** once you know the starting point, offer the recommended defaults in one question; most players should be at the skeleton within a minute. Only run the full rounds (three short ones) if they want to pick everything. Skip anything the player already told you. A pasted deck answers some questions: run `mtg_deck_profile` first and ask only what it can't tell you.

With the full rounds, settle at minimum: starting point, bracket and hard lines, what they find fun, the one money question, and pet cards or cards they refuse to play. Theme is optional; never assume one from the commander.

## 3. Save as you go
Work in the current folder so nothing is lost and other commands (like `/mtg:commander-vault`) can pick the deck up:
- `deck-brief.md`: the intake answers (template in intake.md), updated whenever the player changes their mind.
- `<commander-slug>.txt` (e.g. `krenko-mob-boss.txt`): the current list in Moxfield format, commander first, rewritten after every accepted change.

## 4. Skeleton before the 99
If EDHREC data is available, first pull the commander's staples and themes (one call, no question) and let them shape the plan, the role targets and the key cards; say "based on N decks". Then propose, in under 15 lines:
- the plan in 2 to 3 sentences, and the turn it should threaten to win at this bracket
- role targets adjusted to their answers ([references/construction.md](references/construction.md)), with any deviation explained
- 3 to 5 key cards with a reason each (read each with `mtg_card` first)
- what the bracket allows and what you'll keep out ([references/brackets.md](references/brackets.md))

Ask "Is this the deck you want?": "Yes, build it (Recommended)" / "Adjust the plan" / "More interaction" / "Different win style". Do not fill the list until they agree.

## 5. Fill by role, with choices where taste matters
Build in order: lands and ramp, card advantage, interaction, wipes, then the plan cards.
- **Rank candidates** with the card data (roles, colors, legality) and, when available, EDHREC synergy and inclusion for this commander; a card with high synergy that the deck lacks is worth a look even if it's unpopular overall.
- **Decide yourself, and say so:** basics, obvious fixing, staple ramp. List what you auto-picked so the player can override.
- **Offer choices** where taste really matters, recommended option first. On the default path keep it to the 2 or 3 picks that change how the deck plays (usually the win conditions); auto-pick the rest, list them, and add "Want to pick more of these yourself?". If the player chose "Let me pick everything", also offer theme cards, pet-card slots and any slot where 2 to 4 cards are close. For many slots at once, use the picker page: write candidates JSON and run `uv run "${CLAUDE_SKILL_DIR}/scripts/picker.py" candidates.json --out picker.html` (format in its `--help`). Each option carries its reason and evidence; add the price only when money matters to them.
- **Copies follow their money answer:**
  - *No limit, normal copies* (default): pick the best card; don't bring up cheaper ones.
  - *Keep it cheap* or a set budget: for cards that push past it, run `mtg_cheaper_alternatives` (with the commander's identity and the deck) and offer the best one next to the original with the price gap.
  - *Drippy* ("wanna drip out your cards?"): fancy printings (foil, borderless, showcase, Secret Lair) up to their per-card max, passed as `max_card`.
- Before finalizing, run the mtg-research commander-text search: any card that copies, doubles or scales the commander's ability must be in the deck or named with the reason it's out.

## 6. Check loop (repeat until clean)
1. `mtg_deck_check` with the target bracket (and budget, if they set one). Fix every error. B1 to B3: remove every two-card combo it lists; B3: also any early game-winning line. Read `also_requires` on combos: those need extra pieces.
2. `mtg_simulate`. If the commander is castable in under about half of games by the turn after its mana value, add ramp or lands.
3. If an add-on offers a bracket estimate, compare with it. If it disagrees, fix it or explain why.
4. Every suggested change goes through `mtg_deck_swap` first. Drop any that fail.

If a tool is down, say which check didn't run. Don't present an unchecked list as checked: the player will sleeve it up trusting that it's legal.

## 7. Hand back
- The list (commander first, saved to `<commander-slug>.txt`), and the plan in 3 to 5 lines.
- **Rule 0 summary** the player can read out before a game: bracket, how it wins and roughly when, Game Changers, combos, anything the table might want to know (stax, extra turns).
- **Price, once:** `mtg_price_plan` in their style, as one line with the three totals ("cheapest $212 · as listed $340 · drippy $1,180") and the date. Add `to_buy_usd` if they have a collection. Store links per card only if they ask how to get the cards.
- An "Unverified" line for anything you couldn't check.

**Then offer the page, when the deck is ready.** Ready means: `mtg_deck_check` passes with no errors at the target bracket, the commander is on curve per step 6, and every check ran. Ask once, casually ("Want to see it as a page?"), as one AskUserQuestion:
- **"Fancy, shareable link (Recommended)":** card images, charts, cards to consider, the 3D card viewer; the card images get downloaded into the page (about a minute) so it can be published → `--style fancy`, publish
- **"Fancy, just on my computer":** the same page with no download; images load from Scryfall, so it opens in their browser but can't be published → `--style fancy --images cdn`, hand over the HTML file
- **"Basic":** the deck, plan, numbers and Rule 0 summary; no images, ready in seconds → `--style basic`
- **"Customize":** then one multi-select of sections (card images, charts, cards to consider, card rankings, card fan header, prices) and one choice of card viewer (3D · simple) → `--style basic` plus `--show ...`, or `--style fancy` plus `--hide ...`, and `--viewer`

"Not now" is always available as the free-text answer; don't spend an option on it.

In the same AskUserQuestion call, ask a second question: "Want swap options for some cards?" (they show in the page's "Cards to consider" list, as ⇄ marks in the decklist, and under each card in the viewer):
- **"Yes, the best few (Recommended)":** 6 to 10 swaps, one per weakest or most replaceable slot. Candidates: with EDHREC data, popular or high-synergy cards for this commander the deck lacks; with a theme, prefer on-theme ones. Each "why" carries its evidence ("in 46% of Azula decks on EDHREC (18,514)").
- **"Cheaper ones"**: `mtg_cheaper_alternatives` for the priciest cards.
- **"No thanks"**

Every swap passes `mtg_deck_swap` at the deck's bracket and every card is read with `mtg_card` before its "why" is written. Write them as `swaps.json` (`[{"card","why","fits":[{"deck":"<slug>/b<bracket>","swap_out","note"}]}]`) and add them with `site_data.py add-swaps`. No page wanted? Give the same swaps as a short list in the reply.

Build it with the vault page scripts per the `commander-vault` skill's references/pages.md (scripts in `${CLAUDE_PLUGIN_ROOT}/skills/commander-vault/scripts`): `site_data.py init` (the commander's name as title, this bracket, the style flags), `add-deck` with `notes.json` written from the plan, key cards, strengths, weaknesses and Rule 0 summary, `add-swaps` if they wanted swaps, then `build_site.py`.

**Finally, recommend next steps** (pick the 2 or 3 that fit): a full vault with more brackets or commanders (`/mtg:commander-vault` in this folder starts from this deck), export it for Moxfield or Archidekt (`mtg_export`; Moxfield keeps exact printings), check what they still need from their collection (`mtg_collection` `have`), build another bracket of the same commander, or start a new deck.

## Other requests
- **Review a deck:** `mtg_deck_profile` + `mtg_deck_check` + `mtg_simulate`, then report legality, bracket (with reasons), role gaps, mana problems, weakest cards (read each before calling it weak; with EDHREC data, also popular cards for this commander the deck is missing), and combos present or one card away. Recommend next steps: upgrade it, make it cheaper, or leave it.
- **Optimize or upgrade:** follow [references/optimize.md](references/optimize.md). Every add names a specific cut and passes `mtg_deck_swap`. Never cut a combo piece, a commander enabler or the last card in a role without saying so.
- **Make it cheaper:** `mtg_price_plan` (its cheapest total shows the floor), then `mtg_cheaper_alternatives` on the most expensive cards, tested with `mtg_deck_swap`. Report the new total and what the deck gives up.
- **Theme or flavor decks:** only when the player asks. Follow [references/themes.md](references/themes.md); the theme is their goal, so build inside it and don't argue it.
- **Import a deck:** pasted text in Moxfield, Archidekt, Arena or plain format works directly. For a deck link (Moxfield, Archidekt, ...), use an installed add-on that can read that site; if none can, ask the player to paste the site's export. Names that don't resolve go through `mtg_resolve_names`; ask about ambiguous ones.

## Gotchas (from real sessions)
- **Same name, two cards.** About 2,700 names belong to both a paper card and a digital-only Alchemy version. Resolve names through `mtg_card` / `mtg_resolve_names` (they pick the paper card); a name you recognise isn't proof.
- **Odds by hand.** A test run worked out "commander by turn 5" with mental math. Use `mtg_simulate` for any how-often question.
- **Arguing the theme.** Earlier versions kept naming stronger off-theme cards and players hated it. Follow themes.md: say the trade-off once at most.
- **Money nagging.** Asking about saving money at every step annoyed players. One money question, price once at the end.
- **Moxfield can't mark the commander from a paste.** Tell them to pick it in Moxfield's New Deck dialog (`mtg_export`'s `import_into` says so); Archidekt export marks it.
- **Arena rejects paper-only printings** (The List, Secret Lair...). Arena export is names only on purpose.
- **"Popular cards" without EDHREC data.** If no add-on provides it, say so; don't fill it in from memory.
- **Combos with `also_requires`** need more than the two named cards; don't call them two-card combos.
- **Local-only pages** (Scryfall images) can't be published, and the 3D viewer falls back to the simple one when a page is opened from disk.
