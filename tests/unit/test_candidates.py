"""candidates.py: research -> verified card candidates. Offline with a fake data session, plus one live smoke test."""
import glob, json, os, shutil, subprocess, sys, tempfile, unittest, urllib.request
from types import SimpleNamespace

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PLUGIN = os.path.join(ROOT, "plugins", "edh-companion")
SCRIPT = os.path.join(PLUGIN, "scripts", "candidates.py")
sys.path.insert(0, os.path.join(PLUGIN, "scripts"))
import candidates as cand  # noqa: E402
from edhcore.http import Unavailable  # noqa: E402

from jsonschema import Draft202012Validator  # noqa: E402
from referencing import Registry, Resource  # noqa: E402

TODAY = "2026-11-04"


def registry():
    reg = Registry()
    for f in glob.glob(os.path.join(PLUGIN, "schemas", "*.schema.json")):
        with open(f, encoding="utf-8") as h:
            reg = reg.with_resource(os.path.basename(f), Resource.from_contents(json.load(h)))
    return reg


def errors(doc, kind):
    reg = registry()
    schema = reg.get_or_retrieve(f"{kind}.schema.json").value.contents
    return [f"{list(e.absolute_path)}: {e.message}" for e in Draft202012Validator(schema, registry=reg).iter_errors(doc)]


def write(path, text):
    with open(path, "w", encoding="utf-8") as h:
        h.write(text)


def card(name, ci, legal="legal", gc=False, released="2020-01-01"):
    return {"id": "id-" + name, "oracle_id": "o-" + name, "name": name, "type_line": "Creature", "color_identity": ci,
            "legalities": {"commander": legal}, "game_changer": gc, "released_at": released, "scryfall_uri": "https://scryfall.com/x"}


CARDS = {c["name"].lower(): c for c in [
    card("Krenko, Mob Boss", ["R"]), card("Tymna the Weaver", ["W", "B"]), card("Thrasios, Triton Hero", ["G", "U"]),
    card("Goblin Chieftain", ["R"]), card("Coat of Arms", []), card("Sol Ring", []), card("Mana Crypt", [], legal="banned"),
    card("Counterspell", ["U"]), card("Jeska's Will", ["R"], gc=True), card("Future Goblin", ["R"], legal="not_legal", released="2027-02-01"),
    card("Silver-Bordered Goblin", ["R"], legal="not_legal"), card("Goblin Recruiter", ["R"]), card("Hellrider", ["R"])]}


class FakeScryfall:
    def __init__(self, unavailable=(), prints=None, search_fails=False, stale=()):
        self.unavailable, self.prints, self.search_fails, self.calls = {n.lower() for n in unavailable}, prints or [], search_fails, []
        self.stale_ids = {"id-" + n for n in stale}

    def collection(self, idents, need="legality"):
        self.calls.append(("collection", len(idents)))
        out, nf, un = [], [], []
        for i, x in enumerate(idents):
            n = x["name"].lower()
            out.append(None if n in self.unavailable else CARDS.get(n))
            (un if n in self.unavailable else nf if n not in CARDS else []).append(i)
        return out, nf, un

    def search(self, q, unique="cards", limit=None):
        self.calls.append(("search", q))
        if self.search_fails:
            raise Unavailable("api.scryfall.com/cards/search", "502 after 3 tries")
        return [p for p in self.prints if f'!"{p["name"]}"' in q]


class FakeSession:
    def __init__(self, verification="fresh", **kw):
        self.scryfall, self.verification = FakeScryfall(**kw), verification

    def data_block(self):
        return {"as_of": "2026-11-04 10:00", "verification": self.verification, "endpoints_unavailable": [], "requests": 1}


def args(**kw):
    base = dict(commander=None, bracket=None, theme_sets=None, add=None, add_name=None)
    return SimpleNamespace(**{**base, **kw})


