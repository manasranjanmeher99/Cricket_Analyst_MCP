"""
data_provider.py
-----------------
Pluggable cricket data layer.

Two providers are included:

1. MockProvider      - realistic sample data, works out of the box, no API key.
                        Good for development, demos, and testing the MCP tools.

2. CricAPIProvider    - a thin adapter around a real cricket data API
                        (cricketdata.org's "CricAPI", https://cricketdata.org).
                        Wire in your own key via the CRICAPI_KEY env var.
                        Swap in a different provider (RapidAPI Cricbuzz, ESPN
                        Cricinfo scraping, SportMonks, etc.) by implementing
                        the same CricketDataProvider interface.

The MCP server (server.py) only talks to the CricketDataProvider interface,
so you can switch providers without touching the tool definitions.
"""

from __future__ import annotations

import os
import abc
from typing import Optional
import requests


class CricketDataProvider(abc.ABC):
    """Interface every data provider must implement."""

    @abc.abstractmethod
    def get_player_stats(self, player_name: str, format: str = "all") -> dict:
        ...

    @abc.abstractmethod
    def get_all_players(self) -> list:
        ...

    @abc.abstractmethod
    def get_team_stats(self, team_name: str, format: str = "all") -> dict:
        ...

    @abc.abstractmethod
    def get_match_results(self, team1: Optional[str] = None,
                           team2: Optional[str] = None, limit: int = 5) -> list:
        ...

    @abc.abstractmethod
    def get_recent_matches(self, limit: int = 10) -> list:
        ...

    @abc.abstractmethod
    def search_cricket_news(self, query: str, limit: int = 5) -> list:
        ...


# ---------------------------------------------------------------------------
# Mock provider — realistic sample data, no external dependency
# ---------------------------------------------------------------------------

_MOCK_PLAYERS = {
    "virat kohli": {
        "full_name": "Virat Kohli",
        "country": "India",
        "role": "Batsman",
        "stats": {
            "Test": {"matches": 113, "runs": 8848, "average": 46.85, "hundreds": 29, "fifties": 30, "strike_rate": 55.6},
            "ODI":  {"matches": 292, "runs": 13906, "average": 57.88, "hundreds": 50, "fifties": 72, "strike_rate": 93.6},
            "T20I": {"matches": 125, "runs": 4188, "average": 48.69, "hundreds": 1,  "fifties": 38, "strike_rate": 137.0},
        },
    },
    "rohit sharma": {
        "full_name": "Rohit Sharma",
        "country": "India",
        "role": "Batsman",
        "stats": {
            "Test": {"matches": 67,  "runs": 4301, "average": 40.57, "hundreds": 12, "fifties": 18, "strike_rate": 57.3},
            "ODI":  {"matches": 271, "runs": 10866, "average": 48.96, "hundreds": 31, "fifties": 57, "strike_rate": 91.2},
            "T20I": {"matches": 159, "runs": 4231, "average": 32.05, "hundreds": 5,  "fifties": 29, "strike_rate": 140.9},
        },
    },
    "babar azam": {
        "full_name": "Babar Azam",
        "country": "Pakistan",
        "role": "Batsman",
        "stats": {
            "Test": {"matches": 54,  "runs": 4099, "average": 45.55, "hundreds": 10, "fifties": 22, "strike_rate": 55.0},
            "ODI":  {"matches": 118, "runs": 5729, "average": 56.72, "hundreds": 19, "fifties": 30, "strike_rate": 88.7},
            "T20I": {"matches": 122, "runs": 4223, "average": 41.40, "hundreds": 3,  "fifties": 34, "strike_rate": 129.4},
        },
    },
    "steve smith": {
        "full_name": "Steve Smith",
        "country": "Australia",
        "role": "Batsman",
        "stats": {
            "Test": {"matches": 109, "runs": 9685, "average": 56.97, "hundreds": 32, "fifties": 39, "strike_rate": 54.9},
            "ODI":  {"matches": 155, "runs": 5800, "average": 43.28, "hundreds": 12, "fifties": 33, "strike_rate": 86.6},
            "T20I": {"matches": 67,  "runs": 1055, "average": 25.73, "hundreds": 0,  "fifties": 2,  "strike_rate": 124.6},
        },
    },
    "jasprit bumrah": {
        "full_name": "Jasprit Bumrah",
        "country": "India",
        "role": "Bowler",
        "stats": {
            "Test": {"matches": 43,  "wickets": 187, "average": 20.03, "economy": 2.71, "best": "6/27"},
            "ODI":  {"matches": 89,  "wickets": 149, "average": 24.44, "economy": 4.63, "best": "6/19"},
            "T20I": {"matches": 70,  "wickets": 89,  "average": 19.03, "economy": 6.62, "best": "3/7"},
        },
    },
}

