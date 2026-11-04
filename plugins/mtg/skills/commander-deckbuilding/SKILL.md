---
name: commander-deckbuilding
description: Build, review, upgrade or price a Commander (EDH) deck together with the player, the way they want it: quick recommended defaults, a plan to approve, choices where taste matters, every card checked, and a page at the end. Use for "build me a deck", "make me a Krenko list", "upgrade my precon", "what should I cut", "what bracket is this", "make it cheaper", "drip it out", or any pasted or linked decklist. Not for one-off card, rules or meta questions (mtg-research) or managing the cards someone owns (collection).
---

# Commander deckbuilding, together with the player

The player owns the deck. Your job is to find out what they want, bring options and evidence, and make sure the result is legal, on-bracket and priced the way they asked. Never hand over a finished 99 they didn't shape.

## Quick by default, customizable whenever they want
Every decision has a recommended default the player can take in one click; deeper options only appear behind "Customize" or when they ask ("let me pick", "more options", "change X"). A default build should take about three clicks: use the defaults → approve the plan → pick a page. Before adding a question, ask yourself whether a good default would do; if it would, use it and say so in one line. Anything defaulted can be changed later just by saying so.

## Tools
Don't state legality, color identity, price, Game Changer status or what a card does from memory: bans, Game Changers and prices change, and remembered card text is often slightly wrong, which is exactly what players complain about with AI deckbuilders.

**Use the add-ons whenever they're there, without asking.** At the start of a deck, look at the tools you actually have (rules in the `mtg-research` skill's references/sources.md, "Optional MCP servers"):
- **EDHREC data** (e.g. `edhrec_card_synergy`): card-to-card synergy. Used in steps 3, 4 and 5 to ground the plan, the options and the review in what real decks play. Quote it with the deck count ("in 61% of 4,210 Krenko decks").
- **A second MTG server** (e.g. `mtg-commander` next to `mtg-mcp`): cross-check decklists and EDHREC numbers; note disagreements.
- **Bracket estimate** (e.g. `spellbook_estimate_bracket`): step 5.
- **Deck links and search** (e.g. `moxfield_decklist`, `moxfield_search_decks`): importing, and more real decklists.
- **Web search and videos** (e.g. `parallel-search`, `youtube-transcript`, or the built-in WebSearch/WebFetch): the research pass, step 3. Runs on every new deck, not only when asked.

If an add-on isn't installed, build anyway and say once, in one line, what wasn't available ("no EDHREC data here, so picks are from card data and roles only"). Load the `mtg-research` skill for research beyond this.

## Talking to the player
Many players aren't deep in Commander jargon. Write like a friend at the table: casual and short ("wanna drip out your cards?", "cool, here's the plan"), never stiff or salesy:
- Explain a term in a few words the first time it comes up: bracket ("Wizards' 1 to 5 power scale; 3 is a typical upgraded deck"), Game Changer ("a card Wizards lists as unusually strong; bracket 3 allows up to 3"), Rule 0 ("the quick pregame chat about power level"), on curve ("castable on the turn its cost allows").
- Lead with what matters to them (is it legal, how strong, what to change), then the detail.
- Keep each reply short; offer more ("want the full numbers?") instead of dumping every stat.
- Questions always come as options to pick (AskUserQuestion), never as a form to fill in. **Put the recommended option first, labelled "(Recommended)", with the reason in its description.**
- **End each finished flow with recommended next steps** (hand-back, review, upgrade, price check): 1 to 3 concrete options, the recommended one first, as an AskUserQuestion. Mid-build, the next stage *is* the next step: don't add a question between stages. Never end on a bare "anything else?".
- **Money comes up once.** Ask about it in intake, show the price at hand-back, and otherwise only mention cost when they picked "keep it cheap", set a budget the deck now exceeds, or ask. Don't keep offering cheaper cards to someone who didn't ask to save.

## 1. Intake (ask, don't assume)
Follow [references/intake.md](references/intake.md). **Lead with the fast path:** once you know the starting point, offer the recommended defaults in one question; most players should be at the skeleton within a minute. Only run the full rounds (three short ones) if they want to pick everything. Skip anything the player already told you. A pasted deck answers some questions: read the deck first and ask only what it can't tell you.

With the full rounds, settle at minimum: starting point, bracket and hard lines, what they find fun, the one money question, and pet cards or cards they refuse to play. Theme is optional; never assume one from the commander.

## 2. Save as you go
Work in the current folder so nothing is lost and other commands (like `/mtg:commander-vault`) can pick the deck up:
- `deck-brief.md`: the intake answers (template in intake.md), updated whenever the player changes their mind.
- `<commander-slug>.txt` (e.g. `krenko-mob-boss.txt`): the current list in Moxfield format, commander first, rewritten after every accepted change.

