"""Tier 1 benchmark: the deterministic script work behind common tasks, paired across plugin versions, cold then warm.

  uv run --python 3.12 python tests/bench/bench.py LABEL --root base=PATH --root after=PATH [--scenario NAME ...]
         [--repeat 3] [--pause 20]
  python tests/bench/bench.py --table tests/bench/results/LABEL.json          # Markdown summary of a results file

--root NAME=PATH is a checkout of the repo (e.g. a git worktree of a tagged commit); its plugin scripts are run, while
fixtures and this harness always come from this repo, so every version starts from the same files. Several roots are
interleaved (repeat 1: scenario A on every root, scenario B on every root, ...) so network conditions hit them alike.
Scripts run exactly as the skills run them (`uv run --script ...`) in a temp folder with a fresh EDHC_CACHE_DIR, twice:
cold (empty cache), then warm (what a re-check, a second page build or a resumed session pays). uv environments are
warmed first, so "cold" means an empty data cache, not a cold uv.

Every request and sleep is logged by tests/bench/sitecustomize.py. Per step: wall time split into network (union of
request intervals, body read included), waiting (sleeps outside network time: pacing, 429 holds, backoff, each with
the code line that slept) and local (the rest: Python, uv start-up, disk); requests, failures, 429/5xx, slowest request,
bytes printed. The planted-errors audit also scores detection against tests/fixtures/planted-errors/expected.json.
Writes tests/bench/results/LABEL.json after every scenario (aggregates only; temp paths are replaced by <work>).
Not measured here: Claude's tokens and tool calls (session_stats.py).
"""
import argparse, collections, json, os, platform, shutil, statistics, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(REPO, "tests", "fixtures")
KRENKO, PLANTED = os.path.join(FIX, "krenko"), os.path.join(FIX, "planted-errors")
UV = shutil.which("uv")
SCENARIOS = ["lookup-1", "lookup-10", "research", "candidates", "build", "atlas", "optimize", "audit-planted"]

# Five real swaps for the optimization scenario (cut -> add), all mono-red and legal.
SWAPS = {"Goblin Goon": "Goblin Arsonist", "Pashalik Mons": "Massive Raid", "Foundry Street Denizen": "Mogg Fanatic",
         "Skirk Prospector": "Goblin Grenade", "Goblin Instigator": "Kiki-Jiki, Mirror Breaker"}


def script(path, *args):
    return [UV, "run", "--quiet", "--script", path, *args]


def paths(root):
    p = os.path.join(root, "plugins", "edh-companion")
    return {"deck_check": os.path.join(p, "skills", "audit", "scripts", "deck_check.py"),
            "export": os.path.join(p, "skills", "brew", "scripts", "export_deck.py"),
            "site": os.path.join(p, "skills", "present", "scripts", "site_data.py"),
            "build_site": os.path.join(p, "skills", "present", "scripts", "build_site.py"),
            "companion": os.path.join(p, "scripts", "companion.py"),
            "candidates": os.path.join(p, "scripts", "candidates.py"),
            "card_lookup": os.path.join(p, "scripts", "card_lookup.py"),
            "manifest": os.path.join(p, ".claude-plugin", "plugin.json")}