_MOCK_TEAMS = {
    "india": {
        "team": "India", "ranking": {"Test": 2, "ODI": 1, "T20I": 3},
        "recent_form": ["W", "W", "L", "W", "W"],
        "key_players": ["Virat Kohli", "Rohit Sharma", "Jasprit Bumrah"],
    },
    "australia": {
        "team": "Australia", "ranking": {"Test": 1, "ODI": 3, "T20I": 4},
        "recent_form": ["W", "L", "W", "W", "L"],
        "key_players": ["Steve Smith", "Pat Cummins", "Travis Head"],
    },
    "pakistan": {
        "team": "Pakistan", "ranking": {"Test": 6, "ODI": 5, "T20I": 2},
        "recent_form": ["L", "W", "W", "L", "W"],
        "key_players": ["Babar Azam", "Shaheen Afridi", "Mohammad Rizwan"],
    },
    "england": {
        "team": "England", "ranking": {"Test": 3, "ODI": 4, "T20I": 1},
        "recent_form": ["W", "W", "W", "L", "W"],
        "key_players": ["Joe Root", "Ben Stokes", "Jofra Archer"],
    },
}

_MOCK_RESULTS = [
    {"date": "2026-08-10", "team1": "India", "team2": "Australia", "format": "ODI",
     "winner": "India", "margin": "6 wickets", "venue": "Wankhede Stadium, Mumbai"},
    {"date": "2026-08-05", "team1": "Pakistan", "team2": "England", "format": "T20I",
     "winner": "England", "margin": "14 runs", "venue": "Gaddafi Stadium, Lahore"},
    {"date": "2026-07-29", "team1": "Australia", "team2": "England", "format": "Test",
     "winner": "Australia", "margin": "innings and 42 runs", "venue": "MCG, Melbourne"},
    {"date": "2026-07-20", "team1": "India", "team2": "Pakistan", "format": "ODI",
     "winner": "India", "margin": "34 runs", "venue": "Eden Gardens, Kolkata"},
    {"date": "2026-07-12", "team1": "England", "team2": "India", "format": "T20I",
     "winner": "India", "margin": "3 wickets", "venue": "Lord's, London"},
]

_MOCK_NEWS = [
    {"title": "Kohli closes in on another ODI milestone ahead of series decider",
     "source": "ESPN Cricinfo", "date": "2026-08-16",
     "summary": "A look at the form Kohli is carrying into the final ODI and what the milestone would mean."},
    {"title": "Bumrah ruled fit, set to lead India's pace attack in the series decider",
     "source": "Cricbuzz", "date": "2026-08-15",
     "summary": "Fitness update on India's premier fast bowler ahead of the series finale."},
    {"title": "Babar Azam under pressure after string of low scores",
     "source": "The Cricket Monthly", "date": "2026-08-14",
     "summary": "Analysis of Babar Azam's recent dip in form and what it means for Pakistan's batting order."},
    {"title": "Rohit Sharma reflects on captaincy and the road to the next World Cup",
     "source": "ESPN Cricinfo", "date": "2026-08-12",
     "summary": "Rohit Sharma discusses leadership plans and squad depth in a wide-ranging interview."},
]


