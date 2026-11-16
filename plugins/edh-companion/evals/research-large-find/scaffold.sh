#!/usr/bin/env bash
set -euo pipefail
bash "$(dirname "${BASH_SOURCE[0]}")/workspace.sh" none
P=EDHCompanion/projects/spider-gwen
{
  printf '{"schema_version":"1.0","project":"spider-gwen","version":3,"created":"2026-11-10","scope":{"question":"Spider-Gwen aggro","depth":"deep"},\n'
  printf '"methodology":{"approach":"EDHREC, decklists, creators, Reddit"},\n"sources":[\n'
  for i in $(seq 1 300); do printf '{"id":"src-%03d","title":"Source %d about Spider-Gwen aggro, filler text for size","url":"https://example.com/s/%d","type":"article"},\n' $i $i $i; done
  printf '{"id":"src-301","title":"Gwen deck tech","url":"https://example.com/gwen","type":"video","author":"Spider Lab"}],\n"findings":[\n'
  for i in $(seq 1 600); do printf '{"id":"fnd-%03d","claim":"Filler finding %d: aggro decks like cheap creatures and haste; this sentence pads the file so reading it whole is expensive.","class":"community_opinion","confidence":"medium","evidence":["src-%03d"],"cards":["Goblin Guide"]},\n' $i $i $(( (i % 300) + 1 )); done
  printf '{"id":"fnd-601","headline":"Lightning Bolt is cut in most Gwen lists for Galvanic Discharge","claim":"Spider Lab cuts Lightning Bolt for Galvanic Discharge because the deck wants to hit 3-toughness blockers.","class":"community_opinion","confidence":"medium","evidence":["src-301"],"cards":["Lightning Bolt","Galvanic Discharge"]}],\n'
  printf '"gaps":[],"recommendations":[]}\n'
} > "$P/research.json"
