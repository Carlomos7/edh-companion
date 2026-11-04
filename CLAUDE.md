# Developing edh-companion

This repo is a Claude Code plugin marketplace with one plugin, `plugins/edh-companion/`. Only that folder ships to players; `docs/`, `tests/` and `examples/` stay in the repo.

- Skills: `plugins/edh-companion/skills/<name>/SKILL.md` (research, brew, audit, present, setup). Keep each SKILL.md short; details go in its `references/`, one level deep. Descriptions say what the skill does, when to use it and when not to.
- Shared contract: `plugins/edh-companion/schemas/README.md` (project files) and the JSON schemas next to it. Change them together with `scripts/companion.py` and the tests.
- Don't hardcode MCP tool names in skills; describe the capability and a fallback (see `skills/research/references/sources.md`).
- No new MCP servers, databases or services without a demonstrated need. Scripts are for deterministic work only.
- Player data never goes in the repo (`EDHCompanion/`, `reports/` are git-ignored). The repo is public: no personal paths, names or keys.

## Test
```bash
uv run --python 3.12 --with certifi --with jsonschema --with pyyaml --with pillow --with playwright python -m unittest discover -s tests/unit
claude plugin validate --strict ./plugins/edh-companion
cd plugins/edh-companion && claude plugin eval . --scaffold --mocks off --ablation none --runs 1 --tag activation   # costs real usage
```
Evals can't grant Bash in the Windows sandbox, so script behaviour is covered by the unit tests.

## Release
Bump `version` in `plugins/edh-companion/.claude-plugin/plugin.json` and add a CHANGELOG entry in the same commit. Never add AI attribution lines to commits or PRs.