class MockProvider(CricketDataProvider):
    def get_player_stats(self, player_name: str, format: str = "all") -> dict:
        key = player_name.strip().lower()
        player = _MOCK_PLAYERS.get(key)
        if not player:
            return {"error": f"No data found for player '{player_name}'. "
                              f"Try: {', '.join(p['full_name'] for p in _MOCK_PLAYERS.values())}"}
        if format.lower() == "all":
            return player
        fmt_key = format.upper() if format.upper() != "T20" else "T20I"
        stats = player["stats"].get(fmt_key)
        if not stats:
            return {"error": f"No '{format}' stats for {player['full_name']}"}
        return {"full_name": player["full_name"], "country": player["country"],
                "role": player["role"], "format": fmt_key, "stats": stats}

    def get_all_players(self) -> list:
        """Return full career stats (all formats) for every player in the dataset."""
        return list(_MOCK_PLAYERS.values())

    def get_team_stats(self, team_name: str, format: str = "all") -> dict:
        key = team_name.strip().lower()
        team = _MOCK_TEAMS.get(key)
        if not team:
            return {"error": f"No data found for team '{team_name}'. "
                              f"Try: {', '.join(t['team'] for t in _MOCK_TEAMS.values())}"}
        if format.lower() == "all":
            return team
        fmt_key = format.upper() if format.upper() != "T20" else "T20I"
        ranking = team["ranking"].get(fmt_key)
        if ranking is None:
            return {"error": f"No '{format}' ranking for {team['team']}"}
        return {
            "team": team["team"],
            "format": fmt_key,
            "ranking": ranking,
            "recent_form": team["recent_form"],
            "key_players": team["key_players"],
        }

    def get_match_results(self, team1: Optional[str] = None,
                           team2: Optional[str] = None, limit: int = 5) -> list:
        results = _MOCK_RESULTS
        if team1:
            results = [r for r in results if team1.lower() in
                       (r["team1"].lower(), r["team2"].lower())]
        if team2:
            results = [r for r in results if team2.lower() in
                       (r["team1"].lower(), r["team2"].lower())]
        return results[:limit]

    def get_recent_matches(self, limit: int = 10) -> list:
        return _MOCK_RESULTS[:limit]

    def search_cricket_news(self, query: str, limit: int = 5) -> list:
        q = query.strip().lower()
        matches = [n for n in _MOCK_NEWS if q in n["title"].lower() or q in n["summary"].lower()]
        if not matches:
            matches = _MOCK_NEWS
        return matches[:limit]


# ---------------------------------------------------------------------------
# Live provider — CricketData.org (formerly CricAPI), https://cricketdata.org
#
# Free tier: 100 requests/day, no credit card required. Sign up for a key at
# https://cricketdata.org/signup.aspx and set CRICAPI_KEY in your .env file.
#
# Coverage on the free tier:
#   - Player search + full career stats: LIVE, real data for any real player.
#   - Recent / current matches:          LIVE, real data.
#   - Team rankings and cricket news:    the free tier has no rankings or
#                                         news endpoint, so these fall back to
#                                         the same sample data as MockProvider
#                                         (clearly labeled below). Swap in a
#                                         provider like SportMonks or
#                                         EntitySport if you need those live.
# ---------------------------------------------------------------------------

_CRICAPI_BASE = "https://api.cricapi.com/v1"

# Curated "watchlist" of well-known current players used by get_all_players(),
# since the free tier has no single "every player in the world, with full
# stats" endpoint (that would also blow through a 100 req/day quota almost
# immediately). get_player_stats() below works for ANY player by name,
# regardless of whether they're in this list.
_DEFAULT_PLAYER_WATCHLIST = [
    "Virat Kohli", "Rohit Sharma", "Shubman Gill", "Jasprit Bumrah",
    "Babar Azam", "Steve Smith", "Joe Root", "Ben Stokes",
    "Pat Cummins", "Kane Williamson",
]

# Maps CricketData.org's matchtype values to the Test/ODI/T20I keys used
# throughout this app (and by MockProvider), so both providers look the same
# to server.py and streamlit_app.py.
_FORMAT_MAP = {"test": "Test", "odi": "ODI", "t20i": "T20I", "t20": "T20I"}


