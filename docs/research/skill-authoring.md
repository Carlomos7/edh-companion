# Skill authoring best practices (late 2026)

How to write `SKILL.md` files for Claude Code and the Agent Skills standard, from primary sources only. This note extends [claude-code-standards.md](claude-code-standards.md), which already covers plugin layout, path variables, portability, hooks, the `claude plugin eval` file layout and a first anti-pattern list. Where that note already states a fact, this one points to its section instead of repeating it.

- All pages were fetched on 2026-11-03. For some pages the fetch tool served a cached copy; its reported capture dates were: agentskills.io pages 2026-10-27 to 2026-10-31, the Anthropic engineering post 2026-10-20, the skill-creator blog post 2026-10-03, the "How we use skills" blog post 2026-09-20, and plugin-evals 2026-11-02. The Claude Code skills page and the platform best-practices page were fetched live.
- GitHub files were read with `gh api` on 2026-11-03 from `anthropics/skills` (`skill-creator`, `pdf`, `mcp-builder`, `webapp-testing`) and `anthropics/claude-plugins-official` (`hookify`, `plugin-dev`).
- Anything not confirmed from a primary source is marked **unconfirmed**. Conclusions drawn from several sources are marked **inference**.

Short names used below:

| Short name | URL |
|---|---|
| CC skills | https://code.claude.com/docs/en/skills |
| Best practices | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices |
| Spec | https://agentskills.io/specification |
| Optimizing descriptions | https://agentskills.io/skill-creation/optimizing-descriptions |
| Evaluating skills | https://agentskills.io/skill-creation/evaluating-skills |
| Engineering post | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills |
| How we use skills | https://claude.com/blog/lessons-from-building-claude-code-how-we-use-skills |
| skill-creator post | https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills |
| skill-creator SKILL.md | https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md |
| Plugin evals | https://code.claude.com/docs/en/plugin-evals |
| Prompting guide | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices |
| CC best practices | https://code.claude.com/docs/en/best-practices |
| Hooks reference | https://code.claude.com/docs/en/hooks |

## 1. Descriptions and triggering

### How Claude decides to load a skill

- At session start Claude Code builds a listing of every skill's name and description. Claude scans that listing to decide whether a skill fits the request, so "the description field is not a summary, it's a description of when to trigger this skill." Source: How we use skills.
- The description "carries the entire burden of triggering". When a task matches, the agent reads the full `SKILL.md`. Source: Optimizing descriptions.
- Claude "only consults skills for tasks it can't easily handle on its own". Simple one-step requests such as "read this PDF" may not trigger a skill even with a perfect description. Complex, multi-step or specialized requests trigger reliably. Source: skill-creator SKILL.md, "How skill triggering works".
- If the YAML frontmatter does not parse, the skill still loads with no fields set. `/name` works, but Claude cannot match against the description. Source: CC skills, "Skill not triggering".
- A `paths` glob limits automatic loading to work on matching files inside the working directory. Source: CC skills, frontmatter table and "Skill not triggering".

### What makes a description trigger reliably

- State what the skill does and when to use it, with specific key terms. Source: Best practices, "Writing effective descriptions"; Spec, `description` field.
- Write in third person ("Processes Excel files…"), because the description is injected into the system prompt and a mixed point of view "can cause discovery problems". Source: Best practices.
- The agentskills.io guide instead recommends imperative phrasing ("Use this skill when…"). The two do not conflict in practice: Anthropic's own examples use a third-person "what" sentence followed by a "Use when…" sentence. Sources: Optimizing descriptions; Best practices examples.
- Describe user intent, not implementation. Source: Optimizing descriptions.
- Include concrete trigger words users actually say, such as "babysit". Source: How we use skills. The troubleshooting list starts with "Check the description includes keywords users would naturally say". Source: CC skills.
- List contexts where the user does not name the domain ("even if they don't explicitly mention 'CSV'"). Sources: Optimizing descriptions; skill-creator SKILL.md calls this being a little "pushy" because Claude tends to undertrigger.
- Keep it to "a few sentences to a short paragraph". Source: Optimizing descriptions.
- If the skill triggers too often, make the description more specific, or set `disable-model-invocation: true`. Source: CC skills, "Skill triggers too often".

