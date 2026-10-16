import streamlit as st
import pandas as pd
import plotly.express as px
from bson import ObjectId

from services.db import get_database, get_collections, get_gridfs
from utils.theme import apply_theme, page_header, winner_card, HARBOR, SIGNAL


st.set_page_config(
    page_title="Election Results",
    page_icon="📊",
    layout="wide"
)

apply_theme()

page_header(
    "Election Results",
    subtitle="Published once an election officer declares results for a "
             "closed election.",
    kicker="Public results",
    icon="📊"
)

try:
    db = get_database()
    collections = get_collections(db)
    fs = get_gridfs(db)
except Exception as e:
    st.error("Database connection failed.")
    st.exception(e)
    st.stop()


# ============================================================
# ELECTIONS WHOSE RESULTS ARE PUBLIC
# ============================================================

elections = list(
    collections["elections"].find(
        {"status": "RESULTS_DECLARED"}
    ).sort("results_declared_at", -1)
)

if not elections:
    st.info("Results have not been declared for any election yet.")
    st.stop()

election_map = {str(e["_id"]): e.get("title", "Unnamed Election") for e in elections}

selected_id = st.selectbox(
    "Select Election",
    options=list(election_map.keys()),
    format_func=lambda x: election_map[x]
)

try:
    election_oid = ObjectId(selected_id)
except Exception:
    st.error("Invalid election selected.")
    st.stop()

election = collections["elections"].find_one({"_id": election_oid})

st.markdown(
f"""<div class="vs-card vs-card-accent">
<span class="vs-pill">Declared</span>
<h3 style="margin:0.4rem 0 0 0;">{election.get('title', '')}</h3>
</div>
""",
    unsafe_allow_html=True
)


# ============================================================
# TALLY VOTES (candidates + NOTA)
# ============================================================

pipeline = [
    {"$match": {"election_id": election_oid}},
    {
        "$group": {
            "_id": "$candidate_id",
            "total": {"$sum": 1}
        }
    }
]

results = list(collections["votes"].aggregate(pipeline))

candidates = {
    c["_id"]: c
    for c in collections["candidates"].find({"election_id": election_oid})
}

data = []

for item in results:
    candidate_id = item["_id"]
    votes = item["total"]

    if candidate_id is None:
        data.append({"Candidate": "NOTA", "Party": "-", "Votes": votes, "_id": None})
        continue

    candidate = candidates.get(candidate_id)

    if not candidate:
        continue

    data.append({
        "Candidate": candidate.get("name", "Unknown"),
        "Party": candidate.get("party", "Unknown"),
        "Votes": votes,
        "_id": candidate_id
    })

if data:

    df = pd.DataFrame(data).sort_values("Votes", ascending=False).reset_index(drop=True)

    total_votes = int(df["Votes"].sum())
    leader = df.iloc[0]

    # ========================================================
    # WINNER SPOTLIGHT
    # ========================================================

    if leader["Candidate"] == "NOTA":

        st.info(
            "🚫 **NOTA** received the most votes in this election — "
            "no candidate winner."
        )

    else:

        winner_candidate = candidates.get(leader["_id"], {})

        runner_up_votes = int(df.iloc[1]["Votes"]) if len(df) > 1 else 0
        runner_up_name = df.iloc[1]["Candidate"] if len(df) > 1 else None
        margin = int(leader["Votes"]) - runner_up_votes

        if runner_up_name:
            margin_text = f"Won by {margin:,} votes over {runner_up_name}"
        else:
            margin_text = "Unopposed"

        winner_photo_bytes = None
        photo_id = winner_candidate.get("photo_file")

        if photo_id:
            try:
                winner_photo_bytes = fs.get(photo_id).read()
            except Exception:
                winner_photo_bytes = None

        winner_card(
            name=leader["Candidate"],
            party=leader["Party"],
            constituency=winner_candidate.get("constituency", ""),
            votes=int(leader["Votes"]),
            margin_text=margin_text,
            image_bytes=winner_photo_bytes
        )

    st.divider()

    m1, m2, m3 = st.columns(3)

    with m1:
        st.metric("Total Votes Cast", total_votes)

    with m2:
        st.metric("Candidates / Options", len(df))

    with m3:
        st.metric(
            "Leading",
            leader["Candidate"],
            f"{leader['Votes']} votes"
        )

    st.divider()

    display_df = df.drop(columns=["_id"])

    left, right = st.columns([3, 2])

    with left:
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        csv = display_df.to_csv(index=False)
        st.download_button(
            "⬇️ Download Results CSV",
            data=csv,
            file_name="election_results.csv",
            mime="text/csv",
            use_container_width=True
        )

    with right:
        fig = px.pie(
            display_df,
            names="Candidate",
            values="Votes",
            hole=0.55,
            color_discrete_sequence=[HARBOR, SIGNAL, "#5B6472", "#8C5F17", "#0E2143", "#C9D3E6"]
        )
        fig.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            legend=dict(orientation="h", y=-0.15)
        )
        st.plotly_chart(fig, use_container_width=True)

    fig2 = px.bar(
        display_df,
        x="Candidate",
        y="Votes",
        title="Vote Distribution",
        text="Votes",
        color_discrete_sequence=[HARBOR]
    )
    fig2.update_traces(textposition="outside", marker_color=HARBOR)
    fig2.update_layout(plot_bgcolor="white", paper_bgcolor="white")

    st.plotly_chart(fig2, use_container_width=True)

else:
    st.info("No votes were recorded for this election.")