## 3. Research pass, then the skeleton
**Research before proposing anything; this is what makes the deck good.** No question needed; tell the player in one line ("Researching <commander>: EDHREC, real decklists, combos, videos and Reddit, a few minutes").
- **Start it as soon as the commander, bracket and theme are known** (right after the fast-path answer, or after round 1): dispatch the `vault-researcher` agent in the background with the brief "research pass for <commander>, bracket <N>, theme <theme or none>, deck folder <path>, follow mtg-research references/research-pass.md". No agents available? Run the pass yourself.
- Pick tools by research-pass.md's "Best tool first, then fall back" table: installed add-ons first (best results), then built-in web search, never memory.
- Cover every source type: EDHREC, real decklists (plus Moxfield through an add-on), combos, 3+ creator videos, 4+ Reddit threads or primers, 3+ articles, a live price check, and the current Wizards bracket page (plus cEDH results at bracket 4 and 5).
- Every source goes into `research/claims.jsonl` (kind, url, date, locator, what it was used for). Say any shortfall in one line ("no Command Zone video on her yet").
- A combo the community mentions is a bracket check: don't suggest swaps that complete one.
- Takes that disagree, with each other or with the player's theme, are shown on the page, not acted on unless the player wants to.

Outputs feed everything after: `research/takes.json` → `community` in notes.json; videos → `youtube`; tested swaps → `swaps.json`; the ledger → the page's Sources tab, grouped by source type.

Then use what the research found (EDHREC numbers, what most real lists play, creator traps) to propose, in under 15 lines, with "based on N decks and M lists":
- the plan in 2 to 3 sentences, and the turn it should threaten to win at this bracket
- role targets adjusted to their answers ([references/construction.md](references/construction.md)), with any deviation explained
- 3 to 5 key cards with a reason each (read each card first)
- what the bracket allows and what you'll keep out ([references/brackets.md](references/brackets.md))

Ask "Is this the deck you want?": "Yes, build it (Recommended)" / "Adjust the plan" / "More interaction" / "Different win style". Do not fill the list until they agree.

## 4. Fill by role, with choices where taste matters
Build in order: lands and ramp, card advantage, interaction, wipes, then the plan cards.
- **Rank candidates** with the card data (roles, colors, legality) and, when available, EDHREC synergy and inclusion for this commander; a card with high synergy that the deck lacks is worth a look even if it's unpopular overall.
- **Decide yourself, and say so:** basics, obvious fixing, staple ramp. List what you auto-picked so the player can override.
- **Offer choices** where taste really matters, recommended option first. On the default path keep it to the 2 or 3 picks that change how the deck plays (usually the win conditions); auto-pick the rest, list them, and add "Want to pick more of these yourself?". If the player chose "Let me pick everything", also offer theme cards, pet-card slots and any slot where 2 to 4 cards are close. For many slots at once, use the picker page: write candidates JSON and run `python3 "${CLAUDE_SKILL_DIR}/scripts/picker.py" candidates.json --out picker.html` (format in its `--help`). Each option carries its reason and evidence; add the price only when money matters to them.
- **Copies follow their money answer:**
  - *No limit, normal copies* (default): pick the best card; don't bring up cheaper ones.
  - *Keep it cheap* or a set budget: for cards that push past it, find a cheaper card that does the same job and offer the best one next to the original with the price gap.
  - *Drippy* ("wanna drip out your cards?"): fancy printings (foil, borderless, showcase, Secret Lair) up to their per-card max, passed as `max_card`.
- Before finalizing, run the mtg-research commander-text search: any card that copies, doubles or scales the commander's ability must be in the deck or named with the reason it's out.

## 5. Check loop (repeat until clean)
1. Check the deck at the target bracket (and budget, if they set one) for legality, Game Changers, curve, mana, roles and combos. Fix every error. B1 to B3: remove every two-card combo; B3: also any early game-winning line. Combos that need extra pieces aren't two-card combos.
2. If the commander is castable in under about half of games by the turn after its mana value, add ramp or lands.
3. If an add-on offers a bracket estimate, run it on the final 100 (not a draft) and compare. Treat it as a second opinion: it has missed Game Changers and combos the local data finds. If it disagrees, fix it or explain why, and record it in `checks` with the card count it saw.
4. Check every suggested change for legality, bracket and combos before suggesting it. Drop any that fail.

If a tool is down, say which check didn't run. Don't present an unchecked list as checked: the player will sleeve it up trusting that it's legal.

## 6. Hand back
- The list (commander first, saved to `<commander-slug>.txt`), and the plan in 3 to 5 lines.
- **Rule 0 summary** the player can read out before a game: bracket, how it wins and roughly when, Game Changers, combos, anything the table might want to know (stax, extra turns).
- **Price, once:** in their style, as one line with the three totals ("cheapest $212 · as listed $340 · drippy $1,180") and the date. Add the cost to buy if they have a collection. Store links per card only if they ask how to get the cards.
- An "Unverified" line for anything you couldn't check.

