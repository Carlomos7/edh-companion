"""End-to-end: fixture index -> site_data.py -> build_site.py -> render in headless Chrome.
Browser part is skipped when Playwright/Chrome aren't available. Set CHARTJS=/path/chart.umd.js to serve
Chart.js locally when cdnjs is unreachable."""
import pathlib, json, os, shutil, subprocess, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_mtgdb as base

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PAGES = os.path.join(ROOT, "plugins/mtg/skills/commander-vault/scripts")


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
        cls.steps = [sd("init", cls.site, "--title", "Sith <Vault>", "--bracket", "3", "--themes", tm, "--viewer", "simple"),
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
        cj = os.environ.get("CHARTJS")
        url = pathlib.Path(self.out, "index.html").resolve().as_uri()
        with sync_playwright() as p:
            try:  # a Chrome on PATH, else the installed Chrome found by Playwright (Windows, macOS)
                b = p.chromium.launch(**({"executable_path": chrome} if chrome else {"channel": "chrome"}), args=["--no-sandbox"])
            except Exception as e:
                self.skipTest(f"no Chrome: {str(e)[:80]}")
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

    def build_variant(self, name, **page):
        D = json.load(open(self.site, encoding="utf-8"))
        D["page"] = {**D["page"], **page}
        path = os.path.join(self.w, name + ".json")
        json.dump(D, open(path, "w", encoding="utf-8"))
        out = os.path.join(self.w, name)
        r = subprocess.run([sys.executable, os.path.join(PAGES, "build_site.py"), path, "--out", out, "--raw-cache", self.raw],
                           capture_output=True, text=True, env=self.env)
        return r, out

    def test_page_styles(self):
        """basic: no images, no charts, no viewer, no image download; cdn: Scryfall links, no download, a publish warning."""
        sd = lambda *a: subprocess.run([sys.executable, os.path.join(PAGES, "site_data.py"), "init", *a], capture_output=True,
                                       text=True, env=self.env)
        for style, want in (("basic", ("none", False, "simple")), ("fancy", ("atlas", True, "three"))):
            path = os.path.join(self.w, f"init-{style}.json")
            self.assertEqual(sd(path, "--title", "T", "--style", style).returncode, 0)
            D = json.load(open(path, encoding="utf-8"))
            self.assertEqual((D["page"]["images"], D["page"]["show"]["charts"], D["viewer"]), want)
            self.assertEqual(D["page"]["style"], style)
        path = os.path.join(self.w, "init-custom.json")
        sd(path, "--title", "T", "--style", "basic", "--show", "charts", "--images", "cdn")
        D = json.load(open(path, encoding="utf-8"))
        self.assertEqual((D["page"]["style"], D["page"]["show"]["charts"], D["page"]["images"]), ("custom", True, "cdn"))
        self.assertNotEqual(sd(path, "--title", "T", "--hide", "nonsense").returncode, 0)

        basic = dict(images="none", show={"tiers": False, "charts": False, "swaps": False, "sources": True, "fan": False,
                                          "prices": True, "viewer": False})
        r, out = self.build_variant("basic", **basic)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(os.path.join(out, "img")))  # nothing downloaded
        r, out_cdn = self.build_variant("cdn", images="cdn")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(os.path.join(out_cdn, "img")))
        self.assertIn("artifact", r.stdout + r.stderr)  # says it can't be published as is
        html = open(os.path.join(out_cdn, "index.html"), encoding="utf-8").read()
        self.assertIn('"image_urls"', html)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("playwright not installed")
        chrome = shutil.which("google-chrome") or shutil.which("chromium")
        with sync_playwright() as p:
            try:
                b = p.chromium.launch(**({"executable_path": chrome} if chrome else {"channel": "chrome"}), args=["--no-sandbox"])
            except Exception as e:
                self.skipTest(f"no Chrome: {str(e)[:80]}")
            pg = b.new_page(viewport={"width": 390, "height": 900})
            errors, scripts = [], []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("request", lambda req: scripts.append(req.url) if req.resource_type == "script" else None)
            pg.route("https://fonts.*/**", lambda r: r.fulfill(body="", content_type="text/css"))
            pg.goto(pathlib.Path(out, "index.html").resolve().as_uri())
            pg.wait_for_selector("#tabs button")
            self.assertEqual(pg.locator("#tabs button").all_inner_texts(), ["Sith decks", "Sources & accuracy"])
            pg.wait_for_selector(".decklist .ln")
            self.assertEqual(pg.locator(".decklist .art").count(), 0)
            self.assertEqual(pg.locator("canvas").count(), 0)
            self.assertFalse(any("chart" in u.lower() or "three" in u for u in scripts), scripts)  # basic loads no libraries
            pg.locator(".decklist button.name").first.click()
            self.assertFalse(pg.evaluate("document.querySelector('#viewer').open"))
            overflow = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            self.assertLessEqual(overflow, 0)
            self.assertEqual(errors, [])
            b.close()

    def test_three_viewer_option(self):
        """--viewer 3d: the page loads three.js only then, spins the card, and falls back to the CSS viewer without it."""
        D = json.load(open(self.site, encoding="utf-8"))
        self.assertEqual(D["viewer"], "simple")  # default
        D["viewer"] = "three"
        site3 = os.path.join(self.w, "site3.json")
        json.dump(D, open(site3, "w", encoding="utf-8"))
        out3 = os.path.join(self.w, "site3")
        b3 = subprocess.run([sys.executable, os.path.join(PAGES, "build_site.py"), site3, "--out", out3, "--raw-cache", self.raw],
                            capture_output=True, text=True, env=self.env)
        self.assertEqual(b3.returncode, 0, b3.stdout + b3.stderr)
        D["viewer"] = "webgpu"
        json.dump(D, open(site3, "w", encoding="utf-8"))
        bad = subprocess.run([sys.executable, os.path.join(PAGES, "build_site.py"), site3, "--out", out3 + "x", "--raw-cache", self.raw],
                             capture_output=True, text=True, env=self.env)
        self.assertNotEqual(bad.returncode, 0)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("playwright not installed")
        chrome = shutil.which("google-chrome") or shutil.which("chromium")
        three = os.environ.get("THREEJS")  # offline: path to three.min.js r128
        with sync_playwright() as p:
            try:
                b = p.chromium.launch(**({"executable_path": chrome} if chrome else {"channel": "chrome"}), args=["--no-sandbox"])
            except Exception as e:
                self.skipTest(f"no Chrome: {str(e)[:80]}")
            import functools, http.server, threading
            srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(
                type("Quiet", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None}), directory=out3))
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            served = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
            # served over http: real 3D (if WebGL works); script blocked: simple viewer; opened from disk: simple viewer
            for mode in ("served", "blocked", "disk"):
                blocked = mode != "served"
                pg = b.new_page(viewport={"width": 1280, "height": 900})
                errors, warnings = [], []
                pg.on("pageerror", lambda e: errors.append(str(e)))
                pg.on("console", lambda m: (errors if m.type == "error" else warnings).append(m.text)
                      if m.type in ("error", "warning") and "fonts" not in m.text and "chart" not in m.text.lower() else None)
                pg.route("https://fonts.*/**", lambda r: r.fulfill(body="", content_type="text/css"))
                pg.route("**/chart.umd.min.js", lambda r: r.fulfill(body="", content_type="application/javascript"))
                if mode == "blocked":
                    pg.route("**/three.min.js", lambda r: r.abort())
                elif three:
                    pg.route("**/three.min.js", lambda r: r.fulfill(path=three, content_type="application/javascript"))
                pg.goto(served if mode != "disk" else pathlib.Path(out3, "index.html").resolve().as_uri())
                pg.wait_for_selector("#tabs button")
                pg.locator("#tabs button", has_text="Sith decks").click()
                pg.locator(".decklist button.name").first.click()
                pg.wait_for_selector("dialog[open]")
                pg.wait_for_timeout(1500)
                on = pg.evaluate("V3.on")
                if blocked:
                    self.assertFalse(on)  # no three.js: the simple viewer still works
                    t0 = pg.eval_on_selector("#card3d", "e => e.style.transform")
                    pg.keyboard.press("f")
                    self.assertNotEqual(t0, pg.eval_on_selector("#card3d", "e => e.style.transform"))
                    self.assertTrue(any("simple viewer" in w for w in warnings), warnings)
                elif on:  # three.js loaded and WebGL works
                    self.assertEqual(pg.locator("#stage canvas").count(), 1)
                    self.assertFalse(pg.is_visible("#card3d"))
                    y0 = pg.evaluate("V3.g.rotation.y")
                    pg.keyboard.press("f")
                    pg.wait_for_timeout(800)
                    self.assertGreater(abs(pg.evaluate("V3.g.rotation.y") - y0), 2.5)  # flipped about 180 degrees
                    pg.keyboard.press("ArrowRight")
                    self.assertIn("2 / ", pg.inner_text("#vSide"))
                    pg.screenshot(path=os.path.join(self.w, "shot-3d.png"))
                if mode == "blocked":  # the browser logs the request the test itself blocked
                    errors = [e for e in errors if "Failed to load resource" not in e]
                print(f"3D viewer ({mode}): {'on' if on else 'simple fallback'}", file=sys.stderr)
                self.assertEqual(errors, [], f"console errors ({mode}): {errors}")
                pg.close()
            b.close()
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
