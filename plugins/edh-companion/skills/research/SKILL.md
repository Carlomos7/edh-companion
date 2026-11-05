---
name: research
description: Researches Magic: The Gathering Commander ideas, commanders, cards, themes and strategies across real community knowledge (EDHREC statistics, public decklists and primers, Reddit, articles, YouTube deck techs, tournament results), recommends promising directions, and records cited, classified evidence in RESEARCH.md and research.json. Use when the player is exploring an idea or theme, asks what players recommend or think about something, wants commanders or strategies compared, wants something from YouTube or Reddit investigated, or when another skill finds an evidence gap that changes its conclusions. Not for a single fact or rules question that one lookup answers, not for building or changing a deck (brew), not for verifying finished work (audit), not for pages (present).
---

# Research

Find out what real players know, then recommend. Quality beats volume: relevant, recent, diverse, honestly labelled evidence. Every claim the player sees traces to a source they can open, or is labelled as Claude's judgment or as unresolved.

**Replies:** answer first, reasons next, limits once, next step last (a choice as options, recommended first with why). Read [writing.md](../../references/writing.md) before writing directions, a research reply, RESEARCH.md or findings.

## When to use
- **Use:** "I want a Spider-Man deck, where do I start?", "what are people saying about Anti-Venom?", "best Spider-Man commanders?", "is this Reddit combo real?", "which precon has most of these cards?", "is this Secret Lair still available?", a gap brew or audit reports.
- **Don't use:** "what does lifelink do?", "is Sol Ring banned?", one card's text or price. Answer directly from one authoritative lookup with its date; no files.
- **Parallel agents:** only for several independent subjects (e.g. four commanders to compare); small jobs run inline. One `researcher` owns card data, the others take videos, decklists and community; each writes `research.part-<slug>.json`, merged by `companion.py merge-research` only when every planned worker finished. Plan, briefs and merge: [references/sources.md](references/sources.md), "Parallel research" and "Reliability".
- **Needs approval:** only the one-time research approval, and work clearly beyond it (much deeper than the saved depth, many long videos, an unapproved or excluded tool). Approved research at the saved depth, including every Scryfall search it needs, runs after an announcement, with progress updates and no more questions ([When to ask](../../schemas/README.md#when-to-ask-and-when-not-to)). Research never changes a deck.

## Inputs
The question; optionally the project's PROJECT.md, DECISIONS.md, STATE.md (goals, theme rules, what's settled) and an existing research.json to extend. Project files: [schemas/README.md](../../schemas/README.md).

## Workflow
```
- [ ] 1. Read the project files if there's a project; reuse existing research
- [ ] 2. Depth (quick / comprehensive / deep), the important questions, the recency cutoff
- [ ] 3. Confirm which capabilities work (one cheap call each)
- [ ] 4. Gather: facts, then what's played, then why, then how it plays at tables
- [ ] 5. Label every claim; keep sources with dates and timestamps
- [ ] 6. Hunt for what's missing and where sources disagree; for themes, assess feasibility
- [ ] 7. Recommend: 2 to 4 directions, one recommended, with reasons
- [ ] 8. Write RESEARCH.md + research.json, validate, update STATE.md
```

1. **Reuse.** No project named? Check saved projects first and offer to resume a match ([schemas/README.md](../../schemas/README.md), "Starting a session"). Extend an existing research.json (bump `version`, keep IDs); query it with `companion.py research-find <project> --card NAME | --text WORDS` instead of reading it whole, and only research what it doesn't already answer. A theme in PROJECT.md shapes the search: look for on-theme cards and printings, not only strong cards. Research about an existing deck records the deck version it describes in `scope.deck` ([references/method.md](references/method.md), "When the deck changes after research").
2. **Approval and depth.** Before the first substantial research (not a one-card or one-rule question), run the two-step approval in [references/sources.md](references/sources.md), "Research approval": the tools found, approved by the player, then how often to ask in future. Nothing external is called before that answer. Saved choices are reused across sessions and projects; PROJECT.md "Research preferences" overrides them per project. Announce every substantial task; in "ask every time" mode, wait for a yes. Claude Code's own permission prompts are separate and still apply.
   Depth: Quick, Comprehensive (default) or Deep. Research until the important questions are answered or new sources stop adding anything, then say why it stopped ([references/method.md](references/method.md), "Depth and when to stop"). Recency cutoff: the latest Wizards bans / Game Changers / bracket update; older power or legality claims can support, never decide.
3. **Capabilities, not tool names.** Use approved tools only; respect preferences (PROJECT.md "Research preferences", else `research:` in the config): favour preferred sources, never use excluded ones, say when an exclusion leaves a gap, and ask before falling back to an unapproved tool. Otherwise pick tools by what they do and confirm each with one cheap call; installed doesn't mean working. Which tool for which job, how they behaved when tested, and the fallbacks: [references/sources.md](references/sources.md). When YouTube transcripts work and aren't excluded, comprehensive research includes creator deck techs with timestamps. Record failures and fallbacks in `methodology.tools_failed`. Never fill a gap from memory.
4. **Gather** in this order: card facts and rules → EDHREC and real decklists (what's played, with sample sizes) → creators and primers (why) → Reddit and forums (how it plays at real tables, what's overrated or frustrating) → articles. Parallel lookups where independent. Method and evidence rules: [references/method.md](references/method.md).
5. **Label.** Each finding gets an evidence class (`verified_fact`, `calculated`, `popularity_metric`, `community_opinion`, `model_assessment`, `unresolved`) and a confidence. Popularity isn't effectiveness; one creator is one source however many videos; a statistic without a sample size is `unresolved`. One claim per finding, written per [references/method.md](references/method.md), "Writing findings".
6. **Gaps, disagreements, feasibility.** Search the commander's own mechanic for cards that scale it (easy to miss); look for a less-hyped commander or approach that fits the player better; put conflicting opinions in `disagreements` with both sides cited. For a themed request, you own the card-pool discovery and first feasibility call, written to `feasibility` with confirmed counts vs estimates ([brew's themes.md](../brew/references/themes.md) §2). For an existing deck, collect community-backed alternatives (cards real lists play that this one doesn't, with why) as `card_candidates`.
7. **Recommend.** Only recommend commanders verified legal (eligible, not banned, real pairings; check with `uv run --script "${CLAUDE_PLUGIN_ROOT}/skills/audit/scripts/deck_check.py" --commander "A" [--commander "B"]`, or Scryfall `is:commander` plus its Commander legality when scripts can't run). For a broad idea, present 2 to 4 directions (commanders or approaches) in the shared layout, the recommended one first with why ([writing.md](../../references/writing.md), "Recommending directions"). Add `recommended_next_steps` and only the `follow_up_questions` whose answers change the recommendation.
8. **Write and check.** RESEARCH.md in the one shape in [references/method.md](references/method.md) ("RESEARCH.md shape"). research.json per `schemas/research.schema.json`. Validate: `uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/companion.py" validate <project>`. When the research names cards for a deck, verify them for brew: `uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/candidates.py" <project>` → `candidates.json` (verified cards, evidence kept). Update STATE.md (what's known, open questions, next step). Reply answer-first: the recommendation with its confidence and any caveat that changes it; the biggest disagreement; shortfalls; how many sources were reviewed and why research stopped; the next step last. The evidence stays in the files.

For a quick question in chat with no project, answer inline with citations and skip the files unless the player wants them kept.

## Honesty rules
- Cite only pages you opened; no URLs from memory. Video claims carry the mm:ss you saw, in the finding's `locators`.
- Card facts come only from Scryfall. Resolve every card name from a transcript or thread on Scryfall; drop or list what doesn't resolve.
- What couldn't be checked goes in `gaps`, not into a finding.
- Theme rankings (best cards per theme or group) go in `rankings` ([references/method.md](references/method.md), "Theme rankings").
- Unreleased cards: status and release date come from Scryfall (`released_at`, legality `not_legal` until release); never guess a legal date. Banned is a different status.
- Prices: per printing and finish, with source and date; verified only when read for that exact printing, otherwise an estimate.
- Products and availability (precon and Secret Lair contents, in print or not, reprints, Reserved List): check contents against Scryfall or the official decklist, cite availability claims. A quick "cheapest way to get X?" is a direct answer with dated prices; acquisition plans for a whole deck follow brew's [acquisition.md](../brew/references/acquisition.md).
