#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4.18", "pyyaml"]
# ///
"""Small helpers for edh-companion project folders.

  companion.py where                 print the config file and workspace paths (and whether they exist)
  companion.py validate <project>    check research.json / brew*.json / audit*.json against the schemas,
                                     resolve citation IDs, and report stale or contradictory audits

Exit 0 when everything present is valid, 1 otherwise. Missing files are fine (projects are partial by design).
"""
import glob, json, os, sys
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMAS = os.path.join(HERE, "..", "schemas")
CONFIG = os.path.join(os.path.expanduser("~"), ".config", "edh-companion", "config.yaml")


def workspace():
    """Same order as schemas/README.md: ./EDHCompanion, then config, then ~/Documents/EDHCompanion."""
    if os.path.isdir("EDHCompanion"):
        return os.path.abspath("EDHCompanion"), "current folder"
    if os.path.exists(CONFIG):
        with open(CONFIG, encoding="utf-8") as h:
            ws = (yaml.safe_load(h) or {}).get("workspace")
        if ws:
            return os.path.expanduser(ws), "config"
    return os.path.join(os.path.expanduser("~"), "Documents", "EDHCompanion"), "default"


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
        if seen.get("deck_hash") != brew.get("deck_hash") or seen.get("version") != brew.get("version"):
            notes.append(f"{os.path.basename(ap)}: STALE (audited v{seen.get('version')} {seen.get('deck_hash')}, current v{brew.get('version')} {brew.get('deck_hash')})")
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
    if len(sys.argv) < 2 or sys.argv[1] not in ("where", "validate"):
        sys.exit(__doc__)
    if sys.argv[1] == "where":
        ws, how = workspace()
        print(f"config     {CONFIG} ({'exists' if os.path.exists(CONFIG) else 'not created; optional'})")
        print(f"workspace  {ws} ({how}; {'exists' if os.path.isdir(ws) else 'created on first project'})")
        print(f"projects   {os.path.join(ws, 'projects')}")
        return
    if len(sys.argv) < 3:
        sys.exit("usage: companion.py validate <project-dir>")
    errors, notes = validate(sys.argv[2])
    for e in errors:
        print("ERROR", e)
    for n in notes:
        print("NOTE ", n)
    print(f"{len(errors)} error(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
