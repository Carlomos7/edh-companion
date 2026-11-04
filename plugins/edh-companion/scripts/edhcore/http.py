"""One HTTP client for every script: retries by failure class, cross-process pacing, per-endpoint circuit breaker.

Failure classes (per endpoint = host + path template, never a whole provider):
  rate limit   429             not a failure: wait Retry-After (seconds or HTTP date, capped at MAX_WAIT, default 30 s),
                               and hold the whole pacing bucket so other processes wait too; then retry
  transient    5xx, network,   back off 1, 2, 4 s (+ jitter), at most `tries` attempts per call
               timeouts
  request      other 4xx       raised at once as RequestError; the endpoint answered, so it counts as working (a 4xx
                               probe closes an open breaker)
  persistent   BREAK_AFTER calls in a row that used up their retries on the same endpoint: the breaker opens for that
               endpoint only, 60 s then doubling to 10 min; after the cooldown one probe goes through, any answer closes it.
                               Breaker updates are read-modify-write in one cache transaction, so concurrent
                               processes' failures all count
"""
import email.utils, http.client, json, random, socket, ssl, time, urllib.error, urllib.parse, urllib.request

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # atlas can run without certifi
    CTX = None

UA = "edh-companion/8.0 (+https://github.com/Carlomos7/edh-companion)"
MAX_WAIT = 60
BREAK_AFTER = 3
COOLDOWN, MAX_COOLDOWN = 60.0, 600.0
# Scryfall: search/named/collection 2 per second, the rest 10 per second; Spellbook asks for sparse requests.
PACE = [("api.scryfall.com/cards/search", "scryfall-slow", 0.5), ("api.scryfall.com/cards/named", "scryfall-slow", 0.5),
        ("api.scryfall.com/cards/collection", "scryfall-slow", 0.5), ("api.scryfall.com", "scryfall", 0.1),
        ("backend.commanderspellbook.com", "spellbook", 1.0)]
TRANSIENT = (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, http.client.HTTPException)


class RequestError(RuntimeError):
    def __init__(self, url, code, body=""):
        super().__init__(f"{url}: HTTP {code}")
        self.code, self.body = code, body


class Unavailable(RuntimeError):
    """The endpoint couldn't be used: breaker open, retries used up, rate-limited throughout, or not allowed."""
    def __init__(self, endpoint, reason, until=None):
        super().__init__(f"{endpoint} unavailable: {reason}")
        self.endpoint, self.reason, self.until = endpoint, reason, until


def endpoint(url):
    u = urllib.parse.urlsplit(url)
    parts = [p for p in u.path.split("/") if p]
    if len(parts) >= 2 and len(parts[1]) == 36 and parts[1].count("-") == 4:
        parts[1] = ":id"
    return u.netloc + ("/" + "/".join(parts[:2]) if parts else "")


def bucket(url):
    ep = endpoint(url)
    for prefix, name, interval in PACE:
        if ep.startswith(prefix):
            return name, interval
    return None, 0.0


def retry_after(err, now):
    v = (getattr(err, "headers", None) or {}).get("Retry-After")
    if v is None:
        return None
    v = str(v).strip()
    if v.isdigit():
        return float(v)
    try:
        return max(0.0, email.utils.parsedate_to_datetime(v).timestamp() - now)
    except (TypeError, ValueError):
        return None


class Client:
    def __init__(self, cache=None, policy=None, tries=3, sleep=time.sleep, now=time.time, jitter=random.random, timeout=60):
        from .cache import Cache
        self.cache = cache if cache is not None else Cache(mode="off")
        self.policy = policy
        self.tries, self.sleep, self.now, self.jitter, self.timeout = tries, sleep, now, jitter, timeout
        self.requests = 0
        self.unavailable = {}  # endpoint -> reason, for reports

    def _wait(self, secs):
        if secs > 0:
            self.sleep(min(secs, MAX_WAIT))

    def get_json(self, url):
        return json.loads(self.request(url))

    def post_json(self, url, body):
        return json.loads(self.request(url, json.dumps(body).encode(), {"Content-Type": "application/json"}))

    def request(self, url, data=None, headers=None, accept="application/json"):
        ep = endpoint(url)
        host = urllib.parse.urlsplit(url).netloc
        if self.policy and host and (why := self.policy.blocked(host)):
            self.unavailable[ep] = why
            raise Unavailable(ep, why)
        st, now, probe = self.cache.breaker(ep), self.now(), False
        if st["open_until"] and now >= st["open_until"]:
            def claim(cur):  # cooldown over: one process claims the probe and keeps others out while it runs
                nonlocal probe
                probe = bool(cur["open_until"]) and now >= cur["open_until"]
                return dict(cur, open_until=now + 30) if probe else cur
            st = self.cache.update_breaker(ep, claim)
        if not probe and st["open_until"] and now < st["open_until"]:
            why = f"failing ({st['error']}); retry after {int(st['open_until'] - now)} s"
            self.unavailable[ep] = why
            raise Unavailable(ep, why, st["open_until"])
        name, interval = bucket(url)
        hdr = {"User-Agent": UA, "Accept": accept, **(headers or {})}
        last, only_429 = None, True
        for i in range(self.tries):
            if name:
                self._wait(self.cache.reserve(name, interval))
            try:
                self.requests += 1
                with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=hdr), timeout=self.timeout, context=CTX) as r:
                    body = r.read()
                self._answered(ep, probe)
                return body
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = retry_after(e, self.now())
                    wait = min(30.0 if wait is None else wait, MAX_WAIT)
                    last = "HTTP 429"
                    if name:  # the next reserve() waits for the hold, in this and every other process
                        self.cache.hold(name, self.now() + wait)
                    elif i < self.tries - 1:
                        self._wait(wait)
                    continue
                if e.code < 500:  # an answer: the endpoint works, the request was wrong
                    self._answered(ep, probe)
                    raise RequestError(url, e.code, (e.read() or b"")[:300].decode("utf-8", "replace") if e.fp else "")
                last, only_429 = f"HTTP {e.code}", False
            except TRANSIENT as e:
                last, only_429 = f"network: {getattr(e, 'reason', e)}", False
            if i < self.tries - 1:
                self._wait(2 ** i * (1 + 0.25 * self.jitter()))
        if only_429:  # throttled throughout: the endpoint works, we were just asked to slow down
            self._answered(ep, probe)
            self.unavailable[ep] = "rate-limited (429) on every try"
            raise Unavailable(ep, "rate-limited (429) on every try")
        failed_at = self.now()

        def fail(cur):  # read-modify-write in one transaction: concurrent failures all count
            new = dict(cur, fails=cur["fails"] + 1, error=last)
            if probe or (new["fails"] >= BREAK_AFTER and cur["open_until"] <= failed_at):  # a failed probe reopens at once, for longer
                new["cooldown"] = min(MAX_COOLDOWN, cur["cooldown"] * 2) if cur["cooldown"] else COOLDOWN
                new["open_until"] = failed_at + new["cooldown"]
            return new
        new = self.cache.update_breaker(ep, fail)
        until = new["open_until"] if new["open_until"] > failed_at else None
        self.unavailable[ep] = f"{last} after {self.tries} tries"
        raise Unavailable(ep, f"{last} after {self.tries} tries", until)

    def _answered(self, ep, probe):
        """Any HTTP answer except 5xx/429 (a 404 too) shows the endpoint works: close its breaker."""
        if probe or self.cache.breaker(ep)["fails"]:
            self.cache.update_breaker(ep, lambda cur: dict(self.cache.CLOSED))
