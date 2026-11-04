# Claude Code plugin standards (late 2026)

Research into official, standard practice for building a Claude Code plugin, to guide the redesign of the `mtg` plugin.

- Date accessed for every source: 2026-11-03.
- Primary sources are Anthropic docs (code.claude.com, platform.claude.com, claude.com/docs), Anthropic GitHub repos, and the Agent Skills spec (agentskills.io). Community sources are marked as such.
- Anything not confirmed from a primary source is marked **unconfirmed** or **inference**.

## 1. Recommended plugin layout

### Standard layout

The manifest is `.claude-plugin/plugin.json` and is the only file that goes inside `.claude-plugin/`. Everything else sits at the plugin root. Source: https://code.claude.com/docs/en/plugins (common-mistake note).

Default locations, each optional (source: https://code.claude.com/docs/en/plugins-reference, "Standard layout"):

| Component | Default location | Notes |
|---|---|---|
| Manifest | `.claude-plugin/plugin.json` | Only `name` is required |
| Skills | `skills/<name>/SKILL.md` | Preferred over `commands/` for new plugins |
| Commands | `commands/*.md` | Legacy; "Prefer `skills/` for new plugins" |
| Agents | `agents/*.md` | |
| Hooks | `hooks/hooks.json` | |
| MCP servers | `.mcp.json` | |
| LSP servers | `.lsp.json` | |
| Executables | `bin/` | Put on the Bash tool's `PATH` while enabled |
| Settings | `settings.json` | Only `agent` and `subagentStatusLine` take effect |
| Others | `output-styles/`, `workflows/`, `themes/`, `monitors/monitors.json` | |

`scripts/` at the plugin root is a convention, not a component: hooks point at files there by `${CLAUDE_PLUGIN_ROOT}/scripts/...`. Source: https://code.claude.com/docs/en/plugins/components.md

A `CLAUDE.md` at the plugin root is not loaded; instructions must be written as skills, and `claude plugin validate` warns about it. Source: https://code.claude.com/docs/en/plugins/components.md

### Path variables and persistent data

Source: https://code.claude.com/docs/en/plugins-reference ("Environment variables") and https://code.claude.com/docs/en/plugins/components.md ("Reference plugin paths and store data").

- `${CLAUDE_PLUGIN_ROOT}`: the installed version's directory. Each version gets its own cache directory, so the path changes on update. The docs say "Don't write state there".
- `${CLAUDE_PLUGIN_DATA}`: `~/.claude/plugins/data/<id>/`, created on first reference and kept across plugin updates. Intended for dependencies (`node_modules`, virtual environments), generated code and caches.
- `${CLAUDE_PROJECT_DIR}`: the project root.
- In skill content, `${CLAUDE_PLUGIN_ROOT}` is "substituted only in plugin skills. Use this to reference scripts or files bundled anywhere in the plugin, including resources shared between the plugin's skills." Source: https://code.claude.com/docs/en/skills ("Available string substitutions").
- `${CLAUDE_SKILL_DIR}` is the skill's own directory. Source: same page.
- Hook processes receive `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_PROJECT_DIR` and `CLAUDE_PLUGIN_OPTION_<KEY>`. MCP stdio servers receive `CLAUDE_PLUGIN_ROOT` and `CLAUDE_PLUGIN_DATA`. Source: plugins-reference, "Where each variable resolves".
- The documented pattern for installing dependencies is a `SessionStart` hook that installs into `${CLAUDE_PLUGIN_DATA}` only when the manifest file changed. Source: https://code.claude.com/docs/en/plugins/components.md ("Install dependencies into the data directory").
- Anthropic's own `project-artifact` plugin keeps per-project state in `${CLAUDE_PLUGIN_DATA}/artifacts/<slug>/`. Source: https://github.com/anthropics/claude-plugins-official/blob/main/plugins/project-artifact/skills/project-artifact/SKILL.md

### Bundling an MCP server

- Declare servers in `.mcp.json` at the plugin root, or via the `mcpServers` manifest key (a path, an inline map, or a `.mcpb` bundle path or URL). Source: plugins-reference, "`mcpServers`".
- Example inline stdio server: `{ "command": "node", "args": ["${CLAUDE_PLUGIN_ROOT}/server.js"] }`. Source: same.
- A plugin server appears in `/mcp` as `plugin:<plugin>:<server>`, and its tools are named `mcp__plugin_<plugin>_<server>__<tool>`. Source: https://code.claude.com/docs/en/plugins/components.md
- Do not put API keys or secrets in `.mcp.json`, because every installer receives the file. Source: https://claude.com/docs/plugins/build
- `claude plugin validate` reports MCP entries that would be dropped at load as errors (v2.1.281+). Source: components.md.

### userConfig

Source: https://code.claude.com/docs/en/plugins-reference ("User configuration").

- `userConfig` declares values Claude Code prompts for when the plugin is enabled, "so users don't edit `settings.json` themselves".
- Field types: `string`, `number`, `boolean`, `directory`, `file`. Options include `required`, `default`, `options`, `multiple`, `sensitive` and `min`/`max`.
- `sensitive: true` masks input and stores the value in the OS credential store.
- Values are referenced as `${user_config.KEY}` in MCP and LSP config, exec-form hook `args`, and skill and agent content (non-sensitive values only). They are also exported to hooks as `CLAUDE_PLUGIN_OPTION_<KEY>`.
- Users can set them at install with `claude plugin install --config key=value`. Source: https://code.claude.com/docs/en/plugins/cli-reference

### bin/

- Files in `bin/` are on the Bash `PATH` while the plugin is enabled, after the user's own entries, so they cannot shadow system commands. Source: components.md, "Executables".
- **claude.ai and Cowork refuse to install a plugin that has a top-level `bin/` directory.** Source: plugins-reference standard layout table; https://claude.com/docs/plugins/platform-support

### Version, license and metadata fields

Source: plugins-reference, "Fields".

- `name`: required, kebab-case, permanent. Renaming creates a different plugin for every existing install. Source: https://code.claude.com/docs/en/plugins/publish.md
- `version`: "Setting it keeps users on that version until you change it." Either bump it on every release or omit it in a git-hosted marketplace so the commit SHA is used. Source: publish.md, step 2.
- `license`: an SPDX identifier such as `MIT`.
- Also available: `displayName`, `description`, `author` (`name` required), `homepage` (must parse as a URL or the plugin fails to load), `repository`, `keywords`, `dependencies`, `defaultEnabled`.
- Directory-listing fields `icon`, `documentationUrl`, `supportUrl`, `privacyPolicyUrl` and `termsOfServiceUrl` are read only by Anthropic's directory.
- Before release, set `description`, `author`, `homepage` and `repository`, and add a `README.md` at the plugin root. Source: publish.md.
- `claude plugin tag` creates a `{name}--v{version}` git tag. Tags matter when other plugins declare version ranges on yours. Source: publish.md.

### What loads on which surface

Source: https://claude.com/docs/plugins/platform-support

| Component | claude.ai chat | Cowork | Claude Code |
|---|---|---|---|
| Skills | Loads | Loads | Loads |
| Commands | Loads as a skill | Loads | Loads |
| Agents | Ignored | Loads | Loads |
| Hooks | Ignored | Loads | Loads |
| Remote MCP (http/sse) | Via Connectors tab | Loads | Loads |
| Local MCP (stdio, .mcpb) | Ignored | Loads when the session runs locally | Loads |
| Top-level `bin/` | Plugin can't be installed | Plugin can't be installed | Loads |

## 2. What each extension type is for

### Anthropic's own definitions

Source: https://code.claude.com/docs/en/features-overview ("Match features to your goal", "Compare similar features").

- **Skill**: "Instructions, knowledge, and workflows Claude can use". Use for reusable content, reference docs and repeatable tasks. The description loads every session and the full content loads when used.
- **MCP**: "Connect to external services". Use for external data or actions. Tool names load at start and schemas are deferred.
- **Hook**: a script, HTTP request, MCP tool call, prompt or subagent triggered by lifecycle events. Use for "automation that must run on every matching event". Hooks add zero context unless they return output.
- **Subagent**: an isolated worker with its own context. Use "when you need context isolation or when your context window is getting full".
- **Slash commands**: "Custom commands have been merged into skills." A skill and a command file both create `/name`. Source: https://code.claude.com/docs/en/skills
- **Plugin**: the packaging layer for all of the above. Source: features-overview.

### Hook vs skill

Source: features-overview, "Hook vs Skill" tab.

- Use a hook "when the action must happen the same way every time and doesn't need Claude to think".
- Use a skill "when Claude should decide how to apply the steps".
- "Put guardrails in hooks. An instruction like 'never edit .env' in CLAUDE.md or a skill is a request, not a guarantee."

### Skill vs MCP

- MCP gives Claude "access to something", and a skill teaches Claude "how to do something". They are complementary. Sources: https://claude.com/resources/articles/extending-claude-capabilities-with-skills-mcp-servers and https://claude.com/blog/building-agents-that-reach-production-systems-with-mcp
- The documented pattern is "Skill + MCP: MCP provides the connection; a skill teaches Claude how to use it well". Source: features-overview, "Combine features".

### Deterministic tools: MCP tool or bundled script?

Anthropic does not state one rule for this. What it does say:

- Skills: "Prefer scripts for deterministic operations." Bundled scripts are "more reliable than generated code", and "only the script's output consumes tokens". Source: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Include an MCP connector "when Claude needs to read from or act in your product or data". A remote server reaches every surface. A local server runs only in Claude Code and local Cowork, "so most plugins reference remote servers". Source: https://claude.com/docs/connectors/building/what-to-build
- Local stdio servers launched with `npx`/`uvx` are "fine for personal tools and prototypes" but "not recommended for distribution". Use MCPB when the server must run locally, for example to read local files. Sources: https://github.com/anthropics/claude-plugins-official/blob/main/plugins/mcp-server-dev/skills/build-mcp-server/SKILL.md and https://github.com/anthropics/claude-plugins-official/blob/main/plugins/mcp-server-dev/skills/build-mcpb/SKILL.md


## 3. Skill authoring rules

### Description

Sources: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices and https://code.claude.com/docs/en/skills

- Say both what the skill does and when to use it, with specific key terms.
- Write in third person ("Processes Excel files…", not "I can help…").
- Spec limits: `name` up to 64 characters (lowercase, digits and hyphens, no "anthropic" or "claude", must match the directory name); `description` up to 1,024 characters. Sources: best-practices; https://agentskills.io/specification
- In Claude Code, `description` plus `when_to_use` is truncated at 1,536 characters in the skill listing. "Put the key use case first."
- The whole listing has a budget of about 1% of the context window, and descriptions of the least-used skills are dropped first.
- Angle brackets in `description` and `when_to_use` display as `&lt;`/`&gt;`, so use `[name]` instead. (The current `commander-deckbuilding` `when_to_use` contains `<commander>`.)

### Size and progressive disclosure

- Keep the `SKILL.md` body under 500 lines, and under about 5k tokens. Sources: best-practices; agentskills.io spec; https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- Keep references one level deep from `SKILL.md`. Claude may only `head` files that are reached through other references.
- Give reference files longer than 100 lines a table of contents. Source: best-practices.
- In Claude Code, loaded skill content stays in context for the rest of the session. After compaction only the first 5,000 tokens of each skill are re-attached, within a shared 25,000-token budget. Put the most important instructions at the top. Source: https://code.claude.com/docs/en/skills ("Skill content lifecycle").

### Scripts

Source: best-practices.

- Scripts should "solve, don't defer": handle errors in the script rather than leaving them to Claude.
- No "voodoo constants".
- Say explicitly whether Claude should run a script or read it.
- List the packages a script needs.
- Use forward slashes in paths.
- Use plan-validate-execute with verbose validators.
- In Claude Code, put `${CLAUDE_SKILL_DIR}` (or `${CLAUDE_PLUGIN_ROOT}`) both in the instruction and in an `allowed-tools` Bash rule, so the script runs without a permission prompt. Source: https://code.claude.com/docs/en/skills ("render-chart" example).

### Referencing files across skills

- Spec: "When referencing other files in your skill, use relative paths from the skill root." Source: https://agentskills.io/specification
- Claude Code: `${CLAUDE_PLUGIN_ROOT}` is the documented way to reach "resources shared between the plugin's skills". Source: https://code.claude.com/docs/en/skills
- **Unconfirmed: whether Anthropic forbids reaching into a sibling skill's folder** (`${CLAUDE_SKILL_DIR}/../other-skill/...`, as this repo does). No primary source forbids it. It does break the spec's self-contained-folder model: claude.ai uploads, the Skills API, and per-skill installers copy only one skill directory. Community style guides call it an error (for example https://github.com/b-mendoza/agent-skills/blob/main/docs/best-practices/keep-skills-self-contained.md). The documented in-plugin alternative is a plugin-level `scripts/` folder referenced through `${CLAUDE_PLUGIN_ROOT}`.

### Frontmatter fields in Claude Code

Source: https://code.claude.com/docs/en/skills ("Frontmatter reference", "Control who invokes a skill").

- `name`, `description`, `when_to_use`, `argument-hint`, `model`, `effort`, `shell`, and `paths` (which is not allowed in commands).
- `disable-model-invocation: true`: only the user can run the skill. Its description is not in context. Use it "for workflows with side effects or that you want to control timing".
- `user-invocable: false`: only Claude can invoke the skill. Use it for background knowledge.
- `allowed-tools`: grants tools for the invoking turn only.
- `disallowed-tools`.
- `context: fork` with `agent` and `background`: runs the skill in a subagent that does not see the conversation.
- `hooks`: registered when the skill is invoked, and kept for the rest of the session.
- Unknown fields are silently ignored.

### Portability to claude.ai and the API

- claude.ai uploads, the Skills API and `package_skill.py` accept only `name`, `description`, `license`, `compatibility`, `metadata` and `allowed-tools`. Other keys are rejected ("Unexpected key(s) in SKILL.md frontmatter"). Source: https://code.claude.com/docs/en/skills ("Using skill frontmatter outside Claude Code").
- Custom skills do not sync across surfaces. Source: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- Network access differs by surface (same source):
  - API skills run with no network access and no runtime package installs.
  - claude.ai has varying network access.
  - Claude Code has full network access, but global installs are discouraged.
- The agentskills.io spec's `compatibility` field (up to 500 characters) is where environment needs go, for example "Requires Python 3.14+ and uv". Source: https://agentskills.io/specification

## 4. Is generating HTML pages or artifacts from a skill standard?

**Yes, it is a documented and shipped pattern. Anthropic packages it as its own skill, and in one case as its own plugin.**

- The Claude Code skills docs include a worked example, "Generate visual output" (`codebase-visualizer`): a bundled Python script writes an interactive HTML file. The docs say the pattern "works for any visual output… The bundled script does the work while Claude handles orchestration." Source: https://code.claude.com/docs/en/skills
- `anthropics/skills` ships `web-artifacts-builder` and `frontend-design`. The first initialises a React/Vite project with `scripts/init-artifact.sh`, bundles it to one `bundle.html` with `scripts/bundle-artifact.sh`, then shares it. The second is guidance only. Other visual skills in the repo: `algorithmic-art`, `canvas-design`, `theme-factory`. Sources: https://github.com/anthropics/skills/tree/main/skills and https://github.com/anthropics/skills/blob/main/skills/web-artifacts-builder/SKILL.md
- `claude-plugins-official` ships `project-artifact`, a separate plugin with one skill (Anthropic verified). How it works (sources: https://github.com/anthropics/claude-plugins-official/tree/main/plugins/project-artifact and its SKILL.md):
  - It fills a bundled `template.html` and publishes with the built-in `Artifact` tool.
  - It stores the config and last render in `${CLAUDE_PLUGIN_DATA}`.
  - It entity-encodes fetched text and keeps it out of `<script>` blocks.
  - It says that in headless runs Claude should save the HTML and report that publishing needs an interactive session, "don't improvise another publishing path".
- Artifacts in Claude Code require all of the following. Otherwise "Claude writes a local HTML file or says it cannot publish". Source: https://code.claude.com/docs/en/artifacts
  - A Pro, Max, Ultra, Team or Enterprise plan.
  - A claude.ai login (not an API key, Bedrock, Vertex or Foundry).
  - Not `-p` or the Agent SDK.
- Artifact page limits (same source):
  - A single self-contained page under 16 MiB.
  - A strict CSP: scripts only from cdnjs, unpkg, jsDelivr `/npm/`, the Tailwind CDN and the jQuery CDN, plus fonts from Google Fonts.
  - No external images, and fetches only to the page's own origin.
  - Claude applies a built-in design skill when it builds artifacts.

Where the feature should live. The following is **inference** from the examples above:
- Keep page rendering as its own skill that is optional to use, with a script and template that render from data. This repo already does that.
- Making it a separate plugin, as Anthropic did with `project-artifact`, keeps the core research and deckbuilding plugin usable without a claude.ai login.
- Always provide a "save local HTML" fallback.

## 5. Hooks: costs, matchers and recommended uses

- Plugin hooks are registered when the session loads the plugin, and "fire on their events from then on". They do not wait for the plugin's skills to be used. "To limit when a hook runs, narrow its `matcher`." Source: https://code.claude.com/docs/en/plugins/components.md ("When plugin hooks fire").
- The `matcher` filters by tool name only. It is a JS regex that matches anywhere in the string, so `Edit.*` also matches `NotebookEdit`; use `^Edit$` for an exact match. Source: https://code.claude.com/docs/en/hooks
- The `if` field filters by tool and arguments using permission-rule syntax, for example `"Edit(*.ts)"`, so "the hook process only spawns when the tool call matches". It holds one rule only, and a directory pattern at any depth is written `**/dir/**`. Sources: https://code.claude.com/docs/en/hooks-guide and https://code.claude.com/docs/en/hooks
- Skill-scoped hooks: a skill's `hooks` frontmatter registers hooks only once that skill is invoked. `once: true` is honored only there. Sources: https://code.claude.com/docs/en/skills and https://code.claude.com/docs/en/hooks
- Default timeouts: 600 s for command, http and mcp_tool hooks; 30 s for prompt hooks; 60 s for agent hooks. `UserPromptSubmit` drops to 30 s because it "blocks model processing… a stuck hook stalls the session". Source: hooks reference.
- `async: true` runs a hook in the background, and results arrive while the session runs. Source: hooks reference.
- To return feedback from PostToolUse, exit 2 so Claude sees stderr, or return `additionalContext`. Source: hooks reference.
- A PostToolUse `Edit|Write` hook does not fire when Bash or an outside process writes the file. Use `FileChanged` for that. Source: hooks reference.
- Hooks merge across sources, and all matching hooks fire. Source: features-overview.
- In shell form, quote `"${CLAUDE_PLUGIN_ROOT}"`, or use exec form with `args`. Source: components.md.
- Recommended uses: format or lint after edits, block protected files, logging, notifications, enforcing rules that "must hold every time". Sources: hooks-guide, features-overview.
- Plugin agents ignore their own `hooks`, `mcpServers` and `permissionMode` frontmatter for security reasons. Source: https://code.claude.com/docs/en/sub-agents


## 6. Testing and evals

- `claude plugin validate [--strict] [--json] <dir>` checks manifest, marketplace, skill, agent, command, hook and MCP files. `--strict` fails on warnings and is recommended in CI. It does not check a root `SKILL.md`. Sources: https://code.claude.com/docs/en/plugins/cli-reference and publish.md
- `claude plugin eval` is documented. Source: https://code.claude.com/docs/en/plugin-evals
  - Cases live in `evals/<case>/prompt.md` with `graders/*.md`, and optional `case.yaml` and `mocks/<server>/<tool>.md`.
  - Each case runs with and without the plugin and reports the difference (Δ).
  - A `tool_used: Skill` grader checks that the skill fired.
  - Runs are isolated: no user settings, hooks, CLAUDE.md or MCP, and read-only tools unless granted with `--allow-tools`.
  - Plugin MCP servers are mocked unless you pass `--allow-real-servers` or `--mocks off`.
  - Pin `--model` in CI. Runs cost usage.
  - `claude plugin eval init` scaffolds a suite.
  - The repo's `evals/` layout already matches this format.
- The `skill-creator` plugin (`/plugin install skill-creator@claude-plugins-official`) is a separate loop. It uses `evals/evals.json`, does with/without benchmarks, and tunes descriptions. The two formats are not interchangeable. Source: https://code.claude.com/docs/en/skills ("Run evals with skill-creator").
- Build evaluations first: at least three scenarios, a no-skill baseline, then the minimum instructions needed. Test with Haiku, Sonnet and Opus. Source: best-practices.
- `/skill-doctor` reports each skill's context cost and usage. Source: https://code.claude.com/docs/en/skills
- `skills-ref validate ./my-skill` validates against the open spec. Source: https://agentskills.io/specification
- On claude.ai: zip the plugin and upload it under Customize > Plugins. Source: https://claude.com/docs/plugins/build

## 7. Anti-patterns Anthropic calls out

Skill authoring (source: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices unless noted):

1. Verbose explanations of things Claude already knows ("Concise is key").
2. Vague descriptions ("Helps with documents"), and first- or second-person descriptions.
3. `SKILL.md` over 500 lines, and deeply nested references.
4. Time-sensitive information in the main text; move it to an "Old patterns" section.
5. Inconsistent terminology.
6. Offering too many options instead of a default with an escape hatch.
7. Windows-style backslash paths.
8. Scripts that "defer to Claude" instead of handling errors, and unexplained "voodoo constants".
9. Assuming packages are installed.
10. Unqualified MCP tool names; use `ServerName:tool_name`.
11. Vague skill names (`helper`, `utils`, `tools`) or reserved words (`anthropic`, `claude`).

Plugins and Claude Code (sources as given):

12. Putting `skills/`, `agents/`, `hooks/` or `commands/` inside `.claude-plugin/`. Source: https://code.claude.com/docs/en/plugins
13. Writing state into `${CLAUDE_PLUGIN_ROOT}`; use `${CLAUDE_PLUGIN_DATA}`. Source: components.md.
14. Putting secrets in `.mcp.json`. Source: https://claude.com/docs/plugins/build
15. Setting `version` and then pushing without bumping it, so users stay on the old copy. Source: publish.md.
16. Renaming a published plugin. Source: publish.md.
17. Relying on a skill or CLAUDE.md for rules that must always hold; use a hook. Source: features-overview.
18. Using hook `if` filters as hard security; use permissions instead, because the filter is best-effort. Source: hooks-guide.
19. A plugin-root `CLAUDE.md`, which is not loaded. Source: components.md.
20. A top-level `bin/` in a plugin meant for claude.ai or Cowork. Source: platform-support.
21. Leaving side-effecting workflows model-invocable; set `disable-model-invocation: true`. Source: https://code.claude.com/docs/en/skills
22. Overlapping or vague skill and subagent descriptions, which cause wrong routing. All subagent descriptions share a 15,000-token budget. Sources: features-overview; https://code.claude.com/docs/en/sub-agents
23. Bloating an artifact with embedded raster images or unneeded interactivity, since it costs output tokens. Source: https://code.claude.com/docs/en/artifacts
24. Installing skills from untrusted sources without auditing them, and skills that fetch from external URLs. Source: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

## Unconfirmed items

- Whether reaching into a sibling skill's directory is explicitly disallowed. No primary source says so; see section 3.
- A single Anthropic rule for "deterministic tool as MCP vs script". None found; section 2 gives the related statements.
- Whether `claude plugin eval` and the `experimental.evals` manifest key will change shape. The docs place `evals` under `experimental`, whose "manifest shape may still change". Source: plugins-reference.