### Length limits

- Spec: `description` is 1 to 1,024 characters and contains no XML tags; `name` is up to 64 characters. Sources: Spec; Best practices.
- Claude Code truncates `description` plus `when_to_use` at 1,536 characters per entry in the listing, so put the key use case first. The cap is configurable with `skillListingMaxDescChars`. Source: CC skills. (Also in claude-code-standards.md section 3.)

### Overlap between skills

- To fix false triggers, "add specificity about what the skill does *not* do, or clarify the boundary between this skill and adjacent capabilities". Source: Optimizing descriptions.
- Do not fix failures by pasting the failed query's keywords into the description; that overfits. Address the general category instead. Source: Optimizing descriptions.
- The most valuable negative test prompts are near-misses that share keywords with the skill but need something else. Source: skill-creator SKILL.md, "Description Optimization".
- Skills that straddle several of Anthropic's nine skill categories "confuse the agent"; the best fit one category cleanly. Source: How we use skills, "Types of skills".
- As the skill count grows, description precision becomes critical: too broad gives false triggers, too narrow never fires. Source: skill-creator post.

### `when_to_use` versus `description`

- `when_to_use` holds extra trigger context such as trigger phrases or example requests. Claude Code appends it to `description` in the listing, and it counts toward the 1,536-character cap. Source: CC skills, frontmatter table.
- It is Claude Code-only. claude.ai uploads, the Skills API and `package_skill.py` reject it as an unexpected key. Source: CC skills, "Using skill frontmatter outside Claude Code".
- skill-creator's guidance is the opposite: "All 'when to use' info goes here [description], not in the body." Source: skill-creator SKILL.md. **Inference:** for a plugin that might ever be uploaded to claude.ai, keep all triggering text in `description`; `when_to_use` is only a convenience for Claude Code-only skills.

### How many skills before routing degrades

- **Unconfirmed: no primary source gives a skill count at which routing degrades.**
- What is documented: the best-practices page says Claude chooses "from potentially 100+ available Skills". Source: Best practices.
- The listing budget is 1% of the context window. When it overflows, Claude Code drops descriptions of the least-used skills first and keeps only their names, "which removes the keywords Claude needs to match your request". Source: CC skills, "Skill descriptions are cut short". `/doctor` estimates the listing cost and `/skill-doctor` flags skills never invoked. Source: same page.
- Every model-invocable skill's name and description is in context on every turn of every session where its plugin is enabled. Source: https://code.claude.com/docs/en/plugins/overview, "What an enabled plugin adds to your sessions".

## 2. Size and progressive disclosure

Three loading levels: metadata (about 100 tokens per skill, always loaded), the `SKILL.md` body (loaded on trigger, under about 5,000 tokens recommended), and bundled files (loaded only when read; scripts can run without being read). Sources: Spec, "Progressive disclosure"; Engineering post; skill-creator SKILL.md.

### Length

- Keep the body under 500 lines; split when you approach it. Sources: Best practices; Spec; CC skills tip.
- Keep the body concise even under that limit. "Once a skill loads, its content stays in context across turns, so every line is a recurring token cost. State what to do rather than narrating how or why." Source: CC skills, "Types of skill content".
- After compaction only the first 5,000 tokens of each skill come back, within a shared 25,000-token budget, so put the most important instructions at the top. Source: CC skills, "Skill content lifecycle". (Also in claude-code-standards.md section 3.)
- Claude Code does not re-read the skill on later turns, so write guidance as standing instructions ("Run the tests after every edit", not "Run the tests"). Source: CC skills, "Claude stops following a skill".

### Body versus references

- The body is the overview and navigation; it points to detail "like a table of contents in an onboarding guide". Source: Best practices, "Progressive disclosure patterns".
- Move to references: large API docs, schemas, long example sets, and branches used only in some cases (for example form filling, tracked changes). Sources: Best practices, Patterns 1 to 3; CC skills, "Add supporting files".
- Split by domain when a skill covers several, so Claude reads only the relevant file (for example `reference/finance.md`, `reference/sales.md`). Source: Best practices, Pattern 2; skill-creator SKILL.md ("Domain organization").
- Mutually exclusive or rarely combined contexts should live in separate files. Source: Engineering post.
- Bundled resources cost nothing until read, so complete docs and large datasets are fine to bundle. Source: Best practices, "Runtime environment".
- Output templates belong in `assets/`. Sources: How we use skills; skill-creator SKILL.md anatomy.

