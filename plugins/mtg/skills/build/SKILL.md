---
name: build
description: Start a new Commander deck with Claude: it asks what you like, shows a plan, then builds it with you.
argument-hint: "[commander, colors or idea]"
disable-model-invocation: true
---

Help the player build a new Commander deck. Load the `commander-deckbuilding` skill and follow it from step 1. Starting point from the player: $ARGUMENTS (if empty, step 2's first question asks for it).
