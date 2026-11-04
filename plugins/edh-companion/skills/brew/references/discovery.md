# Guided discovery

The player often starts with a feeling ("I want an Avatar deck"), not a spec. Help them find what they want and what's possible, then let them choose on purpose.

## 1. Explore first
Before asking anything that benefits from context, look: candidate commanders for the idea (Scryfall, EDHREC), the theme's card pool in each color identity, what real decks with those commanders do, and what players say about them. Reuse research.json; call research for anything big.

Only recommend commanders that are verified legal: eligible as a commander and not banned, and for two commanders, a real pairing (see the audit skill's checks.md, "Commander eligibility"). `deck_check.py --commander "A" [--commander "B"]` checks this without a deck.

## 2. Recommend directions
Show 2 to 4 options, the recommended one first with why, each in the shared directions layout (name, feels like, theme fit, strengths and shortcomings with evidence refs, cost when money matters): [writing.md](../../../references/writing.md), "Recommending directions". They can pick another or ask for different ones.

## 3. Ask what matters, one question at a time
Ask at natural decision points, only when the answer changes the deck. Typical order, skipping what's known:
1. Which direction (the options above).
2. **Theme strictness** (if there's a theme): strict / prefer with a few exceptions / themed printings only / none. And whether artwork matters.
3. **Power**: bracket (explain it: Wizards' 1 to 5 scale; 3 is a typical upgraded deck).
4. **Budget**, asked once ([writing.md](../../../references/writing.md), "Facts, citations and money"): "Just build it, see the price at the end (Recommended)" · keep it cheap · a set budget (hard limit or rough target?) · drippy (fancy printings, per-card max) · no expense spared (the ultimate blinged-out deck). Details: money-looks-export.md.
5. Playstyle details only if the direction leaves them open (interaction level, win style).
Multiple choice, recommended first with its reason. For low-impact gaps, state a provisional assumption ("assuming medium interaction; say if not") and move on. Record answers in PROJECT.md.

## 4. Check feasibility before committing
Before committing to a direction, check that the restrictions allow a legal, functional deck: eligible commanders, the eligible pool per color identity and role, and what's confirmed vs estimated. research gathers the evidence (`research.json.feasibility`); the method and what to do when it's constrained or infeasible are in [themes.md](themes.md). Don't call a strict theme impossible without counting, and don't promise a bracket without evidence.

## 5. Explain trade-offs and offer informed choices
If a restriction costs power, consistency, interaction or card access, say what it costs in concrete terms ("strict Avatar has 6 removal spells in these colors; a typical deck runs 8 to 12"). Offer practical paths, recommended first, e.g.:
- **Strict Avatar** (every card on theme; accept lighter removal)
- **Avatar-inspired** (on theme where possible, up to N approved off-theme staples)
- **Widen the pool** (other Avatar products, flavor-matching art)
Respect a flavor-first player: power is one option, never the default pressure.

## 6. Preserve intent
Never relax a restriction silently. Approved exceptions go in PROJECT.md (Theme → Allowed exceptions) and DECISIONS.md, and hold for every later revision. A conflicting new request becomes a question.

## 7. Evaluate the result
After the build: what the deck does well, its remaining shortcomings and compromises (named honestly), and possible improvements that stay inside their rules, plus any that would need a new exception (offered, not pushed).