**Then offer the page, when the deck is ready.** Ready means: the deck passes every check with no errors at the target bracket, the commander is on curve per step 5, and every check ran. Ask once, casually ("Want to see it as a page?"), as one AskUserQuestion:
- **"Fancy, shareable link (Recommended)":** card images, charts, cards to consider, the 3D card viewer; the card images get downloaded into the page (about a minute) so it can be published → `--style fancy`, publish
- **"Fancy, just on my computer":** the same page with no download; images load from Scryfall, so it opens in their browser but can't be published → `--style fancy --images cdn`, hand over the HTML file
- **"Basic":** the deck, plan, numbers and Rule 0 summary; no images, ready in seconds → `--style basic`
- **"Customize":** then one multi-select of sections (card images, charts, cards to consider, card rankings, card fan header, prices) and one choice of card viewer (3D · simple) → `--style basic` plus `--show ...`, or `--style fancy` plus `--hide ...`, and `--viewer`

"Not now" is always available as the free-text answer; don't spend an option on it.

In the same AskUserQuestion call, ask a second question: "Want swap options for some cards?" (they show in the page's "Cards to consider" list, as ⇄ marks in the decklist, and under each card in the viewer):
- **"Yes, the best few (Recommended)":** 6 to 10 swaps, one per weakest or most replaceable slot. Candidates: with EDHREC data, popular or high-synergy cards for this commander the deck lacks; with a theme, prefer on-theme ones. Each "why" carries its evidence ("in 46% of Azula decks on EDHREC (18,514)").
- **"Cheaper ones"**: a cheaper card that does the same job, for the priciest cards.
- **"No thanks"**

Every swap is checked at the deck's bracket and every card is read before its "why" is written. Write them as `swaps.json` (`[{"card","why","fits":[{"deck":"<slug>/b<bracket>","swap_out","note"}]}]`) and add them with `site_data.py add-swaps`. No page wanted? Give the same swaps as a short list in the reply.

Build it with the vault page scripts per the `commander-vault` skill's references/pages.md (scripts in `${CLAUDE_PLUGIN_ROOT}/skills/commander-vault/scripts`): `site_data.py init` (the commander's name as title, this bracket, the style flags), `add-deck` with `notes.json` written from the plan, key cards, strengths, weaknesses, Rule 0 summary and the community research, `add-swaps` if they wanted swaps, `add-claims --ledger research/claims.jsonl` for the sources, then `build_site.py`. The page shows the community takes with links, the videos, and every source.

**Finally, recommend next steps** (pick the 2 or 3 that fit): a full vault with more brackets or commanders (`/mtg:commander-vault` in this folder starts from this deck), export it for Moxfield or Archidekt (Moxfield keeps exact printings), check what they still need from their collection, build another bracket of the same commander, or start a new deck.

## Other requests
- **Review a deck:** check it, then report legality, bracket (with reasons), role gaps, mana problems, weakest cards (read each before calling it weak; with EDHREC data, also popular cards for this commander the deck is missing), and combos present or one card away. Recommend next steps: upgrade it, make it cheaper, or leave it.
- **Optimize or upgrade:** follow [references/optimize.md](references/optimize.md). Every add names a specific cut and is checked for legality, bracket and combos. Never cut a combo piece, a commander enabler or the last card in a role without saying so.
- **Make it cheaper:** price the deck (its cheapest total shows the floor), then find cheaper alternatives for the most expensive cards, checking each swap. Report the new total and what the deck gives up.
- **Theme or flavor decks:** only when the player asks. Follow [references/themes.md](references/themes.md); the theme is their goal, so build inside it and don't argue it.
- **Import a deck:** pasted text in Moxfield, Archidekt, Arena or plain format works directly. For a deck link (Moxfield, Archidekt, ...), use an installed add-on that can read that site; if none can, ask the player to paste the site's export. Ask about names that don't resolve or are ambiguous.

## Gotchas (from real sessions)
- **Same name, two cards.** About 2,700 names belong to both a paper card and a digital-only Alchemy version. Make sure you have the paper card; a name you recognise isn't proof.
- **Arguing the theme.** Earlier versions kept naming stronger off-theme cards and players hated it. Follow themes.md: say the trade-off once at most.
- **Money nagging.** Asking about saving money at every step annoyed players. One money question, price once at the end.
- **Moxfield can't mark the commander from a paste.** Tell them to pick it in Moxfield's New Deck dialog; Archidekt export marks it.
- **Arena rejects paper-only printings** (The List, Secret Lair...). Arena export is names only on purpose.
- **"Popular cards" without EDHREC data.** If no add-on provides it, say so; don't fill it in from memory.
- **Combos that need extra pieces** need more than the two named cards; don't call them two-card combos.
- **Local-only pages** (Scryfall images) can't be published, and the 3D viewer falls back to the simple one when a page is opened from disk.
