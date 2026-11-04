#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4.18", "pyyaml"]
# ///
"""Small helpers for edh-companion project folders.

  companion.py where                 print the config file and workspace paths (and whether they exist)
  companion.py projects             list saved projects and showcases (for resuming in a new session)
  companion.py research [project]   show saved research approval, ask-mode, depth and exclusions (+ project override)
  companion.py validate <project>    check research.json / brew*.json / audit*.json against the schemas,
                                     resolve citation IDs, and report stale or contradictory audits
  companion.py goals-hash <project>  fingerprint of PROJECT.md's rules; audits record it so a rule change makes them stale

Exit 0 when everything present is valid, 1 otherwise. Missing files are fine (projects are partial by design).
"""
import glob, hashlib, json, os, re, sys
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMAS = os.path.join(HERE, "..", "schemas")
CONFIG = os.path.join(os.path.expanduser("~"), ".config", "edh-companion", "config.yaml")


def config():
    if os.path.exists(CONFIG):
        with open(CONFIG, encoding="utf-8") as h:
            return yaml.safe_load(h) or {}
    return {}


def workspace():
    """One persistent workspace, wherever Claude Code starts (schemas/README.md):
    $EDH_COMPANION_HOME, then a folder the player marked as a workspace here (EDHCompanion/workspace.yaml),
    then the config file's workspace, then ~/Documents/EDHCompanion."""
    if os.environ.get("EDH_COMPANION_HOME"):
        return os.path.abspath(os.path.expanduser(os.environ["EDH_COMPANION_HOME"])), "EDH_COMPANION_HOME"
    if os.path.exists(os.path.join("EDHCompanion", "workspace.yaml")):
        return os.path.abspath("EDHCompanion"), "marked folder in the current directory"
    ws = config().get("workspace")
    if ws:
        return os.path.expanduser(ws), "config"
    return os.path.join(os.path.expanduser("~"), "Documents", "EDHCompanion"), "default"


def current_project(start="."):
    """The project Claude Code was started in: the nearest folder (this one or a parent) with PROJECT.md,
    or a folder directly under <workspace>/projects/. None when started elsewhere."""
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, "PROJECT.md")):
            return d
        parent = os.path.dirname(d)
        if os.path.basename(parent) == "projects" and os.path.isdir(d):
            return d
        if parent == d:
            return None
        d = parent


def section(path, heading):
    """Text under a '## heading' in a Markdown file, or ''."""
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as h:
        m = re.search(r"^## " + re.escape(heading) + r"\s*\n(.*?)(?=^## |\Z)", h.read(), re.M | re.S)
    return m.group(1).strip() if m else ""


def research_prefs(project=None):
    """Saved research choices from the config, plus a project's 'Research preferences' section (which wins)."""
    r = config().get("research") or {}
    proj = section(os.path.join(project, "PROJECT.md"), "Research preferences") if project else ""
    return {"approved": r.get("approved") or {}, "excluded": r.get("excluded") or [], "approval": r.get("approval"),
            "depth": r.get("depth"), "prefer": r.get("prefer") or [], "status": r.get("status") or {}, "checked": r.get("checked"),
            "project_override": proj, "onboarded": bool(r.get("approved") or r.get("depth") == "skip")}


def first_line(path, heading=None):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as h:
        lines = [x.strip("- ").strip() for x in h if x.strip() and not x.lstrip().startswith("#")]
    return lines[0][:100] if lines else ""


def projects():
    """Projects and showcases in the workspace, newest first, with enough to offer a resume."""
    ws, how = workspace()
    rows = []
    for kind in ("projects", "showcases"):
        base = os.path.join(ws, kind)
        if not os.path.isdir(base):
            continue
        for name in os.listdir(base):
            d = os.path.join(base, name)
            if not os.path.isdir(d):
                continue
            files = [os.path.join(dp, f) for dp, _, fs in os.walk(d) for f in fs]
            rows.append({"kind": kind[:-1], "name": name, "path": d, "updated": max((os.path.getmtime(f) for f in files), default=os.path.getmtime(d)),
                         "goal": first_line(os.path.join(d, "PROJECT.md")), "state": first_line(os.path.join(d, "STATE.md")),
                         "builds": sorted(os.path.basename(f) for f in glob.glob(os.path.join(d, "brew*.json"))),
                         "reports": os.path.isfile(os.path.join(d, "reports", "index.html")) or os.path.isfile(os.path.join(d, "report", "index.html"))})
    return ws, how, sorted(rows, key=lambda r: -r["updated"])


