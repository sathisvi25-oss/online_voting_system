import io
import uuid
import hashlib
from datetime import datetime, timezone

import streamlit as st

from models.loader import (
    load_face_embedding_model
)

from services.db import (
    get_database,
    get_collections,
    get_gridfs
)

from services.auth import (
    authenticate_face,
    log_auth_attempt
)

from utils.theme import (
    apply_theme,
    page_header,
    section_title,
    candidate_card
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Cast Your Vote",
    page_icon="🗳️",
    layout="wide"
)

apply_theme()


# ============================================================
# PAGE TITLE
# ============================================================

page_header(
    "Cast Your Vote",
    subtitle="Verify your face, then select a candidate or NOTA.",
    kicker="Step 2 of 2",
    icon="🗳️"
)


# ============================================================
# LOGIN CHECK
# ============================================================

if not st.session_state.get(
    "logged_in",
    False
):

    st.error(
        "Please login first."
    )

    st.stop()


# ============================================================
# DATABASE
# ============================================================

try:

    db = get_database()

    collections = get_collections(
        db
    )

    fs = get_gridfs(
        db
    )

except Exception as e:

    st.error(
        "Database connection failed."
    )

    st.exception(e)

    st.stop()


# ============================================================
# VOTER LOGOUT HELPER
# ============================================================

def logout_voter(
    collections=None,
    voter_id=None,
    reason="MANUAL_LOGOUT"
):
    """
    Completely log out the current voter.

    The authentication/session keys are cleared so the Login page
    cannot reuse the previous authenticated session.
    """
    # Record the logout event when database objects are available.
    if collections is not None and voter_id:
        try:
            log_auth_attempt(
                collections,
                voter_id,
                "LOGOUT",
                reason
            )
        except Exception:
            # Logout must still succeed even if audit logging fails.
            pass

    # Clear every Streamlit session-state key.
    # This also removes face authentication state and voter identity.
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # Go directly back to the voter Login page.
    st.switch_page("pages/2_Login.py")


# ============================================================
# GET VOTER
# ============================================================

voter_id = (
    st.session_state.get(
        "voter_id"
    )
)


if not voter_id:

    st.error(
        "Voter session information is missing."
    )

    st.session_state.logged_in = False

    st.stop()


voter = collections[
    "voters"
].find_one(
    {
        "voter_id": voter_id
    }
)


if not voter:

    st.error(
        "Your voter account could not be found."
    )

    st.session_state.logged_in = False

    st.stop()


# ============================================================
# MANUAL VOTER LOGOUT BUTTON
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    f"Logged in Voter: **{voter.get('voter_id', voter_id)}**"
)

if st.sidebar.button(
    "🚪 Logout",
    use_container_width=True,
    key="manual_voter_logout"
):
    logout_voter(
        collections=collections,
        voter_id=voter_id,
        reason="MANUAL_LOGOUT"
    )


# ============================================================
# VERIFICATION STATUS
# ============================================================

if not voter.get(
    "is_verified",
    False
):

    st.warning(
        "Your voter registration has not yet "
        "been approved by the administrator."
    )

    st.stop()


# ============================================================
# CHECK PREVIOUS VOTE
# ============================================================

if voter.get(
    "has_voted",
    False
):

    st.warning(
        "You have already voted."
    )

    st.stop()


# ============================================================
# OPEN ELECTION FOR THIS VOTER
# ============================================================
# IMPORTANT:
# There may be multiple OPEN elections in MongoDB.
# We must not simply select the newest OPEN election because it
# may have no candidates while another OPEN election in the same
# constituency already has candidates.
#
# The election shown to the voter is therefore selected using:
#   1. Election status == OPEN
#   2. Election constituency == voter constituency
#   3. At least one approved/non-rejected candidate exists for
#      that election and candidate constituency == voter constituency
#
# Candidate election_id is accepted as either ObjectId or string
# for compatibility with older records.


def normalize_constituency(value):
    """Normalize constituency names for reliable comparisons."""
    return " ".join(
        str(value or "").strip().casefold().split()
    )


def constituency_matches(first, second):
    """Case/space-insensitive constituency comparison."""
    first_value = normalize_constituency(first)
    second_value = normalize_constituency(second)

    return bool(
        first_value
        and second_value
        and first_value == second_value
    )


