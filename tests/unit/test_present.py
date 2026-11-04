"""present skill pipeline test: fixture project -> site_data.py -> build_site.py. Needs uv and network (Scryfall).

Run: python tests/unit/test_present.py
"""
import importlib.util, json, os, re, shutil, subprocess, tempfile, unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.join(ROOT, "plugins", "edh-companion", "skills", "present", "scripts")
WS = os.path.join(ROOT, "tests", "fixtures", "krenko")
SC_ROOT = os.path.join(ROOT, "tests", "fixtures", "showcase")
SHOWCASE = os.path.join(SC_ROOT, "showcases", "test-showcase")
RESEARCH_ONLY = os.path.join(SC_ROOT, "projects", "spider-research")
TALRAND = os.path.join(SC_ROOT, "projects", "talrand")
spec = importlib.util.spec_from_file_location("site_data", os.path.join(HERE, "site_data.py"))
site_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site_data)


def build_pipeline(tmp, cmd, path, *flags, site=True):
    """site_data.py (+ build_site.py) into tmp; returns (report, data or None, html or None)."""
    data = os.path.join(tmp, "page-data.json")
    p = run(os.path.join(HERE, "site_data.py"), cmd, path, "--out", data, "--images", "cdn", *flags)
    assert p.returncode == 0, p.stderr
    report = json.loads(p.stdout)
    if not site:
        return report, None, None
    with open(data, encoding="utf-8") as h:
        D = json.load(h)
    b = run(os.path.join(HERE, "build_site.py"), data, "--out", os.path.join(tmp, "site"))
    assert json.loads(b.stdout)["pass"], b.stdout
    with open(os.path.join(tmp, "site", "index.html"), encoding="utf-8") as h:
        return report, D, h.read()


def run(*args):
    return subprocess.run([shutil.which("uv"), "run", "--quiet", "--script", *args], capture_output=True, text=True, encoding="utf-8",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))


