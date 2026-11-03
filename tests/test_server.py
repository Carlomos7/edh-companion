"""MCP server smoke test over real stdio, on the synthetic index from test_mtgdb. Needs the mcp package
(the README test command adds it); skipped without it."""
import json, os, sys, unittest

import test_mtgdb as base

SERVER = os.path.join(os.path.dirname(base.SCRIPT), "server.py")
DECK = "1 Darth Vader\n1 Sol Ring\n1 Demonic Tutor\n97 Swamp\n"
TOOLS = {"mtg_card", "mtg_resolve_names", "mtg_deck_check", "mtg_deck_swap", "mtg_deck_profile", "mtg_simulate",
         "mtg_rules", "mtg_data_status", "mtg_data_sync", "mtg_price_plan", "mtg_cheaper_alternatives", "mtg_export"}


class ServerTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import mcp  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("mcp not installed")
        base.MtgdbTest.setUpClass()
        cls.env = dict(base.MtgdbTest.env, MTGDB=base.MtgdbTest.db)

    async def call(self, session, tool, **args):
        res = await session.call_tool(tool, args)
        text = res.content[0].text if res.content else ""
        return res.is_error, (json.loads(text) if not res.is_error else text)

    async def test_tools(self):
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client
        params = StdioServerParameters(command=sys.executable, args=[SERVER], env=self.env)
        with open(os.devnull, "w") as devnull:
            async with stdio_client(params, errlog=devnull) as (r, w), ClientSession(r, w) as s:
                await s.initialize()
                names = {t.name for t in (await s.list_tools()).tools}
                self.assertEqual(names, TOOLS)

                err, card = await self.call(s, "mtg_card", name="sol ring")
                self.assertFalse(err)
                self.assertEqual(card["name"], "Sol Ring")
                self.assertNotIn("printings", card)  # concise by default
                err, msg = await self.call(s, "mtg_card", name="Sol Rng")
                self.assertTrue(err)
                self.assertIn("Sol Ring", msg)  # the error names the fix

                err, check = await self.call(s, "mtg_deck_check", deck=DECK, bracket=3)
                self.assertFalse(err)
                self.assertTrue(check["pass"], check["errors"])
                self.assertEqual(check["game_changers"], ["Demonic Tutor"])
                err, check = await self.call(s, "mtg_deck_check", deck=DECK.replace("97 Swamp", "98 Swamp"), bracket=3)
                self.assertFalse(check["pass"])

                err, swap = await self.call(s, "mtg_deck_swap", deck=DECK, bracket=1, swaps=["-Demonic Tutor +Swamp"])
                self.assertFalse(err)

                err, names = await self.call(s, "mtg_resolve_names", names=["Rhystic Studdy"])
                self.assertEqual(names["names"][0]["name"], "Rhystic Study")

                err, plan = await self.call(s, "mtg_price_plan", deck=DECK, style="budget")
                self.assertFalse(err)
                self.assertLess(plan["totals_usd"]["budget"], plan["totals_usd"]["bling"])
                self.assertIn("(C21) 263", plan["moxfield_export"])

                err, ex = await self.call(s, "mtg_export", deck=DECK, format="arena", printings="bling")
                self.assertFalse(err)
                self.assertTrue(ex["text"].startswith("Commander\n1 Darth Vader"))
                self.assertNotIn("(", ex["text"])  # arena: names only
                err, ex = await self.call(s, "mtg_export", deck=DECK, format="archidekt", printings="bling")
                self.assertIn("1x Darth Vader (SWT) 12 [Commander{top}]", ex["text"])
                self.assertIn("(SLD) 999", ex["text"])  # bling picks the Secret Lair Sol Ring
                err, msg = await self.call(s, "mtg_export", deck="1 Darth Vadr\n99 Swamp")
                self.assertTrue(err)  # unresolved names are refused, not silently dropped

                err, ex = await self.call(s, "mtg_export", deck="1 Sol Ring (SLD) 999 *F*\n1 Darth Vader", commanders=1)
                self.assertIn("1 Sol Ring (SLD) 999 *F*", ex["text"])  # as-listed keeps the player's copy and finish
                err, msg = await self.call(s, "mtg_resolve_names", names=[])
                self.assertTrue(err)  # never falls back to reading the protocol stream

                err, msg = await self.call(s, "mtg_rules", query="trample")
                self.assertTrue(err)  # no rules synced in the fixture: clear error, not a crash
                self.assertIn("sync", msg)

                err, status = await self.call(s, "mtg_data_status")
                self.assertFalse(err)
                self.assertIn("rules", status["refresh"])


if __name__ == "__main__":
    unittest.main()