RESEARCH = {
    "schema_version": "1.0", "version": 4,
    "sources": [{"id": "src-001", "type": "stats"}, {"id": "src-002", "type": "community"}],
    "findings": [
        {"id": "fnd-001", "claim": "x", "class": "community_opinion", "confidence": "medium", "evidence": ["src-002"], "cards": ["Goblin Chieftain"]},
        {"id": "fnd-002", "claim": "y", "class": "verified_fact", "confidence": "high", "evidence": ["src-001"], "cards": ["Goblin Chieftain", "Coat of Arms"]},
        {"id": "fnd-003", "claim": "z", "class": "model_assessment", "confidence": "low", "evidence": [], "cards": ["Mana Crypt", "Counterspell", "Jeska's Will", "Future Goblin", "Silver-Bordered Goblin", "Nonexistent Goblin", "Sol Ring", "Hellrider"]}],
    "card_candidates": [{"card": {"name": "Goblin Chieftain"}, "relevance": "lord", "evidence": ["src-002"], "theme_fit": "on_theme"},
                        {"card": {"name": "Hellrider"}, "relevance": "damage", "evidence": ["src-002"], "theme_fit": "off_theme"}],
    "rankings": [
        {"group": "Krenko", "method": "EDHREC", "cards": [{"card": {"name": "Goblin Chieftain"}, "rank": 1, "why": "", "evidence": ["src-001"], "inclusion_pct": 60.0, "decks": 600, "total_decks": 1000}]},
        {"group": "Goblins", "method": "EDHREC", "cards": [{"card": {"name": "goblin chieftain"}, "rank": 2, "why": "", "evidence": ["src-001"], "inclusion_pct": 40.0, "decks": 40, "total_decks": 100}]}],
}


def brew(commanders=("Krenko, Mob Boss",), bracket=3, policy=None):
    return {"schema_version": "1.0", "version": 1, "deck_hash": "0" * 12, "updated": TODAY, "commander": {"cards": [{"name": n} for n in commanders], "rationale": "r"},
            "target_bracket": {"bracket": bracket}, "strategy": {"archetype": "a", "game_plan": "g"}, "deck": [], "recommendations": [], "theme_policy": policy}