def candidate_query_for_election(election_id):
    """Query candidates for an election using both supported ID types."""
    return {
        "$or": [
            {"election_id": election_id},
            {"election_id": str(election_id)}
        ],
        "status": {
            "$nin": ["PENDING", "REJECTED"]
        }
    }


def get_election_candidates(election_id):
    """Return active candidates linked to one election."""
    return list(
        collections["candidates"].find(
            candidate_query_for_election(election_id)
        ).sort(
            "created_at",
            1
        )
    )


voter_constituency = normalize_constituency(
    voter.get("constituency", "")
)

all_open_elections = list(
    collections["elections"].find(
        {"status": "OPEN"}
    ).sort(
        "created_at",
        -1
    )
)


if not all_open_elections:

    st.info(
        "There is no open election at the moment."
    )

    st.stop()


# ------------------------------------------------------------
# Find the newest OPEN election that actually has candidates
# for this voter's constituency.
# ------------------------------------------------------------

matching_election = None
matching_election_candidates = []

for open_election in all_open_elections:

    raw_election_constituency = open_election.get(
        "constituency",
        ""
    )

    election_constituency = normalize_constituency(
        raw_election_constituency
    )

    # Current schema: the election itself must explicitly match
    # the voter's constituency.
    if election_constituency:

        if election_constituency != voter_constituency:
            continue

    # Load candidates for this exact election.  This is important:
    # do not stop at the first matching OPEN election if it has no
    # candidates.
    election_candidates = get_election_candidates(
        open_election["_id"]
    )

    # Only candidates in the voter's constituency can appear.
    voter_candidates = [
        candidate
        for candidate in election_candidates
        if constituency_matches(
            candidate.get("constituency", ""),
            voter_constituency
        )
    ]

    if not voter_candidates:
        continue

    # Legacy election support:
    # If constituency is missing on the election document, the
    # candidate data can establish it only when the candidates for
    # this election actually belong to the voter's constituency.
    if not election_constituency:
        election_constituency = voter_constituency

    # Final three-way rule for this election's ballot:
    # voter == election == candidate
    valid_candidates = [
        candidate
        for candidate in voter_candidates
        if (
            election_constituency == voter_constituency
            and normalize_constituency(
                candidate.get("constituency", "")
            ) == election_constituency
        )
    ]

    if valid_candidates:
        matching_election = open_election
        matching_election_candidates = valid_candidates
        break


if matching_election is None:

    st.warning(
        "No candidates are currently available for your constituency "
        f"(**{voter.get('constituency', 'Not set')}**) in an open election."
    )

    st.caption(
        "The election, voter, and candidate constituency must all match."
    )

    st.stop()


election = matching_election

election_constituency = normalize_constituency(
    election.get("constituency", "")
)

if not election_constituency:
    election_constituency = voter_constituency

# ============================================================
# ELECTION DETAILS
# ============================================================

st.markdown(
f"""<div class="vs-card vs-card-accent">
<span class="vs-pill">Open now</span>
<h3 style="margin:0.4rem 0 0 0;">{election.get('title', 'Unnamed Election')}</h3>
</div>
""",
    unsafe_allow_html=True
)

st.caption(
    f"Constituency: **{election.get('constituency', election_constituency or 'Not set')}** "
    f"• Your constituency: **{voter.get('constituency', 'Not set')}**"
)


# ============================================================
# SESSION STATE
# ============================================================

if "face_verified" not in st.session_state:

    st.session_state.face_verified = False


if "face_similarity" not in st.session_state:

    st.session_state.face_similarity = 0.0


if "vote_cast" not in st.session_state:

    st.session_state.vote_cast = False


# ============================================================
# STEP 1 — FACE AUTHENTICATION
# ============================================================

st.divider()

st.subheader(
    "Step 1 — Face Authentication"
)


# ------------------------------------------------------------
# Enrolled embedding check
# ------------------------------------------------------------

enrolled_embedding = voter.get(
    "face_embedding"
)


if not enrolled_embedding:

    st.error(
        "Face enrollment is missing for this account."
    )

    st.stop()


st.write(
    "Look directly at the camera and capture your face."
)


# ============================================================
# CAMERA
# ============================================================

live_image = st.camera_input(
    "Capture Live Face"
)


# ============================================================
# VERIFY FACE
# ============================================================

