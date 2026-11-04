---
name: research
description: Researches Magic: The Gathering Commander ideas, commanders, cards, themes and strategies across real community knowledge (EDHREC statistics, public decklists and primers, Reddit, articles, YouTube deck techs, tournament results), recommends promising directions, and records cited, classified evidence in RESEARCH.md and research.json. Use when the player is exploring an idea or theme, asks what players recommend or think about something, wants commanders or strategies compared, wants something from YouTube or Reddit investigated, or when another skill finds an evidence gap that changes its conclusions. Not for a single fact or rules question that one lookup answers, not for building or changing a deck (brew), not for verifying finished work (audit), not for pages (present).
---

# Research

Find out what real players know, then recommend. Quality beats volume: relevant, recent, diverse, honestly labelled evidence. Every claim the player sees traces to a source they can open, or is labelled as Claude's judgment or as unresolved.

## When to use
- **Use:** "I want a Spider-Man deck, where do I start?", "what are people saying about Anti-Venom?", "best Spider-Man commanders?", "is this Reddit combo real?", "which precon has most of these cards?", "is this Secret Lair still available?", a gap brew or audit reports.
- **Don't use:** "what does lifelink do?", "is Sol Ring banned?", one card's text or price. Answer directly from one authoritative lookup with its date; no files.
- **Parallel agents:** only for several independent subjects (e.g. four commanders to compare): one `researcher` agent per 1 to 2 subjects, each writing a part file in the research.json format with its own ID range; merge them into research.json. Small jobs run inline.
- **Needs approval:** a deep pass nobody asked for (say the depth in one line; ask before going deep). Reading never needs approval, and research never changes a deck.

## Inputs
The question; optionally the project's PROJECT.md, DECISIONS.md, STATE.md (goals, theme rules, what's settled) and an existing research.json to extend. Project files: [schemas/README.md](../../schemas/README.md).

## Workflow
```
- [ ] 1. Read the project files if there's a project; reuse existing research
- [ ] 2. Pick depth (quick / standard / deep) and the recency cutoff
- [ ] 3. Confirm which capabilities work (one cheap call each)
- [ ] 4. Gather: facts, then what's played, then why, then how it plays at tables
- [ ] 5. Label every claim; keep sources with dates and timestamps
- [ ] 6. Hunt for what's missing and where sources disagree; for themes, assess feasibility
- [ ] 7. Recommend: 2 to 4 directions, one recommended, with reasons
- [ ] 8. Write RESEARCH.md + research.json, validate, update STATE.md
```

1. **Reuse.** Extend an existing research.json (bump `version`, keep IDs). A theme in PROJECT.md shapes the search: look for on-theme cards and printings, not only strong cards.
2. **Depth from the ask, not a fixed checklist.** Quick (one narrow question): 2 to 5 sources. Standard (a commander or theme): data, 3 to 6 decklists, 2 to 3 creators, 3 to 5 community threads or articles. Deep (comparisons, unusual strategies): standard per subject, plus tournament data where power matters. Recency cutoff: the latest Wizards bans / Game Changers / bracket update; older power or legality claims can support, never decide.
3. **Capabilities, not tool names.** Respect the player's research preferences (PROJECT.md "Research preferences", else `research:` in the setup config): favour preferred sources, never use excluded ones, and say when an exclusion leaves a gap. Otherwise pick tools by what they do and confirm each with one cheap call. [references/sources.md](references/sources.md) lists the capabilities, how installed tools behaved when tested, and the web fallback for each. Record failures and fallbacks in `methodology.tools_failed`. Never fill a gap from memory.
4. **Gather** in this order: card facts and rules → EDHREC and real decklists (what's played, with sample sizes) → creators and primers (why) → Reddit and forums (how it plays at real tables, what's overrated or frustrating) → articles. Smaller creators count when the big ones haven't covered something; subscriber counts prove nothing. Parallel lookups where independent; YouTube transcripts one at a time. Method and evidence rules: [references/method.md](references/method.md).
5. **Label.** Each finding gets an evidence class (`verified_fact`, `calculated`, `popularity_metric`, `community_opinion`, `model_assessment`, `unresolved`) and a confidence. Popularity isn't effectiveness; one creator is one source however many videos; a statistic without a sample size is `unresolved`.
6. **Gaps, disagreements, feasibility.** Search the commander's own mechanic for cards that scale it (easy to miss); look for a less-hyped commander or approach that fits the player better; put conflicting opinions in `disagreements` with both sides cited. For a themed request, you own the card-pool discovery and first feasibility call: whether the franchise has official cards at all (search, don't assume), eligible commanders, the pool per color identity and role, eligible printings and their art, written to `feasibility` with confirmed counts vs estimates ([brew's themes.md](../brew/references/themes.md) §2). For an existing deck, collect community-backed alternatives (cards real lists play that this one doesn't, with why) as `card_candidates`.
7. **Recommend.** Only recommend commanders verified legal (eligible, not banned, real pairings; check with `uv run --script "${CLAUDE_PLUGIN_ROOT}/skills/audit/scripts/deck_check.py" --commander "A" [--commander "B"]`, or Scryfall `is:commander` plus its Commander legality when scripts can't run). For a broad idea, present 2 to 4 directions (commanders or approaches), each in the same short layout: what it does, theme fit, strengths, weaknesses, evidence. Say which you'd pick for this player and why. Add `recommended_next_steps` and only the `follow_up_questions` whose answers change the recommendation.
8. **Write and check.** RESEARCH.md: the recommendation first, claims cited `[fnd-…, src-…]`, then disagreements and gaps. research.json per `schemas/research.schema.json`. Validate: `uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/companion.py" validate <project>`. Update STATE.md (what's known, open questions, next step). Reply in a few lines: recommendation, confidence, the biggest disagreement, shortfalls.

For a quick question in chat with no project, answer inline with citations and skip the files unless the player wants them kept.

## Honesty rules
- Cite only pages you opened; no URLs from memory. Video claims carry the mm:ss you saw.
- Card facts (text, legality, color identity, Game Changer status, printings, art) come from Scryfall, never from videos, EDHREC or memory. Resolve every card name from a transcript or thread on Scryfall; drop or list what doesn't resolve.
- What couldn't be checked goes in `gaps`, not into a finding.
- Prices: per printing and finish, with source and date; verified only when read for that exact printing, otherwise an estimate.
- Products and availability (precon and Secret Lair contents, in print or not, reprints, Reserved List): check contents against Scryfall or the official decklist, cite availability claims. A quick "cheapest way to get X?" is a direct answer with dated prices; acquisition plans for a whole deck follow brew's [acquisition.md](../brew/references/acquisition.md).
