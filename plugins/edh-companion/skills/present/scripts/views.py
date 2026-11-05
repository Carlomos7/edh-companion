"""Presentation view model: pure, deterministic functions from project data (research.json, audit.json, brew.json and
deck_check card records) to the page-data views the template renders. No network, no LLM, never edits project files.

Nothing is dropped: a long claim keeps its full text as `body` next to its short `headline`, every cited source and
timestamp stays reachable, and legacy inline citations in claim text ("[src-101 9:00, 9:40-10:40]", "[video 4:52-5:01]",
"(src-100 1:00-1:14)") become structured `cites[].at` with per-claim video links.
"""
import collections, os, re, sys, urllib.parse

# player-facing labels: the plugin's writing standard (references/writing.md, "Words, labels and numbers")
CLASS_LABEL = {"verified_fact": "Verified fact", "calculated": "Calculated", "popularity_metric": "Popularity data",
               "community_opinion": "Community opinion", "model_assessment": "Claude's judgment", "unresolved": "Unresolved"}
CLASS_ORDER = ("verified_fact", "popularity_metric", "calculated", "community_opinion", "model_assessment", "unresolved")
CONF_RANK = {"high": 0, "medium": 1, "low": 2}
KIND_ORDER = ("video", "article", "community", "decklist", "tournament", "stats", "price", "card_data", "combo", "rules", "official")
KIND_LABEL = {"video": "Videos", "article": "Articles", "community": "Community threads", "decklist": "Decklists",
              "tournament": "Tournament results", "stats": "Statistics", "price": "Prices", "card_data": "Card data",
              "combo": "Combo data", "rules": "Rules", "official": "Official sources"}
HOST_LABEL = {"reddit.com": "Reddit", "youtube.com": "YouTube", "edhrec.com": "EDHREC", "moxfield.com": "Moxfield",
              "archidekt.com": "Archidekt", "scryfall.com": "Scryfall"}
VERDICT_LABEL = {"pass": "Pass", "pass_with_warnings": "Pass with warnings", "fail": "Fail", "incomplete": "Incomplete",
                 "not audited": "Not audited", "audit out of date": "Audit out of date"}
STATUS_ORDER = ("fail", "warning", "unverified", "pass")
STATUS_LABEL = {"fail": "Fail", "warning": "Warning", "unverified": "Unverified", "pass": "Pass"}
BRACKETS = {1: "Exhibition", 2: "Core", 3: "Upgraded", 4: "Optimized", 5: "cEDH"}


# card types live in the shared core so deck_check and pages count the same way
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "scripts"))
from edhcore.types import GROUP_ORDER, TYPE_ORDER, card_types, type_counts  # noqa: E402,F401


# ---------- timestamps and links ----------
TS = r"\d{1,2}:\d{2}(?::\d{2})?"
AT = re.compile(rf"{TS}(?:\s*[-–]\s*{TS})?")
SRC_ID = r"src-[a-z0-9-]*\d{3,}"
# a bracket group that starts with a source id, "video" or a time and contains a time; or "(src-123 1:00)"
REF = re.compile(rf"\s*(?:\[(?=(?:src-|videos?\b|\d{{1,2}}:\d{{2}}))(?=[^\[\]]*\d:\d\d)([^\[\]]*)\]"
                 rf"|\((?={SRC_ID}\b)(?=[^()]*\d:\d\d)([^()]*)\))", re.I)


def seconds(t):
    s = 0
    for p in re.split(r"\s*[-–]\s*", t)[0].split(":"):
        s = s * 60 + int(p)
    return s


def time_url(url, t):
    """Link that opens a video at t (a range opens at its start). YouTube ?t=Ns, Twitch ?t=1h2m3s, Vimeo #t=Ns;
    other hosts can't deep-link, so they get the plain URL and the time stays visible as text."""
    s = seconds(t)
    u = urllib.parse.urlparse(url)
    host = u.netloc.lower().split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    keep = [(k, v) for k, v in urllib.parse.parse_qsl(u.query) if k not in ("t", "start")]
    if host in ("youtu.be", "youtube.com", "youtube-nocookie.com") or host.endswith(".youtube.com"):
        return urllib.parse.urlunparse(u._replace(query=urllib.parse.urlencode(keep + [("t", f"{s}s")])))
    if host == "twitch.tv" or host.endswith(".twitch.tv"):
        return urllib.parse.urlunparse(u._replace(query=urllib.parse.urlencode(keep + [("t", f"{s // 3600}h{s % 3600 // 60}m{s % 60}s")])))
    if host == "vimeo.com" or host.endswith(".vimeo.com"):
        return urllib.parse.urlunparse(u._replace(fragment=f"t={s}s"))
    return url