class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        data = os.path.join(cls.tmp, "page-data.json")
        p = run(os.path.join(HERE, "site_data.py"), "from-workspace", WS, "--out", data, "--images", "cdn")
        assert p.returncode == 0, p.stderr
        cls.report = json.loads(p.stdout)
        with open(data, encoding="utf-8") as h:
            cls.D = json.load(h)
        b = run(os.path.join(HERE, "build_site.py"), data, "--out", os.path.join(cls.tmp, "site"))
        cls.build = json.loads(b.stdout)
        with open(os.path.join(cls.tmp, "site", "index.html"), encoding="utf-8") as h:
            cls.html = h.read()
        with open(os.path.join(cls.tmp, "presentation-checks.md"), encoding="utf-8") as h:
            cls.checks_md = h.read()
        cls.decks = {d["id"]: d for c in cls.D["groups"][0]["commanders"] for d in c["decks"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_builds_without_errors(self):
        self.assertTrue(self.build["pass"], self.build["errors"])
        self.assertEqual(sorted(self.decks), ["b3", "b4"])
        for d in self.decks.values():
            self.assertEqual(sum(c["qty"] for c in d["cards"]), 100)
            self.assertEqual(d["errors"], [])

    def test_audit_states_derived_never_upgraded(self):
        self.assertEqual(self.decks["b3"]["validation"]["state"], "pass_with_warnings")
        self.assertEqual(self.decks["b4"]["validation"]["state"], "audit out of date")
        self.assertNotIn("checks", self.decks["b4"]["validation"])  # an out-of-date audit's checks are never shown
        kinds = {c["kind"] for c in self.decks["b3"]["validation"]["checks"]}
        self.assertEqual(kinds, {"deterministic", "judgment"})
        self.assertIn('"state":"audit out of date"', self.html)
        states = {i["file"]: i["audit_state"] for i in self.report["inputs"] if "audit_state" in i}
        self.assertEqual(states, {"brew-b3.json": "pass_with_warnings", "brew-b4.json": "audit out of date"})
        self.assertIn("| brew-b4.json | 2 | a7499368e991 | audit out of date |", self.checks_md)
        self.assertIn("| cast-by-turn chart | yes |", self.checks_md)
        self.assertIn("## Theme", self.checks_md)

    def test_derivation_rules(self):
        brew = {"version": 2, "deck_hash": "aaaaaaaaaaaa"}
        audit = {"subject": {"deck": {"version": 2, "deck_hash": "bbbbbbbbbbbb"}}, "checks": [], "verdict": {"status": "pass"}, "auditor": {}}
        shown = lambda a, h="aaaaaaaaaaaa": site_data.shown_validation(brew, a, h)["state"]
        self.assertEqual(shown(None), "not audited")
        self.assertEqual(shown(audit), "audit out of date")  # audit of another list
        audit["subject"]["deck"].update(deck_hash="aaaaaaaaaaaa", version=1)
        self.assertEqual(shown(audit), "audit out of date")  # audit of another version
        audit["subject"]["deck"]["version"] = 2
        self.assertEqual(shown(audit, "cccccccccccc"), "audit out of date")  # list changed since
        self.assertEqual(shown(audit), "pass")

    def test_sources_link_out(self):
        src = self.D["sources"]
        self.assertEqual(len(src), 6)
        self.assertTrue(all(re.match(r"https?://", s["url"]) for s in src))
        video = next(s for s in src if s["links"])
        self.assertEqual([l["url"].rsplit("t=", 1)[1] for l in video["links"]], ["25s", "73s", "89s"])
        self.assertTrue(all(c["url"].startswith("http") for c in self.decks["b3"]["summary"]["community"]))
        self.assertTrue(self.D["groups"][0]["commanders"][0]["youtube"])

    def test_no_invented_numbers(self):
        blob = json.dumps(self.D)
        for key in ('"sim"', '"price_styles"', '"printings"', '"cost_to_buy"'):
            self.assertNotIn(key, blob)
        for d in self.decks.values():
            s, cards = d["stats"], d["cards"]
            self.assertEqual(s["lands"], sum(c["qty"] for c in cards if c["land"] and not c["commander"]))
            self.assertAlmostEqual(s["price"], sum(c["price"] * c["qty"] for c in cards if c["price"] is not None), places=1)
            self.assertEqual(s["unpriced"], [c["name"] for c in cards if c["price"] is None])
        hidden = {x["name"] for x in self.report["sections"] if not x["included"]}
        self.assertIn("research tab (commanders compared, disagreements)", hidden)  # krenko's research sits next to builds
        self.assertTrue(all(x["why_not"] for x in self.report["sections"] if not x["included"]))

    def test_sections_and_swaps(self):
        sw = {s["card"]: s for s in self.D["groups"][0]["swaps"]}
        self.assertEqual(set(sw), {"Goblin Surprise", "Jeska's Will"})  # the rejected rec is left out
        self.assertEqual({f["deck"].split("/")[1] for f in sw["Goblin Surprise"]["fits"]}, {"b3", "b4"})
        titles = [x["title"] for x in self.decks["b3"]["summary"]["sections"]]
        self.assertIn("Proposed cuts", titles)
        self.assertEqual(self.D["theme"]["labels"][0]["label"], "On theme")
        self.assertIn("Player decisions (DECISIONS.md)", titles)
        self.assertIn("Theme (PROJECT.md)", titles)
        self.assertEqual(self.D["title"], "Krenko Goblins")
        dfc = next(c for c in self.decks["b3"]["cards"] if c["name"].startswith("Valakut Awakening"))
        self.assertTrue(dfc["back"] and dfc["back"].endswith("_b"))

    def test_no_theme_no_pills(self):
        brew = {"deck": [{"name": "Sol Ring", "qty": 1, "role": "ramp"}], "theme_policy": None}
        self.assertEqual(site_data.theme_setup([brew]), (None, {}))

    def test_roles_from_deck_check_not_brew_labels(self):
        for d in self.decks.values():
            s = d["stats"]
            counted = {}
            for c in d["cards"]:
                self.assertNotIn("role", c)  # the brew label lives in "label"; stats use the Oracle-text rules
                if not c["commander"]:
                    for r in c["roles"]:
                        counted[r] = counted.get(r, 0) + c["qty"]
            self.assertEqual(s["roles"], counted)
            self.assertIn("Oracle-text rules", s["roles_note"])
            self.assertEqual({r: v[0] for r, v in s["template"].items() if r != "lands"}, {r: s["roles"].get(r, 0) for r in ("ramp", "draw", "removal", "wipe")})
            for x in s["label_diff"]:
                self.assertNotIn(x["label"], x["rules"])
            self.assertTrue(all(isinstance(v, list) and v for c in d["cards"] for v in c["roles"].values()))  # every role names its rule

    def test_analytics_from_deck_check(self):
        s = self.decks["b3"]["stats"]
        self.assertEqual(set(s["price_ladder"]), {"affordable_usd", "as_listed_usd", "premium_usd", "note", "as_of"})
        self.assertGreater(s["cast_by_turn"]["runs"], 0)
        self.assertTrue(s["cast_by_turn"]["assumptions"])
        self.assertEqual(set(s["mana"]), {"pips", "sources"})
        self.assertTrue(any(c.get("cheapest") for c in self.decks["b3"]["cards"]))


class Units(unittest.TestCase):
    """Offline: theming, status, hidden analytics."""

    def test_identity_palette(self):
        hues = site_data.identity_hues
        self.assertEqual(hues(["R"]), (site_data.HUES["R"],) * 2)
        self.assertEqual(hues(["R", "U"]), (site_data.HUES["U"], site_data.HUES["R"]))  # WUBRG order: Izzet = blue, red
        self.assertEqual(hues(["W", "U", "B"]), (site_data.GOLD, site_data.GOLD))  # 3+ colors: one muted gold, no rainbow
        self.assertEqual(hues([]), (site_data.NEUTRAL, site_data.NEUTRAL))  # colorless
        self.assertEqual(site_data.resolve_look([], [])["source"], "commander color identity (colorless)")
        self.assertEqual(site_data.resolve_look([])["source"], "neutral")

    def test_accent_contrast(self):
        for hexc in list(site_data.HUES.values()) + [site_data.GOLD, site_data.NEUTRAL, "#ffff00", "#101010", "#c8102e"]:
            look = site_data.palette(hexc)
            for mode, bgs in (("l", site_data.LIGHT_BG), ("d", site_data.DARK_BG)):
                for key in ("a", "a2"):
                    for bg in bgs:
                        self.assertGreaterEqual(site_data.contrast(look[mode][key], bg), 4.5, (hexc, mode, bg))
        self.assertAlmostEqual(site_data.contrast("#000000", "#ffffff"), 21, places=1)

    def test_theme_precedence(self):
        t = lambda c: {"accent": c}
        cands = [("--theme", None), ("showcase.yaml projects[x] theme", t("#112233")), ("showcase.yaml theme", t("#445566")), ("x/report-theme.yaml", t("#778899"))]
        self.assertEqual(site_data.resolve_look(cands, ["R"])["source"], "showcase.yaml projects[x] theme")
        cands[0] = ("--theme", t("#aa0000"))
        self.assertEqual(site_data.resolve_look(cands, ["R"])["source"], "--theme")
        cands[0], cands[1] = ("--theme", None), ("p", None)
        self.assertEqual(site_data.resolve_look(cands, ["R"])["source"], "showcase.yaml theme")
        only_file = [("--theme", None), ("p", None), ("g", None), ("x/report-theme.yaml", {"accent": "#778899", "style": "comic", "label": "L"})]
        look = site_data.resolve_look(only_file, ["R"])
        self.assertEqual((look["source"], look["style"], look["label"]), ("x/report-theme.yaml", "comic", "L"))
        self.assertEqual(site_data.resolve_look([("p", None)], ["G"])["source"], "commander color identity (G)")
        with self.assertRaises(SystemExit):
            site_data.resolve_look([("bad", {"accent": "red"})])
        with self.assertRaises(SystemExit):
            site_data.resolve_look([("bad", {"accent": "#ff0000", "style": "rainbow"})])

    def test_status(self):
        self.assertEqual(site_data.status_of({"status": "upcoming", "releases": "2027-01-15"}), ("upcoming", "2027-01-15"))
        self.assertEqual(site_data.status_of({"status": "legal"}), (None, None))
        self.assertEqual(site_data.status_of({"status": "legal"}, {"status": "banned"}), ("banned", None))

    def test_analytics_hidden_when_absent(self):
        deck = {"stats": {"price": 1}, "cards": [], "validation": {"state": "not audited"}, "summary": {"community": []}}
        D = {"page": {"show": dict.fromkeys(site_data.SECTIONS, True)}, "research": [], "rankings": [], "groups": []}
        names = ("cast-by-turn chart", "price ladder", "mana sources vs color requirements")
        rows = {x["name"]: x for x in site_data.sections(D, [deck])}
        for name in names:
            self.assertFalse(rows[name]["included"])
            self.assertIn("deck_check", rows[name]["why_not"])
        deck["stats"].update(cast_by_turn={"by_turn": {}}, price_ladder={"x": 1}, mana={"pips": {}})
        rows = {x["name"]: x for x in site_data.sections(D, [deck])}
        self.assertTrue(all(rows[n]["included"] for n in names))


class Showcase(unittest.TestCase):
    """from-showcase: krenko (Villains, b3/b4), spider-gwen + talrand (Heroes: commander picker), spider-research (research only)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.report, cls.D, cls.html = build_pipeline(cls.tmp, "from-showcase", SHOWCASE)
        with open(os.path.join(cls.tmp, "presentation-checks.md"), encoding="utf-8") as h:
            cls.checks_md = h.read()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_groups_and_picker(self):
        g = {x["title"]: x for x in self.D["groups"]}
        self.assertEqual(list(g), ["Villains", "Heroes"])
        self.assertEqual([c["project"] for c in g["Heroes"]["commanders"]], ["spider-gwen", "talrand"])  # 2 commanders: picker
        self.assertEqual([d["id"] for d in g["Villains"]["commanders"][0]["decks"]], ["b3", "b4"])  # variant switch
        self.assertTrue(all(d["project"] for x in g.values() for c in x["commanders"] for d in c["decks"]))
        self.assertEqual(self.D["title"], "Test Showcase")
        self.assertEqual({r["project"] for r in self.D["overview"]}, {"krenko", "spider-gwen", "talrand"})
        self.assertEqual([a["name"] for a in g["Villains"]["alts"]], ["Krenko, Mob Boss"])
        self.assertTrue(g["Villains"]["alts"][0]["built"])

    def test_audits_stay_separate(self):
        states = {i["file"]: i.get("audit_state") for i in self.report["inputs"]}
        self.assertEqual(states["krenko/brew-b4.json"], "audit out of date")
        self.assertEqual(states["talrand/brew.json"], "not audited")
        self.assertIn("| krenko/brew-b3.json | 1 |", self.checks_md)

    def test_rankings_tabs(self):
        R = {r["title"]: r for r in self.D["rankings"]}
        self.assertEqual(list(R), ["Spider-Man heroes", "Spider-Man villains"])
        h = R["Spider-Man heroes"]
        self.assertTrue(h["method"].startswith("EDHREC inclusion") and h["as_of"] == "2026-11-04")
        bolt = h["cards"][1]
        self.assertEqual((bolt["rank"], bolt["tier"], bolt["pct"], bolt["decks"], bolt["n"]), (2, "A", 61.2, 252, 412))
        self.assertEqual((bolt["status"], bolt["releases"]), ("upcoming", "2026-12-05"))
        self.assertTrue(bolt["img"] and bolt["evidence"][0]["url"].startswith("https://"))
        v = R["Spider-Man villains"]["cards"]
        self.assertEqual([c["rank"] for c in v], [1, 2, 3])
        self.assertTrue(all(c["tier"] is None and c["pct"] is None for c in v))  # never computed
        self.assertEqual(v[1]["status"], "banned")
        self.assertEqual(len(self.D["research"]), 1)
        self.assertEqual(self.D["research"][0]["commanders"][0]["legal_check"], "deck_check.py --commander 2026-11-04")

    def test_looks(self):
        looks = {c["project"]: c["look"] for g in self.D["groups"] for c in g["commanders"]}
        self.assertEqual(looks["krenko"]["source"], "showcase.yaml projects[../../krenko] theme")
        self.assertEqual(looks["krenko"]["style"], "gothic")
        self.assertEqual(looks["talrand"]["source"], "commander color identity (U)")
        self.assertNotEqual(looks["talrand"]["l"]["a"], looks["spider-gwen"]["l"]["a"])
        self.assertEqual(self.D["look"]["source"], "neutral")
        self.assertIn("| Talrand, Sky Summoner (talrand) | commander color identity (U) |", self.checks_md)

    def test_future_and_showcase_mode(self):
        tal = next(d for g in self.D["groups"] for c in g["commanders"] for d in c["decks"] if d["project"] == "talrand")
        self.assertEqual(tal["future"]["waits_for"][0]["releases"], "2027-01-15")
        self.assertEqual(self.D["page"]["mode"], "showcase")
        self.assertIn("three.min.js", self.html)
        self.assertTrue(self.D["page"]["show"]["fan"])


class ResearchOnly(unittest.TestCase):
    def test_research_only_report(self):
        tmp = tempfile.mkdtemp()
        try:
            report, D, html = build_pipeline(tmp, "from-workspace", RESEARCH_ONLY)
            self.assertEqual(D["groups"], [])
            self.assertEqual(len(D["rankings"]), 2)
            r = D["research"][0]
            self.assertEqual([c["name"] for c in r["commanders"]], ["Spider-Gwen, Free Spirit", "Electro, Assaulting Battery"])
            self.assertTrue(r["commanders"][0]["disadvantages"] and r["disagreements"])
            self.assertEqual(len(D["sources"]), 2)
            self.assertIn('"rankings"', html)
            hidden = {x["name"] for x in report["sections"] if not x["included"]}
            self.assertIn("overview and decklist", hidden)
            build_pipeline(tmp, "from-workspace", RESEARCH_ONLY, "--mode", "summary", site=False)
            with open(os.path.join(tmp, "summary.md"), encoding="utf-8") as h:
                md = h.read()
            self.assertIn("## Ranking: Spider-Man heroes", md)
            self.assertIn("| 2 | A | Electro's Bolt | 61.2% (252 of 412 decks) |", md)
            self.assertIn("popularity", md)
            self.assertIn("### Commanders compared", md)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Modes(unittest.TestCase):
    def test_interactive_and_summary(self):
        tmp = tempfile.mkdtemp()
        try:
            _, D, html = build_pipeline(tmp, "from-workspace", TALRAND, "--mode", "interactive")
            self.assertEqual((D["viewer"], D["page"]["show"]["fan"], D["page"]["calm"]), ("simple", False, True))
            self.assertNotIn("three.min.js", html)  # no three.js reference at all
            self.assertTrue(D["page"]["show"]["charts"] and D["page"]["show"]["prices"])
            os.remove(os.path.join(tmp, "page-data.json"))
            build_pipeline(tmp, "from-workspace", TALRAND, "--mode", "summary", site=False)
            self.assertFalse(os.path.exists(os.path.join(tmp, "page-data.json")))  # summary mode writes Markdown only
            with open(os.path.join(tmp, "summary.md"), encoding="utf-8") as h:
                md = h.read()
            for part in ("# Talrand spells", "**Plan.**", "**Rule 0.** Bracket 2 (Core); no Game Changers", "**Audit.** not audited",
                         "Roles (from fixed Oracle-text rules", "### Decklist", "1 Talrand, Sky Summoner", "**Planned for release.**", "Price ladder"):
                self.assertIn(part, md)
            self.assertNotIn("weak", md.lower())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
