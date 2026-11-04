---
name: build
description: Start a new Commander deck with Claude: it asks what you like, shows a plan, then builds it with you.
argument-hint: "[commander, colors or idea]"
disable-model-invocation: true
---

Help the player build a new Commander deck. Load the `commander-deckbuilding` skill and follow it from the start (Intake). Starting point from the player: $ARGUMENTS (if empty, the first intake question asks for it).