def steps_for(name, work, root):
    """(step, command, output file or None) per scenario; None when this version can't run it. Same inputs on every root."""
    P = paths(root)
    has = lambda k: os.path.exists(P[k])
    fresh = ["--fresh"] if "--fresh" in open(P["deck_check"], encoding="utf-8").read() else []  # what each audit skill runs
    b3, deck = os.path.join(work, "krenko", "brew-b3.json"), os.path.join(KRENKO, "decklists", "b3-v1.txt")
    text = open(deck, encoding="utf-8").read()
    names = [ln[2:].strip() for ln in text.splitlines() if ln[:2] == "1 "]
    j = lambda f: os.path.join(work, f)
    if name.startswith("lookup-"):
        n = int(name.split("-")[1])
        lst = ["Sol Ring"] if n == 1 else names[1:n + 1]
        open(j("lookup.txt"), "w", encoding="utf-8").write("\n".join(lst) + "\n")
        # 8.x: card_lookup.py prints one line per card. 7.8 had no lookup script; its research skill used
        # deck_check --cards-only --json (card data written to a file Claude then reads).
        if has("card_lookup"):
            return [(f"card_lookup names ({n})", script(P["card_lookup"], "names", "--file", j("lookup.txt")), None)]
        return [(f"deck_check --cards-only ({n})", script(P["deck_check"], j("lookup.txt"), "--cards-only", "--json", j("cards.json")), j("cards.json"))]
    if name == "research":
        open(j("names.txt"), "w", encoding="utf-8").write("\n".join(names[:61]) + "\n")
        return [("commander check", script(P["deck_check"], "--commander", "Krenko, Mob Boss"), None),
                ("cards-only 61 names", script(P["deck_check"], j("names.txt"), "--cards-only", "--json", j("cards.json")), j("cards.json"))]
    if name == "candidates":
        return [("candidates", script(P["candidates"], j("krenko")), None)] if has("candidates") else None
    if name == "build":
        return [("deck_check full + cheapest", script(P["deck_check"], b3, "--bracket", "3", "--theme-sets", "m19,m20,fdn", "--cheapest", "--json", j("dc.json")), j("dc.json")),
                ("page data, 2 variants", script(P["site"], "from-workspace", j("krenko"), "--out", j("page/page-data.json"), "--images", "cdn"), None),
                ("export", script(P["export"], b3, "--format", "all", "--out", j("export")), None)]
    if name == "atlas":  # image cache in the work folder (--raw-cache), never the player's ~/.cache
        return [("page data (atlas)", script(P["site"], "from-workspace", j("krenko"), "--out", j("site/page-data.json"), "--images", "atlas"), None),
                ("build_site atlas", script(P["build_site"], j("site/page-data.json"), "--raw-cache", j("img")), None)]
    if name == "optimize":
        swapped = text
        for cut, add in SWAPS.items():
            swapped = swapped.replace(f"1 {cut}\n", f"1 {add}\n")
        open(j("swapped.txt"), "w", encoding="utf-8").write(swapped)
        return [("deck_check before", script(P["deck_check"], deck, "--bracket", "3", "--json", j("before.json")), None),
                ("deck_check after 5 swaps", script(P["deck_check"], j("swapped.txt"), "--bracket", "3", "--json", j("after.json")), None),
                ("validate", script(P["companion"], "validate", j("krenko")), None)]
    if name == "audit-planted":
        exp = json.load(open(os.path.join(PLANTED, "expected.json"), encoding="utf-8"))["decks"]
        return [(f"audit {k}", script(P["deck_check"], os.path.join(PLANTED, d["file"]), "--bracket", str(d["bracket"]), *fresh, "--json", j(f"audit-{k}.json")),
                 j(f"audit-{k}.json")) for k, d in exp.items()]
    raise ValueError(name)


def score(step, out_file):
    """Planted-errors detection for one audit step: planted problems found (right check id, status and card)."""
    d = json.load(open(os.path.join(PLANTED, "expected.json"), encoding="utf-8"))["decks"][step.split(" ", 1)[1]]
    try:
        checks = json.load(open(out_file, encoding="utf-8"))["checks"]
    except (OSError, ValueError):
        return {"planted": len(d["planted"]), "detected": 0, "missed": [p["check"] for p in d["planted"]], "extra": ["no output"]}
    hit = lambda p: any(c["id"] == p["check"] and c["status"] in p["status"] and (p["mentions"] in c.get("detail", "") or p["mentions"] in c.get("cards", []))
                        for c in checks)
    missed = [p["check"] for p in d["planted"] if not hit(p)]
    planted_ids = {p["check"] for p in d["planted"]}
    extra = [f"{c['id']}:{c['status']}" for c in checks if c["status"] != "pass" and c["id"] not in planted_ids]
    return {"planted": len(d["planted"]), "detected": len(d["planted"]) - len(missed), "missed": missed, "extra": extra}


def union(iv):
    tot, end = 0.0, None
    for a, b in sorted(iv):
        if end is None or a > end:
            tot, end = tot + b - a, b
        elif b > end:
            tot, end = tot + b - end, b
    return tot


def split(rows, seconds):
    """Wall time -> network (request + body read intervals), waiting (sleeps not overlapping network), local (the rest)."""
    net = [(r["t"], r["t"] + r["ms"] / 1000) for r in rows if r.get("kind") == "request"]
    net += [(r["t"], r["t"] + r["read_ms"] / 1000) for r in rows if r.get("kind") == "read"]
    slp = [(r["t"], r["t"] + r["ms"] / 1000) for r in rows if r.get("kind") == "sleep"]
    n, both = union(net), union(net + slp)
    return round(n, 2), round(both - n, 2), round(max(0.0, seconds - both), 2)