def _parse_ref(text, default, known):
    """'src-100 6:00 and 4:18; src-101 25:40' -> [(source id, time, note)]. A trailing '(src-x)' names the source of the
    times before it in that part; 'video' or no id means the finding's own video. None when a source can't be resolved."""
    out = []
    for seg in text.split(";"):
        seg = seg.strip()
        m = re.match(rf"({SRC_ID})\b", seg, re.I)
        cur = m.group(1).lower() if m else None
        seg = seg[m.end():] if m else re.sub(r"^videos?\b", "", seg, flags=re.I)
        pending = []
        for piece in seg.split(","):
            pm = re.search(rf"\(({SRC_ID})\)", piece, re.I)
            if pm:
                piece = piece.replace(pm.group(0), " ")
            note = " ".join(AT.sub(" ", piece).split()).strip(" ,;:.-–")
            note = re.sub(r"^(?:and|at|from)\b\s*|\s*\band$", "", note).strip() or None
            pending += [[None, re.sub(r"\s*[-–]\s*", "-", t), note] for t in AT.findall(piece)]
            if pm:
                for e in pending:
                    e[0] = pm.group(1).lower()
                out += pending
                pending = []
        for e in pending:
            e[0] = cur or default
        out += pending
    return out if out and all(e[0] in known for e in out) else None


def strip_refs(text, default, known):
    """Remove resolvable inline citations from text. Returns (clean text, [(source id, time, note)]). A citation
    whose source can't be resolved stays in the text, so nothing is lost."""
    found = []

    def repl(m):
        got = _parse_ref(m.group(1) or m.group(2), default, known)
        if got is None:
            return m.group(0)
        found.extend(got)
        return ""
    return REF.sub(repl, text or "").strip(), found


# ---------- sentences and headlines ----------
_ABBR = re.compile(r"(?:\b(?:e\.g|i\.e|etc|vs|cf|approx|incl|esp|mr|mrs|dr|jr|sr|st|al)|(?<![\w.])[A-Z])\.$", re.I)
_END = re.compile(r"[.!?][\"'”’)\]]*(?=\s+[\"'“‘(\[]?\w)")  # lowercase starts too ("deck_check on v4: ...")
HEAD_MAX, LABEL_MAX = 140, 60  # a headline is a whole sentence up to HEAD_MAX; "Label: ..." under LABEL_MAX is no headline
SHORT_BODY = 200  # same as the template's: a summary up to this shows under the headline
_PAIR = {")": "(", "]": "[", "}": "{", "”": "“"}


def _pairs(text):
    """(open, close) index pairs of brackets and quotations; unclosed ones don't count. A straight ' or " (or ‘’) opens
    after a space or bracket and closes before a non-letter; an apostrophe inside a word (Azula's, can't) is neither."""
    stack, out = [], []

    def close(i, opener):
        for k in range(len(stack) - 1, -1, -1):
            if stack[k][1] == opener:
                out.append((stack[k][0], i))
                del stack[k:]
                return True
        return False
    for i, ch in enumerate(text):
        prev, nxt = text[i - 1] if i else " ", text[i + 1] if i + 1 < len(text) else " "
        if ch in "([{“":
            stack.append((i, ch))
        elif ch in ")]}”":
            close(i, _PAIR[ch])
        elif ch in "'\"‘’":
            opener = "‘" if ch == "’" else ch
            if not prev.isspace() and not nxt.isalnum() and close(i, opener):
                continue
            if ch != "’" and (prev.isspace() or prev in "([{—–/") and not nxt.isspace():
                stack.append((i, ch))
    return out


def _inside(text):
    """Per character: True inside brackets or a quotation (the marks included)."""
    d = [0] * (len(text) + 1)
    for a, b in _pairs(text):
        d[a] += 1
        d[b + 1] -= 1
    out, n = [], 0
    for x in d[:-1]:
        n += x
        out.append(n > 0)
    return out


def sentences(text):
    """Split prose into sentences. Abbreviations (e.g.), initials, an ellipsis and full stops inside brackets or
    quotations don't end one."""
    out, start = [], 0
    text = (text or "").strip()
    ins = _inside(text)
    for m in _END.finditer(text):
        if ins[m.end()] or text[m.start() - 1:m.start()] == "." or (m.group(0)[0] == "." and _ABBR.search(text[start:m.start() + 1])):
            continue
        out.append(text[start:m.end()].strip())
        start = m.end()
    tail = text[start:].strip()
    return out + ([tail] if tail else [])


