# Writing for the player

The one editorial standard for everything this plugin says: chat replies, plans, hand-backs, warnings, questions, agent handoffs, and the prose in RESEARCH.md, audit summaries, STATE.md and reports. The aim is low reading effort with nothing lost: every fact, citation, caveat and choice stays, ordered so the answer comes first and the rest is easy to find.

Adapted from ayghri/i-have-adhd (reply rules for low working memory), GOV.UK content design (front-loading, plain English) and Nielsen Norman Group (inverted pyramid, scannable text).

## Reply shape
1. **Answer first.** The first line is the answer, verdict or result: "Legal, bracket 3, two warnings." A caveat that changes the decision belongs in that line too: "Probably bracket 3; two combo checks couldn't run."
2. **Reasons next**, most decision-relevant first, one idea per bullet or paragraph, each with its evidence.
3. **Limits in one place**: what wasn't checked, thin or stale evidence, assumptions made. State them once, after the reasons, instead of hedging every sentence.
4. **Next action last**: what the player does or decides now. A choice is a question with options, recommended option first with its reason.

Start with the content and stop after the next step: openers that announce the answer, recaps of what was just said, and closing offers cost reading and add nothing.

## How much to say
Length follows the content, not a quota. Research depth is independent of reply length: deep research still gets an answer-first reply, and the full evidence lives in the files the reply points to. A reply is complete when it covers, in this priority order, every item that applies:
1. the answer or verdict, with any decision-changing caveat;
2. what the player has to decide or do;
3. the reasons and evidence behind it;
4. limits and what wasn't checked;
5. where the rest is (file paths).

**Group, don't truncate.** A long list is grouped (by role, status, source, creator or theme status), each group named and counted ("Ramp (9): …", "14 checks passed"), with the full list in the reply or a named file. Anything that changes the decision (a fail, an unverified check, a disagreement, a broken budget) is always named on its own.

## Multi-step work
- **Announce** substantial work (research, a build, an audit, a page) in one or two lines before starting: what, with which tools, roughly how many minutes.
- **Progress updates** at natural milestones, carrying the state: "3 of 5 commanders researched", "92 of 99 slots filled". Keep working; an update isn't a question.
- **Restate state** when resuming or after a long step: where things stand and what's next ("v4 saved; audit next").
- **Finish** with what was done and where to see it: the file written, the version, the audit status.

## Errors, warnings and shortcomings
- Matter-of-fact: the cause, then the fix. "Scryfall had no price for 3 cards, so the total excludes them; re-run the check tomorrow or price them by hand." Plain words, no alarm.
- Warnings are always shown, in the reply and in the files. A warning that changes the decision goes in the first line.
- **Name the shortcoming**: say what falls short and how (consistency, interaction, speed, resilience, mana, card flow; too slow, off-plan, redundant, fragile). "Weak" names nothing; use the specific word.

## Words, labels and numbers
- **Plain labels** wherever a player reads: "Pass with warnings", not `pass_with_warnings`; "needs a decision", not `needs_review`; "the printing check", not `chk-printing-2`. Enums, IDs and snake_case belong in the JSON files.
  - Audit verdicts: Pass · Pass with warnings · Fail · Incomplete. Check results: Pass · Warning · Fail · Unverified.
  - Evidence: Verified fact · Calculated · Popularity data · Community opinion · Claude's judgment · Unresolved.
  - Theme status: On theme · Exception · Off theme · Not checked.
- **Units and context** on every number: "$498 (Scryfall, 2026-11-04)", "8 ramp sources (typical: 10 to 12)", "in 312 of 1,040 EDHREC decks".
- **Define a term on first use**, in a clause: bracket (Wizards' 1 to 5 power scale), Game Changer, Rule 0, mana value, color identity, two-card combo.
- Card names exactly as Scryfall prints them.
- Headings and finding titles state the finding ("Ramp is light: 8 sources vs 10 to 12 typical"); navigation labels stay short nouns.

## Missing or empty data
Say what's missing, why, and what to do: "No EDHREC data for Azula (the tool returned none); popularity rests on 6 decklists instead." Missing isn't zero: write "unknown" or "—" with the reason, never 0 or a bare "N/A". A check that couldn't run is unverified, with the reason.

## Facts, citations and money
- **Card facts** (text, legality, color identity, Game Changer status, printings, art) come only from Scryfall. The authority for every other kind of claim: research's [sources.md](../skills/research/references/sources.md), "Authority per question".
- **In files**, cite IDs in brackets: "[fnd-004, src-012]". In research.json, where in a source a claim is supported goes in the finding's `locators`, never inside the claim text ([schemas/README.md](../schemas/README.md), "Findings and checks").
- **To the player**, name the source as they know it plus the moment: "EDHRECast, 8:00–9:20". Add the ID in brackets when they may want to look it up. Each citation points to the moment that supports that claim.
- **Money**: ask about it once; give the price once, at hand-back, in the player's money style with source and date; raise it again only when a set budget is now broken.

## Recommending directions
When the player is choosing a commander or approach, offer 2 to 4 directions. Lead with the one recommended for this player and why, then give each direction in the same layout:
- **Name**: what it does, in a sentence.
- **Feels like**: how games play (fast and aggressive, grindy value, combo, big turns).
- **Theme fit**: how much of the deck can be on theme in its colors (when there's a theme).
- **Strengths** and **shortcomings**: mechanical, with evidence refs.
- **Cost**: only when money matters to the player.
End with the question; the player can pick another or ask for different ones.

## Audit status
Give the label, the counts, the version checked and how it was checked: "Pass with warnings for v5 (0 fails, 0 unverified, 5 warnings), checked by an independent auditor that saw only the files." A deck the player brought is "checked in this conversation". An out-of-date audit says so: "The audit is for v4; the deck is v5, so v5 isn't verified." Report the verdict exactly as the audit wrote it; required fixes reach the player as proposals.

## Agent handoffs
A subagent's reply carries only what the lead needs to decide; the full evidence stays in the file it wrote. It names the file and its status (complete; partial, with what's missing; failed, with why), the tools that failed and the fallback used, the findings or problems that change the lead's decision (with IDs), and open questions. File contents, transcripts and card JSON stay in the files.

## Where these rules give way
- **Requested full explanations** (rules interactions, primers, "explain why"): full prose with structure.
- **Legality and accuracy caveats, uncertainty and source disagreements**: stated in full and visibly; never compressed into a confident one-liner or tucked away when they change the conclusion.
- **Quotes and citations**: attribution and timestamps stay intact.
- **Destructive or irreversible confirmations** (deleting a project, overwriting a saved setting): name exactly what will happen, whatever it takes in words.
- **Reference data** (decklists, source lists, check lists): complete; grouped or sorted, never cut.
- **Genuinely ambiguous requests**: ask the clarifying question first.