class CricAPIProvider(CricketDataProvider):
    """Adapter around CricketData.org's free Cricket Data API."""

    def __init__(self, api_key: str, timeout: float = 10.0):
        self.api_key = api_key
        self.timeout = timeout
        self._search_cache: dict[str, Optional[dict]] = {}
        self._stats_cache: dict[str, dict] = {}
        # Team rankings/news have no free live endpoint - reuse mock data for those.
        self._fallback = MockProvider()

    # -- low-level HTTP helpers -------------------------------------------------

    def _get(self, path: str, **params) -> dict:
        params["apikey"] = self.api_key
        try:
            resp = requests.get(f"{_CRICAPI_BASE}/{path}", params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            # Network-level failure (DNS, timeout, connection refused, etc.)
            raise RuntimeError(f"could not reach CricketData.org ({exc.__class__.__name__}: {exc})") from exc

        if resp.status_code == 401 or resp.status_code == 403:
            raise RuntimeError(
                f"CricketData.org rejected the API key (HTTP {resp.status_code}). "
                f"Check CRICAPI_KEY in your .env file."
            )
        if resp.status_code == 429:
            raise RuntimeError(
                "CricketData.org rate limit reached (HTTP 429). The free tier allows "
                "100 requests/day - try again later, or upgrade your plan."
            )
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(f"CricketData.org returned HTTP {resp.status_code}: {exc}") from exc

        payload = resp.json()
        if payload.get("status") not in (None, "success"):
            raise RuntimeError(payload.get("message") or f"CricketData.org error: {payload.get('status')}")
        return payload

    def _find_player(self, player_name: str) -> Optional[dict]:
        """Search for a player by (partial, case-insensitive) name. Cached per name."""
        cache_key = player_name.strip().lower()
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]

        payload = self._get("players", search=player_name.strip())
        candidates = payload.get("data") or []

        match = None
        if candidates:
            # Prefer an exact (case-insensitive) name match; otherwise take the
            # top result, since the API already ranks by relevance.
            for c in candidates:
                if c.get("name", "").strip().lower() == cache_key:
                    match = c
                    break
            else:
                match = candidates[0]

        self._search_cache[cache_key] = match
        return match

    # -- stats parsing ------------------------------------------------------

    # Canonical stat name -> every field-name variant CricketData.org (or a
    # similar provider) might use for it. "matches" and "average" in
    # particular are commonly abbreviated ("mat", "avg", "ave"), so a single
    # guessed name silently drops the stat if the API uses a different one.
    _BATTING_ALIASES = {
        "matches": {"matches", "mat", "m", "innings"},
        "runs": {"runs", "r"},
        "average": {"average", "avg", "ave"},
        "strike_rate": {"sr", "strike_rate", "strikerate"},
        "hundreds": {"100s", "hundreds", "100", "hundred"},
        "fifties": {"50s", "fifties", "50", "fifty"},
    }
    _BOWLING_ALIASES = {
        "matches": {"matches", "mat", "m", "innings"},
        "wickets": {"wickets", "wkts", "wkt", "w"},
        "average": {"average", "avg", "ave"},
        "economy": {"econ", "economy", "eco", "er"},
        "best": {"bbi", "best", "bb", "bestbowling"},
    }

    @classmethod
    def _lookup(cls, alias_map: dict, stat: str) -> Optional[str]:
        normalized = stat.strip().lower().replace(" ", "").replace("_", "")
        for canonical, aliases in alias_map.items():
            if any(normalized == a.replace("_", "") for a in aliases):
                return canonical
        return None

    @classmethod
    def _parse_stats(cls, raw_stats: list) -> dict:
        """
        Turn CricketData.org's flat players_info "stats" list — records like
        {"fn": "batting", "matchtype": "test", "stat": "matches", "value": "113"}
        — into the same {"Test": {...}, "ODI": {...}, "T20I": {...}} shape
        MockProvider uses, so the rest of the app doesn't need to care which
        provider is active.
        """
        batting: dict = {}
        bowling: dict = {}
        for row in raw_stats or []:
            fmt = _FORMAT_MAP.get(str(row.get("matchtype", "")).lower())
            if not fmt:
                continue  # skip formats we don't track (e.g. first-class, list-a)
            fn = row.get("fn")
            stat = str(row.get("stat", ""))
            value = row.get("value")

            bucket = batting if fn == "batting" else bowling if fn == "bowling" else None
            if bucket is None:
                continue
            bucket.setdefault(fmt, {})

            alias_map = cls._BATTING_ALIASES if fn == "batting" else cls._BOWLING_ALIASES
            mapped_key = cls._lookup(alias_map, stat)
            if not mapped_key:
                continue
            try:
                value = float(value) if mapped_key != "best" else value
                if mapped_key in ("matches", "runs", "hundreds", "fifties", "wickets") and value is not None:
                    value = int(value)
            except (TypeError, ValueError):
                pass  # keep raw string (e.g. "6/27") if it isn't numeric
            bucket[fmt][mapped_key] = value

        # An all-rounder has entries in both; a specialist only in one. Prefer
        # whichever discipline actually has data for each format.
        merged: dict = {}
        for fmt in set(batting) | set(bowling):
            if fmt in bowling and (fmt not in batting or len(bowling[fmt]) >= len(batting[fmt])):
                merged[fmt] = bowling[fmt]
            else:
                merged[fmt] = batting[fmt]
        return merged

    def _player_card(self, player_id: str, name_hint: str = "") -> dict:
        if player_id in self._stats_cache:
            return self._stats_cache[player_id]

        payload = self._get("players_info", id=player_id)
        data = payload.get("data") or {}
        stats = self._parse_stats(data.get("stats"))

        card = {
            "full_name": data.get("name") or name_hint,
            "country": data.get("country", ""),
            "role": data.get("role", ""),
            "stats": stats,
        }
        self._stats_cache[player_id] = card
        return card

    # -- CricketDataProvider interface --------------------------------------

    def get_player_stats(self, player_name: str, format: str = "all") -> dict:
        try:
            found = self._find_player(player_name)
        except (requests.RequestException, RuntimeError) as exc:
            return {"error": f"Cricket API request failed: {exc}"}

        if not found:
            return {"error": f"No live data found for player '{player_name}'. "
                              f"Check the spelling, or try a more common form of the name."}

        try:
            card = self._player_card(found["id"], name_hint=found.get("name", player_name))
        except (requests.RequestException, RuntimeError) as exc:
            return {"error": f"Cricket API request failed: {exc}"}

        if not card["stats"]:
            return {"error": f"No Test/ODI/T20I stats available for {card['full_name']}."}

        if format.lower() == "all":
            return card

        fmt_key = _FORMAT_MAP.get(format.lower(), format.upper())
        stats = card["stats"].get(fmt_key)
        if not stats:
            return {"error": f"No '{format}' stats for {card['full_name']}"}
        return {"full_name": card["full_name"], "country": card["country"],
                "role": card["role"], "format": fmt_key, "stats": stats}

    def get_all_players(self) -> list:
        players = []
        for name in _DEFAULT_PLAYER_WATCHLIST:
            card = self.get_player_stats(name, format="all")
            if "error" not in card:
                players.append(card)
        return players

    def get_team_stats(self, team_name: str, format: str = "all") -> dict:
        # No free rankings endpoint on CricketData.org - sample data for now.
        return self._fallback.get_team_stats(team_name, format)

    def get_match_results(self, team1: Optional[str] = None,
                           team2: Optional[str] = None, limit: int = 5) -> list:
        matches = self.get_recent_matches(limit=max(limit, 20))
        if team1:
            matches = [m for m in matches if team1.lower() in
                       (m["team1"].lower(), m["team2"].lower())]
        if team2:
            matches = [m for m in matches if team2.lower() in
                       (m["team1"].lower(), m["team2"].lower())]
        return matches[:limit]

    def get_recent_matches(self, limit: int = 10) -> list:
        try:
            payload = self._get("currentMatches", offset=0)
        except (requests.RequestException, RuntimeError):
            return self._fallback.get_recent_matches(limit)

        results = []
        for m in (payload.get("data") or [])[:limit]:
            teams = m.get("teams") or []
            team1 = teams[0] if len(teams) > 0 else m.get("teamInfo", [{}])[0].get("name", "")
            team2 = teams[1] if len(teams) > 1 else ""
            status = m.get("status", "")
            winner = None
            margin = ""
            if " won by " in status:
                winner_part, margin = status.split(" won by ", 1)
                winner = winner_part.strip()
            results.append({
                "date": (m.get("date") or "")[:10],
                "team1": team1,
                "team2": team2,
                "format": m.get("matchType", "").upper(),
                "winner": winner or status or "Result pending",
                "margin": margin.strip(),
                "venue": m.get("venue", ""),
            })
        return results

    def search_cricket_news(self, query: str, limit: int = 5) -> list:
        # CricketData.org's free tier has no news endpoint - sample data for now.
        return self._fallback.search_cricket_news(query, limit)


def get_provider() -> CricketDataProvider:
    """
    Return the active cricket data provider.

    If CRICAPI_KEY is set (get a free key at https://cricketdata.org/signup.aspx),
    returns a CricAPIProvider backed by real, live player and match data.
    Otherwise falls back to MockProvider, which needs no API key at all.
    """
    api_key = os.environ.get("CRICAPI_KEY", "").strip()

    # If someone copies .env.example to .env without editing this line,
    # CRICAPI_KEY ends up literally set to this placeholder string. Treat
    # that the same as "unset" instead of sending it to the live API as a
    # real key (which would just fail with an auth error on every call).
    if api_key.lower() in ("", "your_cricketdata_org_api_key_here"):
        return MockProvider()
    return CricAPIProvider(api_key)