def _cut(s, limit):
    """s shortened at the last word boundary outside brackets and quotations that fits, plus an ellipsis -> (head, rest).
    When a quotation opens too early to cut before it, the head runs to its end instead."""
    ins = _inside(s)
    spaces = [i for i, ch in enumerate(s) if ch == " " and not ins[i]]
    cut = max((i for i in spaces if i <= limit), default=0)
    if cut < 40:
        cut = min((i for i in spaces if i > limit), default=len(s))
    head = s[:cut].rstrip(" ,;:—–-")
    return (head + "…" if cut < len(s) else head), s[cut:].strip()


def headline_parts(text, limit=HEAD_MAX):
    """(headline, rest). The headline is the claim's first sentence. A longer one: "Label: conclusion" with a short label
    gives the conclusion; else it ends at a clause break (semicolon, dash, a colon after 60+ characters) or a word
    boundary with an ellipsis. Never mid-word, never inside brackets or quotations; the full claim stays in the body."""
    ss = sentences(text)
    if not ss:
        return "", ""
    first, rest = ss[0], " ".join(ss[1:])
    if len(first) <= limit:
        return first, rest
    ins = _inside(first)
    colon = next((m.start() for m in re.finditer(r":(?=\s)", first) if not ins[m.start()]), None)
    tail = first[colon + 1:].strip() if colon is not None and colon < LABEL_MAX else ""
    if tail and len(tail) <= limit and tail[0] not in "'\"‘“([":  # a quote or list after the colon: the left part is the point
        return (tail[0].upper() + tail[1:] if re.match(r"[a-z]+\b(?![-\w])", tail) else tail), rest
    cuts = [m.start() for m in re.finditer(r"[:;](?=\s)|\s[—–]\s", first)
            if not ins[m.start()] and (LABEL_MAX if first[m.start()] == ":" else 30) <= m.start() <= limit]
    if cuts:
        return first[:cuts[-1]].rstrip(" ,"), " ".join(x for x in (first[cuts[-1] + 1:].strip(" —–"), rest) if x)
    head, more = _cut(first, limit)
    return head, " ".join(x for x in ("…" + more if more else "", rest) if x)


def headline(text, limit=HEAD_MAX):
    return headline_parts(text, limit)[0]


def summary_of(rest):
    """The sentence after the headline, at most SHORT_BODY characters, so the conclusion shows without opening Details."""
    s = (sentences(rest) or [None])[0]
    return s if not s or len(s) <= SHORT_BODY else _cut(s, SHORT_BODY)[0]


# ---------- research: findings, disagreements, sources ----------
def _host(url):
    h = urllib.parse.urlparse(url or "").netloc.lower()
    h = h[4:] if h.startswith("www.") else h
    return HOST_LABEL.get(h, h or None)


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def _times(entries):
    """[(source id, time, note)] -> {source id: [{t, note?}]}, each time once per source."""
    at = {}
    for sid, t, note in entries:
        lst = at.setdefault(sid, [])
        if all(x["t"] != t for x in lst):
            lst.append({"t": t, **({"note": note} if note else {})})
    return at


def _aliases(author, sid):
    """How a text names a source: its id, the creator's name, each bracketed part ('JoeyDH (EDHRECast)' -> EDHRECast)
    and leading runs of two or more words ('Muscles & Magic The Gathering' -> 'Muscles & Magic')."""
    out = {sid}
    for part in [author or ""] + [x.strip() for x in re.split(r"[()]", author or "") if x.strip()]:
        w = re.sub(r"\s*\([^)]*\)", "", part).split() if part == author else part.split()
        out.update(" ".join(w[:k]) for k in range(2, len(w) + 1))
        if len(w) == 1:
            out.add(w[0])
    return {a for a in out if len(a) >= 4}


BARE = re.compile(rf"\(\s*({TS}(?:\s*[-–]\s*{TS})?(?:\s*,\s*{TS}(?:\s*[-–]\s*{TS})?)*)\s*\)")  # "(2:17, 2:39)", "(17:47-18:15)"


