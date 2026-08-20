"""
server.py
---------
Cricket Analyst MCP Server

Exposes six tools over the Model Context Protocol so any MCP-aware client
(Claude Desktop, Claude Code, a custom agent, etc.) can query cricket
statistics and news, and let the LLM do the analysis on top.

    get_player_stats(player_name, format="all")
    get_all_players()
    get_team_stats(team_name, format="all")
    get_match_results(team1=None, team2=None, limit=5)
    get_player_comparison(player1, player2, format="ODI")
    get_recent_matches(limit=10)
    search_cricket_news(query, limit=5)

Run directly for local stdio use (e.g. from Claude Desktop config):
    python server.py

Requires: pip install "mcp[cli]" requests

Note on SDK versions: the official Python MCP SDK's high-level server class
was named `FastMCP` (in `mcp.server.fastmcp`) for a long time and is still
what most tutorials/configs reference. Newer SDK releases renamed it to
`MCPServer` (in `mcp.server.mcpserver`) with the same decorator-based API.
The import below tries the old path first and falls back to the new one so
this file works either way.
"""

from typing import Optional

try:
    from mcp.server.fastmcp import FastMCP as _MCPServerClass
except ImportError:  # newer SDK releases renamed FastMCP -> MCPServer
    from mcp.server.mcpserver import MCPServer as _MCPServerClass

from data_provider import get_provider

mcp = _MCPServerClass("cricket-analyst")
provider = get_provider()


@mcp.tool()
def get_player_stats(player_name: str, format: str = "all") -> dict:
    """
    Get career statistics for a cricket player.

    Args:
        player_name: Full or partial player name, e.g. "Virat Kohli".
        format: "Test", "ODI", "T20I", or "all" (default) for every format.
    """
    return provider.get_player_stats(player_name, format)


@mcp.tool()
def get_all_players() -> list:
    """
    Get full career statistics (all formats) for every player in the dataset.
    Useful for browsing or dumping the entire player roster at once.
    """
    return provider.get_all_players()


@mcp.tool()
def get_team_stats(team_name: str, format: str = "all") -> dict:
    """
    Get a national team's current rankings, recent form, and key players.

    Args:
        team_name: Team/country name, e.g. "India".
        format: "Test", "ODI", "T20I", or "all" (default).
    """
    return provider.get_team_stats(team_name, format)


@mcp.tool()
def get_match_results(team1: Optional[str] = None,
                       team2: Optional[str] = None,
                       limit: int = 5) -> list:
    """
    Get recent match results, optionally filtered by one or two teams.

    Args:
        team1: Optional team name to filter by.
        team2: Optional second team name (use with team1 for head-to-head).
        limit: Max number of results to return (default 5).
    """
    return provider.get_match_results(team1, team2, limit)


@mcp.tool()
def get_player_comparison(player1: str, player2: str, format: str = "ODI") -> dict:
    """
    Compare two players' stats side by side in a given format.

    Args:
        player1: First player's name, e.g. "Virat Kohli".
        player2: Second player's name, e.g. "Rohit Sharma".
        format: "Test", "ODI", or "T20I" (default "ODI").
    """
    p1 = provider.get_player_stats(player1, format)
    p2 = provider.get_player_stats(player2, format)
    return {
        "format": format,
        "player_1": p1,
        "player_2": p2,
    }


@mcp.tool()
def get_recent_matches(limit: int = 10) -> list:
    """
    Get the most recent completed matches across all teams and formats.

    Args:
        limit: Max number of matches to return (default 10).
    """
    return provider.get_recent_matches(limit)


@mcp.tool()
def search_cricket_news(query: str, limit: int = 5) -> list:
    """
    Search recent cricket news headlines and summaries.

    Args:
        query: Search term, e.g. a player name, team, or event.
        limit: Max number of articles to return (default 5).
    """
    return provider.search_cricket_news(query, limit)


if __name__ == "__main__":
    mcp.run(transport="stdio")
