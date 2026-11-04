"""Which data providers scripts may call directly, from the player's saved research choices.

Reads `research.excluded` from ~/.config/edh-companion/config.yaml (PyYAML when the script has it, else a small reader
for that one key: block lists at any indent, inline or multi-line flow lists, comments) and exclusion lines in a
project's PROJECT.md "## Research preferences" section ("Exclude: ...", "Excluded providers:" + bullets, "Avoid X",
"Do not use: X", "Never use X", "Skip X"). An excluded provider gets no requests; callers fall back to cached data,
marked as such. When a value might cover a provider (its name, "direct", or a generic "APIs"/"all"), it counts as
excluded. EDHC_OFFLINE=1 or --offline turns every provider off. Not onboarded (no config) = everything allowed.
"""
import os, re

CONFIG = os.path.join(os.path.expanduser("~"), ".config", "edh-companion", "config.yaml")
PROVIDERS = {"api.scryfall.com": "scryfall", "cards.scryfall.io": "scryfall", "backend.commanderspellbook.com": "commander spellbook"}
ALIASES = {"scryfall": ("scryfall", "direct"), "commander spellbook": ("spellbook", "direct")}
GENERIC = {"all", "any", "every", "everything", "external", "direct", "the", "api", "apis", "calls", "providers", "sources",
           "web", "http", "network", "requests"}  # a value made only of these words covers every provider
EXCLUDE_LINE = re.compile(r"\b(?:exclud\w*|avoid|do not use|don'?t use|never use|skip)\b\s*(?:[\w ]*?:)?\s*(.*)", re.I)
BULLET = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)")


def _items(value):
    vals = (v.strip().strip("'\"*` ").strip() for v in re.split(r"[,;]", value))
    return [v for v in vals if v]


def _yaml_excluded(text):
    """research.excluded without PyYAML. Comments are dropped; a block list may sit at the key's own indent."""
    lines = [re.sub(r"(^|\s)#.*", "", ln).rstrip() for ln in text.splitlines()]
    in_research = False
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        indent = len(ln) - len(ln.lstrip())
        if indent == 0:
            in_research = ln.startswith("research:")
            continue
        m = re.match(r"\s*excluded\s*:\s*(.*)$", ln) if in_research else None
        if not m:
            continue
        rest = m.group(1)
        if rest.startswith("["):  # flow list, possibly over several lines
            for nxt in lines[i + 1:]:
                if "]" in rest:
                    break
                rest += " " + nxt.strip()
            return _items(rest.strip("[] "))
        if rest:
            return _items(rest)
        out = []
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                continue
            b = re.match(r"^(\s*)-\s+(.*)", nxt)
            if not b or len(b.group(1)) < indent:
                break
            out += _items(b.group(2))
        return out
    return []


def _excluded_config(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as h:
        text = h.read()
    try:
        import yaml
    except ImportError:
        yaml = None
    if yaml:
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError:
            doc = None  # unreadable: the line reader below still finds exclusions
        if isinstance(doc, dict):
            r = doc.get("research")
            v = r.get("excluded") if isinstance(r, dict) else None
            return [str(x) for x in v if x] if isinstance(v, list) else _items(str(v)) if v else []
    return _yaml_excluded(text)


def _excluded_project(project):
    p = os.path.join(project, "PROJECT.md") if project else None
    if not p or not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as h:
        m = re.search(r"^## Research preferences\s*\n(.*?)(?=^## |\Z)", h.read(), re.M | re.S)
    lines, out = (m.group(1) if m else "").splitlines(), []
    for i, line in enumerate(lines):
        x = EXCLUDE_LINE.search(line)
        if not x:
            continue
        if _items(x.group(1)):
            out += _items(x.group(1))
            continue
        head = BULLET.match(line)
        for nxt in lines[i + 1:]:  # "Excluded providers:" followed by bullets (nested under it when it is a bullet)
            b = BULLET.match(nxt)
            if not b or (head and len(b.group(1)) <= len(head.group(1))):
                break
            out += _items(b.group(2))
    return out


def _norm(x):
    return re.sub(r"[^a-z0-9]+", " ", str(x).lower()).strip()


class Policy:
    def __init__(self, project=None, offline=None, config=CONFIG):
        self.offline = bool(offline) or os.environ.get("EDHC_OFFLINE") == "1"
        self.excluded = [_norm(x) for x in _excluded_config(config) + _excluded_project(project)]

    def blocked(self, host):
        """None if the host may be called, else the reason."""
        if self.offline:
            return "offline mode"
        prov = PROVIDERS.get(host) or ("scryfall" if host.endswith(".scryfall.io") else None)
        if not prov:
            return None
        for x in self.excluded:
            if any(a in x for a in ALIASES[prov]) or (x and set(x.split()) <= GENERIC):
                return f"{prov} is excluded in your research preferences"
        return None