class Research:
    """Views over one or more research.json files (several in a showcase). items: [(project or None, research)];
    slugs: {project: folder name} for anchors ("f-<folder>-<finding id>", "s-<folder>-<source id>"), unique per page.
    Sources are numbered once for the whole page, grouped by kind, so every cite's n matches the Sources list."""

    def __init__(self, items, slugs=None):
        self.items, self.slugs, self._names, self._heads = list(items), slugs or {}, {}, {}
        self.src, self.fnd, self.parsed = {}, {}, {}
        srcs = [(p, s) for p, r in self.items for s in r.get("sources", [])]
        rank = {k: i for i, k in enumerate(KIND_ORDER)}
        order = sorted(range(len(srcs)), key=lambda i: (rank.get(srcs[i][1].get("type"), len(rank)), i))
        self.n = {(srcs[i][0], srcs[i][1]["id"]): k + 1 for k, i in enumerate(order)}
        self.order = [srcs[i] for i in order]
        for p, s in srcs:
            self.src[(p, s["id"])] = s
        for p, r in self.items:
            known = {s["id"] for s in r.get("sources", [])}
            for f in r.get("findings", []):
                self.fnd[(p, f["id"])] = f
                ev = [e for e in f.get("evidence", []) if e in known]
                vid = next((e for e in ev if self.src[(p, e)].get("type") == "video"), None)
                default = vid or (ev[0] if ev else None)
                claim, a = strip_refs(f["claim"], default, known)
                expl, b = strip_refs(f.get("explanation"), default, known)
                loc = [(l["source"], t, None) for l in f.get("locators") or [] if l.get("source") in known for t in l.get("at", [])]
                named = self._named(p, claim)
                # at: every time the finding cites; sup: the sources its own claim cites with times (the explanation
                # may name the other side of a disagreement, which must not come along when the finding is cited)
                self.parsed[(p, f["id"])] = (claim, expl or None, _times(a + b + loc + named + self._named(p, expl)), _times(a + loc + named))

    def anchor(self, kind, p, i):
        s = _slug(self.slugs.get(p) or p)
        return f"{kind}-{s}-{_slug(i)}" if s else f"{kind}-{_slug(i)}"

    def _named(self, p, text):
        """Bare times in brackets ("Planeswalker Project ... (2:17, 2:39)") -> [(source id, time, None)] for the video
        named last before them in the same sentence (by creator name or source id). Times with no named video stay text."""
        if p not in self._names:
            self._names[p] = [(re.compile(rf"(?<!\w){re.escape(a)}(?!\w)"), sid) for (q, sid), s in self.src.items()
                              if q == p and s.get("type") == "video" for a in _aliases(s.get("author"), sid)]
        out = []
        for m in BARE.finditer(text or ""):
            before = text[:m.start()]
            seg = before[before.rfind(". ") + 1:]
            hits = [(x.end(), sid) for rx, sid in self._names[p] for x in rx.finditer(seg)]
            if hits:
                out += [(max(hits)[1], re.sub(r"\s*[-–]\s*", "-", t), None) for t in AT.findall(m.group(1))]
        return out

    def text_at(self, p, text):
        """Times in free text (candidates, recommendations, disagreement positions) -> {source id: [{t}]} for cites()."""
        return _times(self._named(p, text))

    def head(self, p, fid):
        """(headline, summary) of a finding: research.json's headline or the claim's first sentence, and the next one."""
        if (p, fid) not in self._heads:
            f, claim = self.fnd[(p, fid)], self.parsed[(p, fid)][0]
            h, rest = (f["headline"], claim if claim != f["headline"] else "") if f.get("headline") else headline_parts(claim)
            self._heads[(p, fid)] = (h, summary_of(rest))
        return self._heads[(p, fid)]

    def _cite(self, p, sid, at):
        s = self.src[(p, sid)]
        return {"n": self.n[(p, sid)], "source_id": sid, "anchor": self.anchor("s", p, sid), "label": s.get("author") or s["title"],
                "kind": s.get("type"), "title": s["title"], "url": s["url"], "at": [dict(a, url=time_url(s["url"], a["t"])) for a in at]}

    def _sources_of(self, p, f):
        """Source ids a finding rests on: its evidence (a finding id stands for that finding's sources), then any
        source named only in its text."""
        out = []
        for e in f.get("evidence", []):
            if (p, e) in self.src:
                out.append(e)
            elif (p, e) in self.fnd:
                out += [x for x in self.fnd[(p, e)].get("evidence", []) if (p, x) in self.src]
        return list(dict.fromkeys(out + list(self.parsed[(p, f["id"])][2])))

    def cites(self, p, refs, at=None):
        """Evidence ids -> cites. Source ids keep the times given in `at`; a finding id brings only the sources its
        claim cites with times (locators, inline times), else its first source. Every source once, in evidence order."""
        merged = {}

        def add(sid, times):
            lst = merged.setdefault(sid, [])
            lst += [a for a in times if all(a["t"] != b["t"] for b in lst)]
        for r in refs or []:
            if (p, r) in self.src:
                add(r, (at or {}).get(r, []))
            elif (p, r) in self.fnd:
                sup = self.parsed[(p, r)][3] or {sid: [] for sid in self._sources_of(p, self.fnd[(p, r)])[:1]}
                for sid, times in sup.items():
                    add(sid, times)
        for sid, times in (at or {}).items():
            add(sid, times)
        return [self._cite(p, sid, times) for sid, times in merged.items()]

    def finding_cites(self, p, f):
        return self.cites(p, f.get("evidence", []), self.parsed[(p, f["id"])][2])

    def _disputed(self):
        return {(p, e) for p, r in self.items for d in r.get("disagreements", []) for pos in d["positions"] for e in pos.get("evidence", [])}

    def _creator(self, p, f):
        for sid in self._sources_of(p, f):
            s = self.src[(p, sid)]
            if s.get("author"):
                return s["author"]
            if _host(s.get("url")):
                return _host(s["url"])
        return "Other sources"

    def findings_view(self):
        """Findings grouped (facts and stats by class, community opinions by creator, then assessments and unresolved),
        most important first: classes in CLASS_ORDER, creators by best confidence then size; items by confidence."""
        disputed, out = self._disputed(), []
        for p, r in self.items:
            groups = {}
            for i, f in enumerate(r.get("findings", [])):
                claim, expl = self.parsed[(p, f["id"])][:2]
                kind, title = ("creator", self._creator(p, f)) if f["class"] == "community_opinion" else ("class", CLASS_LABEL[f["class"]])
                g = groups.setdefault((kind, title), {"id": re.sub(r"[^a-z0-9]+", "-", f"{p or ''} {kind} {title}".lower()).strip("-"),
                                                      "title": title, "kind": kind, "project": p, "items": [], "_k": (CLASS_ORDER.index(f["class"]), i)})
                h, summary = self.head(p, f["id"])
                g["items"].append({"id": f["id"], "anchor": self.anchor("f", p, f["id"]), "headline": h, "summary": summary, "body": claim,
                                   "class": f["class"], "class_label": CLASS_LABEL[f["class"]], "confidence": f["confidence"], "cards": f.get("cards") or [],
                                   "cites": self.finding_cites(p, f), "disputed": (p, f["id"]) in disputed, "explanation": expl,
                                   "limitations": f.get("limitations"), "_r": (CONF_RANK.get(f["confidence"], 3), i)})
            for g in groups.values():
                g["items"].sort(key=lambda x: x.pop("_r"))
                ci, first = g.pop("_k")
                g["_k"] = (ci, min(CONF_RANK.get(x["confidence"], 3) for x in g["items"]), -len(g["items"]), first)
            for g in sorted(groups.values(), key=lambda g: g["_k"]):
                g.pop("_k")
                out.append(g)
        return out

    def disagreements_view(self):
        out = []
        for p, r in self.items:
            for d in r.get("disagreements", []):
                out.append({"topic": d["topic"], "explanation": d.get("explanation"), "project": p,
                            "positions": [{"text": pos["position"], "cites": self.cites(p, pos.get("evidence", []), self.text_at(p, pos["position"])),
                                           "findings": [e for e in pos.get("evidence", []) if (p, e) in self.fnd]} for pos in d["positions"]]})
        return out

    def sources_view(self):
        """Every source, numbered like the cites and grouped by kind; cited_by = [{id, anchor, project, headline}] of the
        citing findings (same project); moments = the times findings cite (each with those finding ids), plus the
        source's own listed timestamps no finding names."""
        cited, moments = collections.defaultdict(list), collections.defaultdict(dict)
        for (p, fid), f in self.fnd.items():
            for c in self.finding_cites(p, f):
                cited[(p, c["source_id"])].append(fid)
                for a in c["at"]:
                    moments[(p, c["source_id"])].setdefault(a["t"], {"t": a["t"], "url": a["url"], "findings": []})["findings"].append(fid)
        groups = {}
        for p, s in self.order:
            key = (p, s["id"])
            ms = moments[key]
            starts = {seconds(t) for t in ms}
            for t in s.get("timestamps") or []:
                if seconds(t) not in starts:
                    ms[t] = {"t": t, "url": time_url(s["url"], t), "findings": []}
            k = s.get("type")
            g = groups.setdefault(k, {"kind": k, "kind_label": KIND_LABEL.get(k, (k or "Other").replace("_", " ").capitalize()), "items": []})
            g["items"].append({"n": self.n[key], "id": s["id"], "anchor": self.anchor("s", p, s["id"]), "project": p, "title": s["title"],
                               "creator": s.get("author"), "date": s.get("published") or s.get("accessed"), "url": s["url"],
                               "primary": bool(s.get("primary")), "sample_size": s.get("sample_size"),
                               "cited_by": [{"id": fid, "anchor": self.anchor("f", p, fid), "project": p, "headline": self.head(p, fid)[0]}
                                            for fid in dict.fromkeys(cited.get(key, []))],
                               "moments": sorted(ms.values(), key=lambda m: seconds(m["t"]))})
        return list(groups.values())


