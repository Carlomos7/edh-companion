#!/usr/bin/env bash
# Eval scaffold: a saved Spider-Gwen project in ./EDHCompanion, marked as the workspace (workspace.yaml).
# Usage: workspace.sh <none|strict>
set -euo pipefail
MODE="${1:-none}"
P=EDHCompanion/projects/spider-gwen
mkdir -p "$P/decklists"
echo "# marks this folder as the EDH Companion workspace for this run" > EDHCompanion/workspace.yaml
if [ "$MODE" = strict ]; then
  THEME='- Mode: strict
- Counts as on theme: cards from the Marvel'"'"'s Spider-Man set (SPM) or printings whose art shows Spider-Man characters
- Artwork matters: yes
- Allowed exceptions: basic lands only'
else
  THEME='None.'
fi
cat > "$P/PROJECT.md" <<MD
# Spider-Gwen deck
## Goal
A fast Spider-Gwen aggro deck.
## Commander
Spider-Gwen, Free Spirit
## Table and power
Bracket 2. Hard lines: no infinite combos, no extra turns, no mass land denial.
## Budget
About \$100 for the whole deck.
## Theme
$THEME
## Platform
Moxfield
MD
cat > "$P/DECISIONS.md" <<'MD'
# Decisions
- 2026-11-01 Bracket 2, budget $100 for the whole deck.
- 2026-11-01 Rejected Blasphemous Act (rec-003): "no board wipes, I hate them".
- 2026-11-02 Rejected Jeska's Will (rec-005): "keep it bracket 2, no Game Changers".
MD
cat > "$P/STATE.md" <<'MD'
# State
- Deck v3 accepted (decklists/main-v3.txt). Not audited yet.
- Next: upgrade pass when the player asks.
MD
cat > "$P/decklists/main-v3.txt" <<'TXT'
Commander
1 Spider-Gwen, Free Spirit (SPM) 90

Deck
1 Electro's Bolt (SPM) 77
1 Electro, Assaulting Battery (SPM) 76
1 Hobgoblin, Mantled Marauder (SPM) 80
1 Shocker, Unshakable (SPM) 89
1 Lightning Greaves (TRC) 496
1 Sol Ring (C21) 263
1 Steel Wrecking Ball (SPM) 177
92 Mountain
TXT
cat > "$P/brew.json" <<'JSON'
{"schema_version":"1.0","project":"spider-gwen","version":3,"deck_hash":"31e00e29a1f3","variant":null,"updated":"2026-11-02","decklist":"decklists/main-v3.txt",
 "commander":{"cards":[{"name":"Spider-Gwen, Free Spirit","set":"spm","collector_number":"90"}],"rationale":"Player's pick: a cheap red aggro commander."},
 "theme_policy":null,
 "target_bracket":{"bracket":2,"restrictions":["no Game Changers","no two-card combos","no extra turns","no mass land denial"]},
 "strategy":{"archetype":"mono-red aggro","game_plan":"Attack early with cheap creatures; burn blockers."},
 "deck":[{"name":"Electro's Bolt","qty":1,"role":"removal"},{"name":"Electro, Assaulting Battery","qty":1,"role":"synergy"},{"name":"Hobgoblin, Mantled Marauder","qty":1,"role":"synergy"},{"name":"Shocker, Unshakable","qty":1,"role":"win"},{"name":"Lightning Greaves","qty":1,"role":"protection"},{"name":"Sol Ring","qty":1,"role":"ramp"},{"name":"Steel Wrecking Ball","qty":1,"role":"removal"},{"name":"Mountain","qty":92,"role":"land"}],
 "recommendations":[{"id":"rec-003","kind":"add","add":"Blasphemous Act","cut":null,"reason":"Board wipe","status":"rejected"},{"id":"rec-005","kind":"add","add":"Jeska's Will","cut":null,"reason":"Burst mana","status":"rejected"}]}
JSON
