# Intake: finding out what the player wants

Ask with AskUserQuestion: 2 to 4 options per question, the recommended or most common first, and "Other" is always available. Ask 1 to 3 questions per round, in this order, and skip what you already know. Explain in one line why a question matters only when the answer changes the build a lot.

Why this order: players start from very different places (a commander, colors, a favorite card or character), bracket and hard lines rule cards in or out, and what they find fun decides which of many legal decks is theirs. Budget comes after the plan so the plan isn't shaped by price before the player has said what they want.

## Fast path first (don't slow people down)
As soon as you know the starting point (question 1, or what they typed), offer the recommended setup in one question before any other round:

"Want me to just run with my recommended setup?"
- **"Yeah, use your defaults" (Recommended):** list them in the option's description, one line: bracket 3 · no infinite combos, extra turns or land destruction · best cards, normal copies, price at the end · medium interaction · plays to the commander's strengths · cards you own when close (only if they have a collection) · no theme
- **"Defaults, but let me set money":** ask only question 7, then go
- **"Let me pick everything":** run rounds 1 to 3 below

When they take the defaults, ask nothing else up front: go straight to the skeleton (the skeleton's "Is this the deck you want?" is their chance to steer). Pet cards are optional: one line, "Any cards you definitely want in? (or just say go)". Write the defaults into `deck-brief.md` as their answers.

For a pasted deck, the defaults come from the deck itself: its current bracket, its current spend level, any theme its printings show.

## Round 1: starting point and table
1. **Starting point.** A commander they named · colors or a mechanic · a favorite card or character · an existing deck or precon to upgrade · "surprise me".
2. **Bracket.** Show each with its intent:
   - B1 Exhibition: theme first, games go 9+ turns
   - B2 Core: precon level, no Game Changers, 8+ turns
   - B3 Upgraded: up to 3 Game Changers, no early combos, 6+ turns
   - B4 Optimized: anything legal, fast and strong
   - B5 cEDH: tournament-level
   - "Not sure, I'll describe my table"
3. **Hard lines** (multi-select; defaults come from the bracket, the player can override): infinite combos · extra turns · mass land denial · stax/tax effects · Game Changers.

## Round 2: what makes it fun
4. **Fun profile** (pick up to two): big splashy turns · clever engines or combos · winning efficiently · theme and flavor · making an unusual commander work.
5. **Win style:** combat · combo · drain or burn · alternate win · "whatever fits the commander".
6. **Interaction appetite:** light (mostly do my thing) · medium · heavy (lots of removal and counterspells).

## Round 3: money and cards
7. **Money: one question, asked once, in a casual voice.** Ask something like "How do you wanna do cards?" with:
   - **"Just build it, I'll see the price at the end" (Recommended):** the best card for each slot, normal copies
   - **"Keep it cheap":** cheapest copies, and cheaper cards that do the same job where it matters
   - **"I've got a budget":** then ask once, "Cool, about how much for the whole deck?"
   - **"Wanna drip out your cards?":** foils, borderless, showcase, Secret Lair. Then ask once, "How much are you down to spend on a single card?" (e.g. "nothing over $30")

   Keep this tone for the follow-ups too ("Want me to drip out the commander too?" is fine). Don't ask about proxies unless they bring it up. Don't ask about money again later.
8. **Collection** (only if `mtg_collection` `show` finds one): "Use cards you own when they're close in quality (Recommended)" · owned cards only where possible · ignore it. If they have none, don't ask; the hand-back can suggest importing one.
9. **Pet cards and never-plays** (free text): must-includes, and cards or effects they won't play.

## Ask only when relevant
- **Theme or flavor:** only if they mention one or picked "theme and flavor" above. Then follow themes.md.
- **Complexity:** if the commander makes a lot of triggers or long turns, ask whether that's fun or tiring for them.
- **Popular or original:** if they say they're tired of seeing the same cards, prefer lower-inclusion picks and say so.

## Defaults (the fast path, or whenever the player says "you pick")
| Question | Default |
|---|---|
| Bracket | 3 (for a pasted deck: the bracket it plays at now) |
| Hard lines | what the bracket rules out; at 3: no early infinite combos, no chained extra turns, no land destruction |
| Fun and win style | whatever the commander does best |
| Interaction | medium |
| Money | best cards, normal copies, price shown at the end |
| Collection | use cards they own when close in quality, if they have a collection |
| Theme | none (for a pasted deck: keep the theme its printings show) |
| Proxies | not used |

Say which defaults you used in one line, so they can change any of them.

## deck-brief.md
Write it after intake; update it whenever the player changes their mind.

```markdown
# Deck brief: <commander>
- Starting point: <commander / colors / card / upgrade of ...>
- Bracket: B<n> (<hard lines allowed or excluded>)
- Fun: <profile>; win style: <style>; interaction: <light/medium/heavy>
- Money: <no limit / keep it cheap / budget $X / drippy, max $Y per card>
- Collection: <prefer owned / owned only / ignored / none>
- Must include: <cards>
- Never: <cards or effects>
- Theme: <none / spec>
- Data as of: cards <date>, rules <effective date>
- Decisions so far: <short log of choices the player made>
```