# ---------- audit ----------
def split_method(detail):
    """'[method: how] result' -> ('how', 'result'); brackets inside the method are balanced. No prefix -> (None, detail)."""
    m = re.match(r"\s*\[method:\s*", detail or "", re.I)
    if not m:
        return None, detail
    depth, i = 1, m.end()
    while i < len(detail) and depth:
        depth += {"[": 1, "]": -1}.get(detail[i], 0)
        i += 1
    return (detail[m.end():i - 1].strip(), detail[i:].strip() or None) if not depth else (None, detail)


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def lead_and_more(text, label=None):
    """The first sentence that says more than the verdict label, and the rest (in order)."""
    ss = sentences(text)
    i = next((k for k, s in enumerate(ss) if not (label and _norm(s).startswith(_norm(label)))), 0)
    return (ss[i] if ss else None), " ".join(ss[:i] + ss[i + 1:]) or None


def audit_view(audit, validation):
    """Verdict with a human label, counts, checks grouped fail > warning > unverified > pass (passes collapsed),
    method split from the result and a method shared by many checks factored out. Only a current audit shows checks."""
    state = validation["state"]
    v = {"verdict": state, "verdict_label": VERDICT_LABEL.get(state, state.replace("_", " ").capitalize()), "note": validation.get("note"),
         "counts": dict.fromkeys(STATUS_ORDER, 0), "summary": None, "method_common": None, "groups": [], "required_fixes": [], "next_steps": []}
    if not audit or "checks" not in validation:
        return v
    checks = []
    for c in audit["checks"]:
        method, result = (c["method"], c.get("detail")) if c.get("method") else split_method(c.get("detail"))
        checks.append({"id": c["id"], "title": c["requirement"], "status": c["status"], "status_label": STATUS_LABEL[c["status"]],
                       "result": result, "method": method, "cards": c.get("cards") or [], "area": c.get("area"), "kind": c.get("kind"),
                       "evidence": c.get("evidence") or []})
    common = collections.Counter(c["method"] for c in checks if c["method"]).most_common(1)
    if common and common[0][1] >= 2 and common[0][1] * 3 >= len(checks):  # shared by at least a third of the checks
        v["method_common"] = common[0][0]
    names = {"fail": ("check failed", "checks failed"), "warning": ("warning", "warnings"), "unverified": ("unverified", "unverified"),
             "pass": ("check passed", "checks passed")}
    for s in STATUS_ORDER:
        cs = [c for c in checks if c["status"] == s]
        v["counts"][s] = len(cs)
        if cs:
            v["groups"].append({"status": s, "label": f"{len(cs)} {names[s][len(cs) != 1]}", "open": s != "pass", "checks": cs})
    lead, more = lead_and_more(audit["verdict"].get("summary"), v["verdict_label"])
    v["summary"] = {"lead": lead, "more": more}
    title = {c["id"]: c["title"] for c in checks}
    v["required_fixes"] = [dict(f, title=title.get(f.get("check"))) for f in audit.get("required_fixes") or []]
    v["next_steps"] = list(audit.get("recommended_next_steps") or [])
    v.update(audited=audit.get("created"), independent=(audit.get("auditor") or {}).get("independent"),
             limitations=list(audit["verdict"].get("limitations") or []))
    for key, name in (("bracket_findings", "bracket"), ("combo_findings", "combos"), ("theme_violations", "theme_violations"),
                      ("legality_issues", "legality_issues"), ("research_gaps", "research_gaps"), ("recommendations", "recommendations"),
                      ("follow_up_questions", "follow_up_questions")):
        if audit.get(key):
            v[name] = audit[key]
    return v


