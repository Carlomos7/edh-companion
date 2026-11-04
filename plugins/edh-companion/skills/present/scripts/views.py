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


def sentences(text):
    """Split prose into sentences (abbreviations like e.g. and initials don't end one)."""
    out, start = [], 0
    text = (text or "").strip()
    for m in _END.finditer(text):
        if m.group(0)[0] == "." and _ABBR.search(text[start:m.start() + 1]):
            continue
        out.append(text[start:m.end()].strip())
        start = m.end()
    tail = text[start:].strip()
    return out + ([tail] if tail else [])


def headline(text, limit=100):
    """The claim's first sentence. A long one ends at its last clause break (colon, semicolon, dash) that fits, or else
    at a word boundary with an ellipsis; never mid-word. The full claim always stays in the item's body."""
    first = (sentences(text) or [""])[0]
    if len(first) <= limit:
        return first
    cuts = [m.start() for m in re.finditer(r"[:;](?=\s)|\s[—–]\s", first)
            if 30 <= m.start() <= limit and first[:m.start()].count("(") == first[:m.start()].count(")")]  # not inside brackets
    if cuts:
        return first[:cuts[-1]].rstrip(" ,")
    cut = first.rfind(" ", 0, limit)
    head = first[:cut if cut > 0 else limit]
    if head.count("(") > head.count(")") and head.rfind("(") >= 30:
        head = head[:head.rfind("(")]
    return head.rstrip(" ,;:—–(") + "…"


# ---------- research: findings, disagreements, sources ----------
def _host(url):
    h = urllib.parse.urlparse(url or "").netloc.lower()
    h = h[4:] if h.startswith("www.") else h
    return HOST_LABEL.get(h, h or None)


class Research:
    """Views over one or more research.json files (several in a showcase). items: [(project or None, research)].
    Sources are numbered once for the whole page, grouped by kind, so every cite's n matches the Sources list."""

    def __init__(self, items):
        self.items = list(items)
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
                at = {}
                for sid, t, note in a + b + [(l["source"], t, None) for l in f.get("locators") or [] if l.get("source") in known for t in l.get("at", [])]:
                    lst = at.setdefault(sid, [])
                    if all(x["t"] != t for x in lst):
                        lst.append({"t": t, **({"note": note} if note else {})})
                self.parsed[(p, f["id"])] = (claim, expl or None, at)

    def _cite(self, p, sid, at):
        s = self.src[(p, sid)]
        return {"n": self.n[(p, sid)], "source_id": sid, "label": s.get("author") or s["title"], "kind": s.get("type"),
                "title": s["title"], "url": s["url"], "at": [dict(a, url=time_url(s["url"], a["t"])) for a in at]}

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
        """Evidence ids -> cites. Source ids keep the times given in `at`; a finding id brings its own sources with
        the times that finding cites. Every source is listed once, in evidence order."""
        merged = {}

        def add(sid, times):
            lst = merged.setdefault(sid, [])
            lst += [a for a in times if all(a["t"] != b["t"] for b in lst)]
        for r in refs or []:
            if (p, r) in self.src:
                add(r, (at or {}).get(r, []))
            elif (p, r) in self.fnd:
                f_at = self.parsed[(p, r)][2]
                for sid in self._sources_of(p, self.fnd[(p, r)]):
                    add(sid, f_at.get(sid, []))
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
                claim, expl, _ = self.parsed[(p, f["id"])]
                kind, title = ("creator", self._creator(p, f)) if f["class"] == "community_opinion" else ("class", CLASS_LABEL[f["class"]])
                g = groups.setdefault((kind, title), {"id": re.sub(r"[^a-z0-9]+", "-", f"{p or ''} {kind} {title}".lower()).strip("-"),
                                                      "title": title, "kind": kind, "project": p, "items": [], "_k": (CLASS_ORDER.index(f["class"]), i)})
                g["items"].append({"id": f["id"], "headline": f.get("headline") or headline(claim), "body": claim, "class": f["class"],
                                   "class_label": CLASS_LABEL[f["class"]], "confidence": f["confidence"], "cards": f.get("cards") or [],
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
                            "positions": [{"text": pos["position"], "cites": self.cites(p, pos.get("evidence", [])),
                                           "findings": [e for e in pos.get("evidence", []) if (p, e) in self.fnd]} for pos in d["positions"]]})
        return out

    def sources_view(self):
        """Every source, numbered like the cites and grouped by kind; cited_by = finding ids; moments = the times
        findings cite (each with those findings), plus the source's own listed timestamps no finding names."""
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
            g["items"].append({"n": self.n[key], "id": s["id"], "project": p, "title": s["title"], "creator": s.get("author"),
                               "date": s.get("published") or s.get("accessed"), "url": s["url"], "primary": bool(s.get("primary")),
                               "sample_size": s.get("sample_size"), "cited_by": list(dict.fromkeys(cited.get(key, []))),
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
def research_notices(research, brew, label=None):
    """Honest staleness notes for research next to a deck. research.json scope.deck (the deck it was written for)
    decides when present; older files fall back to: research dated before the deck's last change, or research that
    names only earlier deck versions (e.g. 'main-v3' for a v4 deck). Also: a deck built from older research."""
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
        text = " ".join([scope.get("question") or ""] + [f"{f['claim']} {f.get('explanation') or ''}" for f in research.get("findings", [])])
        found = re.findall(r"\b((?:[a-z]+-)?v(\d+))\b", text, re.I)
        if found and ver and max(int(n) for _, n in found) < ver:
            why.append(f"it refers to {collections.Counter(t for t, _ in found).most_common(1)[0][0]}")
        if research.get("created") and brew.get("updated") and research["created"] < brew["updated"]:
            why.append(f"it is dated {research['created']} and the deck changed on {brew['updated']}")
    if why:
        out.append({"level": "warn", "text": f"{pre}Research was written for an earlier version of this deck ({'; '.join(why)}); the deck is now "
                                             f"version {ver}. Findings that name specific cards may describe the older list."})
    if brew.get("research_version") and research.get("version") and brew["research_version"] < research["version"]:
        out.append({"level": "info", "text": f"{pre}The deck was built from research version {brew['research_version']}; research.json is now "
                                             f"version {research['version']}, so newer findings may not be in the list yet."})
    return out


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