def goals_hash(d):
    """Hash of PROJECT.md with whitespace normalised; None if there's no PROJECT.md."""
    p = os.path.join(d, "PROJECT.md")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as h:
        text = re.sub(r"\s+", " ", h.read()).strip().lower()
    return hashlib.sha1(text.encode()).hexdigest()[:12]


def registry():
    reg = Registry()
    for f in glob.glob(os.path.join(SCHEMAS, "*.schema.json")):
        with open(f, encoding="utf-8") as h:
            reg = reg.with_resource(os.path.basename(f), Resource.from_contents(json.load(h)))
    return reg


def check_schema(path, kind, reg, errors):
    try:
        with open(path, encoding="utf-8") as h:
            doc = json.load(h)
    except Exception as e:  # an unreadable file is an error, not a skip
        errors.append(f"{path}: cannot parse: {e}")
        return None
    schema = reg.get_or_retrieve(f"{kind}.schema.json").value.contents
    for e in Draft202012Validator(schema, registry=reg).iter_errors(doc):
        errors.append(f"{path}: {'/'.join(str(x) for x in e.absolute_path) or '(root)'}: {e.message}")
    return doc


def validate(d):
    reg, errors, notes = registry(), [], []
    research = None
    p = os.path.join(d, "research.json")
    if os.path.exists(p):
        research = check_schema(p, "research", reg, errors)
    if research:
        src = [s["id"] for s in research.get("sources", [])]
        fnd = [f["id"] for f in research.get("findings", [])]
        if len(set(src)) != len(src) or len(set(fnd)) != len(fnd):
            errors.append(f"{p}: duplicate source or finding id")
        known = set(src) | set(fnd)
        for sec in ("findings", "commanders", "card_candidates", "alternatives", "recommendations"):
            for item in research.get(sec, []) or []:
                for ref in item.get("evidence", []) or []:
                    if ref.startswith(("src-", "fnd-")) and ref not in known:
                        errors.append(f"{p}: {sec}: evidence {ref} is not a defined source or finding")
    known = {s["id"] for s in (research or {}).get("sources", [])} | {f["id"] for f in (research or {}).get("findings", [])}
    for bp in sorted(glob.glob(os.path.join(d, "brew*.json"))):
        brew = check_schema(bp, "brew", reg, errors)
        if not brew:
            continue
        ids = [r["id"] for r in brew.get("recommendations", [])]
        if len(set(ids)) != len(ids):
            errors.append(f"{bp}: duplicate recommendation id")
        for r in brew.get("recommendations", []):
            for ref in r.get("evidence", []) or []:
                if research is not None and ref.startswith(("src-", "fnd-")) and ref not in known:
                    errors.append(f"{bp}: {r['id']}: evidence {ref} not in research.json")
        if brew.get("decklist") and not os.path.exists(os.path.join(d, brew["decklist"])):
            errors.append(f"{bp}: decklist {brew['decklist']} not found")
        ap = os.path.join(d, os.path.basename(bp).replace("brew", "audit", 1))
        if not os.path.exists(ap):
            notes.append(f"{os.path.basename(bp)} v{brew.get('version')}: not audited")
            continue
        audit = check_schema(ap, "audit", reg, errors)
        if not audit:
            continue
        seen = (audit.get("subject") or {}).get("deck") or {}
        gh = (audit.get("subject") or {}).get("goals_hash")
        if seen.get("deck_hash") != brew.get("deck_hash") or seen.get("version") != brew.get("version"):
            notes.append(f"{os.path.basename(ap)}: STALE (audited v{seen.get('version')} {seen.get('deck_hash')}, current v{brew.get('version')} {brew.get('deck_hash')})")
        elif gh and gh != goals_hash(d):
            notes.append(f"{os.path.basename(ap)}: STALE (PROJECT.md rules changed since the audit)")
        else:
            notes.append(f"{os.path.basename(ap)}: current, verdict {audit['verdict']['status']}")
    for ap in sorted(glob.glob(os.path.join(d, "audit*.json"))):
        try:
            with open(ap, encoding="utf-8") as h:
                audit = json.load(h)
        except Exception:
            continue
        if not os.path.exists(ap.replace("audit", "brew", 1)):
            check_schema(ap, "audit", reg, errors)
        st = [c.get("status") for c in audit.get("checks", [])]
        if (audit.get("verdict") or {}).get("status") == "pass" and any(s in ("fail", "unverified") for s in st):
            errors.append(f"{ap}: verdict is pass but a check is fail or unverified")
        ids = [c.get("id") for c in audit.get("checks", [])]
        if len(set(ids)) != len(ids):
            errors.append(f"{ap}: duplicate check id")
    return errors, notes


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("where", "projects", "research", "validate", "goals-hash"):
        sys.exit(__doc__)
    if sys.argv[1] == "where":
        ws, how = workspace()
        print(f"config     {CONFIG} ({'exists' if os.path.exists(CONFIG) else 'not created; optional'})")
        print(f"workspace  {ws} ({how}; {'exists' if os.path.isdir(ws) else 'created on first project'})")
        print(f"projects   {os.path.join(ws, 'projects')}")
        cur = current_project()
        if cur:
            print(f"project    {os.path.basename(cur)} ({cur}; Claude Code started inside it)")
        here = os.path.abspath("EDHCompanion")
        if os.path.isdir(here) and here != ws:
            print(f"note       {here} exists here but isn't the workspace (no workspace.yaml); it is not used")
        return
    if sys.argv[1] == "research":
        proj = sys.argv[2] if len(sys.argv) > 2 else current_project()
        p = research_prefs(proj)
        if not p["onboarded"]:
            print("research approval: not set up yet (asked once, on the first substantial research request; trivial lookups don't ask)")
        else:
            print(f"approved tools: " + (", ".join(f"{k}={v}" + (f" [{p['status'][k]}]" if k in p["status"] else "") for k, v in p["approved"].items()) or "none (no external research)"))
            print(f"excluded:       {', '.join(p['excluded']) or 'none'}")
            print(f"ask before research: {p['approval'] or 'on_change (default)'}")
            print(f"depth:          {p['depth'] or 'comprehensive (default)'}")
            if p["prefer"]:
                print(f"prefer:         {', '.join(p['prefer'])}")
            if p["checked"]:
                print(f"last verified:  {p['checked']}")
        if p["project_override"]:
            print(f"project override ({os.path.basename(proj)}): {p['project_override']}")
        print("Claude Code's own tool permission prompts are separate (see /permissions).")
        return
    if sys.argv[1] == "projects":
        import time
        ws, how, rows = projects()
        print(f"workspace {ws} ({how})")
        cur = current_project()
        if cur:
            print(f"current   {os.path.basename(cur)} (started inside this project: {cur})")
        if not rows:
            print("no projects yet")
        for r in rows:
            when = time.strftime("%Y-%m-%d", time.localtime(r["updated"]))
            extra = ", ".join(x for x in [", ".join(r["builds"]), "page" if r["reports"] else ""] if x)
            print(f"- {r['kind']} {r['name']} ({when}){': ' + r['goal'] if r['goal'] else ''}{' | now: ' + r['state'] if r['state'] else ''}{' | ' + extra if extra else ''}")
        return
    if len(sys.argv) < 3:
        sys.exit(f"usage: companion.py {sys.argv[1]} <project-dir>")
    if sys.argv[1] == "goals-hash":
        print(goals_hash(sys.argv[2]) or "no PROJECT.md")
        return
    errors, notes = validate(sys.argv[2])
    for e in errors:
        print("ERROR", e)
    for n in notes:
        print("NOTE ", n)
    print(f"{len(errors)} error(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