def counts_text(counts):
    return ", ".join(f"{counts[s]} {n}" for s, n in (("fail", "failed"), ("warning", "warnings"), ("unverified", "unverified"), ("pass", "passed")) if counts.get(s))


# ---------- recommendations ----------
def recs_view(recs, deck_names, cites=lambda refs: []):
    """Applied = what the current list shows (its add is in the deck; a pure cut is gone from it), whatever the status
    says; rejected ones are counted and listed apart; the rest are proposals."""
    names = {n.lower() for n in deck_names} | {n.split(" // ")[0].lower() for n in deck_names}
    out = {"proposed": [], "applied": [], "rejected": [], "rejected_count": 0}
    for r in recs or []:
        add_in = bool(r.get("add")) and r["add"].lower() in names
        cut_in = bool(r.get("cut")) and r["cut"].lower() in names
        item = {"id": r.get("id"), "status": r["status"], "status_label": r["status"].replace("_", " ").capitalize(), "kind": r.get("kind"),
                "add": r.get("add"), "cut": r.get("cut"), "reason": r.get("reason"), "tradeoffs": r.get("tradeoffs"), "theme": r.get("theme"),
                "add_in_deck": add_in, "cut_in_deck": cut_in, "cites": cites(r.get("evidence") or [])}
        if r["status"] == "rejected":
            out["rejected"].append(item)
        elif add_in if r.get("add") else (not cut_in if r.get("cut") else r["status"] == "accepted"):
            out["applied"].append(item)
        else:
            out["proposed"].append(item)
    out["rejected_count"] = len(out["rejected"])
    return out


