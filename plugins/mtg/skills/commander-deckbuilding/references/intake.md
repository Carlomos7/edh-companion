# Intake: finding out what the player wants

Ask with AskUserQuestion: 2 to 4 options per question, the recommended or most common first, and "Other" is always available. Ask 1 to 3 questions per round, in this order, and skip what you already know. Explain in one line why a question matters only when the answer changes the build a lot.

Why this order: players start from very different places (a commander, colors, a favorite card or character), bracket and hard lines rule cards in or out, and what they find fun decides which of many legal decks is theirs. Budget comes after the plan so the plan isn't shaped by price before the player has said what they want.

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
7. **Budget.** Total: under $100 · $100 to $250 · $250 to $500 · no limit. Ask whether proxies are fine at their table only if they bring it up.
8. **Price style** (decides which copies are suggested and priced):
   - **Budget:** cheapest legal copy of every card; offer cheaper alternatives for expensive slots
   - **Balanced:** normal copies; offer alternatives only for the priciest cards
   - **Bling:** foils, borderless, showcase, Secret Lair. Then ask their per-card ceiling (e.g. "nothing over $30 a copy")
9. **Collection.** If `mtg_collection` `show` finds one, ask: prefer cards I own · owned cards only where possible · ignore it. If they have none and owning matters, offer to import one (the `collection` skill explains how to export from Moxfield, Archidekt or ManaBox).
10. **Pet cards and never-plays** (free text): must-includes, and cards or effects they won't play.

## Ask only when relevant
- **Theme or flavor:** only if they mention one or picked "theme and flavor" above. Then follow themes.md.
- **Complexity:** if the commander makes a lot of triggers or long turns, ask whether that's fun or tiring for them.
- **Popular or original:** if they say they're tired of seeing the same cards, prefer lower-inclusion picks and say so.

## Defaults when the player says "you pick"
B3, interaction medium, balanced price style, no total cap but tell them the price, no theme, no proxies. Say which defaults you used in one line.

## deck-brief.md
Write it after intake; update it whenever the player changes their mind.

```markdown
# Deck brief: <commander>
- Starting point: <commander / colors / card / upgrade of ...>
- Bracket: B<n> (<hard lines allowed or excluded>)
- Fun: <profile>; win style: <style>; interaction: <light/medium/heavy>
- Budget: <total>; price style: <budget/balanced/bling> (<per-card ceiling>)
- Collection: <prefer owned / owned only / ignored / none>
- Must include: <cards>
- Never: <cards or effects>
- Theme: <none / spec>
- Data as of: cards <date>, rules <effective date>
- Decisions so far: <short log of choices the player made>
```
