"""
streamlit_app.py
----------------
Streamlit UI for the Cricket Analyst MCP project.

The Ask the Analyst tab uses GPT through agent_openai.py.
The other tabs use the local cricket data provider directly.

Run:
    streamlit run streamlit_app.py
"""

import asyncio
import os

import streamlit as st
from dotenv import load_dotenv

from data_provider import get_provider

# Load OPENAI_API_KEY / OPENAI_MODEL from a local .env file, if present.
load_dotenv()

st.set_page_config(page_title="Cricket Analyst", page_icon="🏏", layout="centered")
provider = get_provider()

st.title("🏏 Cricket Analyst MCP")
st.caption("MCP Server → Cricket Data → GPT Agent → Streamlit")


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

# Which stat keys are shown as metric tiles, and in what order, per role.
_BATTING_METRICS = [
    ("matches", "Matches"),
    ("runs", "Runs"),
    ("average", "Average"),
    ("strike_rate", "Strike Rate"),
    ("hundreds", "100s"),
    ("fifties", "50s"),
]
_BOWLING_METRICS = [
    ("matches", "Matches"),
    ("wickets", "Wickets"),
    ("average", "Average"),
    ("economy", "Economy"),
    ("best", "Best Figures"),
]


def render_format_stats(stats: dict):
    """Render one format's stats (Test/ODI/T20I) as metric tiles."""
    metrics = _BOWLING_METRICS if "wickets" in stats else _BATTING_METRICS
    cols = st.columns(len(metrics))
    for col, (key, label) in zip(cols, metrics):
        value = stats.get(key, "—")
        col.metric(label, value)


def render_player_card(data: dict):
    """Render a get_player_stats() result (single format or 'all')."""
    if "error" in data:
        st.error(data["error"])
        return

    st.markdown(f"### {data['full_name']}")
    st.caption(f"{data.get('country', '')} · {data.get('role', '')}")

    if "format" in data:
        # Single-format response.
        st.markdown(f"**{data['format']}**")
        render_format_stats(data["stats"])
    else:
        # "all" response: one tab per format available for this player.
        formats = list(data["stats"].keys())
        tabs = st.tabs(formats)
        for tab, fmt in zip(tabs, formats):
            with tab:
                render_format_stats(data["stats"][fmt])


def render_team_card(data: dict):
    """Render a get_team_stats() result (single format or 'all')."""
    if "error" in data:
        st.error(data["error"])
        return

    st.markdown(f"### {data['team']}")

    if "ranking" in data and isinstance(data["ranking"], int):
        # Single-format response.
        st.markdown(f"**{data['format']} ranking**")
        col1, col2 = st.columns(2)
        col1.metric("World Ranking", f"#{data['ranking']}")
        col2.metric("Recent Form", " ".join(data["recent_form"]))
        st.markdown("**Key players:** " + ", ".join(data["key_players"]))
    else:
        # "all" response: rankings per format as metric tiles, plus shared info.
        rankings = data["ranking"]
        cols = st.columns(len(rankings))
        for col, (fmt, rank) in zip(cols, rankings.items()):
            col.metric(f"{fmt} Rank", f"#{rank}")
        st.markdown("**Recent form:** " + " ".join(data["recent_form"]))
        st.markdown("**Key players:** " + ", ".join(data["key_players"]))


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_ask, tab_players, tab_teams, tab_matches, tab_news = st.tabs(
    ["Ask the Analyst", "Players", "Teams", "Matches", "News"]
)

with tab_ask:
    st.write("Ask a cricket question. GPT can discover and call the MCP tools as needed.")
    question = st.text_area(
        "Your question",
        value="Compare Virat Kohli and Rohit Sharma in ODI cricket.",
        height=100,
    )

    if st.button("Analyze with GPT", type="primary"):
        if not os.environ.get("OPENAI_API_KEY"):
            st.error("OPENAI_API_KEY is not set. Add it to your environment or .env file.")
        elif not question.strip():
            st.warning("Enter a question first.")
        else:
            from agent_openai import run_agent

            with st.spinner("GPT is using the Cricket Analyst MCP tools..."):
                try:
                    answer = asyncio.run(run_agent(question.strip()))
                    st.markdown(answer)
                except Exception as exc:
                    st.error(f"Agent error: {exc}")

with tab_players:
    player_name = st.text_input("Player name", value="Virat Kohli", key="player")
    fmt = st.selectbox("Format", ["all", "Test", "ODI", "T20I"], key="player_fmt")
    if st.button("Get stats"):
        render_player_card(provider.get_player_stats(player_name, fmt))

    st.divider()
    st.subheader("All players")
    st.caption("Full career stats (every format) for every player in the dataset.")
    if st.button("Load all players"):
        all_players = provider.get_all_players()
        for player in all_players:
            with st.expander(f"{player['full_name']} — {player['country']} ({player['role']})"):
                render_player_card(player)

    st.divider()
    st.subheader("Compare two players")
    col1, col2 = st.columns(2)
    p1 = col1.text_input("Player 1", value="Virat Kohli")
    p2 = col2.text_input("Player 2", value="Rohit Sharma")
    cmp_fmt = st.selectbox("Format", ["Test", "ODI", "T20I"], key="cmp_fmt")
    if st.button("Compare"):
        with col1:
            render_player_card(provider.get_player_stats(p1, cmp_fmt))
        with col2:
            render_player_card(provider.get_player_stats(p2, cmp_fmt))

with tab_teams:
    team_name = st.text_input("Team name", value="India")
    team_fmt = st.selectbox("Format", ["all", "Test", "ODI", "T20I"], key="team_fmt")
    if st.button("Get team stats"):
        render_team_card(provider.get_team_stats(team_name, team_fmt))

with tab_matches:
    limit = st.slider("How many matches", 1, 20, 5)
    if st.button("Show recent matches"):
        matches = provider.get_recent_matches(limit)
        if not matches:
            st.info("No matches found.")
        for match in matches:
            with st.container(border=True):
                st.markdown(f"**{match['team1']} vs {match['team2']}** · {match['format']}")
                st.write(f"🏆 {match['winner']} won by {match['margin']}")
                st.caption(f"{match['venue']} · {match['date']}")

with tab_news:
    query = st.text_input("Search term", value="Kohli")
    if st.button("Search news"):
        news = provider.search_cricket_news(query)
        for item in news:
            with st.container(border=True):
                st.markdown(f"**{item['title']}**")
                st.caption(f"{item['source']} · {item['date']}")
                st.write(item["summary"])