# ---------- notices ----------
def research_notices(research, brew, label=None, lists=()):
    """Honest staleness notes for research next to a deck. research.json scope.deck (the deck it was written for)
    decides when present; older files fall back to: research whose newest named decklist file (lists: the build's
    files in decklists/, e.g. main-v3.txt) is older than the newest one, or research dated strictly before the deck's
    last change. File numbers are never compared with brew versions (main-v5.txt can be version 4). Also: a deck built
    from older research."""
    out, pre = [], f"{label}: " if label else ""
    scope = research.get("scope") or {}
    ver, why = brew.get("version"), []
    if scope.get("deck"):
        sd = scope["deck"]
        if sd.get("version") != ver:
            why.append(f"it was written for version {sd.get('version')}")
        elif sd.get("deck_hash") and brew.get("deck_hash") and sd["deck_hash"] != brew["deck_hash"]:
            why.append("the card list changed after it was written")
    else:
        text = " ".join([scope.get("question") or ""] + [f"{f['claim']} {f.get('explanation') or ''}" for f in research.get("findings", [])]).lower()
        files = {m.group(1).lower(): int(m.group(2)) for m in (re.fullmatch(r"(.+-v(\d+))\.txt", os.path.basename(x), re.I) for x in lists) if m}
        named = [s for s in files if re.search(rf"(?<![\w-]){re.escape(s)}(?![\w-])", text)]
        newest = max(files, key=files.get) if files else None
        if named and files[max(named, key=files.get)] < files[newest]:
            why.append(f"it names {max(named, key=files.get)}.txt; the newest list is {newest}.txt")
        if research.get("created") and brew.get("updated") and research["created"][:10] < brew["updated"][:10]:
            why.append(f"it is dated {research['created'][:10]} and the deck changed on {brew['updated'][:10]}")
    if why:
        out.append({"level": "warn", "text": f"{pre}Research was written for an earlier version of this deck ({'; '.join(why)}); the deck is now "
                                             f"version {ver}. Findings that name specific cards may describe the older list."})
    if brew.get("research_version") and research.get("version") and brew["research_version"] < research["version"]:
        out.append({"level": "info", "text": f"{pre}The deck was built from research version {brew['research_version']}; research.json is now "
                                             f"version {research['version']}, so newer findings may not be in the list yet."})
    return out


# ---------- private notes ----------
PRIVATE_MIN = 20
_STRAIGHT = str.maketrans("‘’“”", "''\"\"")


def _norm_map(s):
    """s lowercased, whitespace runs as one space, curly quotes straight; plus each kept character's index in s."""
    out, idx = [], []
    for i, ch in enumerate(s):
        if ch.isspace():
            if out and out[-1] != " ":
                out.append(" ")
                idx.append(i)
            continue
        out.append((ch.lower()[:1] or ch).translate(_STRAIGHT))
        idx.append(i)
    return "".join(out), idx


