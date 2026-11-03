"""End-to-end: fixture index -> site_data.py -> build_site.py -> render in headless Chrome.
Browser part is skipped when Playwright/Chrome aren't available. Set CHARTJS=/path/chart.umd.js to serve
Chart.js locally when cdnjs is unreachable."""
import json, os, shutil, subprocess, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_mtgdb as base

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PAGES = os.path.join(ROOT, "plugins/mtg-pages/skills/mtg-pages/scripts")


class PagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.MtgdbTest.setUpClass()
        cls.T = base.MtgdbTest
        cls.env = dict(cls.T.env, MTGDB=cls.T.db)
        cls.w = tempfile.mkdtemp()
        cls.site = os.path.join(cls.w, "site-data.json")
        tm = os.path.join(cls.w, "theme.json")
        json.dump({"built": time.strftime("%Y-%m-%d"), "spec": {"mode": "prefer", "labels": ["Sith", "Star Wars"], "franchise_label": "Star Wars"},
                   "printings": {"set:swt": "Sith", "sld#999": "Star Wars"}}, open(tm, "w"))
        cls.deck = os.path.join(cls.w, "b3.txt")
        open(cls.deck, "w").write("1 Darth Vader (SWT) 12\n1 Sol Ring (SLD) 999\n1 Demonic Tutor (CMM) 1\n97 Swamp (SWT) 300\n")
        cls.deck4 = os.path.join(cls.w, "b4.txt")
        open(cls.deck4, "w").write("1 Darth Vader (SWT) 12\n1 Sol Ring (SLD) 999\n1 Demonic Tutor (CMM) 1\n1 Vampiric Tutor (CMM) 2\n96 Swamp (SWT) 300\n")
        notes = os.path.join(cls.w, "notes.json")
        json.dump({"pitch": "Vader <b>hunts</b>.", "key_cards": ["Sol Ring"], "youtube": [{"title": "Deck tech", "url": "https://youtu.be/x", "channel": "C", "date": "2026-10-01"}],
                   "checks": {"spellbook": True}, "role_builder_counts": {"ramp": 3}}, open(notes, "w"))
        reasons = os.path.join(cls.w, "off.json")
        json.dump({"Demonic Tutor": "no themed printing"}, open(reasons, "w"))
        cards = os.path.join(cls.w, "edhrec.json")
        json.dump([{"name": "Sol Ring", "pct": 88, "n": 1200}, {"name": "Totally Fake Card", "pct": 30, "n": 40}, {"name": "rhystic studdy", "pct": 31, "n": 40}, {"name": "Demonic Tutor", "pct": 12, "n": 1200}], open(cards, "w"))
        merged = os.path.join(cls.w, "merged.json")
        json.dump([{"card": "Necropotence", "why": "draw", "fits": [{"deck": "vader/b3", "swap_out": "Swamp"}]}], open(merged, "w"))
        led = os.path.join(cls.w, "claims.jsonl")
        open(led, "w").write(json.dumps({"id": "1", "type": "must-play", "claim": "Sol Ring is a must", "status": "verified", "subject": "vader",
                                         "sources": [{"url": "https://edhrec.com/x", "date": "2026-11-01", "kind": "edhrec"}]}) + "\n" +
                             json.dumps({"id": "2", "type": "plan", "claim": "Vader wins by turn 7", "status": "unverified", "subject": "vader", "sources": []}) + "\n")
        sd = lambda *a: subprocess.run([sys.executable, os.path.join(PAGES, "site_data.py")] + list(a), capture_output=True, text=True, env=cls.env)
        cls.steps = [sd("init", cls.site, "--title", "Sith <Vault>", "--bracket", "3", "--themes", tm),
                     sd("add-deck", cls.site, "--group", "Sith decks", "--slug", "vader", "--deck", cls.deck, "--bracket", "3", "--notes", notes, "--reasons", reasons),
                     sd("add-deck", cls.site, "--group", "Sith decks", "--slug", "vader", "--deck", cls.deck4, "--bracket", "4"),
                     sd("add-tier", cls.site, "--id", "sith", "--title", "Sith cards", "--cards", cards),
                     sd("add-swaps", cls.site, "--group", "Sith decks", "--merged", merged),
                     sd("add-claims", cls.site, "--ledger", led)]
        # placeholder art in the raw cache so no network is needed
        from PIL import Image
        cls.raw = os.path.join(cls.w, "raw")
        os.makedirs(cls.raw, exist_ok=True)
        D = json.load(open(cls.site))
        for i, k in enumerate(D.get("images", {})):
            Image.new("RGB", (488, 680), ((i * 47) % 255, 90, 160)).save(os.path.join(cls.raw, k + ".jpg"))
        cls.out = os.path.join(cls.w, "site")
        cls.build = subprocess.run([sys.executable, os.path.join(PAGES, "build_site.py"), cls.site, "--out", cls.out, "--raw-cache", cls.raw],
                                   capture_output=True, text=True, env=cls.env)

    def test_data_steps_succeed(self):
        codes = [s.returncode for s in self.steps]
        self.assertEqual(codes[0], 0, self.steps[0].stderr)
        self.assertEqual(codes[1], 0, self.steps[1].stdout + self.steps[1].stderr)  # b3 passes
        self.assertEqual(codes[2], 0, self.steps[2].stdout)  # 2 Game Changers is fine at B4
        for s in self.steps[3:]:
            self.assertEqual(s.returncode, 0, s.stderr)
        self.assertIn("skipped unresolved", self.steps[3].stderr)  # fake names are dropped, typos are fixed

    def test_site_data_content(self):
        D = json.load(open(self.site))
        deck = D["groups"][0]["commanders"][0]["decks"]
        self.assertEqual([d["bracket"] for d in deck], [3, 4])
        b3 = deck[0]
        self.assertEqual(sum(c["qty"] for c in b3["cards"]), 100)
        self.assertEqual(b3["theme"]["counts"]["Sith"], 1 + 97)
        # commander and basics are exempt, so the percentage is over Sol Ring + Demonic Tutor only: 0 of 2 primary
        self.assertEqual(b3["theme"]["counted_cards"], 2)
        self.assertLessEqual(b3["theme"]["on_theme_pct"], 100)
        self.assertEqual(b3["theme"]["on_theme_pct"], 0.0)
        self.assertIn("turn_5", b3["stats"]["sim"])
        self.assertEqual(b3["stats"]["template"]["lands"][0], 97)
        self.assertIn("ramp", b3["stats"]["role_compare"])
        self.assertTrue(b3["checks"]["validate"])
        self.assertEqual(next(c for c in b3["cards"] if c["name"] == "Demonic Tutor")["reason"], "no themed printing")
        self.assertIn("Sol Ring", D["printings"])
        self.assertEqual(D["accuracy"]["claims_unverified"], 1)

    def test_build_passes_and_respects_limits(self):
        rep = json.loads(self.build.stdout)
        self.assertTrue(rep["pass"], rep)
        self.assertEqual(rep["data"], "inline")
        self.assertTrue(any(f.endswith(".webp") for f in rep["supporting_files"]))
        html = open(os.path.join(self.out, "index.html"), encoding="utf-8").read()
        self.assertNotIn("data:image", html)
        self.assertNotIn("https://cards.scryfall.io", html)  # image urls never ship
        self.assertIn("<title>Sith Vault</title>", html)

    def test_build_rejects_bad_data(self):
        D = json.load(open(self.site))
        D["groups"][0]["commanders"][0]["decks"][0]["cards"][0]["qty"] = 2
        D["tiers"][0]["cards"][0]["pct"] = None
        bad = os.path.join(self.w, "bad.json")
        json.dump(D, open(bad, "w"))
        p = subprocess.run([sys.executable, os.path.join(PAGES, "build_site.py"), bad, "--out", os.path.join(self.w, "x"), "--no-images"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        msg = p.stdout
        self.assertIn("101 cards", msg)
        self.assertIn("has no pct", msg)

    def test_render_in_chrome(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("playwright not installed")
        chrome = shutil.which("google-chrome") or shutil.which("chromium")
        if not chrome:
            self.skipTest("no Chrome")
        cj = os.environ.get("CHARTJS")
        url = "file://" + os.path.join(self.out, "index.html")
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"])
            for width, name in ((1280, "desktop"), (390, "phone")):
                pg = b.new_page(viewport={"width": width, "height": 900})
                errors = []
                pg.on("pageerror", lambda e: errors.append(str(e)))
                pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "fonts" not in m.text else None)
                if cj:
                    pg.route("**/chart.umd.min.js", lambda r: r.fulfill(path=cj, content_type="application/javascript"))
                pg.route("https://fonts.*/**", lambda r: r.fulfill(body="", content_type="text/css"))
                pg.goto(url)
                pg.wait_for_selector("#tabs button")
                tabs = pg.locator("#tabs button").all_inner_texts()
                self.assertEqual(tabs, ["Sith cards", "Sith decks", "Sources & accuracy"])
                # tier tab: S tier holds Sol Ring (88%), C holds Demonic Tutor (12%)
                self.assertIn("Sol Ring", pg.locator(".tier").first.inner_text())
                pg.locator("#tabs button", has_text="Sith decks").click()
                pg.wait_for_selector(".decklist .ln")
                self.assertEqual(pg.locator(".decklist .ln").count(), 4)
                body = pg.inner_text("main")
                self.assertIn("Vader <b>hunts</b>.", body)  # agent text is shown as text, never parsed as HTML
                self.assertNotIn("<b>hunts</b>", pg.inner_html("main"))
                self.assertIn("on theme", body)
                if cj:
                    self.assertGreaterEqual(pg.locator("canvas").count(), 4)
                # bracket switch
                pg.locator("button.btn", has_text="B4").click()
                self.assertIn("Game Changers", pg.inner_text("main"))
                # viewer: open, flip with F, arrows, close restores focus
                pg.locator(".decklist button.name").first.click()
                pg.wait_for_selector("dialog[open]")
                t0 = pg.eval_on_selector("#card3d", "e => e.style.transform")
                pg.keyboard.press("f")
                self.assertNotEqual(t0, pg.eval_on_selector("#card3d", "e => e.style.transform"))
                pg.keyboard.press("ArrowRight")
                self.assertIn("2 / 5", pg.inner_text("#vSide"))  # browses the whole B4 list
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(100)
                self.assertTrue(pg.evaluate("document.activeElement.classList.contains('name')"))
                wrapped = pg.evaluate("[...document.querySelectorAll('.bullet .num')].filter(e => e.getClientRects().length > 1 || e.offsetHeight > 24).length")
                self.assertEqual(wrapped, 0, "template numbers wrap")
                overflow = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                self.assertLessEqual(overflow, 0, f"horizontal scroll at {name}")
                pg.locator("#tabs button", has_text="Sources").click()
                self.assertIn("Vader wins by turn 7", pg.inner_text("main"))
                pg.screenshot(path=os.path.join(self.w, f"shot-{name}.png"), full_page=False)
                self.assertEqual(errors, [], f"console errors at {name}: {errors}")
                pg.close()
            b.close()
        print("screenshots in", self.w, file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
