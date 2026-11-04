"""Shared deterministic data core for edh-companion scripts (stdlib + certifi).

  http      one HTTP client: retries by failure class, cross-process pacing, per-endpoint circuit breaker
  cache     disposable SQLite cache (cards, searches, combos) + shared pacing/breaker state
  policy    which providers the player excluded (config + project), offline mode
  scryfall  cached, batched Scryfall access with freshness rules per data category
  spellbook cached Commander Spellbook combo lookup
  cards     one normalized card record and the small card helpers every script needs
  decklist  decklist parsing (text and brew.json) and deck hashes

Scripts import it with sys.path pointing at plugins/edh-companion/scripts. Nothing here talks to Claude or MCPs.
"""