class Redactor:
    """Hides quotes of private notes in page text. A span of PRIVATE_MIN+ characters (case and spacing ignored) shared
    with a private line becomes "[private note]", widened to whole words, or to the quotation it sits in. Card names,
    small words and text also in a public file (brew.json, source titles) don't count as private: the span is hidden
    only when the rest has 4+ letters inside quotation marks (a quote), 12+ outside (a shared phrase). count = spans hidden."""
    SMALL = {"and", "or", "plus", "with", "then", "vs", "the", "of", "a", "an", "to", "in", "on", "at", "for", "as", "by", "is"}

    def __init__(self, private_lines, public_texts=(), names=()):
        k, self.count = PRIVATE_MIN, 0
        grams = lambda t: (n[i:i + k] for n in [_norm_map(t)[0]] for i in range(len(n) - k + 1))
        self.public = {g for t in public_texts for g in grams(t)}
        self.grams = {g for t in private_lines for g in grams(t)} - self.public
        self.vocab = {w for x in names if x for w in re.findall(r"[a-z]+", _norm_map(x)[0])} | self.SMALL  # words of card names

    def __call__(self, text):
        k = PRIVATE_MIN
        if not self.grams or not isinstance(text, str) or len(text) < k:
            return text
        n, idx = _norm_map(text)
        hit, pub = [False] * (len(n) + 1), [False] * len(n)
        for i in range(len(n) - k + 1):
            if n[i:i + k] in self.grams:
                hit[i:i + k] = [True] * k
        if not any(hit):
            return text
        for i in range(len(n) - k + 1):
            if n[i:i + k] in self.public:
                pub[i:i + k] = [True] * k
        pairs = _pairs(text)
        quotes = [(a, b) for a, b in pairs if text[a] in "'\"‘“"]
        spans, i = [], 0
        while i < len(n):
            if not hit[i]:
                i += 1
                continue
            j = i
            while hit[j]:
                j += 1
            while i > 0 and n[i - 1].isalnum():  # whole words
                i -= 1
            while j < len(n) and n[j].isalnum():
                j += 1
            a, b = idx[i], idx[j - 1] + 1
            while a < b and not text[a].isalnum():
                a += 1
            while b > a and not text[b - 1].isalnum() and text[b - 1] not in ")'\"’”":
                b -= 1
            q = min(((x, y) for x, y in quotes if x <= a and b <= y + 1), key=lambda p: p[1] - p[0], default=None)
            own = sum(len(w.group()) for w in re.finditer(r"[a-z]+", n[i:j])
                      if w.group() not in self.vocab and not all(pub[i + w.start():i + w.end()]))
            if own >= (4 if q else 12):
                if q:
                    a, b = q[0], q[1] + 1
                for x, y in pairs:  # a span that crosses a bracket takes the whole bracket, so none is left open
                    a, b = (x if x < a <= y < b else a), (y + 1 if a < x < b <= y else b)
                spans.append([a, b])
            i = j
        if not spans:
            return text
        merged = []
        for a, b in sorted(spans):
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        self.count += len(merged)
        for a, b in reversed(merged):
            text = text[:a] + "[private note]" + text[b:]
        return text


# ---------- hero ----------
IDENTITY = {"": "Colorless", "W": "Mono-white", "U": "Mono-blue", "B": "Mono-black", "R": "Mono-red", "G": "Mono-green",
            "WU": "Azorius", "UB": "Dimir", "BR": "Rakdos", "RG": "Gruul", "WG": "Selesnya", "WB": "Orzhov", "UR": "Izzet",
            "BG": "Golgari", "WR": "Boros", "UG": "Simic", "WUB": "Esper", "UBR": "Grixis", "BRG": "Jund", "WRG": "Naya",
            "WUG": "Bant", "WBG": "Abzan", "WUR": "Jeskai", "UBG": "Sultai", "WBR": "Mardu", "URG": "Temur", "WUBRG": "Five-color"}


def identity_name(identity):
    ci = "".join(c for c in "WUBRG" if c in (identity or []))
    name = IDENTITY.get(ci) or f"Four-color (no {next(c for c in 'WUBRG' if c not in ci)})"
    return f"{name} ({ci})" if ci else name


def hero(cm, identity, art_crop=None, d=None):
    """Hero facts for a commander and one build (default: its first): name, one metadata line, the audit verdict, 4 key stats."""
    d = d or cm["decks"][0]
    s, av = d["stats"], d.get("audit_view") or {}
    b = d["bracket"]
    gc_rule = {1: "none allowed", 2: "none allowed", 3: "up to 3 allowed"}.get(b)
    mdfc = s.get("mdfc_lands") or 0
    meta = [f"Bracket {b} ({BRACKETS.get(b, '')})", identity_name(identity) if identity is not None else None, d.get("archetype"),
            f"Version {d['version']}" + (f" · {d['project']}" if d.get("project") else "")]
    verdict = av.get("verdict_label")
    if verdict and any(av.get("counts", {}).values()):
        verdict += ": " + counts_text(av["counts"])
    return {"name": cm["name"], "meta": [m for m in meta if m], "verdict": verdict,
            "stats": [{"label": "Value", "value": None if s.get("price") is None else f"${s['price']:,.2f}",
                       "context": "listed printings" + (f", Scryfall {s['price_as_of']}" if s.get("price_as_of") else "")},
                      {"label": "Average mana value", "value": f"{s['avg_mv']}", "context": "nonland cards"},
                      {"label": "Lands", "value": f"{s['lands']}" + (f" + {mdfc} MDFC" if mdfc else ""), "context": "typical 35–38"},
                      {"label": "Game Changers", "value": f"{len(s['game_changers'])}", "context": f"{gc_rule} at bracket {b}" if gc_rule else None}],
            "art": cm.get("img"), "art_crop": art_crop}
