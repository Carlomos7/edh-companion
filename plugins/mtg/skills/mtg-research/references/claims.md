# Claim ledger

One JSON object per line in `claims.jsonl`. Every opinion or external fact that will reach the user gets a line. Facts computed by `mtgdb.py` don't need one.

```json
{"id": "vader-001", "subject": "darth-vader", "type": "must-play",
 "claim": "Phyrexian Arena is a core draw engine in this deck",
 "cards": ["Phyrexian Arena"],
 "sources": [
   {"url": "https://www.youtube.com/watch?v=...", "kind": "video", "author": "Channel name", "date": "2026-07-12", "locator": "14:05"},
   {"url": "https://edhrec.com/commanders/...", "kind": "edhrec", "date": "2026-11-03", "locator": "Top Cards"}],
 "n": null, "confidence": "high", "status": "unverified", "verifier_note": ""}
```

## Types
`must-play`, `trap`, `combo`, `rules` (cite rule numbers in `locator`), `plan`, `stat` (needs `n`), `cedh`, `printing-theme`, `ban-or-gc`, `price`, `community`, `other`.
High impact (always verified): must-play, trap, combo, rules, cedh, printing-theme, ban-or-gc.

## Rules (enforced by `audit-claims`)
- Every source has `url` and `date`; videos also a `locator` timestamp.
- must-play / trap / combo: 2 independent sources (different `author`, or different site).
- `stat` claims carry `n` (sample size).
- Every name in `cards` resolves in the index.
- `--since <date>`: high-impact sources older than the cutoff are flagged.
- `--require-verified`: high-impact claims must have `status: verified`.

## Confidence
- **high**: 2+ independent current sources agree, or data from the authority for that question.
- **medium**: one strong source, or sources agree but are dated.
- **low**: single opinion, small sample (n < 50), or conflicting sources. Say so to the user.

## Verification statuses
`unverified` → set by the author. `verified` / `refuted` / `unverifiable` → set only by a verifier who re-opened the source, with `verifier_note` saying what they checked.
