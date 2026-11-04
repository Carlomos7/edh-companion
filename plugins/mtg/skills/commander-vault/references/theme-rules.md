# Theme rules (vault runs)

The general rules live in `commander-deckbuilding/references/themes.md`: modes, spec format, edge cases, and above all "The player's theme is the goal" (no re-arguing the theme, no off-theme suggestions unless asked). Read that first and put that section in every brief. Vault specifics:

- Intake asks the themes.md question once for the whole vault. A vault can be `mode: none` (best decks for a set of commanders); pills, counts and theme filters are then left off the page.
- The lead writes `vault/theme-spec.json` and runs `mtgdb.py theme-build vault/theme-spec.json --out vault/themed-printings.json`. Never hand-map set codes.
- G0 checks the map both ways (contact sheet for false positives, searches for gaps) and runs `theme-pool` per commander when mode is strict. Report any commander where strict isn't realistic before building.
- Deckbuilders write off-theme reasons to `vault/<slug>/off-theme.json` (`{"Card": "reason"}`); the hook and validate read it.
- Disputes: an agent that thinks a tag is wrong logs a `printing-theme` claim with the image URL; the verifier checks the art; the lead edits the spec's include/exclude and rebuilds the map.
