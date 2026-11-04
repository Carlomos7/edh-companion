"""A data session: one cache, one HTTP client, one provider policy, and a record of how fresh the data it served is.

  s = Session(fresh=False, offline=False, project=None)
  cards, missing, unavailable = s.scryfall.collection([{"name": "Sol Ring"}], need="legality")
  s.data_block()  ->  {"as_of", "verification": fresh|cached|stale|unavailable|None (nothing looked up), "endpoints_unavailable": [...], "requests"}

Freshness per data category (MAX_AGE). --fresh = max age 0 (final audits). When a refresh fails, a cached copy up to
STALE_LIMIT old is used and the result says "stale"; with no copy the item is "unavailable". Callers report checks that
relied on stale or unavailable data as unverified.
"""
import hashlib, json, time

from .cache import Cache
from .cards import match_name, norm_name
from .http import Client, RequestError, Unavailable
from .policy import Policy

DAY = 86400
MAX_AGE = {"oracle": 7 * DAY, "legality": DAY, "price": DAY, "search": DAY, "combos": DAY}
STALE_LIMIT = 30 * DAY
RANK = {"fresh": 0, "cached": 1, "stale": 2, "unavailable": 3}
SCRYFALL = "https://api.scryfall.com"


class Session:
    def __init__(self, fresh=False, offline=False, project=None, cache=None, client=None, policy=None, now=time.time):
        self.fresh, self.now = fresh, now
        self.cache = cache if cache is not None else Cache(now=now)
        self.policy = policy if policy is not None else Policy(project=project, offline=offline)
        self.client = client if client is not None else Client(self.cache, self.policy, now=now)
        self.status, self.oldest, self.used = "fresh", None, False  # used: some data was looked up (else verification None)
        self.scryfall = Scryfall(self)
        self.spellbook = Spellbook(self)

    # --- provenance --------------------------------------------------------------------------------------------
    def _mark(self, status, fetched_at=None):
        self.used = True
        if RANK[status] > RANK[self.status]:
            self.status = status
        if fetched_at is not None:
            self.oldest = fetched_at if self.oldest is None else min(self.oldest, fetched_at)

    def ok(self, fetched_at, need):
        return not self.fresh and self.now() - fetched_at <= MAX_AGE[need]

    def cached(self, key, need):
        """Cache hit within the freshness rule for `need`, else None."""
        hit = self.cache.get(key)
        if hit and self.ok(hit[1], need):
            self._mark("cached", hit[1])
            return hit[0]
        return None

    def fallback(self, key):
        """After a failed refresh: an older copy (≤ STALE_LIMIT), marked stale; else None, marked unavailable."""
        hit = self.cache.get(key)
        if hit and self.now() - hit[1] <= STALE_LIMIT:
            self._mark("stale", hit[1])
            return hit[0]
        self._mark("unavailable")
        return None

    def fetched(self):
        self._mark("fresh", self.now())

    def data_block(self):
        return {"as_of": time.strftime("%Y-%m-%d %H:%M", time.localtime(self.oldest)) if self.oldest else None,
                "verification": self.status if self.used else None, "endpoints_unavailable": [f"{k}: {v}" for k, v in sorted(self.client.unavailable.items())],
                "requests": self.client.requests, **({"cache_note": self.cache.note} if self.cache.note else {})}


def ident_key(ident):
    if ident.get("id"):
        return "card:id:" + ident["id"]
    if ident.get("set") and ident.get("collector_number"):
        return f"card:print:{ident['set'].lower()}:{ident['collector_number']}"
    return "card:name:" + ident["name"].lower()


def ident_for(e):
    """Scryfall collection identifier for a decklist entry {name, set, cn}; split names use their front half."""
    if e.get("set") and e.get("cn"):
        return {"set": e["set"], "collector_number": e["cn"]}
    return {"name": e["name"].split(" // ")[0]}


def _ident_norm(x):
    """Comparable form of a collection identifier (Scryfall's echo in not_found may differ in case or punctuation)."""
    return tuple(sorted((k, norm_name(str(v)) if k == "name" else str(v).lower()) for k, v in x.items()))


def _matches(card, ident):
    if ident.get("id"):
        return card.get("id") == ident["id"]
    if ident.get("set") and ident.get("collector_number"):
        return card.get("set") == ident["set"].lower() and card.get("collector_number") == str(ident["collector_number"])
    return match_name(card, ident["name"])


