"""hook.py (offline paths), research-find --summary, companion.py card / archive-findings, eval cost budgets."""
import contextlib, importlib.util, io, json, os, shutil, sys, tempfile, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS = os.path.join(ROOT, "plugins", "edh-companion", "scripts")


def mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


hook = mod("hook", os.path.join(SCRIPTS, "hook.py"))
co = mod("companion", os.path.join(SCRIPTS, "companion.py"))
stats = mod("session_stats", os.path.join(ROOT, "tests", "bench", "session_stats.py"))


def put(p, x):
    with open(p, "w", encoding="utf-8") as h:
        h.write(x if isinstance(x, str) else json.dumps(x))


RESEARCH = {"sources": [{"id": "src-1", "author": "Spider Lab", "url": "https://youtube.com/a"},
                        {"id": "src-2", "author": "Spider Lab", "url": "https://youtube.com/b"},
                        {"id": "src-3", "url": "https://www.reddit.com/r/EDH/x"}],
            "findings": [{"id": "fnd-1", "claim": "Bolt is cut for Galvanic Discharge.", "class": "community_opinion", "confidence": "medium",
                          "evidence": ["src-1", "src-2"], "facet": "card", "cards": ["Lightning Bolt"]},
                         {"id": "fnd-2", "claim": "Players like Bolt.", "class": "community_opinion", "confidence": "low",
                          "evidence": ["src-3"], "facet": "card", "cards": ["Lightning Bolt"]},
                         {"id": "fnd-3", "claim": "Old take.", "class": "model_assessment", "confidence": "low", "evidence": ["src-3"],
                          "status": "superseded", "superseded_by": "fnd-1"},
                         {"id": "fnd-4", "claim": "Old but cited.", "class": "model_assessment", "confidence": "low", "evidence": ["src-3"],
                          "status": "superseded"}]}


class Findings(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        put(os.path.join(self.d, "research.json"), RESEARCH)
        put(os.path.join(self.d, "brew.json"), {"version": 2, "deck": [{"name": "Lightning Bolt", "qty": 1, "role": "removal", "set": "sld",
                                                                         "collector_number": "IFIYW-2", "evidence": ["fnd-4"]}],
                                                 "recommendations": [{"id": "rec-1", "add": "Galvanic Discharge", "cut": "Lightning Bolt", "status": "proposed"}]})
        put(os.path.join(self.d, "DECISIONS.md"), "- D-1 2026-11-16 Kept Lightning Bolt for now.\n")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_summary_counts_creators_not_videos_and_skips_superseded(self):
        lines = co.research_summary(RESEARCH)
        self.assertEqual(lines, ["card · community_opinion: 2 finding(s) from 2 creator(s) (low 1, medium 1) | fnd-1, fnd-2"])

    def test_summary_counts_independent_roots(self):
        r = {"sources": RESEARCH["sources"] + [{"id": "src-4", "author": "Repost Blog", "url": "https://blog.example/x", "derived_from": ["src-3"]},
                                               {"id": "src-5", "title": "pasted list", "origin": "pasted", "authorship": "machine_generated", "generator": "a deck generator"}],
             "findings": [{"id": "fnd-5", "claim": "Bolt is in most lists.", "class": "popularity_metric", "confidence": "low",
                           "evidence": ["src-3", "src-4", "src-5"], "facet": "card"}]}
        self.assertEqual(co.research_summary(r), ["card · popularity_metric: 1 finding(s) from 1 creator(s) + 1 generated (low 1) | fnd-5"])

    def test_card_report_finds_every_place(self):
        rows = "\n".join(co.card_report(self.d, "Lightning Bolt"))
        for frag in ("deck     brew.json v2: 1 Lightning Bolt (SLD IFIYW-2)", "rec      brew.json rec-1 [proposed]", "finding  fnd-1", "decision D-1"):
            self.assertIn(frag, rows)

    def test_archive_keeps_cited_findings_and_ids_stay_known(self):
        self.assertEqual(co.archive_findings(self.d), ["fnd-3"])
        left = [f["id"] for f in json.load(open(os.path.join(self.d, "research.json"), encoding="utf-8"))["findings"]]
        self.assertEqual(left, ["fnd-1", "fnd-2", "fnd-4"])  # fnd-4 is cited by the deck
        self.assertEqual(co.archived_ids(self.d), {"fnd-3"})
        self.assertEqual(co.archive_findings(self.d), [])


class Hooks(unittest.TestCase):
    def test_unwatched_write_is_ignored_and_session_line_names_the_project(self):
        self.assertEqual(hook.post_write({"tool_input": {"file_path": "C:/somewhere/notes.txt"}}), 0)
        d = tempfile.mkdtemp()
        try:
            put(os.path.join(d, "PROJECT.md"), "# p\n")
            put(os.path.join(d, "STATE.md"), "# State\n- main v3: audit pass\n")
            put(os.path.join(d, "brew.json"), "{}")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                hook.session_start({"cwd": d})
            self.assertIn("main v3: audit pass; builds: brew.json", out.getvalue())
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(hook.subagent_stop({"cwd": d, "agent_type": "edh-companion:researcher"}), 0)
            self.assertEqual(out.getvalue(), "")  # not the auditor: never blocks
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_hooks_json_points_at_hook_py(self):
        h = json.load(open(os.path.join(ROOT, "plugins", "edh-companion", "hooks", "hooks.json"), encoding="utf-8"))
        cmds = [x["command"] for ev in h["hooks"].values() for m in ev for x in m["hooks"]]
        self.assertEqual(len(cmds), 3)
        self.assertTrue(all("${CLAUDE_PLUGIN_ROOT}/scripts/hook.py" in c for c in cmds))


class Budgets(unittest.TestCase):
    def test_twenty_percent_slack(self):
        runs = [{"case": "a", "cost_usd": 0.12, "turns": 5}, {"case": "a", "cost_usd": 0.13, "turns": 5}, {"case": "b", "cost_usd": 0.3, "turns": 3}]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(stats.over_budget(runs, {"a": {"cost_usd": 0.105}, "b": {"turns": 3}}), 0)  # 0.125 <= 0.126
            self.assertEqual(stats.over_budget(runs, {"a": {"cost_usd": 0.1}}), 1)


if __name__ == "__main__":
    unittest.main()