def request_stats(rows):
    reqs = [r for r in rows if r.get("kind") == "request"]
    reads = collections.defaultdict(int)
    for r in rows:
        if r.get("kind") == "read":
            reads[r["id"]] += r["read_ms"]
    total = [r["ms"] + reads[r["id"]] for r in reqs]
    st = lambda r: r["status"] if isinstance(r["status"], int) else 0
    sleeps = collections.Counter()
    for r in rows:
        if r.get("kind") == "sleep":
            sleeps[f"{r['where']}: {r['line']}"] += r["ms"] / 1000
    return {"requests": len(reqs),
            "failed": sum(1 for r in reqs if st(r) == 0 or st(r) >= 400) + sum(1 for r in rows if r.get("kind") == "read" and "error" in r),
            "http_429": sum(1 for r in reqs if st(r) == 429), "http_5xx": sum(1 for r in reqs if st(r) >= 500),
            "request_ms_sum": sum(total), "request_ms_max": max(total, default=0),
            "slowest": max(((t, r["url"].split("?")[0]) for t, r in zip(total, reqs)), default=None),
            "sleeps": {k: round(v, 2) for k, v in sleeps.most_common()}, "probe_lines_lost": sum(1 for r in rows if r.get("kind") == "lost")}


def endpoints(rows):
    ep, seen = collections.Counter(), collections.Counter()
    for r in rows:
        if r.get("kind") != "request":
            continue
        path = r["url"].split("?")[0].replace("https://", "")
        host = path.split("/")[0]
        ep[host if host.endswith("scryfall.io") else "/".join(path.split("/")[:3])] += 1
        seen[(r["method"], r["url"], r["body"])] += 1
    return dict(ep.most_common()), sum(n - 1 for n in seen.values() if n > 1)


def read_log(log, start):
    if not os.path.exists(log):
        return [], start
    lines = open(log, encoding="utf-8").read().splitlines()
    rows = []
    for x in lines[start:]:
        try:
            rows.append(json.loads(x))
        except ValueError:  # a torn line: counted, never guessed
            rows.append({"kind": "lost"})
    return rows, len(lines)


def run_scenario(name, root):
    work = tempfile.mkdtemp(prefix=f"edhc-bench-{name}-")
    shutil.copytree(KRENKO, os.path.join(work, "krenko"))
    os.makedirs(os.path.join(work, "cache"))
    steps = steps_for(name, work, root)
    if steps is None:
        shutil.rmtree(work, ignore_errors=True)
        return None
    clean = lambda s: s.replace(work, "<work>").replace(root, "<root>").replace(REPO, "<repo>").replace(os.path.expanduser("~"), "~")
    out = []
    for phase in ("cold", "warm"):
        log = os.path.join(work, f"{phase}.jsonl")
        env = dict(os.environ, PYTHONPATH=HERE, EDHC_BENCH_LOG=log, EDHC_CACHE_DIR=os.path.join(work, "cache"), PYTHONIOENCODING="utf-8")
        t_all, per, pos, allrows = time.perf_counter(), [], 0, []
        for step, cmd, out_file in steps:
            t0 = time.perf_counter()
            p = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=work)
            secs = time.perf_counter() - t0
            rows, pos = read_log(log, pos)
            allrows += rows
            net, wait, local = split(rows, secs)
            row = {"step": step, "seconds": round(secs, 2), "network_s": net, "waiting_s": wait, "local_s": local, "exit": p.returncode,
                   "stdout_bytes": len(p.stdout.encode("utf-8")), **request_stats(rows)}
            if out_file and os.path.exists(out_file):
                row["file_bytes"] = os.path.getsize(out_file)
            if name == "audit-planted":
                row["detection"] = score(step, out_file)
            if p.returncode not in (0, 1, 2):
                row["stderr"] = clean(p.stderr.strip()[-300:])
            per.append(row)
        ep, dup = endpoints(allrows)
        tot = request_stats(allrows)
        out.append({"phase": phase, "seconds": round(time.perf_counter() - t_all, 2),
                    **{k: round(sum(s[k] for s in per), 2) for k in ("network_s", "waiting_s", "local_s", "stdout_bytes")},
                    **{k: tot[k] for k in ("requests", "failed", "http_429", "http_5xx", "request_ms_max", "sleeps", "probe_lines_lost")},
                    "duplicates": dup, "by_endpoint": ep, "steps": per})
    shutil.rmtree(work, ignore_errors=True)
    return out


def warm_uv(roots):
    """Resolve each script's uv environment once so the first measured step doesn't pay for package installs."""
    for root in roots.values():
        for p in paths(root).values():
            if p.endswith(".py") and os.path.exists(p):
                subprocess.run(script(p, "--help"), capture_output=True)


def version(root):
    try:
        v = json.load(open(paths(root)["manifest"], encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError):
        v = None
    c = subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "-C", root, "status", "--porcelain", "plugins"], capture_output=True, text=True).stdout.strip())
    return {"plugin_version": v, "commit": c, "uncommitted_changes": dirty}