class Scryfall:
    def __init__(self, s):
        self.s = s
        self.stale_ids = set()  # card ids served from an over-age copy after a failed refresh (callers flag just these)

    def _store(self, card, ident=None):
        if ident:
            self.s.cache.put(ident_key(ident), "card", card)
        self.s.cache.put("card:id:" + card["id"], "card", card)

    def collection(self, idents, need="legality"):
        """Cards for identifiers ({name} | {set, collector_number} | {id}), cache first, 75 per request for the rest.
        Returns (cards aligned with idents or None, not_found indices, unavailable indices)."""
        out, misses, not_found, unavailable = [None] * len(idents), [], [], []
        for i, ident in enumerate(idents):
            out[i] = self.s.cached(ident_key(ident), need)
            if out[i] is None:
                misses.append(i)
        for start in range(0, len(misses), 75):
            chunk = misses[start:start + 75]
            body = [{k: v for k, v in idents[i].items() if k in ("name", "set", "collector_number", "id")} for i in chunk]
            try:
                res = self.s.client.post_json(SCRYFALL + "/cards/collection", {"identifiers": body})
            except (Unavailable, RequestError):
                for i in chunk:
                    out[i] = self.s.fallback(ident_key(idents[i]))
                    if out[i] is None:
                        unavailable.append(i)
                    else:
                        self.stale_ids.add(out[i].get("id"))
                continue
            self.s.fetched()
            data, gone = list(res.get("data") or []), [_ident_norm(x) for x in res.get("not_found") or []]
            found = []
            for i, b in zip(chunk, body):  # Scryfall echoes the identifiers it couldn't find in `not_found`
                if _ident_norm(b) in gone:
                    gone.remove(_ident_norm(b))
                    not_found.append(i)
                else:
                    found.append(i)
            # data holds the found cards in request order: pair them up. Name/set matching is only a sanity check
            # (prefer a matching card if the pair disagrees) and the fallback when the counts don't line up.
            aligned = len(data) == len(found)
            for n, i in enumerate(found):
                own = data[n] if aligned else None
                card = own if own and _matches(own, idents[i]) else next((c for c in data if _matches(c, idents[i])), own)
                if card is None:
                    not_found.append(i)
                else:
                    out[i] = card
                    self._store(card, idents[i])
            not_found.sort()
        return out, not_found, unavailable

    def named(self, names, need="legality"):
        """{name: card or None} for card names (batched)."""
        cards, _, _ = self.collection([{"name": n.split(" // ")[0]} for n in names], need)
        return dict(zip(names, cards))

    def search(self, q, unique="cards", need="search", limit=None):
        """All results of a Scryfall search (every page, or up to `limit` cards). [] when nothing matches.
        Raises Unavailable when it can't be done and there's no usable copy."""
        key = f"search:{unique}:{q}" + (f":{limit}" if limit else "")
        hit = self.s.cached(key, need)
        if hit is not None:
            return hit
        import urllib.parse
        url, cards = SCRYFALL + "/cards/search?" + urllib.parse.urlencode({"q": q, "unique": unique}), []
        try:
            while url and (not limit or len(cards) < limit):
                try:
                    res = self.s.client.get_json(url)
                except RequestError as e:
                    if e.code == 404:  # Scryfall's "no cards found"
                        break
                    raise
                cards += res.get("data", [])
                url = res.get("next_page") if res.get("has_more") else None
        except (Unavailable, RequestError):
            old = self.s.fallback(key)
            if old is None:
                raise
            return old
        self.s.fetched()
        cards = cards[:limit] if limit else cards
        self.s.cache.put(key, "search", cards)
        return cards

    def card(self, card_id, need="legality"):
        return self.collection([{"id": card_id}], need)[0][0]


class Spellbook:
    URL = "https://backend.commanderspellbook.com/find-my-combos"

    def __init__(self, s):
        self.s = s

    def find_my_combos(self, commanders, main):
        """main: [(name, qty)]. Cached by the sorted list for MAX_AGE['combos']."""
        body = {"commanders": [{"card": n} for n in commanders], "main": [{"card": n, "quantity": q} for n, q in main]}
        key = "combos:" + hashlib.sha1(json.dumps({"c": sorted(commanders), "m": sorted(main)}).encode()).hexdigest()
        hit = self.s.cached(key, "combos")
        if hit is not None:
            return hit
        try:
            res = self.s.client.post_json(self.URL, body)
        except (Unavailable, RequestError):
            old = self.s.fallback(key)
            if old is None:
                raise
            return old
        self.s.fetched()
        self.s.cache.put(key, "combos", res)
        return res
