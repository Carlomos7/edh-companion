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
  companion.py research-plan <project> --worker slug:role:subject1,subject2 [--worker ...]
                                     record the parallel research workers a merge expects (research.plan.json)
  companion.py merge-research <project> [--allow-partial]
                                     merge research.part-<slug>.json files into research.json (validated, idempotent)
  companion.py research-find <project> [--card NAME] [--text WORDS] [--class CLASS] [--limit N]
                                     compact matching findings, candidates and rankings with their evidence

Exit 0 when everything present is valid, 1 otherwise. Missing files are fine (projects are partial by design).
"""
import argparse, copy, datetime, glob, hashlib, json, os, re, shutil, sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
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


PLAN = "research.plan.json"
EDHREC = ("inclusion_pct", "decks", "total_decks")


def today():
    return datetime.date.today().isoformat()


def norm_url(u):
    """Key for spotting the same page twice: lowercase host without www./m., http = https, no trailing slash,
    utm_* or fragment; YouTube links (watch, youtu.be, shorts, live, embed) reduce to the video id."""
    p = urlsplit(str(u).strip())
    host, q = re.sub(r"^(www|m)\.", "", p.netloc.lower()), parse_qsl(p.query, keep_blank_values=True)
    if host in ("youtube.com", "youtu.be"):
        m = re.fullmatch(r"/(?:shorts|live|embed)/([^/]+)/?", p.path)
        vid = p.path.strip("/") if host == "youtu.be" else m.group(1) if m else dict(q).get("v")
        if vid:
            return "youtube:" + vid
    q = sorted((k, v) for k, v in q if not k.lower().startswith("utm_"))
    return urlunsplit(("https" if p.scheme.lower() in ("http", "https") else p.scheme.lower(), host, p.path.rstrip("/"), urlencode(q), ""))


def evidence_lists(doc):
    """(top-level section, list) for every evidence list in a research.json, wherever it is nested."""
    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get("evidence"), list):
                yield x["evidence"]
            for k, v in x.items():
                if k != "evidence":
                    yield from walk(v)
        elif isinstance(x, list):
            for v in x:
                yield from walk(v)
    for sec, v in doc.items():
        if sec not in ("sources", "methodology"):
            for ev in walk(v):
                yield sec, ev
    if isinstance(doc.get("feasibility"), dict) and isinstance(doc["feasibility"].get("commanders"), list):
        yield "feasibility", doc["feasibility"]["commanders"]  # names, but any src-/fnd- ref there must resolve


def edhrec_problems(c):
    pct, n, tot = (c.get(k) for k in EDHREC)
    if tot is not None and tot <= 0:
        return [f"total_decks {tot} must be > 0"]
    if tot is not None and n is not None and n > tot:
        return [f"decks {n} > total_decks {tot}"]
    if None not in (pct, n, tot) and abs(pct - 100 * n / tot) > 2:
        return [f"inclusion_pct {pct} != {100 * n / tot:.1f} (decks/total_decks)"]
    return []


HARD_REF_SECTIONS = ("findings", "commanders", "card_candidates", "alternatives", "recommendations")  # checked since 7.8


def research_problems(doc, known=(), soft=None):
    """Consistency problems schemas can't express: duplicate IDs/URLs, dangling refs, future dates, EDHREC maths.
    With a `soft` list, checks newer than 7.8 go there instead (warnings), so existing projects stay valid."""
    out, now = [], today()
    warn = out if soft is None else soft
    src = [s.get("id") for s in doc.get("sources", [])]
    fnd = [f.get("id") for f in doc.get("findings", [])]
    if len(set(src)) != len(src) or len(set(fnd)) != len(fnd):
        out.append("duplicate source or finding id")
    ids = set(src) | set(fnd) | set(known)
    for sec, ev in evidence_lists(doc):
        for ref in ev:
            if isinstance(ref, str) and ref.startswith(("src-", "fnd-")) and ref not in ids:
                (out if sec in HARD_REF_SECTIONS else warn).append(f"{sec}: evidence {ref} is not a defined source or finding")
    first = {}
    for s in doc.get("sources", []):
        k = norm_url(s.get("url", ""))
        if k in first:
            warn.append(f"sources: {s.get('id')} has the same URL as {first[k]}")
        first.setdefault(k, s.get("id"))
        for f in ("accessed", "published"):
            if isinstance(s.get(f), str) and s[f] > now:
                warn.append(f"sources: {s.get('id')}: {f} {s[f]} is in the future")
    for r in doc.get("rankings", []) or []:
        for c in r.get("cards", []):
            warn += [f"rankings: {r.get('group')}: {(c.get('card') or {}).get('name')}: {m}" for m in edhrec_problems(c)]
    for c in doc.get("card_candidates", []) or []:
        warn += [f"card_candidates: {(c.get('card') or {}).get('name')}: {m}" for m in edhrec_problems(c)]
    return out


def validate(d):
    reg, errors, notes = registry(), [], []
    research = None
    p = os.path.join(d, "research.json")
    if os.path.exists(p):
        research = check_schema(p, "research", reg, errors)
    if research:
        warns = []
        errors += [f"{p}: {m}" for m in research_problems(research, soft=warns)]
        notes += [f"WARN  {p}: {m}" for m in warns]
    pp = os.path.join(d, PLAN)
    if os.path.exists(pp):
        plan = check_schema(pp, "research-plan", reg, errors) or {}
        gaps = " ".join(g for g in (research or {}).get("gaps", []) if isinstance(g, str))
        # partial/failed workers are fine once merge-research recorded their gap; pending ones are still owed
        pend = [w.get("slug") for w in plan.get("workers", []) if w.get("status") == "pending"
                or (w.get("status") in ("partial", "failed") and f"research incomplete: worker {w.get('slug')} (" not in gaps)]
        if pend:
            errors.append(f"{pp}: research incomplete: worker(s) not merged: {', '.join(map(str, pend))} (run merge-research)")
    parts = sorted(os.path.basename(x) for x in glob.glob(os.path.join(d, "research.part-*.json")))
    if parts:
        errors.append(f"{d}: research incomplete: unmerged {', '.join(parts)} (run merge-research)")
    cp = os.path.join(d, "candidates.json")
    if os.path.exists(cp) and os.path.exists(p) and os.path.getmtime(cp) < os.path.getmtime(p):
        notes.append("candidates.json stale (older than research.json)")
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


def dump(doc):
    return json.dumps(doc, indent=1, ensure_ascii=False) + "\n"


def write_atomic(path, text):
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as h:
        h.write(text)
    os.replace(path + ".tmp", path)


def load(path):
    with open(path, encoding="utf-8") as h:
        return json.load(h)


def research_plan(d, specs):
    """Create or extend research.plan.json; existing workers are never reset."""
    pp = os.path.join(d, PLAN)
    plan = load(pp) if os.path.exists(pp) else {"schema_version": "1.0", "created": today(), "workers": []}
    have = {w["slug"] for w in plan["workers"]}
    for spec in specs:
        slug, role, subjects = (spec.split(":", 2) + ["", ""])[:3]
        if not re.fullmatch(r"[a-z0-9-]+", slug) or not role.strip():
            sys.exit(f"bad --worker {spec!r}: use slug:role:subject1,subject2 (slug is a-z, 0-9, -)")
        if slug in have:
            print(f"kept   {slug} (already planned)")
            continue
        have.add(slug)
        plan["workers"].append({"slug": slug, "role": role.strip(), "subjects": [s.strip() for s in subjects.split(",") if s.strip()],
                                "id_prefix": slug, "status": "pending", "part_hash": None})
        print(f"added  {slug}: research.part-{slug}.json, IDs src-{slug}-001 / fnd-{slug}-001")
    os.makedirs(d, exist_ok=True)
    write_atomic(pp, dump(plan))
    print(f"{PLAN}: {len(plan['workers'])} worker(s)")


def union(a, b):
    return a + [x for x in b if x not in a]


def secs(ts):
    return sum(int(x) * 60 ** i for i, x in enumerate(reversed(ts.split(":"))))


def merge_cards(doc, dst, items, where, stats):
    """Merge card entries by name: evidence is unioned; differing EDHREC numbers become a disagreement, never an average."""
    by = {}
    for c in dst:
        by.setdefault(c["card"]["name"].lower(), c)
    for c in items:
        keep = by.get(c["card"]["name"].lower())
        if keep is None:
            dst.append(c)
            by[c["card"]["name"].lower()] = c
            stats["cards added"] += 1
            continue
        a = {k: keep[k] for k in EDHREC if keep.get(k) is not None}
        b = {k: c[k] for k in EDHREC if c.get(k) is not None}
        diff = b if a and any(k in a and a[k] != v for k, v in b.items()) else {}
        if not a:
            keep.update(b)
        # any other conclusion (theme_fit, relevance, role, synergy, rank, why, ...) that differs is recorded, never dropped
        for k, v in c.items():
            if k in ("card", "evidence", *EDHREC) or v is None:
                continue
            if keep.get(k) is None:
                keep[k] = v
            elif keep[k] != v:
                diff[k] = v
        if diff:
            disagree(doc, f"{keep['card']['name']}{where}", {k: keep.get(k) for k in diff}, keep["evidence"], diff, c["evidence"])
            stats["disagreements"] += 1
        keep["evidence"] = union(keep["evidence"], c["evidence"])
        stats["cards merged by name"] += 1


def disagree(doc, topic, a, ev_a, b, ev_b):
    fmt = lambda x: "; ".join(f"{k} {v if isinstance(v, (str, int, float)) else json.dumps(v, ensure_ascii=False)}" for k, v in x.items())
    doc.setdefault("disagreements", []).append({
        "topic": f"Workers differ on {topic}: {', '.join(b)}",
        "positions": [{"position": fmt(a), "evidence": list(ev_a)}, {"position": fmt(b), "evidence": list(ev_b)}],
        "explanation": "Parallel research workers reported different values; the first is kept, not averaged."})


def merge_part(doc, part, remap, stats):
    seen = {}
    for s in doc["sources"]:
        seen.setdefault(norm_url(s["url"]), s)
    for s in part["sources"]:
        keep = seen.get(norm_url(s["url"]))
        if keep is None:
            doc["sources"].append(s)
            seen[norm_url(s["url"])] = s
            stats["sources added"] += 1
            continue
        remap[s["id"]] = keep["id"]
        ts = union(keep.get("timestamps") or [], s.get("timestamps") or [])
        if ts:
            keep["timestamps"] = sorted(ts, key=secs)
        stats["duplicate URLs folded"] += 1
    stats["findings added"] += len(part["findings"])
    merge_cards(doc, doc.setdefault("card_candidates", []), part.get("card_candidates", []), "", stats)
    groups = {}
    for r in doc.get("rankings", []):
        groups.setdefault(r["group"].lower(), r)
    for r in part.get("rankings", []):
        g = groups.get(r["group"].lower())
        if g is None:
            doc.setdefault("rankings", []).append(r)
            groups[r["group"].lower()] = r
            stats["cards added"] += len(r["cards"])
        else:
            merge_cards(doc, g["cards"], r["cards"], f" ({g['group']})", stats)
    m, pm = doc["methodology"], part["methodology"]
    for k, v in pm.get("coverage", {}).items():
        m["coverage"][k] = m["coverage"].get(k, 0) + v
    for k in ("tools_used", "tools_failed", "workers"):
        if pm.get(k):
            m[k] = union(m.get(k) or [], pm[k])
    if pm.get("sources_reviewed") is not None:
        m["sources_reviewed"] = (m.get("sources_reviewed") or 0) + pm["sources_reviewed"]
    for k, v in pm.items():
        m.setdefault(k, v)
    for k, v in part.items():  # findings, commanders, gaps, alternatives, ...: appended; missing scalars filled in
        if k in ("schema_version", "version", "created", "project", "scope", "methodology", "sources", "card_candidates", "rankings"):
            continue
        if isinstance(v, list):
            doc[k] = union(doc.get(k) or [], v)
        elif doc.get(k) is None:
            doc[k] = v
        elif v is not None and v != doc[k]:  # e.g. feasibility: keep the first, record the second, never drop it
            keep, strip = doc[k], lambda o: {x: y for x, y in o.items() if x != "evidence"} if isinstance(o, dict) else o
            if isinstance(keep, dict) and isinstance(v, dict) and strip(keep) == strip(v):
                if v.get("evidence"):
                    keep["evidence"] = union(keep.get("evidence") or [], v["evidence"])
                continue
            a, b = (strip(keep), strip(v)) if isinstance(keep, dict) and isinstance(v, dict) else ({k: keep}, {k: v})
            diff = [x for x in set(a) | set(b) if a.get(x) != b.get(x)]
            disagree(doc, k, {x: a.get(x) for x in sorted(diff)}, (keep.get("evidence") if isinstance(keep, dict) else None) or [],
                     {x: b.get(x) for x in sorted(diff)}, (v.get("evidence") if isinstance(v, dict) else None) or [])
            stats["disagreements"] += 1


def merge_research(d, allow_partial=False):
    """Merge the plan's research.part-<slug>.json files into research.json. Returns the exit code."""
    reg, errs = registry(), []
    pp, rp = os.path.join(d, PLAN), os.path.join(d, "research.json")
    if not os.path.exists(pp):
        print(f"no {PLAN}: run research-plan before spawning workers")
        return 1
    plan = check_schema(pp, "research-plan", reg, errs)
    base = check_schema(rp, "research", reg, errs) if os.path.exists(rp) else None
    if errs:
        print("\n".join(["cannot merge, fix first:"] + errs[:8]))
        return 1
    base_ids = {x["id"] for x in (base or {}).get("sources", []) + (base or {}).get("findings", [])}
    base_urls = {norm_url(s["url"]) for s in (base or {}).get("sources", [])}
    merged, tidy, short, conflicts = [], [], [], []
    for w in plan["workers"]:
        slug, name = w["slug"], f"research.part-{w['slug']}.json"
        path = os.path.join(d, name)
        if not os.path.exists(path):
            if w["status"] == "pending":  # merged / partial / failed workers already have their content or gap filed
                short.append((w, "pending", "missing"))
            continue
        with open(path, "rb") as h:
            digest = hashlib.sha256(h.read()).hexdigest()
        if digest == w["part_hash"]:
            tidy.append((w, path, digest))  # merged before; only the file move was left
            continue
        if w["part_hash"]:
            conflicts.append(f"{name}: worker {slug} is already merged but this part differs; plan a new worker instead")
            continue
        perrs = []
        part = check_schema(path, "research", reg, perrs)
        if part is not None and not perrs:
            own = [x["id"] for x in part["sources"] + part["findings"]]
            prefixed = all(re.fullmatch(rf"(src|fnd)-{re.escape(slug)}-[0-9]{{3,}}", i) for i in own)
            # a crash after research.json was replaced but before the plan was saved: every finding is there and every
            # source is there or was folded into an existing one by URL; anything less is a new part and is checked in full
            if prefixed and base_ids & set(own) and all(f["id"] in base_ids for f in part["findings"]) and \
                    all(s["id"] in base_ids or norm_url(s["url"]) in base_urls for s in part["sources"]):
                tidy.append((w, path, digest))
                continue
            perrs += [f"id {i} must start with {i[:3]}-{slug}-" for i in own if not re.fullmatch(rf"(src|fnd)-{re.escape(slug)}-[0-9]{{3,}}", i)]
            perrs += [f"id {i} is already in research.json" for i in own if i in base_ids]
            perrs += research_problems(part, known=base_ids)
            if not (part["methodology"].get("workers") or []):
                perrs.append("methodology.workers has no status")
        if perrs:
            short.append((w, "failed", "invalid: " + "; ".join(e.replace(path + ": ", "") for e in perrs[:3])))
            continue
        bad = [x["status"] for x in part["methodology"]["workers"] if not x["status"].startswith("complete")]
        if bad and (bad[0].startswith("failed") or not allow_partial):
            short.append((w, "failed" if bad[0].startswith("failed") else "partial", bad[0]))
            continue
        merged.append((w, path, digest, part))
        if bad:  # --allow-partial: the partial content is merged and what's missing stays a gap
            short.append((w, "partial", bad[0]))
    if conflicts:
        print("\n".join(conflicts))
        return 1
    if short and not allow_partial:
        print("research incomplete, nothing written:")
        for w, _, why in short:
            print(f"- {w['slug']} ({w['role']}): {why}"[:300])
        print(f"merge-research --allow-partial merges the {len(merged)} complete part(s) plus valid partial ones and records what is missing as gaps")
        return 1

    stats, remap = {k: 0 for k in ("sources added", "duplicate URLs folded", "findings added", "cards added", "cards merged by name", "disagreements")}, {}
    doc = copy.deepcopy(base)
    for w, path, digest, part in merged:
        if doc is None:
            doc = {k: part[k] for k in ("schema_version", "project", "created", "scope") if k in part}
            doc.update(version=0, methodology={"approach": part["methodology"]["approach"], "coverage": {}}, sources=[], findings=[], gaps=[])
        merge_part(doc, copy.deepcopy(part), remap, stats)
    if doc is None and short:  # every worker failed or is missing: still keep the gaps and who ran
        doc = {"schema_version": "1.0", "version": 0, "created": today(), "scope": {"question": "; ".join(s for w, *_ in short for s in w["subjects"]) or "research"},
               "methodology": {"approach": "parallel research workers; none returned usable results", "coverage": {},
                               "workers": [{"role": w["role"], "subjects": w["subjects"], "status": why if why.startswith(("partial", "failed")) else f"failed: {why}"}
                                           for w, _, why in short]},
               "sources": [], "findings": [], "gaps": []}
    if doc is not None:
        for _, ev in evidence_lists(doc):
            ev[:] = list(dict.fromkeys(remap.get(r, r) for r in ev))
        done = {w["slug"] for w, *_ in merged + tidy}
        doc["gaps"] = [g for g in doc["gaps"] if not any(g.startswith(f"research incomplete: worker {s} (") for s in done | {w["slug"] for w, *_ in short})]
        doc["gaps"] += [f"research incomplete: worker {w['slug']} ({w['role']}: {', '.join(w['subjects'])}) {why}"[:300] for w, _, why in short]
        inc = lambda g: g.startswith("research incomplete: worker ")  # sorted, so a re-run with the same gaps writes nothing
        doc["gaps"] = [g for g in doc["gaps"] if not inc(g)] + sorted(g for g in doc["gaps"] if inc(g))
    new_plan = copy.deepcopy(plan)
    for w in new_plan["workers"]:
        for pw, path, digest, *_ in merged + tidy:
            if pw["slug"] == w["slug"]:
                w.update(status="merged", part_hash=digest)
        for pw, status, _ in short:
            if pw["slug"] == w["slug"]:
                w["status"] = status
    changed = doc is not None and dump(doc) != dump(base)
    if not changed and new_plan == plan and not tidy:
        print("nothing to merge")
        return 0

    version = (base or {}).get("version", 0) + (1 if changed else 0)
    vdir = os.path.join(d, "research.parts", f"v{version}")
    if changed:
        doc["version"] = version
        if base:
            os.makedirs(vdir, exist_ok=True)
            shutil.copyfile(rp, os.path.join(vdir, "research.prev.json"))
        tmp = rp + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8", newline="\n") as h:
                h.write(dump(doc))
            errs = []
            check_schema(tmp, "research", reg, errs)
            old = set(research_problems(base)) if base else set()
            errs += [m for m in research_problems(load(tmp)) if m not in old]
            if errs:
                os.remove(tmp)
                print("\n".join(["merge would make research.json invalid, nothing written:"] + errs[:8]))
                return 1
            os.replace(tmp, rp)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise
    write_atomic(pp, dump(new_plan))
    for _, path, *_ in merged + tidy:
        os.makedirs(vdir, exist_ok=True)
        os.replace(path, os.path.join(vdir, os.path.basename(path)))
    print(f"merged {len(merged)} part(s){': ' + ', '.join(w['slug'] for w, *_ in merged) if merged else ''}" +
          (f"; tidied {len(tidy)} already-merged part(s)" if tidy else ""))
    print(", ".join(f"{k} {v}" for k, v in stats.items()))
    for w, _, why in short:
        print(f"gap: {w['slug']} ({w['role']}) {why}"[:200])
    if changed:
        print(f"research.json v{version}" + (f" (previous kept in research.parts/v{version}/research.prev.json)" if base else ""))
    return 0


