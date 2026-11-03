# Rules sources and collaborative deckbuilding research

All sources accessed 2026-11-03 unless stated. Items marked **UNCONFIRMED** could not be verified against a primary source.

## Summary

- The current Comprehensive Rules are effective September 25, 2026. Wizards links them from one stable page, and the file URL contains a date, so a new version shows up as a new link on that page.
- Wizards has run Commander since September 30, 2024. The Commander Format Panel advises, and Wizards makes the final call.
- The last change to Commander bans, Brackets, or Game Changers was February 9, 2026. The Game Changers list has 53 cards. Brackets are still labeled beta.
- Scryfall card objects carry `legalities.commander` and a `game_changer` boolean. Scryfall is the practical machine-readable source. Wizards publishes no API or feed for any of this.
- The next general Banned and Restricted announcement is scheduled for November 30, 2026. Commander keeps its own schedule and may not change on that date.
- Players mostly complain that AI deckbuilders invent cards, break deck rules (count, singleton, color identity, bans), give generic staple lists, and are confidently wrong about rules.

---

## Part A: "Latest rules" sources

### A1. Comprehensive Rules (CR)

**Where it lives.** The stable landing page is https://magic.wizards.com/en/rules. It links DOCX, PDF and TXT files ([source](https://magic.wizards.com/en/rules)).