def show(name, root_name, phases):
    for ph in phases:
        print(f"{name:13} {root_name:6} {ph['phase']:4} {ph['seconds']:6.1f}s  net {ph['network_s']:5.1f} wait {ph['waiting_s']:5.1f} local {ph['local_s']:5.1f}"
              f"  req {ph['requests']:3} dup {ph['duplicates']:2} fail {ph['failed']} 429 {ph['http_429']} 5xx {ph['http_5xx']}  max {ph['request_ms_max']} ms", flush=True)


def run(a):
    roots = {k: os.path.abspath(v) for k, v in (r.split("=", 1) for r in a.root)}
    res = {"label": a.label, "date": time.strftime("%Y-%m-%d %H:%M"), "repeats": a.repeat, "pause_s": a.pause,
           "machine": {"os": platform.platform(), "python": platform.python_version(), "cpus": os.cpu_count()},
           "roots": {k: version(v) for k, v in roots.items()}, "runs": []}
    path = os.path.join(HERE, "results", f"{a.label}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    warm_uv(roots)
    first = True
    for rep in range(1, a.repeat + 1):
        for name in a.scenario or SCENARIOS:
            for rn, root in roots.items():
                if not first:
                    time.sleep(a.pause)  # keep our own runs from tripping Scryfall's rate limit
                first = False
                phases = run_scenario(name, root)
                if phases is None:
                    continue
                res["runs"].append({"repeat": rep, "scenario": name, "root": rn, "phases": phases})
                show(name, rn, phases)
                json.dump(res, open(path, "w", encoding="utf-8"), indent=1)
    print("wrote", path)


def table(files):
    """Median [min–max] per scenario, version and phase across repeats (and across files)."""
    docs = [json.load(open(f, encoding="utf-8")) for f in files]
    runs = [r for d in docs for r in d["runs"]]
    label = {k: v.get("plugin_version") or k for d in docs for k, v in d.get("roots", {}).items()}
    seen = list(dict.fromkeys(r["root"] for r in runs))  # versions in the order they ran
    groups = collections.defaultdict(list)
    for r in runs:
        for ph in r["phases"]:
            groups[(r["scenario"], ph["phase"], r["root"])].append(ph)
    fmt = lambda xs, d=1: (f"{statistics.median(xs):.{d}f}" + (f" [{min(xs):.{d}f}–{max(xs):.{d}f}]" if min(xs) != max(xs) else "")) if xs else "–"
    print("| Scenario | Phase | Version | n | Wall s | Network s | Waiting s | Local s | Requests | Dup | Failed | 429 / 5xx | Slowest request ms | Printed bytes |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    order = {s: i for i, s in enumerate(SCENARIOS)}
    for (s, ph, rn), xs in sorted(groups.items(), key=lambda k: (order.get(k[0][0], 99), k[0][1] != "cold", seen.index(k[0][2]))):
        g = lambda k: [x[k] for x in xs]
        print(f"| {s} | {ph} | {label.get(rn, rn)} | {len(xs)} | {fmt(g('seconds'))} | {fmt(g('network_s'))} | {fmt(g('waiting_s'))} | {fmt(g('local_s'))} | {fmt(g('requests'), 0)} | "
              f"{fmt(g('duplicates'), 0)} | {sum(g('failed'))} | {sum(g('http_429'))} / {sum(g('http_5xx'))} | {fmt(g('request_ms_max'), 0)} | {fmt(g('stdout_bytes'), 0)} |")
    det = collections.defaultdict(lambda: [0, 0, set(), set()])
    for r in runs:
        if r["scenario"] == "audit-planted":
            for ph in r["phases"]:
                for st in ph["steps"]:
                    d, x = st["detection"], det[r["root"]]
                    x[0], x[1] = x[0] + d["detected"], x[1] + d["planted"]
                    x[2].update(f"{st['step'][6:]}:{m}" for m in d["missed"])
                    x[3].update(f"{st['step'][6:]}:{e}" for e in d["extra"])
    for rn, (hit, tot, missed, extra) in det.items():
        print(f"\nDetection {label.get(rn, rn)}: {hit}/{tot} planted problems over all runs; missed {sorted(missed) or 'none'}; other non-pass checks {sorted(extra) or 'none'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label", nargs="?")
    ap.add_argument("--root", action="append", default=[], help="NAME=PATH of a repo checkout (default: this repo, as 'current')")
    ap.add_argument("--scenario", action="append", choices=SCENARIOS)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--pause", type=float, default=20, help="seconds between scenario runs")
    ap.add_argument("--table", nargs="+", metavar="RESULTS_JSON")
    a = ap.parse_args()
    if a.table:
        return table(a.table)
    if not a.label:
        ap.error("give a LABEL (or --table FILES)")
    if not UV:
        sys.exit("uv not found")
    a.root = a.root or [f"current={REPO}"]
    run(a)


if __name__ == "__main__":
    main()
