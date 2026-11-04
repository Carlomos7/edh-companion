---
name: present
description: Turns Commander research, deck builds and audit results from a project into a polished interactive page using the plugin's existing deck-browser template (card images and enlarged viewer, deck and variant comparisons, mana curves and charts, filters and sorting, swaps, theme and audit status, clickable sources with video timestamps, Moxfield export), then tests it in a browser. Use when the player asks for a visual, interactive or shareable report, deck browser, gallery, comparison page, dashboard or charts, or wants an existing page changed. Not for conversational answers, plain decklists, short explanations or Markdown summaries, and never automatically just because research or a build finished.
---

# Present

Pages show the project's data as it is: no number, citation or verification status appears unless a project file says so. The established deck-browser template gives every page the same look and working features; reuse it rather than designing a new one.

## When to use
- **Use:** "show these decks in an interactive comparison", "make a page for my Spider-Man deck", "something I can share", "add the bracket 4 version to the page".
- **Don't use:** a question, a decklist, a chat summary. After a build, *offer* a page in one line; build it on a yes.
- **Depends on** project files from research, brew and audit; it never creates or upgrades them. A deck without a current audit shows "not audited" or "audit out of date"; offer an audit, never fake one.
- **Needs approval:** publishing (the Artifact tool makes a private link; say so), and a large page nobody asked for (a simple request gets a simple page).

## Three modes (offer when a report would help; recommend one)
| Mode | What it is | Good for |
|---|---|---|
| **Deck Summary** (`--mode summary`) | clean Markdown report: plan, Rule 0 line, stats, list, audit state, sources. Export to Word or PDF with the installed `docx`/`pdf` skills (or pandoc) if they want a file to share | reading, printing, sending |
| **Interactive Report** (`--mode interactive`) | the template without the heavy extras: card images, decklists, filters, comparisons, prices, essential charts | everyday browsing, phones |
| **Showcase** (`--mode showcase`, default) | the full template: 3D card viewer, card fan, animations, every chart and tab | sharing and showing off |
Reports work at any stage: research only (commanders compared, theme rankings tabs), one deck, several builds, or several projects. Changing a page means rebuilding from the project files with the same flags; never hand-edit generated HTML.

## Several decks and projects
- Builds group into tabs by brew.json `group` (e.g. Heroes / Villains), with a commander picker and bracket/variant switches inside.
- Before making a new report, check `<workspace>/showcases/` for one that fits; offer to add the deck there (tab, variant or group) rather than a standalone page. With the player's yes, save the grouping in showcase.yaml and reuse it next time without asking. Keep unrelated projects apart unless asked. Format: [schemas/README.md](../../schemas/README.md), "Showcases".
- Colors follow each commander's color identity automatically; a theme the player asks for (e.g. Spider-Man comic, Doom gothic) is saved in report-theme.yaml or showcase.yaml only if they want it kept ("Report themes").

## Workflow (template page)
```
- [ ] 1. Read the project: brew*.json, audit*.json, research.json, PROJECT.md, DECISIONS.md; note stale audits
- [ ] 2. Validate (companion.py validate); fix or report problems first
- [ ] 3. Build the site data and render the template into reports/
- [ ] 4. Test in a real browser (phone and desktop) and run an accessibility scan
- [ ] 5. Finish reports/presentation-checks.md; deliver
```
1. **Read.** Project files: [schemas/README.md](../../schemas/README.md). For a showcase, read showcase.yaml and each listed project.
2. **Validate.** `uv run --script "${CLAUDE_PLUGIN_ROOT}/scripts/companion.py" validate <project>`. The builder refuses invalid inputs.
3. **Build.** Commands, flags, styles (fancy / basic / custom), image modes and what each section needs: [references/pages.md](references/pages.md). Design and the data-to-section mapping: [references/page-spec.md](references/page-spec.md) (read when changing the template). Card data and images come from deck_check.py and Scryfall through the scripts, never typed.
4. **Test.** Serve `reports/` over http and check it at about 390 px and 1440 px: no console errors, no sideways scroll, cards open, variants switch, filters work, sources open; then an axe-core scan. Use the installed `webapp-testing` skill (Playwright) when available, else `chrome-browser` or a Playwright script; with no browser available, say the page is untested.
   Where the data has them, include: alternatives with their trade-offs (grouped as within budget / worth stretching for / best regardless of budget, gameplay vs printing upgrades kept apart), printing details (set, finish, treatment) and dated prices (labelled estimate when not verified), theme status and known limitations, and the export files from brew (`decklists/export/`) as supporting files linked from the page or listed in the reply.
5. **Record and deliver.** `reports/presentation-checks.md`: inputs (file, version, hash, audit state), sections shown or hidden and why, test results, open issues, what wasn't tested. Deliver per pages.md: publish with the Artifact tool (page plus image atlases as supporting files) when available, else give the folder path.

## Design rules
- Reuse the template's tokens, type, card viewer, chips, charts and legends. For a simple page or a template change, load `frontend-design` or `artifact-design` if installed; `web-artifacts-builder` only for an app-like request the template can't serve.
- MTG conventions: WUBRG order and mana symbols, card names linking to Scryfall, the standard card ratio, Game Changer and bracket labels as Wizards names them.
- Accessible: WCAG 2.2 AA contrast, keyboard navigation, 24 px+ targets, never meaning by color alone, reduced motion respected.
- Missing data hides its section (with a short "not available" note where a reader would expect it); never placeholders or estimates.

## Template changes
Edit `assets/template.html` only for something every page needs, keep existing behaviour working, and re-run `tests/unit/test_present.py` plus the browser check on the fixture project.