**Current version.** The current version is effective September 25, 2026 ([TXT](https://media.wizards.com/2026/downloads/MagicCompRules%2020260925.txt), [PDF](https://media.wizards.com/2026/downloads/MagicCompRules%2020260925.pdf)).

**URL pattern.** The pattern is `https://media.wizards.com/{YYYY}/downloads/MagicCompRules%20{YYYYMMDD}.{txt|pdf|docx}`. Two cautions:
- The date in the file name is not always the effective date. `MagicCompRules%2020260819.txt` says "effective as of August 7, 2026" ([source](https://media.wizards.com/2026/downloads/MagicCompRules%2020260819.txt)). Do not build the URL from a guessed date. Scrape the link from the rules page instead.
- The first line of the TXT states the effective date ("These rules are effective as of September 25, 2026."). Parse this line to get the version.

**How often it changes.** In 2026 so far there were versions effective January 16, February 27, April 17, June 19, August 7 and September 25. That is roughly one per set release, about every 6 to 8 weeks ([Jan](https://media.wizards.com/2026/downloads/MagicCompRules%2020260116.pdf), [Feb](https://media.wizards.com/2026/downloads/MagicCompRules%2020260227.pdf), [Apr](https://media.wizards.com/2026/downloads/MagicCompRules%2020260417.pdf), [Jun](https://media.wizards.com/2026/downloads/MagicCompRules%2020260619.pdf), [Aug](https://media.wizards.com/2026/downloads/MagicCompRules%2020260807.pdf), [Sep](https://media.wizards.com/2026/downloads/MagicCompRules%2020260925.pdf)).

**How to detect a new version.**
1. Fetch https://magic.wizards.com/en/rules.
2. Regex the TXT link: `MagicCompRules%20(\d{8})\.txt`.
3. If the link differs from the cached one, download the file and read its first line for the effective date.
4. Note: the TXT has historically been served with Windows-1252 or BOM quirks. Normalize the encoding before parsing. **UNCONFIRMED** for 2026 files.

**Commander rules inside the CR.** Rule 903 covers the Commander variant (rule 903.4 is color identity). I cross-checked 903.4 with the MTG connector's `rules_lookup`, and the text matches the published CR. Brackets and Game Changers are not in the CR ([Mana Grove, citing CR 903](https://themanagrove.com/articles/commander-game-changers)). Treat them as a separate data source.

**Mirror.** The judges' blog keeps an HTML copy that is easier to read, currently labeled "Effective September 25, 2026" ([source](https://blogs.magicjudges.org/rules/comprehensive-rules/)). It is useful for deep links to individual rules but is not authoritative.

### A2. Commander governance, banned list, Brackets, Game Changers

**Who governs.** On September 30, 2024 the Commander Rules Committee handed management of the format to Wizards' game design team ([Wizards](https://magic.wizards.com/en/news/announcements/on-the-future-of-commander)). On October 22, 2024 Wizards created the Commander Format Panel, a paid advisory group led by Gavin Verhey. Its members include three of the five former RC members. "Wizards makes the final calls" ([Wizards](https://magic.wizards.com/en/news/announcements/introducing-the-commander-format-panel), [MTG Wiki](https://mtg.wiki/page/Commander_Format_Panel)). The panel rotates some members each October to December ([MTG Wiki](https://mtg.wiki/page/Commander_Format_Panel)).

**mtgcommander.net.** The old site is frozen. Its last post is the "September 2024 Quarterly Update" ([source](https://mtgcommander.net/index.php/faq/)). Do not use it as a rules source. Its Rule Zero and social-contract FAQ is still useful context for intake.

**Official pages to poll.**

| What | URL | Notes |
| --- | --- | --- |
| Commander format page (rules summary, Brackets, Game Changers) | https://magic.wizards.com/en/formats/commander | Game Changers are rendered by color tabs. A text fetch got the intro but not the full card list ([source](https://magic.wizards.com/en/formats/commander)). |
| Banned & Restricted (all formats) | https://magic.wizards.com/en/banned-restricted-list | Has a "Commander Banned Cards" section ([source](https://magic.wizards.com/en/banned-restricted-list)). |
| Announcements index | https://magic.wizards.com/en/news/announcements | B&R and Brackets updates are posted here. |

**Current Commander banned list.** These are the named cards from the official page as of the fetch:

Ancestral Recall, Balance, Black Lotus, Chaos Orb, Channel, Dockside Extortionist, Emrakul the Aeons Torn, Erayo Soratami Ascendant, Falling Star, Fastbond, Flash, Golos Tireless Pilgrim, Griselbrand, Hullbreacher, Iona Shield of Emeria, Karakas, Jeweled Lotus, Leovold Emissary of Trest, Library of Alexandria, Limited Resources, Mana Crypt, the five Moxen, Nadu Winged Wisdom, Paradox Engine, Primeval Titan, Prophet of Kruphix, Recurring Nightmare, Rofellos Llanowar Emissary, Shahrazad, Sundering Titan, Sylvan Primordial, Time Vault, Time Walk, Tinker, Tolarian Academy, Trade Secrets, Upheaval, Yawgmoth's Bargain.

The list also bans the 25 Conspiracy cards, the 9 ante cards, and cards banned for offensive depictions. Lutri, the Spellchaser is banned only as a companion ([source](https://magic.wizards.com/en/banned-restricted-list)). Third-party counts of "83 banned" include the Conspiracy and ante cards ([ArcaneMetriX](https://arcanemetrix.com/articles/commander-banlist)).

**Last Commander B&R change: February 9, 2026.** Biorhythm was unbanned and went onto the Game Changers list. Lutri was unbanned except as a companion and is not a Game Changer. The article says Commander "gets to operate on its own schedule" and is no longer limited to one update window per year ([Wizards](https://magic.wizards.com/en/news/announcements/commander-banned-and-restricted-february-9-2026)).

**Later announcements.** The general B&R announcements of May 18, June 29, August 10 and October 12, 2026 made no Commander change ([Mana Grove summary](https://themanagrove.com/articles/commander-game-changers), [Oct 12 official](https://magic.wizards.com/en/news/announcements/banned-and-restricted-october-12-2026)). The next general announcement is **November 30, 2026** ([Wizards](https://magic.wizards.com/en/news/announcements/banned-and-restricted-october-12-2026)).

**Commander Brackets.**
- Brackets launched as a beta on February 11, 2025 ([Wizards](https://magic.wizards.com/en/news/announcements/introducing-commander-brackets-beta)). They were updated on April 22, 2025 ([Wizards](https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-april-22-2025)), October 21, 2025 ([Wizards](https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-october-21-2025)) and February 9, 2026 ([Wizards](https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-february-9-2026)).
- **Current rules (the October 2025 shape; February 2026 changed only the list).** Brackets 1 and 2 allow no Game Changers, Bracket 3 allows up to three, and Brackets 4 and 5 allow any number ([format page](https://magic.wizards.com/en/formats/commander)).
- Minimum expected game length is 9, 8, 6 and 4 turns for Brackets 1 to 4, and any turn for Bracket 5 ([October 2025 update](https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-october-21-2025), [Moxfield summary](https://moxfield.com/commanderbrackets)).
- Tutor limits were removed in October 2025. The remaining barometers are two-card infinite combos, extra turns and mass land denial ([format page](https://magic.wizards.com/en/formats/commander)).
- Wizards stresses intent over checklist: "a tool to guide pregame conversations—not an ultimate arbiter." Bracket 1 explicitly allows bending card legality by agreement ([February 2026](https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-february-9-2026)).
- Still labeled beta. **UNCONFIRMED:** one secondary source says the February 2026 article expects the beta tag to be dropped later in 2026 ([Mana Grove](https://themanagrove.com/articles/commander-brackets-explained)). I did not see that sentence in the official excerpt I fetched.

**Game Changers list.**
- **53 cards**, last changed February 9, 2026, when Farewell and Biorhythm were added ([Wizards](https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-february-9-2026), [MTG Wiki](https://mtg.wiki/page/Game_Changers)).
- Scryfall's `is:gamechanger` returned 53 cards on November 1 and 2, 2026 according to sites that sync from it ([Playgroup.gg](https://playgroup.gg/commander/game-changers), [Gamertag Mythras](https://gamertagmythras.com/blog/magic-the-gathering/mtg-commander-brackets)).
- Policy: unbanned cards go straight onto the list. Lutri is the one exception ([Wizards](https://magic.wizards.com/en/news/announcements/commander-banned-and-restricted-february-9-2026)).
- **UNCONFIRMED:** that no Brackets or Game Changers change has happened since February 9, 2026. Several secondary sources checked between October 20 and November 1, 2026 say so ([Mana Grove](https://themanagrove.com/articles/commander-game-changers), [Gamertag Mythras](https://gamertagmythras.com/blog/magic-the-gathering/mtg-commander-brackets)), and the February article had promised a check-in around May or June. I found no official later update, but I did not read the full announcements archive.

**RSS or feed.** **UNCONFIRMED / likely none.** I found no RSS or Atom feed for magic.wizards.com news or announcements. The practical approach is to poll the three pages in the table above, plus the Scryfall bulk-data `updated_at` timestamp (see A3). Scryfall's own blog has a feed at https://scryfall.com/blog/feed ([source](https://scryfall.com/docs/api/bulk-data)).

**Suggested refresh check for the plugin.** Each item is one cheap HTTP call:
1. Rules page: has the TXT link date changed?
2. Banned-restricted page: hash the "Commander Banned Cards" section.
3. Announcements index: are there new titles that contain "Commander", "Brackets" or "Banned"?
4. Scryfall `GET https://api.scryfall.com/bulk-data/oracle-cards`: compare `updated_at`, then recount `game_changer == true` and `legalities.commander == "banned"`.

### A3. Scryfall: legality and the game_changer flag

**Fields.** Card objects have `legalities` (values `legal`, `not_legal`, `restricted`, `banned`, keyed by format and including `commander`). They also have `game_changer` (Boolean, nullable): "True if this card is on the Commander Game Changer list" ([Scryfall card docs](https://scryfall.com/docs/api/cards)).
- `not_legal` means no permitted set. `banned` means Wizards banned the card ([Scryfall FAQ](https://scryfall.com/docs/faqs/what-do-the-different-legalities-mean-10)).
- Scryfall has no separate "banned as companion" value, so Lutri needs a hand-coded exception. **UNCONFIRMED** how Scryfall represents Lutri. Check the live card.

**Search syntax.** `is:gamechanger` is used by tools that sync from Scryfall ([Playgroup.gg](https://playgroup.gg/commander/game-changers)). `legal:commander` and `banned:commander` are standard Scryfall syntax (**UNCONFIRMED** against the syntax page this session).

**Bulk data.**
- Files are gzipped JSONL, and old JSON was retired on July 20, 2026. Bulk data is "only collected once every 12-24 hours."
- Use the live card API for fresh objects, or `GET https://api.scryfall.com/cards/manifest` to check what changed ([bulk docs](https://scryfall.com/docs/api/bulk-data), [blog, July 1, 2026](https://scryfall.com/blog/two-new-ways-to-sync-scryfall-data-236)).
- The Oracle Cards file was last updated 2026-11-01 22:02 UTC when fetched ([bulk docs](https://scryfall.com/docs/api/bulk-data)).
- `GET https://api.scryfall.com/bulk-data` lists the files with their `updated_at` values.
- The manifest is rate-limited to 10 requests per minute and covers card existence and image updates, not legality changes ([manifest docs](https://scryfall.com/docs/api/cards/manifest)).

**Update speed after an announcement.** **UNCONFIRMED.** I found no published service level. In April 2025 Wizards said it "worked with great community tools like Archidekt, Moxfield, and Scryfall to make sure those sites were ready to roll out and track those immediately" ([Wizards](https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-april-22-2025)). So same-day updates on the live API are likely. Bulk files can still lag by up to 12 to 24 hours. The plugin should treat the official page as the source of truth for the first day after an announcement.

### A4. Other machine-readable sources for Brackets and Game Changers

- **No official API or JSON from Wizards** was found (**UNCONFIRMED** absence). The format page is HTML only.
- **Commander Spellbook API** (EDHREC / Space Cow Media) has `GET`/`POST /estimate-bracket` for a decklist and `/find-my-combos` ([API docs](https://spacecowmedia.github.io/commander-spellbook-backend/api.html)). This is useful for combo-based bracket checks, but it is not an official bracket ruling. EDHREC's combo pages show recommended brackets from the same data ([EDHREC guide](https://edhrec.com/guides/how-to-use-edhrec)).
- **MTGJSON** is used by third parties to rebuild the ban list ([Mana Grove](https://themanagrove.com/articles/commander-ban-list)). **UNCONFIRMED** whether it carries a Game Changer flag.
- **mtgdb.org** has `/v1/gamechangers` and `/v1/commander-brackets` endpoints ([docs](https://mtgdb.org/docs)). It is a third-party site of unknown upkeep, so use it only as a cross-check.
- **Deck sites:**
  - Archidekt estimates brackets and originally used Game Changers only. It later added an explanation and mass land denial detection (Blood Moon example) ([Archidekt](https://archidekt.com/forum/thread/11356226)).
  - Moxfield shows a bracket gauge and Game Changer markers ([Moxfield](https://moxfield.com/commanderbrackets)).
  - These estimators disagree with each other ([Archidekt thread](https://archidekt.com/forum/thread/11356226?&page=2)).

---

## Part B: Collaborative deckbuilding UX

### B1. How good builders and tools find out what a player wants

**Official framing: intent first.** Wizards defines each bracket by player expectations and game length, not only by card lists. They ask players to bracket honestly by intent ([October 2025](https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-october-21-2025), [April 2025](https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-april-22-2025)). The old RC FAQ said to "communicate what you enjoy about Commander, what you're hoping (or not) to see in that game (such as specific cards, length of games, or general strategies)" ([mtgcommander.net](https://mtgcommander.net/index.php/faq/)).

**Rule 0 scripts.** Community scripts converge on the same short list ([MTGEDH](https://mtgedh.com/mtg-commander-rule-0-the-pregame-talk-that-actually-works), [Proxy King](https://proxyking.biz/how-to-have-a-great-commander-rule-zero-discussion-without-the-awkward-vibes)):
- Target power or bracket.
- How the deck wins and on what turn it threatens.
- Combos, stax, mass land destruction and extra turns.
- Proxies.
- Time available.

**Command Zone template (episode 658, February 2025).** About 38 lands, 10 ramp, 12 card advantage, 12 targeted disruption, 6 mass disruption, and the rest "plan" cards. Categories overlap ([YouTube](https://www.youtube.com/watch?v=OSNV6224cHg); counts as summarized by [Farseek](https://farseek.ai/blog/how-to-analyze-your-commander-deck) and [a GitHub transcription](https://github.com/OlliTapio/mtg-deck-optimizer/blob/main/command_zone_template.md); **UNCONFIRMED** against the video itself). Episode 659 explains when to break the template ([EDHREC](https://edhrec.com/articles/the-command-zone-the-problem-with-deckbuilding-templates-the-command-zone-659-mtg-edh-magic-gathering)). An earlier framing splits plan cards into enablers, payoffs and enhancers ([Commander Deck Maker](https://commanderdeckmaker.com/learn/deckbuilding/command-zone-template)). For an AI, this is a skeleton to fill after the player's goals are known, not a substitute for them.

**Psychographics.**
- Timmy, Johnny and Spike: "Spike asks 'Is it good enough to play?'; Johnny asks 'What can I do with this?'; and Timmy asks 'Would I like to play with this?'" ([Wizards](https://magic.wizards.com/en/news/making-magic/designing-timmy-2009-03-05)). Vorthos (flavor) and Melvin (mechanics aesthetics) are named but are not psychographics ([same](https://magic.wizards.com/en/news/making-magic/designing-timmy-2009-03-05)).
- EDH-specific types include Barktooth (obscure commanders), Herm (wins via combos) and the "blorbo" builder who builds around a favorite character ([EDHREC](https://edhrec.com/articles/an-introduction-to-edh-player-psychographics), [EDHREC](https://edhrec.com/articles/different-approaches-to-building-a-commander-deck)).

**Tool features that encode preferences.**
- EDHREC commander pages filter by Bracket, Budget and Tags (themes) ([EDHREC](https://edhrec.com/guides/how-to-use-edhrec)), with price filters ([EDHREC](https://edhrec.com/articles/edhrec-just-got-an-upgrade)).
- Archidekt has collection tracking, EDH Recs, landbase and combo tabs, and Scryfall-syntax filters ([EDHREC guide to Archidekt](https://edhrec.com/guides/how-to-use-archidekt-the-mtg-deckbuilding-site)).
- Moxfield has a bracket gauge ([Moxfield](https://moxfield.com/commanderbrackets)).
- Budget models include a hard budget and an add-on budget on top of an owned collection ([Flipside](https://flipsidegaming.com/blogs/magic-blog/commander-deckbuilding-the-budget-blueprint)).
- Human builders also check owned cards first, because owning the mana base makes a build more likely ([Magic Margins](https://magicmargins.ca/blog/how-to-pick-a-commander)).

**Dimensions that matter.** Each line names the dimension, then the source.
1. **Why they play / fun source** (big spells, clever combos, winning, theme or flavor, an obscure commander): [Wizards](https://magic.wizards.com/en/news/making-magic/timmy-johnny-and-spike-revisited-2006-03-20-2), [EDHREC](https://edhrec.com/articles/an-introduction-to-edh-player-psychographics).
2. **Starting point** (commander, colors, mechanic or character): [EDHREC](https://edhrec.com/articles/different-approaches-to-building-a-commander-deck).
3. **Win style and speed** (combat, combo, alt-win, big turn; turn expectations): [Wizards Oct 2025](https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-october-21-2025), [Proxy King](https://proxyking.biz/how-to-have-a-great-commander-rule-zero-discussion-without-the-awkward-vibes).
4. **Bracket and table expectations** (the target bracket and what the pod actually plays): [format page](https://magic.wizards.com/en/formats/commander).
5. **Hard lines** (infinite combos, extra turns, mass land denial, stax, Game Changers): [format page](https://magic.wizards.com/en/formats/commander), [MTGEDH](https://mtgedh.com/mtg-commander-rule-0-the-pregame-talk-that-actually-works).
6. **Interaction level** (how much removal and counterspells they enjoy casting and facing): [Proxy King](https://proxyking.biz/how-to-have-a-great-commander-rule-zero-discussion-without-the-awkward-vibes).
7. **Budget model** (hard cap, add-on budget, or proxies okay): [Flipside](https://flipsidegaming.com/blogs/magic-blog/commander-deckbuilding-the-budget-blueprint), [MTGEDH](https://mtgedh.com/mtg-commander-rule-0-the-pregame-talk-that-actually-works).
8. **Owned collection**: [Magic Margins](https://magicmargins.ca/blog/how-to-pick-a-commander), [Archidekt collection](https://edhrec.com/guides/how-to-use-archidekt-the-mtg-deckbuilding-site).
9. **Pet cards and must-includes, banned-by-me cards**: r/EDH "Show me your pet cards!" thread title seen in [this listing](https://www.reddit.com/r/EDH/comments/17eivyr/if_not_edhrec_then_what_do_you_use_for_decklist/). This is weak evidence, but the concept is widespread.
10. **Theme and flavor** (Vorthos, Bracket 1 theme-over-function): [Wizards Oct 2025](https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-october-21-2025).
11. **Complexity tolerance** (triggers to track, long turns, rules-heavy lines). No primary source was found. This is **my inference** from Wizards noting "the wordiness of cards" as a concern ([February 2026](https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-february-9-2026)).
12. **Popularity vs. originality** (EDHREC "homogenizes the format" complaints): [r/EDH](https://www.reddit.com/r/EDH/comments/1wpw09a/as_a_newer_edh_player_i_was_tired_of_ai_giving_me), [r/EDH](https://www.reddit.com/r/EDH/comments/17eivyr/if_not_edhrec_then_what_do_you_use_for_decklist/).

### B2. Player complaints about AI deckbuilders

**Invented cards and wrong card facts.** A user in "Do not use AI to make deck suggestions or clarify rules. It's wrong most of the time" (r/EDH, about 811 upvotes) reports these errors ([r/EDH](https://www.reddit.com/r/EDH/comments/1q0epg2/do_not_use_ai_to_make_deck_suggestions_or_clarify)):
- A suggested "Lullmage's Shadow", which does not exist.
- Lightning Runner described as an artifact creature.
- Viscera Seer named as a Cleric.
- Misleading combo explanations.
- Confidence that does not match accuracy.

**Illegal decks.**
- An SCG test found that ChatGPT produced 83-card and 49-card "decks", duplicates (three Sorrow's Path), a five-color list under a mono-black commander, a non-legendary commander and a $2,099 list ([Star City Games](https://articles.starcitygames.com/magic-the-gathering/ai-brewed-me-two-commander-decklists)).
- An r/mtg thread (about 802 votes) lists "suggesting banned cards or illegal deck sizes, or too many copies of a card" ([r/mtg](https://www.reddit.com/r/mtg/comments/1tjmyhb/ai_assisted_deck_building_is_lame)).
- One newer player built a tool because "AI [was] giving me illegal deck advice." Replies note the AI also gets CMC wrong and mixes up similarly named cards ([r/EDH](https://www.reddit.com/r/EDH/comments/1wpw09a/as_a_newer_edh_player_i_was_tired_of_ai_giving_me)).
- A vendor write-up lists: commander counted inside the 99, off-color picks, and "replace X with Y" adding both cards ([Farseek](https://farseek.ai/blog/chatgpt-fails-commander-deckbuilding)). This source is biased because it sells a product, but it matches the threads above.

**Generic or incoherent lists.**
- "Looks reasonable at first glance," with Tendrils of Agony in a deck that cannot storm ([r/EDH](https://www.reddit.com/r/EDH/comments/1ob82wn/aiassisted_deck_building)).
- Popularity data dressed up as reasoning ([Farseek](https://farseek.ai/blog/chatgpt-fails-commander-deckbuilding)).
- "AI deckbuilding is just netdecking, and certainly worse quality netdecking" ([r/mtg](https://www.reddit.com/r/mtg/comments/1tjmyhb/ai_assisted_deck_building_is_lame)).

**Taking the creative part away.** Strong social pushback: "replacing the creative part of the game with AI slop" ([r/EDH](https://www.reddit.com/r/EDH/comments/1ob82wn/aiassisted_deck_building)). Users also say a tool should teach the search skill, not hand over a list ([r/EDH](https://www.reddit.com/r/EDH/comments/1wpw09a/as_a_newer_edh_player_i_was_tired_of_ai_giving_me)). Positive comments frame AI as "Scryfall on steroids that is not always correct" or as a sparring partner ([r/mtg](https://www.reddit.com/r/mtg/comments/1tjmyhb/ai_assisted_deck_building_is_lame)).

**Wrong bracket.** Bracket estimators disagree with each other and miss intent. One example: a bracket-check site said Bracket 2 for a deck the owner felt was Bracket 3 ([r/EDH](https://www.reddit.com/r/EDH/comments/1lfvale/any_way_to_see_what_bracket_my_deck_is_in)). Archidekt and Moxfield gave different results for the same decks ([Archidekt](https://archidekt.com/forum/thread/11356226?&page=2)). **UNCONFIRMED:** I found no thread that blames an LLM specifically for a wrong bracket. The evidence is about tools in general.

**Ignoring stated preferences.** **UNCONFIRMED** as a distinct cited complaint. It is implied by the "generic list" and "ignores your actual deck" complaints ([Farseek](https://farseek.ai/blog/chatgpt-fails-commander-deckbuilding)).

### B3. Recommended intake and iteration flow

These are design recommendations, not sourced facts. Each one traces back to the findings above.

**Step 0: Rules freshness check (silent, then one line).**
Compare the cached CR date, ban list hash, Game Changers count and Scryfall `updated_at` with the live values (A2 refresh check).
- If anything changed, or the cache is more than 7 days old, tell the user one line, for example: "Rules data is from <date>; refresh now?" Refresh only if they agree.
- Always show the dates in use, for example "CR 2026-09-25 · Commander B&R 2026-02-09 · 53 Game Changers".

**Step 1: Starting point (one question, choices).** Ask what they are starting from:
- a commander,
- colors,
- a mechanic or theme,
- a favorite character or card,
- "surprise me",
- or an existing list or precon to upgrade.

This mirrors how real players start ([EDHREC](https://edhrec.com/articles/different-approaches-to-building-a-commander-deck)).

**Step 2: Table and bracket (choices plus free text).**
- Ask for the target bracket (1 to 5, each with its one-line intent and turn expectation), or "I don't know, describe my pod."
- Then ask about hard lines: infinite combos, extra turns, mass land denial, stax, and the number of Game Changers.
- Present these as defaults that the bracket implies, and let the user override them. Brackets are guidance, not law ([Wizards Feb 2026](https://magic.wizards.com/en/news/announcements/commander-brackets-beta-update-february-9-2026)).

**Step 3: Fun profile (pick up to two).**
- Big splashy plays.
- Clever engines or combos.
- Winning efficiently.
- Theme and flavor.
- Making an underdog commander work.

Then ask for win style (combat, combo, alt-win, drain, big turn) and interaction appetite (low, medium, high).

**Step 4: Constraints.**
- Budget model: hard cap, add-on over collection, or proxies okay.
- Collection import (Archidekt, Moxfield or a CSV), with a "prefer owned" vs. "owned only" toggle.
- Pet cards (must include) and never-include cards.
- Complexity tolerance.

**Step 5: Show, don't dump.**
- Propose a skeleton first: the plan in 2 to 3 sentences, the category targets (Command Zone baselines adjusted to their answers), and 3 to 5 key cards with reasons.
- Ask "Is this the deck you want?" before filling all 99 slots. This answers the "generic list" and "removes creativity" complaints.

**Step 6: Fill in chunks.** Build by category (ramp, then draw, removal, plan, lands).
- Offer **choices** where taste matters: theme cards, win conditions, pet-card swaps, budget tradeoffs.
- **Decide automatically** where taste rarely matters: basic land counts and obvious color-fixing within budget. State what was auto-picked so the user can override it.

**Step 7: Validate every turn, with tools and not memory.** Every card name must resolve through Scryfall (or the MTG connector) before it is shown. Check, and state the counts plainly:
- exactly 100 cards including the commander;
- singleton except basics and cards that say otherwise;
- color identity per CR 903.4;
- `legalities.commander`;
- Lutri banned as a companion;
- Game Changer count vs. bracket;
- Commander Spellbook combos vs. bracket.

This targets every complaint category in B2.

**Step 8: Iterate.** For "swap X", show 3 to 5 alternatives with a one-line reason and price, then re-run validation. Keep a short "player profile" record (bracket, hard lines, pets, budget, owned) and reuse it across sessions. Re-ask only when a request conflicts with it.

**Step 9: Explain for the Rule 0 talk.** End with a short summary the player can say at the table: bracket, win turn, combos or Game Changers present, anything spicy. This is the conversation Wizards wants brackets to support ([format page](https://magic.wizards.com/en/formats/commander)).

## Unconfirmed items (collected)

1. No RSS or Atom feed or official API for Wizards announcements, bans, Brackets or Game Changers.
2. No Brackets or Game Changers change between February 9, 2026 and November 3, 2026. This is based on secondary sources, and the full official archive was not read.
3. Scryfall's lag after an announcement. Same day on the live API is likely, and bulk files lag 12 to 24 hours.
4. How Scryfall represents Lutri's "banned as companion only" status.
5. Whether MTGJSON carries a Game Changer flag.
6. Exact Command Zone episode 658 counts. Taken from secondary transcriptions, not the video.
7. Whether the February 2026 article says the beta tag will be dropped in 2026.
8. Encoding quirks of the 2026 CR TXT files.
9. Cited complaint threads that specifically blame LLMs for a wrong bracket or for ignoring stated preferences.