if live_image is not None:

    st.image(
        live_image,
        caption="Captured Live Image",
        use_container_width=True
    )


    if st.button(
        "🔐 Verify Face",
        use_container_width=True
    ):

        with st.spinner(
            "Detecting and verifying your face..."
        ):

            try:

                # ------------------------------------------------
                # Load DINOv2
                # ------------------------------------------------

                processor, model = (
                    load_face_embedding_model()
                )


                # ------------------------------------------------
                # Authenticate
                # ------------------------------------------------

                authenticated, similarity = (
                    authenticate_face(
                        live_image,
                        enrolled_embedding,
                        processor,
                        model,
                        threshold=0.85
                    )
                )


            except Exception as e:

                st.error(
                    "Face authentication failed."
                )

                st.exception(e)

                st.stop()


        # ====================================================
        # DISPLAY SIMILARITY
        # ====================================================

        st.metric(
            "Face Similarity",
            f"{similarity * 100:.2f}%"
        )


        st.session_state.face_similarity = (
            similarity
        )


        # ====================================================
        # AUTH RESULT
        # ====================================================

        if authenticated:

            st.session_state.face_verified = True

            log_auth_attempt(
                collections,
                voter_id,
                "SUCCESS",
                "FACE_AUTH",
                similarity=similarity
            )

            st.success(
                "✅ Face authentication successful."
            )

        else:

            st.session_state.face_verified = False

            log_auth_attempt(
                collections,
                voter_id,
                "FAIL",
                "FACE_AUTH",
                similarity=similarity
            )

            st.error(
                "❌ Face authentication failed."
            )


# ============================================================
# STEP 2 — BALLOT
# ============================================================

