"""Tier 2 benchmark: what a Claude Code run cost, from a session transcript or from `claude plugin eval` results.

  python tests/bench/session_stats.py SESSION.jsonl [--json OUT]           a real session (~/.claude/projects/<dir>/<id>.jsonl)
  python tests/bench/session_stats.py --eval RESULT.json ... [--json OUT]  eval runs (aggregate-result.json or --json output)

Session transcript (main thread plus subagent transcripts in <id>/subagents/ when present):
  tokens          input, output, cache read, cache creation (each API message counted once, by message id)
  context         largest single-request context (input + cache read + cache creation) = peak context size
  tool calls      by tool name; duplicate calls (same tool + same input); errored tool results; 429/502 seen in results
  subagents       number of subagent transcripts
  wall time       first to last timestamp
Eval runs: per run, the eval's own costUsd, durationSeconds, turns and grader verdicts (the quality measure), plus from
the run's trace.jsonl (kept with --keep-temp): tokens by kind as the CLI's result reports them for every model call
(uncached input, cache creation, cache read, output), tool calls (main thread and subagents), duplicate calls, errored
tool results, permission denials and subagents spawned. Prices are never computed here.
Prints aggregates only (no message content), so results can be shared. Fields a file doesn't have are reported as
null ("unavailable"), never guessed.
"""
import argparse, collections, glob, hashlib, json, os, re, statistics, sys
from datetime import datetime


def rows(path):
    with open(path, encoding="utf-8") as h:
        for line in h:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def stats(paths):
    seen_msg, tok = set(), collections.Counter()
    peak, tools, dup, errors, codes, ts = 0, collections.Counter(), collections.Counter(), 0, collections.Counter(), []
    have_usage = False
    for p in paths:
        for d in rows(p):
            if d.get("timestamp"):
                ts.append(d["timestamp"])
            m = d.get("message") or {}
            if d.get("type") == "assistant":
                u, mid = m.get("usage"), m.get("id")
                if u and mid not in seen_msg:
                    seen_msg.add(mid)
                    have_usage = True
                    for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                        tok[k] += u.get(k) or 0
                    peak = max(peak, (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0))
                for b in m.get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        tools[b["name"]] += 1
                        dup[(b["name"], hashlib.sha1(json.dumps(b.get("input"), sort_keys=True).encode()).hexdigest())] += 1
            elif d.get("type") == "user":
                for b in m.get("content") or [] if isinstance(m.get("content"), list) else []:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        errors += bool(b.get("is_error"))
                        text = json.dumps(b.get("content"))
                        for code in ("429", "502", "503"):
                            if re.search(rf"\b(HTTP |status |Error |error: ){code}\b|\b{code} (Too Many|Bad Gateway|Service)", text):
                                codes[code] += 1
    span = None
    if len(ts) > 1:
        t = sorted(datetime.fromisoformat(x.replace("Z", "+00:00")) for x in ts)
        span = round((t[-1] - t[0]).total_seconds() / 60, 1)
    return {"files": len(paths), "subagents": len(paths) - 1, "wall_minutes": span,
            "tokens": dict(tok) if have_usage else None, "peak_context_tokens": peak if have_usage else None,
            "api_messages": len(seen_msg), "tool_calls": sum(tools.values()), "by_tool": dict(tools.most_common()),
            "duplicate_tool_calls": sum(n - 1 for n in dup.values() if n > 1), "tool_errors": errors, "http_errors_seen": dict(codes)}


