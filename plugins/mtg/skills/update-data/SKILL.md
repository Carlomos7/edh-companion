---
name: update-data
description: See how current the card data and rules are, and refresh them (about a minute).
disable-model-invocation: true
---

Call `mtg_data_status` with check_remote true. Show the player one short line per source in plain words ("Cards, bans and prices: today", "Rules: effective Sep 25, 2026"). If anything is out of date or missing, ask once whether to refresh, then run `mtg_data_sync` and confirm what changed.
