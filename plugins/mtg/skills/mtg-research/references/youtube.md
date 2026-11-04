# Video research protocol

## Picking videos
- Search for "<commander> deck tech", "<commander> upgrade", "<commander> cEDH". Prefer the last 12 months, and anything after the latest bans/Game Changers update.
- Prefer creators who show a decklist link (Moxfield/Archidekt) and explain choices. Note the channel; one creator's three videos count as one source.
- Flag sponsored or precon-promo videos; they can support, not decide.
- Rough channel fit: The Command Zone and EDHRECast for template and staples; budget channels for budget builds; cEDH creators (e.g. Play to Win, cEDH-focused channels) only for B5. Rank channels by what you actually find, not by this list.

## Pulling transcripts
- **One video at a time**, never in parallel (parallel fetches get rate limited).
- **Transcript tool blocked** ("YouTube is blocking requests from your IP", common on some networks): fetch the video URL with a web fetch tool instead (`parallel-search` `web_fetch`, or WebFetch) and ask for the transcript; it usually returns it with timestamps. `get_video_info` still works for title, channel, date and the decklist link.
- Still nothing? Use the video's linked decklist and description, and cite the video as "watch" only, without quoting it.
- If the video links a decklist, pull it (`moxfield_decklist`) and treat it as the primary artifact; the transcript explains it.

## Extracting
- Pull out: plan (how the deck wins), must-plays with reasons, traps (cards the creator says underperform), combos, mulligan or play notes.
- Record a timestamp (mm:ss) for every claim.
- Collect every card name mentioned, then check them all against Scryfall:
  - Exact match: use that name.
  - Close or ambiguous match: pick from candidates using context (colors, what the card does), and note it.
  - No match: drop it, or find the real card from the linked decklist. Never write an unresolved name into a deck or claim.
- Check every card the creator recommends on Scryfall: still legal, in color identity, and its Game Changer status (the video may predate a change).

## What creators can't establish alone
Combos (confirm in Spellbook), bracket (confirm with rules + Spellbook), prices (Scryfall), legality (Scryfall), cEDH viability (EDHTop16 / cEDH DB).