class Candidates(unittest.TestCase):
    def run_build(self, research=RESEARCH, brew_doc=None, session=None, **kw):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        write(os.path.join(d, "research.json"), json.dumps(research))
        write(os.path.join(d, "brew.json"), json.dumps(brew_doc or brew()))
        self.session = session or FakeSession()
        doc = cand.build(d, args(**kw), self.session, today=TODAY)
        self.assertEqual(errors(doc, "candidates"), [])
        return doc, {c["name"]: c for c in doc["cards"]}

    def test_verdicts(self):
        doc, by = self.run_build()
        self.assertEqual(by["Sol Ring"]["verdict"], "eligible")
        self.assertEqual(by["Mana Crypt"]["verdict"], "ineligible")
        self.assertIn("banned in Commander", by["Mana Crypt"]["reasons"])
        self.assertEqual(by["Counterspell"]["verdict"], "ineligible")
        self.assertFalse(by["Counterspell"]["in_identity"])
        self.assertEqual(by["Silver-Bordered Goblin"]["verdict"], "ineligible")
        self.assertEqual(by["Nonexistent Goblin"]["verdict"], "ineligible")
        self.assertIn("not found on Scryfall", by["Nonexistent Goblin"]["reasons"])
        jw = by["Jeska's Will"]
        self.assertEqual((jw["verdict"], jw["status"]), ("needs_review", "legal"))
        self.assertTrue(any("bracket 3 allows up to 3 per deck" in r for r in jw["reasons"]))
        fg = by["Future Goblin"]
        self.assertEqual((fg["verdict"], fg["status"]), ("needs_review", "upcoming"))
        self.assertNotIn("Krenko, Mob Boss", by)  # commanders aren't candidates for the 99
        self.assertEqual(doc["research_version"], 4)
        self.assertEqual(doc["counts"], {"eligible": sum(c["verdict"] == "eligible" for c in doc["cards"]),
                                         "needs_review": sum(c["verdict"] == "needs_review" for c in doc["cards"]),
                                         "ineligible": sum(c["verdict"] == "ineligible" for c in doc["cards"])})
        self.assertEqual([c[0] for c in self.session.scryfall.calls], ["collection"])  # one batched lookup

    def test_gc_note_follows_bracket(self):
        _, by = self.run_build(brew_doc=brew(bracket=2))
        self.assertTrue(any("bracket 2 allows no Game Changers" in r for r in by["Jeska's Will"]["reasons"]))
        _, by = self.run_build(bracket=4)
        self.assertEqual(by["Jeska's Will"]["verdict"], "needs_review")
        self.assertTrue(any("bracket 4 allows any" in r for r in by["Jeska's Will"]["reasons"]))

    def test_partner_identity_union(self):
        doc, by = self.run_build(commander=["Tymna the Weaver", "Thrasios, Triton Hero"])
        self.assertEqual(doc["color_identity"], ["B", "G", "U", "W"])
        self.assertTrue(by["Counterspell"]["in_identity"])
        self.assertEqual(by["Goblin Chieftain"]["verdict"], "ineligible")

    def test_evidence_union_and_strongest_class(self):
        _, by = self.run_build()
        gc = by["Goblin Chieftain"]  # research names differing in case merge into one card
        self.assertEqual(sorted(gc["evidence"]), ["fnd-001", "fnd-002", "src-001", "src-002"])
        self.assertEqual((gc["evidence_class"], gc["evidence_confidence"]), ("verified_fact", "high"))
        self.assertEqual(by["Counterspell"]["evidence_class"], "model_assessment")

    def test_edhrec_conflict_kept(self):
        _, by = self.run_build()
        gc = by["Goblin Chieftain"]
        self.assertEqual(gc["edhrec"], {"inclusion_pct": 60.0, "decks": 600, "total_decks": 1000})
        self.assertEqual(sorted(x["inclusion_pct"] for x in gc["edhrec_conflict"]), [40.0, 60.0])

    def test_added_card_needs_review(self):
        _, by = self.run_build(add_name=["Goblin Recruiter"])
        gr = by["Goblin Recruiter"]
        self.assertEqual((gr["verdict"], gr["evidence"], gr["evidence_class"], gr["added"]), ("needs_review", [], None, True))
        self.assertIn("no research evidence yet", gr["reasons"])

    def test_added_from_file(self):
        f = os.path.join(tempfile.mkdtemp(), "add.txt")
        self.addCleanup(shutil.rmtree, os.path.dirname(f), True)
        open(f, "w", encoding="utf-8").write("# new\n1 Goblin Recruiter\n\n")
        _, by = self.run_build(add=f)
        self.assertEqual(by["Goblin Recruiter"]["verdict"], "needs_review")

    def test_unavailable_data_needs_review(self):
        _, by = self.run_build(session=FakeSession(unavailable=["Sol Ring"]))
        self.assertEqual(by["Sol Ring"]["verdict"], "needs_review")
        self.assertIn("card data unavailable", by["Sol Ring"]["reasons"])

    def test_stale_cards_never_eligible_others_unaffected(self):
        pol = {"mode": "prefer", "eligibility": "Goblins", "art_required": False,
               "exceptions": [{"card": "Coat of Arms", "reason": "anthem", "approved_by": "player"}]}
        _, by = self.run_build(brew_doc=brew(policy=pol), session=FakeSession(verification="stale", stale=["Goblin Chieftain"]))
        self.assertEqual(by["Goblin Chieftain"]["verdict"], "needs_review")
        self.assertTrue(any("data stale" in r for r in by["Goblin Chieftain"]["reasons"]))
        self.assertEqual(by["Coat of Arms"]["verdict"], "eligible")    # served fresh: not flagged

    def test_theme_exception_eligible(self):
        pol = {"mode": "prefer", "eligibility": "Goblins", "art_required": False,
               "exceptions": [{"card": "Coat of Arms", "reason": "anthem", "approved_by": "player"}]}
        _, by = self.run_build(brew_doc=brew(policy=pol))
        ca = by["Coat of Arms"]
        self.assertEqual((ca["verdict"], ca["theme"]["fit"]), ("eligible", "exception"))
        self.assertEqual(by["Goblin Chieftain"]["theme"]["fit"], "on_theme")  # research theme_fit
        self.assertIn("research marks it off theme", by["Hellrider"]["reasons"])
        self.assertTrue(any("theme unclear" in r for r in by["Sol Ring"]["reasons"]))

    def test_art_required_without_theme_printing(self):
        pol = {"mode": "strict", "eligibility": "Spider-Man art", "art_required": True, "exceptions": []}
        prints = [{"name": "Sol Ring", "oracle_id": "o-Sol Ring", "set": "spm", "collector_number": "9", "id": "p1", "illustration_id": "i1"}]
        _, by = self.run_build(brew_doc=brew(policy=pol), session=FakeSession(prints=prints), theme_sets="spm")
        hr = by["Hellrider"]
        self.assertEqual((hr["verdict"], hr["theme"]["fit"], hr["printings_on_theme"]), ("needs_review", "off_theme", []))
        sr = by["Sol Ring"]
        self.assertEqual((sr["verdict"], sr["theme"]["fit"], sr["printing_choice"]), ("eligible", "on_theme", "needed"))
        self.assertEqual(sr["printings_on_theme"][0]["printing_id"], "p1")
        self.assertEqual(sum(c[0] == "search" for c in self.session.scryfall.calls), 1)  # one printing query per 15 names

    def test_printing_choice_is_a_field_not_a_verdict_reason(self):
        """Review: art-themed projects (Azula) had every card needs_review only because a printing must be chosen."""
        pol = {"mode": "prefer", "eligibility": "Avatar art", "art_required": True,
               "exceptions": [{"card": "Coat of Arms", "reason": "anthem", "approved_by": "player"}]}
        b = brew(policy=pol)
        b["deck"] = [{"name": "Goblin Chieftain", "qty": 1, "set": "tla", "collector_number": "5"}]
        prints = [{"name": n, "oracle_id": "o-" + n, "set": "tla", "collector_number": "1", "id": "p-" + n} for n in ("Sol Ring", "Goblin Chieftain")]
        doc, by = self.run_build(brew_doc=b, session=FakeSession(prints=prints), theme_sets="tla")
        self.assertFalse([r for c in doc["cards"] for r in c["reasons"] if "art decides" in r or "choose a printing" in r])
        self.assertEqual((by["Sol Ring"]["verdict"], by["Sol Ring"]["printing_choice"]), ("eligible", "needed"))
        self.assertEqual((by["Goblin Chieftain"]["verdict"], by["Goblin Chieftain"]["printing_choice"]), ("eligible", "done"))
        self.assertEqual(by["Coat of Arms"]["printing_choice"], "n/a")             # approved exception
        self.assertEqual(by["Mana Crypt"]["verdict"], "ineligible")                # hard rules unchanged
        self.assertEqual(by["Hellrider"]["verdict"], "needs_review")               # theme fit still decides
        self.assertEqual(doc["printing_choice"], {"needed": sum(c["printing_choice"] == "needed" for c in doc["cards"]), "done": 1})
        _, by = self.run_build()                                                    # no art rule: n/a everywhere
        self.assertEqual({c["printing_choice"] for c in by.values()}, {"n/a"})

    def test_future_reprint_is_not_upcoming(self):
        """A new printing of an old card (Abrade's 2026 reprint) is not an upcoming card."""
        self.assertEqual(cand.status_of(dict(card("Abrade", ["R"], released="2026-11-13"), reprint=True), TODAY), "legal")
        self.assertEqual(cand.status_of(card("New Card", ["R"], released="2026-11-13"), TODAY), "upcoming")

    def test_strict_set_theme_flags_but_never_rejects(self):
        pol = {"mode": "strict", "eligibility": "official set cards", "art_required": False, "exceptions": []}
        _, by = self.run_build(brew_doc=brew(policy=pol), theme_sets="spm")
        self.assertEqual(by["Hellrider"]["verdict"], "needs_review")   # a set filter alone never rejects a card
        self.assertTrue(any("strict theme" in r for r in by["Hellrider"]["reasons"]))
        self.assertEqual(by["Goblin Chieftain"]["theme"]["fit"], "on_theme")  # research said on theme: not rejected

    def test_printing_search_unavailable(self):
        pol = {"mode": "prefer", "eligibility": "x", "art_required": False, "exceptions": []}
        _, by = self.run_build(brew_doc=brew(policy=pol), session=FakeSession(search_fails=True), theme_sets="spm")
        self.assertEqual(by["Sol Ring"]["verdict"], "needs_review")
        self.assertIn("printing data unavailable: theme not checked", by["Sol Ring"]["reasons"])


