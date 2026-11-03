#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=2.3,<3", "ijson", "pillow"]
# ///
"""mtgdb MCP server: card facts, deck checks, combos, rules and data freshness from the local index.

Every tool runs the same code as the `mtgdb.py` CLI (one source of truth). Started by the plugin's .mcp.json over stdio.
"""
import contextlib, io, json, os, sys, tempfile, threading
from typing import Literal

import anyio
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mtgdb  # noqa: E402

_lock = threading.Lock()  # mtgdb keeps module state; one command at a time
READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
Format = Literal["concise", "detailed"]

mcp = MCPServer(
    "mtgdb",
    instructions=(
        "Local Magic: The Gathering data: card facts, legality, printings, prices, Game Changers, role tags, rulings, "
        "Commander Spellbook combos and the Comprehensive Rules. Use these tools for any card fact instead of memory. "
        "Call mtg_data_status at the start of deck work; if anything is stale, offer the user mtg_data_sync."),
)


def run(*argv):
    """Run one mtgdb CLI command in-process. Returns (parsed JSON or text, exit code)."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with _lock, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            mtgdb.main([str(a) for a in argv])
        except SystemExit as e:
            if isinstance(e.code, str):
                err.write(e.code)
                code = 1
            else:
                code = e.code or 0
    text = out.getvalue().strip()
    if not text:
        raise ToolError((err.getvalue().strip() or f"mtgdb {argv[0]} returned nothing")[-1500:])
    try:
        return json.loads(text), code
    except json.JSONDecodeError:
        return text, code


@contextlib.contextmanager
def deck_file(deck):
    """Accept a decklist as text or as a path to a .txt file."""
    if "\n" not in deck and deck.strip().lower().endswith(".txt"):
        path = os.path.abspath(os.path.expanduser(deck.strip()))
        if not os.path.isfile(path):
            raise ToolError(f"deck file not found: {path}. Pass the decklist text instead.")
        yield path
        return
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "deck.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(deck)
        yield path


def deck_args(bracket, commanders, budget):
    return ["--bracket", bracket, "--commanders", commanders] + (["--budget", budget] if budget is not None else [])


@mcp.tool(annotations=READ)
def mtg_card(name: str, response_format: Format = "concise") -> dict:
    """One card's facts from the local Scryfall index: oracle text, color identity, mana value, Commander legality,
    Game Changer flag, role tags and official rulings. detailed adds every legal printing with prices.
    Unknown names return suggestions; use mtg_resolve_names for messy input."""
    card, code = run("card", name)
    if code:
        raise ToolError(f"'{name}' is not a card. Did you mean: {[s['name'] for s in card.get('suggestions', [])]}?")
    if response_format == "concise":
        keep = ("name", "mana_cost", "cmc", "type_line", "oracle_text", "color_identity", "commander_legal", "gc", "role_tags")
        res = {k: card[k] for k in keep if k in card}
        res["rulings"] = len(card.get("rulings", []))
        return res
    printings, _ = run("printings", name)
    return {**card, "printings": printings}


@mcp.tool(annotations=READ)
def mtg_resolve_names(names: list[str]) -> dict:
    """Map messy card names (typos, transcripts, partial names) to real card names. Each result is exact, fuzzy,
    ambiguous (pick from candidates) or none. Run this before putting any name from a video or paste into a deck."""
    res, _ = run("normalize", *names)
    return {"names": res, "unresolved": [r["input"] for r in res if r["match"] in ("ambiguous", "none")]}


@mcp.tool(annotations=READ)
def mtg_deck_check(deck: str, bracket: int, commanders: int = 1, budget: float | None = None,
                   response_format: Format = "concise") -> dict:
    """Full check of a Commander deck: count, singleton, color identity, legality, playable printings, Game Changers,
    bracket rules (extra turns, mass land denial), budget, curve, color sources vs pips, role counts and every
    Commander Spellbook combo in the list. `deck` is the decklist text (Moxfield export is fine) or a .txt path.
    A Commander section in the list overrides `commanders`. concise returns problems and totals; detailed adds per-card data."""
    with deck_file(deck) as path:
        val, _ = run("validate", path, *deck_args(bracket, commanders, budget))
        stats, _ = run("stats", path, "--commanders", commanders)
        combos, _ = run("combos", path, "--commanders", commanders)
    roles = {k: v["count"] if isinstance(v, dict) else v for k, v in (stats.get("roles") or {}).items()}
    res = {"pass": val["pass"], "errors": val["errors"], "warnings": val["warnings"], "bracket": bracket,
           "game_changers": val["game_changers"], "extra_turn_cards": val["extra_turn_cards"],
           "price_usd": val["price_usd"], "prices_as_of": val["prices_as_of"],
           "lands": stats.get("lands"), "avg_mv_nonland": stats.get("avg_mv_nonland"), "curve": stats.get("curve"),
           "pips": stats.get("pips"), "sources": stats.get("sources"), "roles": roles, "roles_source": stats.get("roles_source"),
           "two_card_combos": [{"cards": c["cards"], "produces": c["produces"][:3], "url": c["url"]} for c in combos["two_card"]],
           "combo_count": combos["count"], "combos_source": combos["source"]}
    if bracket <= 3 and combos["two_card"]:
        res["warnings"].append(f"{len(combos['two_card'])} two-card combo(s): brackets 1 to 3 should not have these")
    if response_format == "detailed":
        res.update({"validate": val, "stats": stats, "combos": combos["included"]})
    return res


@mcp.tool(annotations=READ)
def mtg_deck_swap(deck: str, bracket: int, swaps: list[str], commanders: int = 1, budget: float | None = None) -> dict:
    """Test swaps on a copy of a deck and re-run the hard checks. Each swap is "-Card Out +Card In". Returns whether the
    deck still passes, new problems and the cost change. Never suggest a swap that fails here."""
    with deck_file(deck) as path:
        res, _ = run("swaptest", path, *deck_args(bracket, commanders, budget), *[x for s in swaps for x in ("--swap", s)])
    return res


@mcp.tool(annotations=READ)
def mtg_deck_profile(deck: str, commanders: int = 1) -> dict:
    """Snapshot of an existing deck before optimizing: commanders, color identity, legality, bracket signals
    (Game Changers, combos, extra turns, tutors), cost, and which sets its printings come from (a theme hint)."""
    with deck_file(deck) as path:
        res, _ = run("profile", path, "--commanders", commanders)
    return res


@mcp.tool(annotations=READ)
def mtg_simulate(deck: str, commanders: int = 1, on_the_draw: bool = False, turns: int = 8) -> dict:
    """Goldfish simulation: percent of games the commander can be cast by each turn, and how often the opening hand
    has 2 to 5 lands. Use it to judge ramp and land count, and to compare a deck before and after changes."""
    with deck_file(deck) as path:
        res, _ = run("simulate", path, "--commanders", commanders, "--turns", turns, *(["--draw"] if on_the_draw else []))
    return res


@mcp.tool(annotations=READ)
def mtg_rules(query: str, limit: int = 10) -> dict:
    """Comprehensive Rules lookup with the effective date. `query` is a rule number (702.19, 903.8) for that rule and
    its subrules, or a keyword or phrase (trample, commander tax) for the glossary entry and every rule that mentions it."""
    res, code = run("rules", query, "--limit", limit)
    if code and not res.get("rules"):
        raise ToolError(res.get("error") or f"no rule matches '{query}'. Try a shorter keyword or a rule number.")
    return res


@mcp.tool(annotations=READ)
def mtg_data_status(check_remote: bool = False) -> dict:
    """Date and staleness of every data source (cards with bans and Game Changers, role tags, rulings, combos,
    Comprehensive Rules, prices). check_remote also asks Scryfall and Wizards whether newer versions exist.
    `refresh` lists sources worth syncing; offer mtg_data_sync for them."""
    if not os.path.exists(mtgdb.DB_DEFAULT):
        return {"sources": {}, "refresh": ["cards", "tags", "rulings", "combos", "rules"],
                "hint": "No card index yet. Run mtg_data_sync (about 1 minute, about 120 MB download) before anything else."}
    res, _ = run("status", *(["--remote"] if check_remote else []))
    return res


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=True, open_world_hint=True))
async def mtg_data_sync(ctx: Context, sources: list[Literal["cards", "tags", "rulings", "combos", "rules", "prices"]] | None = None) -> dict:
    """Download the latest data from the official sources: cards (Scryfall: legality, bans, Game Changers, prices),
    tags (Scryfall Tagger), rulings, combos (Commander Spellbook), rules (Wizards). Default: all but prices.
    About 40 seconds for everything; prices add about 20 seconds. Only run when the user agrees."""
    todo = sources or ["cards", "tags", "rulings", "combos", "rules"]
    synced, failed = {}, {}
    for i, src in enumerate(todo):
        await ctx.report_progress(i, len(todo), f"syncing {src}")
        res, _ = await anyio.to_thread.run_sync(run, "sync", src)
        synced.update(res.get("synced", {}))
        failed.update(res.get("failed", {}))
    await ctx.report_progress(len(todo), len(todo), "done")
    return {"synced": synced, "failed": failed}


def record_path():
    """mtg-pages and other plugins find mtgdb.py through this file, since installed plugin paths change per version."""
    try:
        os.makedirs(mtgdb.CACHE, exist_ok=True)
        with open(os.path.join(mtgdb.CACHE, "mtgdb-path.txt"), "w", encoding="utf-8") as f:
            f.write(os.path.abspath(mtgdb.__file__))
    except OSError:
        pass


if __name__ == "__main__":
    record_path()
    mcp.run("stdio")
