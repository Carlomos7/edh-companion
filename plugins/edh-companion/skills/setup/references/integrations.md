# Optional integrations

Suggest these only for a missing capability that would clearly help, one line each. Never install anything yourself; the player runs the command.

| Capability | Option | Install |
|---|---|---|
| MTG data (cards, EDHREC, combos, decklists) | j4th MTG MCP, or its hosted claude.ai connector | `claude mcp add mtg --scope user -- uvx --with "selectolax<1.0" mtg-mcp-server` |
| Web search | Parallel | `claude mcp add parallel-search --scope user --transport http https://search.parallel.ai/mcp` |
| Semantic search | Exa | `claude mcp add exa --scope user --transport http https://mcp.exa.ai/mcp` |
| Video transcripts | jkawamoto YouTube transcripts | `claude mcp add youtube-transcript --scope user -- uvx --from git+https://github.com/jkawamoto/mcp-youtube-transcript mcp-youtube-transcript` |
| Scripts (deck checker, pages) | uv | `winget install astral-sh.uv` (Windows) or `brew install uv` (macOS) |

Built-in web search also works without any of these. `selectolax<1.0` is pinned because selectolax 1.0 breaks mtg-mcp-server 3.0.0 on startup.
