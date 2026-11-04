"""Disposable SQLite cache shared by every script and process.

Location: $EDHC_CACHE_DIR, else ~/.cache/edh-companion. Holds card data, search results and combo lookups (kv), plus
the shared pacing clock (pace) and per-endpoint circuit-breaker state (breaker), so parallel processes cooperate.

Safety: the cache is disposable, so a corrupt database is rebuilt. Recovery only ever deletes the three files named in
FILES inside the cache dir, and only when that dir passes `safe_dir` (not home, not a workspace, project or repo, nor
inside one). Otherwise the cache is turned off for the run and nothing is deleted.
"""
import json, os, sqlite3, time

FILES = ("cache.sqlite", "cache.sqlite-wal", "cache.sqlite-shm")
MARKERS = ("workspace.yaml", "PROJECT.md", "brew.json", "research.json", ".git", ".claude-plugin")
SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, kind TEXT, json TEXT, fetched_at REAL);
CREATE TABLE IF NOT EXISTS pace (bucket TEXT PRIMARY KEY, next_ok REAL);
CREATE TABLE IF NOT EXISTS breaker (endpoint TEXT PRIMARY KEY, fails INTEGER, open_until REAL, cooldown REAL, error TEXT);
"""


def cache_dir():
    return os.path.abspath(os.path.expanduser(os.environ.get("EDHC_CACHE_DIR") or os.path.join("~", ".cache", "edh-companion")))


def safe_dir(d):
    """True when d may hold (and lose) the cache files: not the home dir, and neither d nor any parent is a
    workspace, project or repository."""
    d, home = os.path.realpath(d), os.path.realpath(os.path.expanduser("~"))
    if d == home:
        return False
    cur = d
    while cur != home:  # the home dir itself may hold dotfiles repos; only d and its parents below home are checked
        if os.path.basename(cur) == "EDHCompanion" or any(os.path.exists(os.path.join(cur, m)) for m in MARKERS):
            return False
        parent = os.path.dirname(cur)
        if parent == cur:
            return True
        cur = parent
    return True


class Cache:
    """mode: normal (stored and shared), off (nothing stored; pacing and breaker kept in memory, EDHC_NO_CACHE=1)."""

    def __init__(self, path=None, mode=None, now=time.time):
        self.mode = mode or ("off" if os.environ.get("EDHC_NO_CACHE") == "1" else "normal")
        self.dir = os.path.dirname(path) if path else cache_dir()
        self.path = path or os.path.join(self.dir, FILES[0])
        self.now = now
        self.db = None
        self.note = None
        self.mem = {"pace": {}, "breaker": {}}
        if self.mode != "off":
            self._open()

    # --- connection and recovery -------------------------------------------------------------------------------
    def _open(self, retry=True):
        if not safe_dir(self.dir):
            self.note = f"cache off: {self.dir} is inside a workspace, project or repository"
            self.db = None
            return
        try:
            os.makedirs(self.dir, exist_ok=True)
            self.db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA busy_timeout=30000")
            self.db.executescript(SCHEMA)
            self.db.execute("SELECT count(*) FROM kv").fetchone()
        except sqlite3.OperationalError as e:  # read-only, disk I/O, full disk, locked: not corruption, never wipe
            self._close()
            self.note = f"cache off: {e}"
        except sqlite3.DatabaseError as e:
            self._close()
            if retry and self._wipe():
                self.note = f"cache rebuilt after error: {e}"
                return self._open(retry=False)
            self.note = f"cache off: {e}"
            self.db = None
        except OSError as e:
            self._close()
            self.note = f"cache off: {e}"
            self.db = None

    def _close(self):
        try:
            if self.db:
                self.db.close()
        except Exception:  # noqa: BLE001
            pass
        self.db = None

    def _wipe(self):
        """Delete only the cache's own files, only in a safe dir. Returns True if it could."""
        if not safe_dir(self.dir):
            return False
        for f in FILES:
            p = os.path.join(self.dir, f)
            try:
                if os.path.isfile(p):
                    os.remove(p)
            except OSError:
                return False
        return True

    def _run(self, fn):
        """Run a DB operation; on corruption rebuild once, then give up quietly (the cache is optional). Any other
        operational error (read-only, disk I/O, full disk) turns the cache off for the run: pacing and breaker
        continue in memory. Never raises."""
        if not self.db:
            return None
        try:
            return fn(self.db)
        except sqlite3.OperationalError as e:
            if "locked" in str(e) or "busy" in str(e):
                return None
            self._close()
            self.note = f"cache off: {e}"
            return None
        except sqlite3.DatabaseError as e:
            self._close()
            if self._wipe():
                self._open(retry=False)
                self.note = f"cache rebuilt after error: {e}"
            return None

    def _tx(self, fn):
        """fn(db) inside one BEGIN IMMEDIATE transaction (serialised across processes); None if the cache can't."""
        def run(db):
            db.execute("BEGIN IMMEDIATE")
            try:
                res = fn(db)
                db.execute("COMMIT")
                return res
            except Exception:
                if db.in_transaction:
                    db.execute("ROLLBACK")
                raise
        return self._run(run)

    # --- key/value -----------------------------------------------------------------------------------------------
    def get(self, key):
        """(value, fetched_at) or None. Freshness is the caller's call (edhcore.session), so --fresh can still fall
        back to an older copy when the network fails, and say so."""
        row = self._run(lambda db: db.execute("SELECT json, fetched_at FROM kv WHERE key=?", (key,)).fetchone())
        if not row:
            return None
        try:
            return json.loads(row[0]), row[1]
        except ValueError:
            return None

    def put(self, key, kind, value, fetched_at=None):
        t = self.now() if fetched_at is None else fetched_at
        self._run(lambda db: db.execute("INSERT OR REPLACE INTO kv VALUES (?,?,?,?)", (key, kind, json.dumps(value), t)))

    # --- shared pacing -------------------------------------------------------------------------------------------
    def reserve(self, bucket, interval):
        """Reserve the next request slot for a bucket across all processes; returns seconds to wait first."""
        now = self.now()

        def tx(db):
            row = db.execute("SELECT next_ok FROM pace WHERE bucket=?", (bucket,)).fetchone()
            start = max(now, row[0] if row else 0)
            db.execute("INSERT OR REPLACE INTO pace VALUES (?,?)", (bucket, start + interval))
            return start - now

        wait = self._tx(tx)
        if wait is None:  # no shared DB: pace within this process only
            start = max(now, self.mem["pace"].get(bucket, 0))
            self.mem["pace"][bucket] = start + interval
            wait = start - now
        return max(0.0, wait)

    def hold(self, bucket, until):
        """A 429 told us to wait: no process starts a request in this bucket before `until`."""
        def tx(db):
            row = db.execute("SELECT next_ok FROM pace WHERE bucket=?", (bucket,)).fetchone()
            db.execute("INSERT OR REPLACE INTO pace VALUES (?,?)", (bucket, max(until, row[0] if row else 0)))
            return True
        if not self._tx(tx):
            self.mem["pace"][bucket] = max(until, self.mem["pace"].get(bucket, 0))

    # --- circuit breaker -----------------------------------------------------------------------------------------
    CLOSED = {"fails": 0, "open_until": 0, "cooldown": 0, "error": None}
    SELECT_BREAKER = "SELECT fails, open_until, cooldown, error FROM breaker WHERE endpoint=?"

    def breaker(self, endpoint):
        row = self._run(lambda db: db.execute(self.SELECT_BREAKER, (endpoint,)).fetchone())
        if row:
            return {"fails": row[0], "open_until": row[1], "cooldown": row[2], "error": row[3]}
        return dict(self.mem["breaker"].get(endpoint) or self.CLOSED)

    def update_breaker(self, endpoint, fn):
        """new = fn(current state), read and written in one transaction so concurrent processes never lose an update.
        Returns the new state."""
        def tx(db):
            row = db.execute(self.SELECT_BREAKER, (endpoint,)).fetchone()
            new = fn({"fails": row[0], "open_until": row[1], "cooldown": row[2], "error": row[3]} if row else dict(self.CLOSED))
            db.execute("INSERT OR REPLACE INTO breaker VALUES (?,?,?,?,?)", (endpoint, new["fails"], new["open_until"], new["cooldown"], new["error"]))
            return new
        new = self._tx(tx)
        if new is None:  # no shared DB: this process only
            new = fn(dict(self.mem["breaker"].get(endpoint) or self.CLOSED))
        self.mem["breaker"][endpoint] = dict(new)
        return new