if st.session_state.get(
    "face_verified",
    False
):

    st.divider()

    st.subheader(
        "Step 2 — Ballot"
    )


    # ========================================================
    # LOAD CANDIDATES FOR THE SELECTED ELECTION
    # ========================================================
    # matching_election_candidates was already calculated while
    # selecting the correct OPEN election. Re-use that exact list
    # so the ballot cannot accidentally query a different election.

    candidates = list(matching_election_candidates)

    # Also keep a robust defensive lookup for legacy records in case
    # the session state is refreshed while this page is running.
    if not candidates:
        candidates = get_election_candidates(
            election["_id"]
        )

    # ========================================================
    # THREE-WAY CONSTITUENCY RULE
    # ========================================================
    # VOTER CONSTITUENCY
    #          ==
    # ELECTION CONSTITUENCY
    #          ==
    # CANDIDATE CONSTITUENCY
    #
    # Only candidates satisfying all three are displayed.

    candidates = [
        candidate
        for candidate in candidates
        if (
            voter_constituency
            and election_constituency
            and normalize_constituency(
                candidate.get("constituency", "")
            ) == voter_constituency
            and normalize_constituency(
                candidate.get("constituency", "")
            ) == election_constituency
        )
    ]

    # ========================================================
    # NO CANDIDATES
    # ========================================================

    if not candidates:

        st.info(
            "No candidates are contesting in your constituency "
            f"(**{voter.get('constituency', '')}**) for this "
            "election yet."
        )

        st.stop()


    # ========================================================
    # CANDIDATE GALLERY
    # ========================================================

    gallery_cols = st.columns(
        min(len(candidates), 4)
        or 1
    )

    for i, candidate in enumerate(candidates):

        photo_bytes = None

        photo_id = candidate.get(
            "photo_file"
        )

        if photo_id:

            try:

                photo_bytes = fs.get(
                    photo_id
                ).read()

            except Exception:

                photo_bytes = None

        with gallery_cols[i % len(gallery_cols)]:

            candidate_card(
                name=candidate.get(
                    "name",
                    "Unknown"
                ),
                subtitle=candidate.get(
                    "party",
                    ""
                ),
                image_bytes=photo_bytes
            )


    # ========================================================
    # BALLOT OPTIONS
    # ========================================================

    options = [
        f"{candidate.get('name', 'Unknown')} - "
        f"{candidate.get('party', '')}"
        for candidate in candidates
    ]


    options.append(
        "NOTA"
    )


    choice = st.radio(
        "Select Candidate",
        options,
        index=None
    )


    # ========================================================
    # CONFIRMATION
    # ========================================================

    confirm = st.checkbox(
        "I confirm my selection."
    )


    # ========================================================
    # CAST VOTE
    # ========================================================

    if st.button(
        "🗳️ Cast Vote",
        use_container_width=True
    ):

        # ----------------------------------------------------
        # Choice check
        # ----------------------------------------------------

        if choice is None:

            st.warning(
                "Please select a candidate or NOTA."
            )

            st.stop()


        # ----------------------------------------------------
        # Confirmation check
        # ----------------------------------------------------

        if not confirm:

            st.warning(
                "Please confirm your selection."
            )

            st.stop()


        # ====================================================
        # PREVENT SECOND VOTE
        # ====================================================

        fresh_voter = collections[
            "voters"
        ].find_one(
            {
                "voter_id": voter_id
            }
        )


        if fresh_voter and fresh_voter.get(
            "has_voted",
            False
        ):

            st.error(
                "A vote has already been recorded "
                "for this voter."
            )

            st.session_state.face_verified = False

            st.stop()


        # ====================================================
        # FIND CANDIDATE AND RE-CHECK CONSTITUENCY
        # ====================================================

        selected_candidate = None
        selected_candidate_doc = None


        if choice != "NOTA":

            for candidate in candidates:

                label = (
                    f"{candidate.get('name', 'Unknown')} - "
                    f"{candidate.get('party', '')}"
                )

                if choice == label:

                    selected_candidate = (
                        candidate["_id"]
                    )

                    selected_candidate_doc = candidate

                    break


            if selected_candidate is None:

                st.error(
                    "Selected candidate could not be found."
                )

                st.stop()


            # Final server-side safety check immediately before
            # recording the vote.
            candidate_constituency = normalize_constituency(
                selected_candidate_doc.get("constituency", "")
            )

            if not (
                voter_constituency
                and election_constituency
                and candidate_constituency
                and voter_constituency == election_constituency
                and election_constituency == candidate_constituency
            ):

                st.error(
                    "❌ Constituency mismatch. "
                    "Your voter constituency, the election constituency, "
                    "and the selected candidate constituency must match."
                )

                st.info(
                    f"Voter: {voter.get('constituency', 'Not set')} | "
                    f"Election: {election.get('constituency', 'Not set')} | "
                    f"Candidate: {selected_candidate_doc.get('constituency', 'Not set')}"
                )

                st.session_state.face_verified = False

                st.stop()


        # ====================================================
        # RECEIPT ID
        # ====================================================

        receipt_id = str(
            uuid.uuid4()
        )


        # ====================================================
        # VOTE HASH
        # ====================================================

        vote_hash = hashlib.sha256(
            choice.encode(
                "utf-8"
            )
        ).hexdigest()


        # ====================================================
        # UPDATE VOTER FIRST
        # ====================================================

        vote_result = collections[
            "voters"
        ].update_one(
            {
                "voter_id":
                    voter_id,

                "has_voted":
                    {
                        "$ne": True
                    }
            },
            {
                "$set":
                    {
                        "has_voted":
                            True,

                        "voted_at":
                            datetime.now(
                                timezone.utc
                            )
                    }
            }
        )


        if vote_result.modified_count != 1:

            st.error(
                "Your vote could not be recorded. "
                "You may have already voted."
            )

            st.session_state.face_verified = False

            st.stop()


        # ====================================================
        # INSERT VOTE
        # ====================================================

        try:

            collections[
                "votes"
            ].insert_one(
                {

                    "election_id":
                        election["_id"],

                    "candidate_id":
                        selected_candidate,

                    "vote_hash":
                        vote_hash,

                    "timestamp":
                        datetime.now(
                            timezone.utc
                        ),

                    "receipt_id":
                        receipt_id
                }
            )

        except Exception as e:

            st.error(
                "Vote record insertion failed."
            )

            st.exception(e)

            st.stop()


        # ====================================================
        # SUCCESS MESSAGE
        # ====================================================

        st.success(
            "✅ Vote recorded successfully."
        )

        st.info(
            f"Receipt ID: {receipt_id}"
        )

        st.warning(
            "🔒 You are being logged out automatically..."
        )


        # ====================================================
        # AUTOMATIC VOTER LOGOUT AFTER VOTE
        # ====================================================
        #
        # The vote has already been written to MongoDB above.
        # Now completely destroy the authenticated session and
        # redirect to the Login page.
        #
        # This prevents the same browser session from returning
        # to the ballot as the previous voter.

        logout_voter(
            collections=collections,
            voter_id=voter_id,
            reason="AUTO_LOGOUT_AFTER_VOTE"
        )