### Nesting depth

- Keep every reference one level deep from `SKILL.md`. Claude may only preview (`head -100`) files reached through other files. Sources: Best practices, "Avoid deeply nested references"; Spec, "File references".
- Give long reference files a table of contents at the top. The threshold differs by source: 100 lines in Best practices, 300 lines in skill-creator SKILL.md.

### Linking style

- Use relative paths from the skill root with forward slashes, for example `[the reference guide](references/REFERENCE.md)`. Sources: Spec; Best practices, "Avoid Windows-style paths".
- Say what each file contains and when to read it, for example "For complete API details, see [reference.md](reference.md)". Sources: CC skills, "Add supporting files"; skill-creator SKILL.md.
- Name files by content (`form_validation_rules.md`, not `doc2.md`). Source: Best practices, "Runtime environment".
- In Claude Code, run bundled scripts through `${CLAUDE_SKILL_DIR}` (or `${CLAUDE_PLUGIN_ROOT}` for plugin-wide files) so the path does not depend on the working directory. Source: CC skills, "Available string substitutions". (Cross-skill references are covered in claude-code-standards.md section 3.)

### Loading cost

- Description: every turn, in every session where the skill is enabled, unless `disable-model-invocation: true` removes it from context. Source: CC skills, "Control who invokes a skill".
- Body: once per invocation, then for the rest of the session. A repeat invocation with identical rendered content adds only a short note; different arguments or `!` output append the full content again. Source: CC skills, "Skill content lifecycle".
- Scripts: only their output costs tokens. Source: Best practices, "Runtime environment".
- Subagents with preloaded skills get the full skill content at startup, not just the description. Source: CC skills, note under "Control who invokes a skill".

## 3. Frontmatter fields and substitutions in Claude Code

Source for every row: CC skills, "Frontmatter reference" and "Using skill frontmatter outside Claude Code". "Spec" means the field is in the Agent Skills standard and accepted by claude.ai uploads and the Skills API; "CC only" means those paths reject it with a hard error.

| Field | Scope | What it does |
|---|---|---|
| `name` | Spec | Command name. Defaults to the directory name. In a plugin it sets the last segment of `/plugin:name`. Not allowed in `commands/*.md` files. |
| `description` | Spec | Recommended. Falls back to the first non-empty body line. Angle brackets display as `&lt;`/`&gt;`; use `[name]`. |
| `license`, `compatibility`, `metadata` | Spec | Accepted, not acted on. `compatibility` is up to 500 characters. |
| `allowed-tools` | Spec (experimental) | Pre-approves listed tools for the invoking turn only; does not restrict other tools. |
| `when_to_use` | CC only | Extra trigger text appended to the description, inside the 1,536-character cap. |
| `argument-hint` | CC only | Autocomplete hint, for example `[issue-number]`. |
| `arguments` | CC only | Names positional arguments for `$name` substitution. |
| `disable-model-invocation` | CC only | Claude cannot invoke the skill; its description leaves context; it cannot be preloaded into subagents or fired by a session-scoped scheduled task. |
| `user-invocable` | CC only | `false` hides it from the `/` menu; Claude can still invoke it. |
| `disallowed-tools` | CC only | Removes tools while the skill is active; clears on the next user message. |
| `model` | CC only | Model for the rest of the turn; with `context: fork`, the subagent's model. |
| `effort` | CC only | `low` to `max` for the rest of the turn; with `context: fork`, the subagent's effort. |
| `context: fork`, `agent`, `background` | CC only | Run the body as a task in a subagent (default `general-purpose`) that does not see the conversation; runs in the background unless `background: false`. |
| `hooks` | CC only | Registered when the skill is invoked, kept for the rest of the session. `once: true` is honored only here. |
| `paths` | CC only | Globs that limit automatic loading. Not allowed in `commands/*.md`. |
| `shell` | CC only | `bash` (default) or `powershell` for `!` blocks. |

Notes:

