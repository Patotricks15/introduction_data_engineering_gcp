import os

import pandas as pd
import streamlit as st
from google.cloud import bigquery


PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
DATASET_ID = os.environ.get("GCP_DATASET_ID", "esports_streaming")

st.set_page_config(page_title="Arena Pulse", layout="wide")
st.title("Arena Pulse")
st.caption("Live e-sports gameplay and team chat")

if not PROJECT_ID:
    st.error("Set GCP_PROJECT_ID before starting the dashboard.")
    st.stop()

client = bigquery.Client(project=PROJECT_ID)


@st.fragment(run_every="5s")
def live_dashboard() -> None:
    leaderboard = client.query(
        f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.live_leaderboard` ORDER BY score DESC"
    ).to_dataframe()
    chat = client.query(
        f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.live_chat` ORDER BY event_time DESC LIMIT 20"
    ).to_dataframe()

    total_score = int(leaderboard["score"].sum()) if not leaderboard.empty else 0
    leaders = len(leaderboard)
    chat_count = len(chat)
    metric_columns = st.columns(3)
    metric_columns[0].metric("Active players", leaders)
    metric_columns[1].metric("Points scored", total_score)
    metric_columns[2].metric("Recent messages", chat_count)

    left, right = st.columns([1.05, 0.95])
    with left:
        st.subheader("Live leaderboard")
        if leaderboard.empty:
            st.info("Waiting for gameplay events...")
        else:
            st.dataframe(
                leaderboard[["display_name", "team", "rank", "score", "kills", "assists"]],
                hide_index=True,
                use_container_width=True,
            )
            chart_data = leaderboard.set_index("display_name")[["score"]]
            st.bar_chart(chart_data, color="#1a73e8")
    with right:
        st.subheader("Team chat")
        if chat.empty:
            st.info("Waiting for chat events...")
        else:
            for message in chat.itertuples():
                st.markdown(
                    f"**{message.display_name}** - {message.team}  \n"
                    f"{message.message}"
                )
                st.caption(pd.Timestamp(message.event_time).strftime("%H:%M:%S UTC"))


live_dashboard()