def trace_stats(path):
    """One eval run's stream-json trace. Token totals come from the final result event's modelUsage (every model call,
    subagents and server tools included): per-message usage in a stream is partial, so it isn't summed."""
    calls, tools, dup, errors, sub_calls, res = set(), collections.Counter(), collections.Counter(), 0, 0, None
    for d in rows(path):
        m = d.get("message") or {}
        if d.get("type") == "assistant":
            for b in m.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id") not in calls:
                    calls.add(b.get("id"))
                    tools[b["name"]] += 1
                    sub_calls += bool(d.get("parent_tool_use_id"))
                    dup[(b["name"], hashlib.sha1(json.dumps(b.get("input"), sort_keys=True).encode()).hexdigest())] += 1
        elif d.get("type") == "user" and isinstance(m.get("content"), list):
            errors += sum(1 for b in m["content"] if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"))
        elif d.get("type") == "result":
            res = d
    mu = list(((res or {}).get("modelUsage") or {}).values())
    tok = {k: sum(u.get(src) or 0 for u in mu) for k, src in (("input_uncached", "inputTokens"), ("cache_creation", "cacheCreationInputTokens"),
                                                               ("cache_read", "cacheReadInputTokens"), ("output", "outputTokens"))} if mu else None
    return {"tokens": tok, "models": sorted((res or {}).get("modelUsage") or {}), "tool_calls": sum(tools.values()), "subagent_tool_calls": sub_calls,
            "by_tool": dict(tools.most_common()), "duplicate_tool_calls": sum(n - 1 for n in dup.values() if n > 1), "tool_errors": errors,
            "permission_denials": len((res or {}).get("permission_denials") or []) if res else None,
            "subagents": ((res or {}).get("subagent_stats") or {}).get("spawned") if res else None}


def eval_runs(files):
    """Every run of every case in eval result files, with its trace stats when the trace still exists."""
    out = []
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        ver = next((p.get("version") for p in d["suite"].get("plugins", [])), None)
        for c in d["cases"]:
            for arm, runs in c["arms"].items():
                for r in runs:
                    tp = r.get("tracePath")
                    out.append({"case": c["name"], "version": ver, "arm": arm, "passed": r.get("passed"), "score": r.get("score"),
                                "graders": {g["name"]: g.get("passed") for g in r.get("graders", [])}, "error": r.get("error"),
                                "cost_usd": r.get("costUsd"), "judge_cost_usd": r.get("judgeCostUsd"), "duration_s": r.get("durationSeconds"),
                                "turns": r.get("turns"), "trace": trace_stats(tp) if tp and os.path.exists(tp) else None})
    return out


def eval_table(runs):
    groups = collections.defaultdict(list)
    for r in runs:
        groups[(r["case"], r["version"])].append(r)
    med = lambda xs, d=2: "–" if not xs else (f"{statistics.median(xs):.{d}f}" + (f" [{min(xs):.{d}f}–{max(xs):.{d}f}]" if len(xs) > 1 and min(xs) != max(xs) else ""))
    print("| Case | Version | Runs | Passed | Cost USD | Duration s | Turns | Uncached in | Cache write | Cache read | Output | Tool calls | Dup | Errors | Denied | Subagents |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for (case, ver), rs in sorted(groups.items()):
        tr = [r["trace"] for r in rs if r["trace"]]
        tk = lambda k: [t["tokens"][k] for t in tr if t["tokens"]]
        tv = lambda k: [t[k] for t in tr if t[k] is not None]
        print(f"| {case} | {ver} | {len(rs)} | {sum(1 for r in rs if r['passed'])}/{len(rs)} | {med([r['cost_usd'] for r in rs if r['cost_usd'] is not None], 3)} | "
              f"{med([r['duration_s'] for r in rs if r['duration_s'] is not None], 0)} | {med([r['turns'] for r in rs if r['turns'] is not None], 0)} | "
              f"{med(tk('input_uncached'), 0)} | {med(tk('cache_creation'), 0)} | {med(tk('cache_read'), 0)} | {med(tk('output'), 0)} | "
              f"{med(tv('tool_calls'), 0)} | {med(tv('duplicate_tool_calls'), 0)} | {med(tv('tool_errors'), 0)} | {med(tv('permission_denials'), 0)} | {med(tv('subagents'), 0)} |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session", nargs="?")
    ap.add_argument("--eval", nargs="+", metavar="RESULT_JSON")
    ap.add_argument("--json")
    a = ap.parse_args()
    if a.eval:
        runs = eval_runs(a.eval)
        if a.json:
            json.dump(runs, open(a.json, "w", encoding="utf-8"), indent=1)
        return eval_table(runs)
    if not a.session:
        ap.error("give a SESSION.jsonl or --eval RESULT.json ...")
    sub = os.path.join(os.path.splitext(a.session)[0], "subagents")
    paths = [a.session] + sorted(glob.glob(os.path.join(sub, "*.jsonl")))
    s = stats(paths)
    if a.json:
        json.dump(s, open(a.json, "w", encoding="utf-8"), indent=1)
    t = s["tokens"] or {}
    print(f"files {s['files']} (subagents {s['subagents']}), wall {s['wall_minutes']} min, API messages {s['api_messages']}")
    print("tokens " + (f"in {t.get('input_tokens')}, out {t.get('output_tokens')}, cache read {t.get('cache_read_input_tokens')}, "
                       f"cache write {t.get('cache_creation_input_tokens')}; peak context {s['peak_context_tokens']}" if t else "unavailable"))
    print(f"tool calls {s['tool_calls']}, duplicates {s['duplicate_tool_calls']}, errors {s['tool_errors']}, http errors {s['http_errors_seen']}")
    print("by tool: " + ", ".join(f"{k} {v}" for k, v in list(s["by_tool"].items())[:12]))


if __name__ == "__main__":
    sys.exit(main())