def research_find(d, card=None, text=None, cls=None, limit=20):
    if not os.path.exists(os.path.join(d, "research.json")):
        sys.exit(f"no research.json in {d}")
    r = load(os.path.join(d, "research.json"))
    titles = {s["id"]: s.get("title", "") for s in r.get("sources", [])}
    words = (text or "").lower().split()
    cardl = (card or "").lower()
    ev = lambda refs: "; ".join(f"{x} {titles[x][:40]}" if x in titles else x for x in refs)
    hit = lambda hay: all(w in hay.lower() for w in words)
    rows = []
    for f in r.get("findings", []):
        if cls and f.get("class") != cls:
            continue
        if card and not any(cardl in c.lower() for c in f.get("cards") or []) and cardl not in f["claim"].lower():
            continue
        if hit(f"{f['claim']} {f.get('explanation') or ''}"):
            rows.append(f"{f['id']} [{f['class']}/{f['confidence']}] {f['claim'][:140]} | {ev(f['evidence'])}")
    if not cls:
        for c in r.get("card_candidates", []):
            if cardl in c["card"]["name"].lower() and hit(f"{c['card']['name']} {c['relevance']} {c.get('synergy') or ''} {c.get('role') or ''}"):
                rows.append(f"candidate {c['card']['name']}: {c['relevance'][:120]} | {ev(c['evidence'])}")
        for g in r.get("rankings", []):
            for c in g["cards"]:
                nums = f" ({c['inclusion_pct']}% {c.get('decks')}/{c.get('total_decks')})" if c.get("inclusion_pct") is not None else ""
                if cardl in c["card"]["name"].lower() and hit(f"{g['group']} {c['card']['name']} {c['why']}"):
                    rows.append(f"rank {g['group']} #{c['rank']} {c['card']['name']}{nums}: {c['why'][:100]} | {ev(c['evidence'])}")
    for x in rows[:limit]:
        print(x)
    print(f"... {len(rows) - limit} more (raise --limit or narrow the search)" if len(rows) > limit else f"{len(rows)} match(es)")


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("research-plan", "merge-research", "research-find"):
        ap = argparse.ArgumentParser(prog=f"companion.py {sys.argv[1]}")
        ap.add_argument("project")
        if sys.argv[1] == "research-plan":
            ap.add_argument("--worker", action="append", required=True, help="slug:role:subject1,subject2")
            a = ap.parse_args(sys.argv[2:])
            return research_plan(a.project, a.worker)
        if sys.argv[1] == "merge-research":
            ap.add_argument("--allow-partial", action="store_true", help="merge complete and valid partial parts and record what is missing as gaps")
            a = ap.parse_args(sys.argv[2:])
            sys.exit(merge_research(a.project, a.allow_partial))
        ap.add_argument("--card")
        ap.add_argument("--text")
        ap.add_argument("--class", dest="cls")
        ap.add_argument("--limit", type=int, default=20)
        a = ap.parse_args(sys.argv[2:])
        return research_find(a.project, a.card, a.text, a.cls, a.limit)
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
        print(n if n.startswith("WARN ") else f"NOTE  {n}")
    print(f"{len(errors)} error(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
