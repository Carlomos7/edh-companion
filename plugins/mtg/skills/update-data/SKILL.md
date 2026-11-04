---
name: update-data
description: See how current the card data and rules are, and refresh them (about a minute).
disable-model-invocation: true
---

Call `mtg_data_status` with check_remote true and show one short line per source in plain words ("Cards, bans and prices: today", "Rules: effective Sep 25, 2026"). The player asked for this, so refresh anything stale or missing right away with `mtg_data_sync` (no question) and confirm what changed. If everything is current, say so. Vendor prices (Card Kingdom, Cardmarket, buylists) are optional and about 300 MB: offer them in one line, don't sync them unasked.
