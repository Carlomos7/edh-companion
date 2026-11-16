#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Claude Code hooks for edh-companion (hooks/hooks.json). Stdlib only and quick: each event exits at once unless it
concerns a project file, and only then starts companion.py.

  hook.py post-write     PostToolUse Write|Edit: a research.json or brew*.json was written → validate its project;
                         problems go back to Claude (exit 2) so it fixes them in the same turn
  hook.py session-start  SessionStart startup|resume: one line of project status when Claude Code starts inside a
                         project (its STATE.md first line and audit states); silent elsewhere
  hook.py subagent-stop  SubagentStop (auditor): if the auditor wrote an audit*.json in the last 30 minutes that doesn't
                         validate, block the stop with the errors so it fixes the file
Reads the hook's JSON on stdin. Never writes project files.
"""
import json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
WATCHED = re.compile(r"(?:^|[\\/])(research\.json|brew(?:-[\w-]+)?\.json|audit(?:-[\w-]+)?\.json)$")


def project_of(path):
    d = os.path.dirname(os.path.abspath(path)) if os.path.isfile(path) or "." in os.path.basename(path) else os.path.abspath(path)
    while True:
        if os.path.exists(os.path.join(d, "PROJECT.md")) or os.path.exists(os.path.join(d, "brew.json")) or os.path.exists(os.path.join(d, "research.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def validate(project):
    """(ok, text) from companion.py validate. A missing uv is not a failure of the player's files."""
    try:
        r = subprocess.run(["uv", "run", "--quiet", "--script", os.path.join(HERE, "companion.py"), "validate", project],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return True, ""
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def post_write(ev):
    path = (ev.get("tool_input") or {}).get("file_path") or ""
    if not WATCHED.search(path):
        return 0
    proj = project_of(path)
    if not proj:
        return 0
    ok, out = validate(proj)
    if ok:
        return 0
    errs = [l for l in out.splitlines() if not l.startswith(("WARN", "ok", "audit")) and l.strip()][:15]
    print(f"edh-companion validate failed for {os.path.basename(proj)} after writing {os.path.basename(path)}:\n" + "\n".join(errs), file=sys.stderr)
    return 2


def session_start(ev):
    proj = project_of(os.path.join(ev.get("cwd") or os.getcwd(), "x.md"))
    if not proj:
        return 0
    st = os.path.join(proj, "STATE.md")
    first = ""
    if os.path.exists(st):
        with open(st, encoding="utf-8") as h:
            first = next((l.strip("-* \n") for l in h if l.strip() and not l.startswith("#")), "")
    builds = sorted(f for f in os.listdir(proj) if re.fullmatch(r"brew(?:-[\w-]+)?\.json", f))
    print(f"edh-companion project {os.path.basename(proj)}: {first or 'no STATE.md'}; builds: {', '.join(builds) or 'none'}. "
          f"Read STATE.md before acting; run `companion.py validate` for audit states.")
    return 0


def subagent_stop(ev):
    if ev.get("stop_hook_active"):
        return 0  # already blocked once: don't loop
    kind = str(ev.get("agent_type") or ev.get("subagent_type") or "")
    if kind and "auditor" not in kind:
        return 0
    proj = project_of(os.path.join(ev.get("cwd") or os.getcwd(), "x.md"))
    cands = []
    for root in [r for r in (proj, ev.get("cwd")) if r]:
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if not x.startswith(".") and x not in ("reports", "decklists", "sources", "archive")]
            cands += [os.path.join(dirpath, f) for f in files if re.fullmatch(r"audit(?:-[\w-]+)?\.json", f)]
            if dirpath.count(os.sep) - root.count(os.sep) >= 3:
                dirs[:] = []
    recent = [p for p in set(cands) if time.time() - os.path.getmtime(p) < 1800]
    bad = []
    for p in recent:
        ok, out = validate(os.path.dirname(p))
        if not ok:
            bad.append(f"{p}:\n" + "\n".join(l for l in out.splitlines() if os.path.basename(p) in l or "audit" in l.lower())[:1500])
    if bad:
        print(json.dumps({"decision": "block", "reason": "audit.json doesn't validate; fix it before finishing:\n" + "\n".join(bad)}))
    return 0


def main():
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        ev = {}
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    fn = {"post-write": post_write, "session-start": session_start, "subagent-stop": subagent_stop}.get(cmd)
    sys.exit(fn(ev) if fn else 0)


if __name__ == "__main__":
    main()
