"""Benchmark probe: logs every urllib request and every time.sleep in any Python process with tests/bench on PYTHONPATH.

Loaded automatically by Python at start-up (site module) when EDHC_BENCH_LOG is set; writes one JSON line per event (t = start, epoch seconds):
  request  method, url, body hash, status, ms (until the headers arrive); a second line with read_ms and bytes when
           the body is read (urlopen returns at the headers, so a slow body would otherwise be invisible)
  sleep    seconds asked, ms slept, where (file:function) and the calling source line, so a pacing wait, a 429 hold
           and a retry backoff can be told apart without guessing
Works through `uv run --script` subprocesses because they inherit PYTHONPATH. Changes no behaviour: the real urlopen,
read and sleep are always called. Logs URLs and code lines only, never response bodies.
"""
import os

if os.environ.get("EDHC_BENCH_LOG"):
    import hashlib, json, linecache, sys, time, urllib.request

    _real, _sleep = urllib.request.urlopen, time.sleep
    _log = os.environ["EDHC_BENCH_LOG"]

    def _write(row):
        with open(_log, "a", encoding="utf-8") as h:
            h.write(json.dumps(dict(row, pid=os.getpid())) + "\n")

    def _row(req, status, t0):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        data = getattr(req, "data", None)
        return {"kind": "request", "id": f"{os.getpid()}-{t0}", "t": round(time.time() - (time.perf_counter() - t0), 3), "method": req.get_method() if hasattr(req, "get_method") else "GET",
                "url": url, "body": hashlib.sha1(data).hexdigest()[:12] if data else None, "status": status,
                "ms": round((time.perf_counter() - t0) * 1000)}

    def urlopen(req, *a, **k):
        t0 = time.perf_counter()
        try:
            r = _real(req, *a, **k)
        except Exception as e:  # noqa: BLE001
            _write(_row(req, getattr(e, "code", None) or type(e).__name__, t0))
            raise
        row = _row(req, getattr(r, "status", 200), t0)
        _write(row)
        orig = r.read

        def read(*ra, **rk):
            t1, w1 = time.perf_counter(), time.time()
            try:
                data = orig(*ra, **rk)
            except Exception as e:  # noqa: BLE001  e.g. a timeout while reading the body
                _write({"kind": "read", "id": row["id"], "t": round(w1, 3), "read_ms": round((time.perf_counter() - t1) * 1000), "error": type(e).__name__})
                raise
            _write({"kind": "read", "id": row["id"], "t": round(w1, 3), "read_ms": round((time.perf_counter() - t1) * 1000), "bytes": len(data or b"")})
            return data
        r.read = read
        return r

    def sleep(secs):
        f = sys._getframe(1)
        if f.f_code.co_name == "_wait" and f.f_back:  # edhcore waits go through Client._wait; its caller's line says why
            f = f.f_back
        where = f"{os.path.basename(f.f_code.co_filename)}:{f.f_code.co_name}"
        line = linecache.getline(f.f_code.co_filename, f.f_lineno).strip()[:90]
        t0, w0 = time.perf_counter(), time.time()
        try:
            _sleep(secs)
        finally:
            _write({"kind": "sleep", "t": round(w0, 3), "asked": round(secs, 3), "ms": round((time.perf_counter() - t0) * 1000), "where": where, "line": line})

    urllib.request.urlopen = urlopen
    time.sleep = sleep