class BrewSchema(unittest.TestCase):
    def test_fixture_brews_still_valid(self):
        files = glob.glob(os.path.join(ROOT, "tests", "fixtures", "**", "brew*.json"), recursive=True)
        self.assertTrue(files)
        for f in files:
            with open(f, encoding="utf-8") as h:
                self.assertEqual(errors(json.load(h), "brew"), [], f)

    def test_deck_evidence(self):
        b = brew()
        b["deck"] = [{"name": "Sol Ring", "qty": 1, "role": "ramp", "evidence": ["src-001", "fnd-worker-002"]}]
        self.assertEqual(errors(b, "brew"), [])
        b["deck"][0]["evidence"] = ["not-an-id"]
        self.assertNotEqual(errors(b, "brew"), [])


def online():
    try:
        req = urllib.request.Request("https://api.scryfall.com/sets/spm", headers={"User-Agent": "edh-companion-tests/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception:
        return False


@unittest.skipUnless(online(), "Scryfall unreachable")
class Live(unittest.TestCase):
    def test_krenko_smoke(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        proj = os.path.join(d, "krenko")
        shutil.copytree(os.path.join(ROOT, "tests", "fixtures", "krenko"), proj)
        r = subprocess.run([sys.executable, SCRIPT, proj, "--add-name", "Goblin Chieftain", "--add-name", "Counterspell"],
                           capture_output=True, text=True, encoding="utf-8", timeout=180)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("wrote", r.stdout)
        with open(os.path.join(proj, "candidates.json"), encoding="utf-8") as h:
            doc = json.load(h)
        self.assertEqual(errors(doc, "candidates"), [])
        by = {c["name"]: c for c in doc["cards"]}
        self.assertEqual(by["Counterspell"]["verdict"], "ineligible")
        self.assertEqual(by["Goblin Chieftain"]["verdict"], "needs_review")  # added: no research evidence yet


if __name__ == "__main__":
    unittest.main()