- Unknown field names are ignored silently, so a typo such as `disable_model_invocation` does nothing. Source: CC skills.
- Booleans accept `yes`, `no`, `on`, `off`, `1`, `0`. Source: CC skills.
- `context: fork` only makes sense for skills with an explicit task. A guidelines-only skill gives the subagent "no actionable prompt". A backgrounded fork gets the narrower background tool set and edits outside checkpoints. Source: CC skills, "Run skills in a subagent".
- A skill's hooks are capped per source at 1,024 hooks and 16,384 matcher characters per session (v2.1.304+). Source: Hooks reference, "Limits on skill hooks".

### Substitutions

Source: CC skills, "Available string substitutions" and "Pass arguments to skills".

- `$ARGUMENTS` is the full argument string. `$ARGUMENTS[N]` and `$N` are 0-based positional arguments with shell-style quoting. `$name` comes from the `arguments` field.
- If no placeholder receives the arguments, Claude Code appends `ARGUMENTS: <value>` to the content.
- An unfilled indexed placeholder (`$2` with one argument) stays as literal text. An unfilled named placeholder becomes an empty string.
- Escape a literal `$1` as `\$1`.
- `${CLAUDE_SESSION_ID}`, `${CLAUDE_EFFORT}`, `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PROJECT_DIR}` work in all skills. `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` work only in plugin skills.
- These variables are substituted in the body and in Bash rules in `allowed-tools`. Use the same variable in both so the script runs without a prompt.
- Writing `ultrathink` anywhere in the skill requests deeper reasoning. Source: CC skills, "Inject dynamic context" tip.

### `!` command blocks (dynamic context injection)

Source: CC skills, "Inject dynamic context" through "Permission checks on injected commands".

- `` !`cmd` `` at the start of a line or after whitespace, or a fenced ` ```! ` block, runs before Claude sees the skill; the output replaces the placeholder. Output is not re-scanned.
- Any failing command aborts the whole invocation, and Claude never sees the skill. Exit code 1 from search and comparison commands is treated as normal. Append `|| true` to commands expected to exit non-zero.
- The commands never prompt. Outside auto mode, anything that is not allowed by permission rules or `allowed-tools` aborts the invocation. So pre-approve every injected command in `allowed-tools`.
- Each command runs in the session's current directory with the Bash tool's 2-minute timeout. Use `${CLAUDE_SKILL_DIR}` or `${CLAUDE_PROJECT_DIR}` in paths.
- `disableSkillShellExecution` replaces them with a placeholder. Skills synced from claude.ai never run them on the local machine.
- They are Claude Code-only and do nothing in claude.ai chat or the API. Source: CC skills, "Using skill frontmatter outside Claude Code".

## 4. User-invoked command skills versus model-invoked skills

### When to set `disable-model-invocation: true`

- Use it "for workflows with side effects or that you want to control timing, like `/commit`, `/deploy`, or `/send-slack-message`. You don't want Claude deciding to deploy because your code looks ready." Source: CC skills, "Control who invokes a skill".
- If Claude tries to invoke such a skill, Claude Code blocks the call and tells Claude not to reproduce the steps another way. Source: same section.
- It also removes the description from context, which saves listing budget. Source: same section's table.
- Use `user-invocable: false` for background knowledge that is not a meaningful command. Source: same section.
- A user typing `/name` after other text in a message gives Claude permission to run the skill in that message, without running it directly. Source: CC skills, "Where you write the skill's name".

### Naming

- Lowercase letters, digits and hyphens; no leading or trailing hyphen; no `anthropic` or `claude`. Sources: Spec; Best practices.
- Gerund form is suggested (`processing-pdfs`); noun phrases and action forms are acceptable. Avoid vague (`helper`, `utils`) and generic (`documents`, `data`) names, and mixed patterns inside one collection. Source: Best practices, "Naming conventions".
- Plugin skills are always namespaced as `/plugin:skill`; the bare name also works when no other command uses it. Source: CC skills, "How a skill gets its command name".

### Argument hints

- Put placeholders in `argument-hint` (for example `[issue-number]` or `[filename] [format]`), not angle brackets in the description. Source: CC skills, frontmatter table and "Angle brackets in a skill description".
- `argument-hint` breaks claude.ai and API uploads, so check the target before using it. Source: CC skills, "Angle brackets…".

### Thin "router" command skills that load another skill

- **Unconfirmed as a documented recommendation.** No Claude Code docs page recommends a command whose only job is to load another skill.
- Anthropic does use the pattern in its own plugins. `hookify`'s `/hookify` command starts with "**FIRST: Load the hookify:writing-rules skill** using the Skill tool" and lists `Skill` in `allowed-tools`. `plugin-dev`'s `/create-plugin` command tells Claude to load `plugin-structure`, `skill-development` and other skills before each phase. Sources: https://github.com/anthropics/claude-plugins-official/blob/main/plugins/hookify/commands/hookify.md and https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/commands/create-plugin.md
- Anthropic's Claude Code team says skill dependency management "is not natively built into marketplaces or skills yet, but you can just reference other skills by name, and the model will invoke them if they are installed." Source: How we use skills, "Composing skills".
- **Inference:** a target skill with `disable-model-invocation: true` cannot be loaded this way, because the router asks Claude to call the Skill tool and Claude Code blocks Claude's call (CC skills, "Control who invokes a skill"). The target must stay model-invocable.
- **Inference:** a router adds a second skill body to context on top of its own, so it only pays off when the command adds something the target lacks: arguments, `allowed-tools`, an ordering of several skills, or a user-only trigger for a model-invocable knowledge skill. Plugin-dev's `create-plugin` also calls `commands/` a "legacy format" and says new user-invoked commands should be skills. Source: create-plugin.md above.

## 5. Writing instructions models follow

- **Conciseness.** "Default assumption: Claude is already very smart." Ask of each paragraph whether it "justif[ies] its token cost". Source: Best practices, "Concise is key". "Don't state the obvious"; focus on what "pushes Claude out of its normal way of thinking". Source: How we use skills.
- **Gotchas.** "The highest-signal content in any skill is the Gotchas section", built from real failures and updated over time. Source: How we use skills.
- **Degrees of freedom.** Match specificity to fragility: prose heuristics when many approaches work, parameterised pseudocode when a preferred pattern exists, exact scripts ("Run exactly this script… Do not modify the command") when steps are fragile. Source: Best practices, "Set appropriate degrees of freedom". "Avoid railroading Claude": skills are reused widely, so leave room to adapt. Source: How we use skills.
- **Defaults over options.** Give one default and an escape hatch, not a menu ("Use pdfplumber… For scanned PDFs requiring OCR, use pdf2image"). Source: Best practices, "Avoid offering too many options".
- **Examples.** Use concrete input/output pairs when output style matters; they convey style "more clearly than descriptions alone". Source: Best practices, "Examples pattern". Keep the skill general rather than narrow to the examples. Source: skill-creator SKILL.md, "Writing Style".
- **Checklists and workflows.** Break complex tasks into numbered steps, and for long ones give a checklist Claude copies into its reply and ticks off. Use conditional branches ("Creating new content? → …") at decision points; move large branches into their own files. Source: Best practices, "Use workflows for complex tasks" and "Conditional workflow pattern".
- **Feedback loops.** "Run validator → fix errors → repeat… greatly improves output quality." The validator can be a script or a reference document such as a style guide. Source: Best practices, "Implement feedback loops".
- **ALL-CAPS and over-constraint.** "If you find yourself writing ALWAYS or NEVER in all caps… that's a yellow flag"; explain the reasoning instead. Source: skill-creator SKILL.md. "Reasoning-based instructions (\"Do X because Y tends to cause Z\") work better than rigid directives." If pass rates plateau as rules are added, "the skill may be over-constrained — try removing instructions". Source: Evaluating skills. Current models "follow a plainly worded line, and piling on emphasis mostly makes Claude over-apply the rule"; a rule that cannot bend belongs in a hook or deny rule. Source: CC best practices. Opus 4.5 and later may overtrigger on "CRITICAL: You MUST use this tool when…"; use "Use this tool when…". Source: Prompting guide.
  - Conflicting older advice: the best-practices page's iteration example still has Claude suggest "stronger language such as 'MUST filter'", and its strict template example says "ALWAYS use this exact template". Source: Best practices. The newer sources above take precedence for current models (**inference** from their dates and model references).
- **Imperative voice.** "Prefer using the imperative form in instructions." Source: skill-creator SKILL.md.
- **Consistent terminology.** Pick one term ("field", "extract") and keep it. Source: Best practices, "Use consistent terminology".
- **Time-sensitive information.** No "before August 2025" rules in the main text; put superseded methods in a collapsed "Old patterns" section. Source: Best practices, "Avoid time-sensitive information".
- **Output templates.** Strict template for machine-read formats, "sensible default… use your best judgment" for flexible ones. Source: Best practices, "Template pattern".
- **Setup and memory.** Store user configuration (for example a Slack channel) in a `config.json` and ask when it is missing, with `AskUserQuestion` for multiple choice. Keep run history in a log under `${CLAUDE_PLUGIN_DATA}` so later runs can see what changed. Source: How we use skills.
- **Rules that must always hold.** Move them to a hook, optionally the skill's own `hooks` frontmatter. Source: CC skills, "Claude stops following a skill".

## 6. Scripts in skills

- **When to bundle.** "Prefer scripts for deterministic operations." Pre-made scripts are more reliable than generated code, save tokens and time, and stay consistent. Source: Best practices, "Provide utility scripts" and "Runtime environment".
- Bundle a script when test transcripts show every run writing a similar helper (for example each run writes its own `create_docx.py`). Source: skill-creator SKILL.md, "Look for repeated work across test cases".
- Libraries of helper functions let Claude "spend its turns on composition… rather than reconstructing boilerplate". Source: How we use skills.
- **Run versus read.** Say which: "Run `analyze_form.py`" versus "See `analyze_form.py` for the algorithm". Execution is the default. Sources: Best practices; Engineering post.
- Anthropic's `webapp-testing` skill tells Claude to run scripts with `--help` first and not read the source, because large scripts "pollute your context window". Source: https://github.com/anthropics/skills/blob/main/skills/webapp-testing/SKILL.md
- **Solve, don't punt.** Handle errors inside the script (create a missing file, fall back on permission errors) instead of failing and leaving it to Claude. Document every constant ("no voodoo constants"). Source: Best practices, "Solve, don't defer".
- **Verbose validation.** Validators should name the problem and the valid options ("Field 'signature_date' not found. Available fields: …"). Use plan-validate-execute for batch, destructive or high-stakes operations. Source: Best practices, "Create verifiable intermediate outputs".
- **Dependencies.** List required packages; do not assume they are installed. The API has no network and no runtime installs. Source: Best practices, "Package dependencies" and "Avoid assuming tools are installed".
- **MCP tool references.** Use fully qualified names, `ServerName:tool_name`, to avoid "tool not found" when several servers are present. Source: Best practices, "MCP tool references". In Claude Code a plugin server's tools are named `mcp__plugin_<plugin>_<server>__<tool>`. Source: Hooks reference, "Match MCP tools". **Unconfirmed:** which of the two forms Claude resolves more reliably inside a Claude Code skill body; no source compares them.
- Claude Code specifics (pre-approving the script with `allowed-tools`, `${CLAUDE_SKILL_DIR}`) are in claude-code-standards.md section 3.

## 7. Testing and evaluation

### Eval-driven development

- Build evaluations before writing extensive documentation: run Claude without the skill on representative tasks, record failures, write three scenarios, measure a baseline, write the minimum instructions that pass, iterate. Source: Best practices, "Build evaluations first"; Engineering post, "Start with evaluation".
- Work with one Claude instance (A) to write the skill and a fresh instance (B) to use it on real tasks; bring B's failures back to A. Source: Best practices, "Develop Skills iteratively with Claude".
- Watch how Claude navigates the skill: unexpected reading order, ignored files, or one file read every time (which may belong in the body). Source: Best practices, "Observe how Claude navigates Skills".
- Test each prompt in a fresh session with and without the skill; leftover authoring context hides gaps. Seeing a skill trigger does not show it did the job, so measure triggering and output quality separately. Source: CC skills, "Evaluate and iterate on a skill".
- Evals also show when a "capability uplift" skill has become unnecessary: the base model passes without it. Source: skill-creator post.

### Output-quality evals

- Start with 2 to 3 realistic prompts with file paths and context, including one edge case. Add assertions after seeing first outputs. Source: Evaluating skills.
- Good assertions are objectively checkable; avoid vague ("output is good") and brittle (exact phrase) ones. Use scripts for mechanical checks. Require concrete evidence for a PASS. Source: Evaluating skills.
- Compare the pass-rate delta against the token and time cost of the skill. Source: Evaluating skills, "Aggregating results".
- High variance across runs means a flaky eval or ambiguous instructions. Source: Evaluating skills.

### Trigger evals

- About 20 queries: 8 to 10 should-trigger and 8 to 10 near-miss should-not-trigger, varied in phrasing, explicitness, detail and complexity. Source: Optimizing descriptions.
- Run each 3 times, pass on a trigger rate above 0.5, split 60% train and 40% validation, and pick the description with the best validation score. Sources: Optimizing descriptions; skill-creator SKILL.md.
- In Claude Code, detect triggering by a `Skill` tool call in `claude -p --output-format json`. Source: Optimizing descriptions, example script.

### Tools

- `claude plugin eval` (for plugin skills): each case runs 3 times by default in isolated sessions, with and without the plugin. A `tool_used` grader on `Skill` with an `input_match` on the skill name shows whether the skill fired; it is reported but excluded from the score in two-arm runs. A delta near zero with that grader failing usually means the description does not trigger on natural phrasing. Default `--threshold` is 1.0. Pin `--model` in CI. Source: Plugin evals. (File layout is in claude-code-standards.md section 6.)
- For a "must not trigger" case, use `tool_used` with `min: 0`, `max: 0` and `arm: both`. Source: Plugin evals, "Score against the no-plugin baseline".
- skill-creator (`/plugin install skill-creator@claude-plugins-official`): `evals/evals.json`, parallel subagent runs, `grading.json`, `benchmark.json`, blind A/B between versions, description tuning, and an HTML review viewer. Its format does not interoperate with `claude plugin eval`. Sources: CC skills, "Run evals with skill-creator"; skill-creator SKILL.md.
- skill-creator's description loop needs `claude -p`, so it only runs in Claude Code or Cowork. Source: skill-creator SKILL.md, "Claude.ai-specific instructions".
- Anthropic measures internal skill usage with a `PreToolUse` hook on the `Skill` tool to find undertriggering skills. Source: How we use skills. Typing `/name` bypasses `PreToolUse`; the `UserPromptExpansion` event covers that path. Source: Hooks reference.

### Multiple models

- Test with every model you plan to use: does Haiku get enough guidance, is Sonnet efficient, does Opus get over-explained? Source: Best practices, "Test with all models you plan to use".
- Re-run evals after model updates to catch regressions. Source: skill-creator post.
- Run trigger evals on the model the user actually runs. Source: skill-creator SKILL.md, Step 3.
- `claude plugin eval --model` and `--judge-model` choose the agent and judge models. Source: Plugin evals.

## 8. Anti-pattern checklist

This extends the 24 items in claude-code-standards.md section 7; items already listed there are not repeated.

1. A description that summarises the skill for humans instead of saying when to trigger it. Source: How we use skills.
2. A description with no words users would actually type, or none of the indirect cases. Sources: CC skills, "Skill not triggering"; Optimizing descriptions.
3. Fixing false negatives by pasting failed queries into the description (overfitting). Source: Optimizing descriptions.
4. Two skills whose descriptions do not say where one ends and the other begins. Source: Optimizing descriptions.
5. A skill that straddles several jobs. Source: How we use skills.
6. Trigger text only in `when_to_use` in a skill that may be uploaded to claude.ai. Source: CC skills.
7. Angle-bracket placeholders in `description` or `when_to_use`. Source: CC skills.
8. Misspelled frontmatter keys, which are silently ignored, and malformed YAML, which disables triggering. Source: CC skills.
9. Restating what Claude already does by default. Sources: Best practices; How we use skills.
10. ALL-CAPS ALWAYS/NEVER and "CRITICAL: You MUST" in place of a reason. Sources: skill-creator SKILL.md; Evaluating skills; CC best practices; Prompting guide.
11. Over-specific instructions that railroad Claude on a reusable skill. Source: How we use skills.
12. One-time phrasing ("Run the tests") for guidance meant to hold for the whole task. Source: CC skills.
13. Key instructions at the bottom of a long `SKILL.md`, where compaction cuts them. Source: CC skills.
14. Reference files that link to further reference files. Sources: Best practices; Spec.
15. Links to supporting files without saying what is in them or when to read them. Sources: CC skills; skill-creator SKILL.md.
16. A `!` command that can exit non-zero, or one not covered by `allowed-tools`, which aborts the whole skill. Source: CC skills.
17. `context: fork` on a guidelines-only skill with no task. Source: CC skills.
18. A router command that tries to load a `disable-model-invocation: true` skill (**inference**, see section 4).
19. Telling Claude to read a large bundled script when it should run it. Sources: Best practices; webapp-testing SKILL.md.
20. No gotchas section, or one never updated after failures. Source: How we use skills.
21. Shipping without a no-skill baseline, or testing only in the session that wrote the skill. Source: CC skills, "Evaluate and iterate on a skill".
22. Should-not-trigger tests that are obviously unrelated instead of near-misses. Source: skill-creator SKILL.md.
23. Testing on one model only. Source: Best practices.

## Checklist for reviewing a skill

Each check should be answered yes.

1. Does the `description` say what the skill does and when to use it, in under 1,024 characters, with the key use case first? (Spec; CC skills)
2. Is the description in third person, or third person plus a "Use when…" sentence, with no "I can help" or "You can use"? (Best practices)
3. Does the description contain words users would actually type, and name at least one case where the user does not name the domain? (Optimizing descriptions)
4. If another skill in the plugin covers nearby ground, does the description say where this one stops? (Optimizing descriptions)
5. Is every triggering phrase in `description` (not only `when_to_use`) if the skill may be uploaded to claude.ai? (CC skills)
6. Is the `name` lowercase-hyphenated, specific, free of `claude`/`anthropic`, and consistent with the other skills' naming pattern? (Best practices)
7. Does a skill with side effects or user-controlled timing set `disable-model-invocation: true`? (CC skills)
8. Are all frontmatter keys spelled exactly as documented, and does `claude plugin validate` pass? (CC skills)
9. Is `SKILL.md` under 500 lines, with the most important instructions in the first part? (Best practices; CC skills)
10. Does every line tell Claude something it would not do by default? (Best practices; How we use skills)
11. Is there a gotchas section built from observed failures? (How we use skills)
12. Is every reference file linked directly from `SKILL.md`, with a note on what it contains and when to read it? (Best practices; CC skills)
13. Do reference files over 100 lines start with a table of contents? (Best practices)
14. Are rules explained with a reason instead of ALL-CAPS ALWAYS/NEVER, and are hard rules enforced by a hook rather than emphasis? (skill-creator SKILL.md; CC best practices)
15. Does the skill give one default per choice, with an escape hatch, rather than a list of options? (Best practices)
16. Is terminology consistent, and is there no dated "before/after" guidance outside an "Old patterns" section? (Best practices)
17. Does each bundled script say whether to run or read it, handle its own errors, document its constants, and list its dependencies? (Best practices)
18. Are MCP tools named in fully qualified form? (Best practices)
19. Is every `!` command pre-approved in `allowed-tools`, path-safe through `${CLAUDE_SKILL_DIR}` or `${CLAUDE_PLUGIN_ROOT}`, and safe on a non-zero exit? (CC skills)
20. Is there an eval with a no-skill baseline and a `tool_used: Skill` trigger check, including near-miss should-not-trigger prompts, run on every model the plugin targets? (Plugin evals; Best practices; skill-creator SKILL.md)

## Unconfirmed items

- A skill count at which routing degrades. Only the 1% listing budget and "potentially 100+" are documented (section 1).
- Whether thin router commands are a recommended pattern. Anthropic's own plugins use them and the Claude Code team says to reference skills by name, but no docs page recommends them (section 4).
- Whether a router can load a `disable-model-invocation: true` skill. The docs say Claude Code blocks Claude's call, which implies no; this was not tested (section 4).
- Which MCP tool-name form (`Server:tool` or `mcp__plugin_…__tool`) works better inside a Claude Code skill body (section 6).
- The table-of-contents threshold: 100 lines (Best practices) versus 300 lines (skill-creator SKILL.md).
