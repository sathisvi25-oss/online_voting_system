import streamlit as st
from bson import ObjectId
from datetime import datetime, timezone
import bcrypt
import pandas as pd
import plotly.express as px

from services.db import get_database, get_gridfs
from utils.theme import apply_theme, page_header

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Admin Dashboard",
    page_icon="🛠️",
    layout="wide"
)

apply_theme()


# ============================================================
# DATABASE
# ============================================================

try:
    db = get_database()
    fs = get_gridfs(db)

    voters_col = db["voters"]
    votes_col = db["votes"]
    auth_logs_col = db["auth_logs"]
    elections_col = db["elections"]
    candidates_col = db["candidates"]
    admins_col = db["admins"]

except Exception as e:
    st.error("❌ Unable to connect to MongoDB Atlas")
    st.exception(e)
    st.stop()


# ============================================================
# SESSION STATE
# ============================================================

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if "admin_username" not in st.session_state:
    st.session_state.admin_username = None


# ============================================================
# DEFAULT ADMIN ACCOUNT
# ============================================================

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


def ensure_default_admin():
    """Create the demo admin account if it does not exist."""

    try:
        existing_admin = admins_col.find_one({
            "username": DEFAULT_ADMIN_USERNAME
        })

        if existing_admin is not None:
            return False

        password_hash = bcrypt.hashpw(
            DEFAULT_ADMIN_PASSWORD.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        admins_col.insert_one({
            "username": DEFAULT_ADMIN_USERNAME,
            "password_hash": password_hash,
            "created_at": datetime.now(timezone.utc),
            "created_by": "SYSTEM"
        })

        return True

    except Exception as e:
        st.warning(f"Unable to initialize default admin account: {e}")
        return False


admin_created = ensure_default_admin()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_object_id(value):
    """
    Convert a string to ObjectId safely.
    Returns None when the value is invalid.
    """
    try:
        return ObjectId(value)
    except Exception:
        return None


def format_datetime(value):
    """Format MongoDB datetime values for display."""
    if not value:
        return "N/A"

    try:
        return value.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value)


def normalize_constituency(value):
    """Normalize constituency names for safe comparison."""
    return " ".join(str(value or "").strip().casefold().split())


def constituencies_match(first, second):
    """Case/space-insensitive constituency comparison."""
    first_value = normalize_constituency(first)
    second_value = normalize_constituency(second)
    return bool(first_value and second_value and first_value == second_value)


def get_candidates_for_election(election_oid):
    """
    Load candidates for an election and support both legacy ObjectId
    and string election_id values. Legacy string IDs are repaired to
    ObjectId so every page uses one consistent data type.
    """
    if election_oid is None:
        return []

    election_id_string = str(election_oid)

    candidates = list(
        candidates_col.find({
            "$or": [
                {"election_id": election_oid},
                {"election_id": election_id_string}
            ]
        }).sort(
            "created_at",
            1
        )
    )

    for candidate in candidates:
        candidate_election_id = candidate.get("election_id")
        if isinstance(candidate_election_id, str):
            converted = safe_object_id(candidate_election_id)
            if converted is not None and converted == election_oid:
                candidates_col.update_one(
                    {"_id": candidate["_id"]},
                    {"$set": {"election_id": election_oid}}
                )
                candidate["election_id"] = election_oid

    return candidates


def repair_election_constituency(election):
    """
    Repair older election records created before the constituency field
    existed. When all candidates for that election have the same
    non-empty constituency, that constituency is safely written to the
    election document.

    Returns the refreshed election document.
    """
    if not election:
        return election

    existing = normalize_constituency(election.get("constituency"))
    if existing:
        return election

    election_oid = election.get("_id")
    candidates = get_candidates_for_election(election_oid)

    candidate_constituencies = {
        normalize_constituency(c.get("constituency"))
        for c in candidates
        if normalize_constituency(c.get("constituency"))
    }

    if len(candidate_constituencies) == 1:
        repaired_constituency = next(iter(candidate_constituencies))

        # Preserve the first stored display value where possible.
        display_value = next(
            c.get("constituency", "").strip()
            for c in candidates
            if normalize_constituency(c.get("constituency")) == repaired_constituency
        )

        elections_col.update_one(
            {"_id": election_oid},
            {
                "$set": {
                    "constituency": display_value,
                    "constituency_repaired_at": datetime.now(timezone.utc),
                    "constituency_repaired_by": "SYSTEM_COMPATIBILITY_FIX"
                }
            }
        )

        refreshed = elections_col.find_one({"_id": election_oid})
        return refreshed or election

    return election


def voter_can_vote_for_candidate(voter, election, candidate):
    """
    Final constituency rule:

        VOTER CONSTITUENCY == ELECTION CONSTITUENCY
        == CANDIDATE CONSTITUENCY

    All three must be present and equal.
    This function is also the rule that should be used by 3_Vote.py
    immediately before a vote is inserted into MongoDB.
    """
    voter_constituency = normalize_constituency(voter.get("constituency"))
    election_constituency = normalize_constituency(election.get("constituency"))
    candidate_constituency = normalize_constituency(candidate.get("constituency"))

    return (
        bool(voter_constituency)
        and bool(election_constituency)
        and bool(candidate_constituency)
        and voter_constituency == election_constituency
        and election_constituency == candidate_constituency
    )


# ============================================================
# ADMIN LOGIN
# ============================================================

def admin_login(username, password):

    admin = admins_col.find_one({
        "username": username
    })

    if not admin:
        return False

    try:
        password_hash = admin.get("password_hash")

        if not password_hash:
            return False

        if isinstance(password_hash, str):
            password_hash = password_hash.encode("utf-8")

        password_ok = bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash
        )

        if password_ok:
            st.session_state.admin_logged_in = True
            st.session_state.admin_username = username

            # Authentication log
            auth_logs_col.insert_one({
                "voter_id": None,
                "username": username,
                "attempt_time": datetime.now(timezone.utc),
                "status": "SUCCESS",
                "auth_type": "ADMIN_LOGIN"
            })

            return True

    except Exception:
        return False

    return False


# ============================================================
# LOGIN SCREEN
# ============================================================

if not st.session_state.admin_logged_in:

    page_header(
        "Admin Login",
        subtitle="Election Officer / Administrator access only.",
        kicker="Restricted",
        icon="🛠️"
    )

    if admin_created:
        st.success("Default admin account created successfully.")
        st.info("Demo login: admin / admin123")

    left, mid, right = st.columns([1, 2, 1])

    with mid:

        with st.form("admin_login_form"):

            username = st.text_input(
                "Username",
                value=DEFAULT_ADMIN_USERNAME
            )

            password = st.text_input(
                "Password",
                type="password"
            )

            login = st.form_submit_button(
                "Login",
                use_container_width=True
            )

    if login:

        if not username or not password:

            st.warning(
                "Enter username and password."
            )

        elif admin_login(
            username,
            password
        ):

            st.success(
                "Admin login successful."
            )

            st.rerun()

        else:

            # Failed authentication log
            auth_logs_col.insert_one({
                "voter_id": None,
                "username": username,
                "attempt_time": datetime.now(timezone.utc),
                "status": "FAIL",
                "auth_type": "ADMIN_LOGIN"
            })

            st.error(
                "Invalid admin credentials."
            )

    st.stop()


# ============================================================
# ADMIN HEADER
# ============================================================

st.markdown(
f"""<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
<div>
<span style="font-family:'Sora',sans-serif; font-weight:800; font-size:1.6rem; color:#10162B;">
🛠️ Election Admin Dashboard
</span>
</div>
</div>
""",
    unsafe_allow_html=True
)

st.caption(
    f"Logged in as: **{st.session_state.admin_username}**"
)

if st.button("🚪 Logout"):

    # Log logout
    auth_logs_col.insert_one({
        "voter_id": None,
        "username": st.session_state.admin_username,
        "attempt_time": datetime.now(timezone.utc),
        "status": "LOGOUT",
        "auth_type": "ADMIN_LOGIN"
    })

    st.session_state.admin_logged_in = False
    st.session_state.admin_username = None

    st.rerun()


st.divider()


# ============================================================
# SIDEBAR MENU
# ============================================================

menu = st.sidebar.radio(
    "Admin Menu",
    [
        "📊 Dashboard",
        "👤 Voter Approvals",
        "🗳️ Election Management",
        "👥 Candidate Management",
        "🔐 Authentication Logs",
        "🏆 Results"
    ]
)


# ============================================================
# DASHBOARD
# ============================================================

if menu == "📊 Dashboard":

    st.header("📊 Election Dashboard")

    # --------------------------------
    # Statistics
    # --------------------------------

    total_voters = voters_col.count_documents({})

    approved_voters = voters_col.count_documents({
        "is_verified": True
    })

    voted_voters = voters_col.count_documents({
        "has_voted": True
    })

    pending_voters = voters_col.count_documents({
        "is_verified": False
    })

    total_votes = votes_col.count_documents({})

    failed_auth = auth_logs_col.count_documents({
        "status": {
            "$in": [
                "FAIL",
                "SPOOF_DETECTED",
                "LOCKED"
            ]
        }
    })

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Total Voters",
            total_voters
        )

        st.metric(
            "Approved Voters",
            approved_voters
        )

    with col2:

        st.metric(
            "Votes Cast",
            total_votes
        )

        st.metric(
            "Pending Approvals",
            pending_voters
        )

    with col3:

        turnout = 0

        if approved_voters > 0:
            turnout = (
                voted_voters /
                approved_voters
            ) * 100

        st.metric(
            "Turnout",
            f"{turnout:.2f}%"
        )

        st.metric(
            "Failed Authentication",
            failed_auth
        )

    st.divider()

    # --------------------------------
    # Election status
    # --------------------------------

    st.subheader("🗳️ Current Election")

    election = elections_col.find_one(
        sort=[
            ("created_at", -1)
        ]
    )

    if election:

        st.write(
            f"**Election:** "
            f"{election.get('title', 'N/A')}"
        )

        st.write(
            f"**Status:** "
            f"{election.get('status', 'N/A')}"
        )

        st.write(
            f"**Start:** "
            f"{format_datetime(election.get('start_time'))}"
        )

        st.write(
            f"**End:** "
            f"{format_datetime(election.get('end_time'))}"
        )

    else:

        st.info(
            "No election has been created yet."
        )


# ============================================================
# VOTER APPROVALS
# ============================================================

elif menu == "👤 Voter Approvals":

    st.header(
        "👤 Voter Registration Approvals"
    )

    pending = list(
        voters_col.find({
            "is_verified": False
        }).sort(
            "reg_date",
            -1
        )
    )

    if not pending:

        st.success(
            "No pending voter registrations."
        )

    else:

        st.info(
            f"{len(pending)} registration(s) "
            "waiting for approval."
        )

        for voter in pending:

            voter_id = str(
                voter.get("_id")
            )

            with st.expander(
                f"{voter.get('name', 'Unknown')} — "
                f"{voter.get('voter_id', '')}"
            ):

                col1, col2 = st.columns(2)

                with col1:

                    st.write(
                        f"**Name:** "
                        f"{voter.get('name', '')}"
                    )

                    st.write(
                        f"**Voter ID:** "
                        f"{voter.get('voter_id', '')}"
                    )

                    st.write(
                        f"**Email:** "
                        f"{voter.get('email', '')}"
                    )

                    st.write(
                        f"**Phone:** "
                        f"{voter.get('phone', '')}"
                    )

                    st.write(
                        f"**Constituency:** "
                        f"{voter.get('constituency', '')}"
                    )

                with col2:

                    confidence = voter.get(
                        "ocr_confidence",
                        0
                    )

                    st.metric(
                        "OCR Confidence",
                        f"{confidence * 100:.2f}%"
                    )

                    st.write(
                        "**OCR Text:**"
                    )

                    st.code(
                        voter.get(
                            "ocr_text",
                            "No OCR text"
                        )
                    )

                st.divider()

                approve_col, reject_col = st.columns(2)

                # ----------------------------------
                # APPROVE
                # ----------------------------------

                with approve_col:

                    if st.button(
                        "✅ Approve",
                        key=f"approve_{voter_id}",
                        use_container_width=True
                    ):

                        voters_col.update_one(
                            {
                                "_id": voter["_id"]
                            },
                            {
                                "$set": {
                                    "is_verified": True,
                                    "rejected": False,
                                    "verified_at":
                                        datetime.now(timezone.utc),
                                    "verified_by":
                                        st.session_state.admin_username
                                }
                            }
                        )

                        st.success(
                            "Voter approved."
                        )

                        st.rerun()

                # ----------------------------------
                # REJECT
                # ----------------------------------

                with reject_col:

                    if st.button(
                        "❌ Reject",
                        key=f"reject_{voter_id}",
                        use_container_width=True
                    ):

                        voters_col.update_one(
                            {
                                "_id": voter["_id"]
                            },
                            {
                                "$set": {
                                    "is_verified": False,
                                    "rejected": True,
                                    "rejected_at":
                                        datetime.now(timezone.utc),
                                    "rejected_by":
                                        st.session_state.admin_username
                                }
                            }
                        )

                        st.warning(
                            "Voter registration rejected."
                        )

                        st.rerun()


# ============================================================
# ELECTION MANAGEMENT
# ============================================================

elif menu == "🗳️ Election Management":

    st.header(
        "🗳️ Election Management"
    )

    # --------------------------------
    # Create Election
    # --------------------------------

    st.subheader(
        "➕ Create New Election"
    )

    with st.form(
        "create_election_form"
    ):

        title = st.text_input(
            "Election Title"
        )

        election_constituency = st.text_input(
            "Election Constituency",
            placeholder="Example: Chennai Central",
            help=(
                "This constituency controls voter eligibility. "
                "A voter can vote only when the voter, election, "
                "and selected candidate all have the same constituency."
            )
        )

        start_date = st.date_input(
            "Start Date"
        )

        start_time = st.time_input(
            "Start Time"
        )

        end_date = st.date_input(
            "End Date"
        )

        end_time = st.time_input(
            "End Time"
        )

        create = st.form_submit_button(
            "Create Election",
            use_container_width=True
        )

    if create:

        if not title.strip():

            st.error(
                "Election title is required."
            )

        elif not election_constituency.strip():

            st.error(
                "Election constituency is required."
            )

        else:

            start_datetime = datetime.combine(
                start_date,
                start_time
            )

            end_datetime = datetime.combine(
                end_date,
                end_time
            )

            if end_datetime <= start_datetime:

                st.error(
                    "End time must be after start time."
                )

            else:

                election = {

                    "title":
                        title.strip(),

                    "constituency":
                        election_constituency.strip(),

                    "start_time":
                        start_datetime,

                    "end_time":
                        end_datetime,

                    "status":
                        "DRAFT",

                    "created_by":
                        st.session_state.admin_username,

                    "created_at":
                        datetime.now(timezone.utc)
                }

                elections_col.insert_one(
                    election
                )

                st.success(
                    "Election created successfully."
                )

                st.rerun()

    st.divider()

    # --------------------------------
    # Existing Elections
    # --------------------------------

    st.subheader(
        "📋 Existing Elections"
    )

    elections = list(
        elections_col.find().sort(
            "created_at",
            -1
        )
    )

    if not elections:

        st.info(
            "No elections available."
        )

    else:

        for election in elections:

            # Automatically repair elections created before the
            # constituency field was introduced. This fixes older
            # elections that already have candidates such as "thondi".
            election = repair_election_constituency(election)

            election_id = str(
                election["_id"]
            )

            with st.expander(
                election.get(
                    "title",
                    "Unnamed Election"
                )
            ):

                current_status = election.get(
                    "status",
                    "DRAFT"
                )

                st.write(
                    f"**Status:** {current_status}"
                )

                current_election_constituency = election.get("constituency", "")

                if current_election_constituency:
                    st.write(
                        f"**Election Constituency:** "
                        f"{current_election_constituency}"
                    )
                else:
                    st.warning(
                        "⚠️ This older election has no constituency. "
                        "Set the constituency before opening polling."
                    )

                with st.expander("⚙️ Set / Update Election Constituency"):

                    updated_constituency = st.text_input(
                        "Election Constituency",
                        value=current_election_constituency,
                        key=f"edit_constituency_{election_id}",
                        placeholder="Example: Chennai Central"
                    )

                    if st.button(
                        "💾 Save Constituency",
                        key=f"save_constituency_{election_id}",
                        use_container_width=True
                    ):

                        if not updated_constituency.strip():
                            st.error("Election constituency is required.")
                        else:
                            elections_col.update_one(
                                {"_id": election["_id"]},
                                {
                                    "$set": {
                                        "constituency": updated_constituency.strip(),
                                        "constituency_updated_at": datetime.now(timezone.utc),
                                        "constituency_updated_by": st.session_state.admin_username
                                    }
                                }
                            )
                            st.success("Election constituency updated.")
                            st.rerun()

                st.write(
                    f"**Start:** "
                    f"{format_datetime(election.get('start_time'))}"
                )

                st.write(
                    f"**End:** "
                    f"{format_datetime(election.get('end_time'))}"
                )

                st.write(
                    f"**Created By:** "
                    f"{election.get('created_by', 'N/A')}"
                )

                col1, col2, col3 = st.columns(3)

                # --------------------------------
                # OPEN
                # --------------------------------

                with col1:

                    if current_status in [
                        "DRAFT",
                        "CLOSED"
                    ]:

                        if st.button(
                            "🟢 Open Polling",
                            key=f"open_{election_id}",
                            use_container_width=True
                        ):

                            election_constituency_value = normalize_constituency(
                                election.get("constituency")
                            )

                            if not election_constituency_value:

                                st.error(
                                    "❌ Cannot open polling. "
                                    "Election constituency is required."
                                )
                                st.stop()

                            election_candidates = get_candidates_for_election(
                                election["_id"]
                            )

                            if not election_candidates:

                                st.error(
                                    "❌ Cannot open polling. "
                                    "Add at least one candidate first."
                                )
                                st.stop()

                            invalid_candidates = [
                                candidate
                                for candidate in election_candidates
                                if not constituencies_match(
                                    candidate.get("constituency"),
                                    election.get("constituency")
                                )
                            ]

                            if invalid_candidates:

                                st.error(
                                    "❌ Cannot open polling. "
                                    "Every candidate constituency must match "
                                    "the election constituency."
                                )
                                st.stop()

                            elections_col.update_one(
                                {
                                    "_id":
                                        election["_id"]
                                },
                                {
                                    "$set": {
                                        "status":
                                            "OPEN",
                                        "opened_at":
                                            datetime.now(timezone.utc),
                                        "opened_by":
                                            st.session_state.admin_username
                                    }
                                }
                            )

                            st.success(
                                "Polling opened."
                            )

                            st.rerun()

                # --------------------------------
                # CLOSE
                # --------------------------------

                with col2:

                    if current_status == "OPEN":

                        if st.button(
                            "🔴 Close Polling",
                            key=f"close_{election_id}",
                            use_container_width=True
                        ):

                            elections_col.update_one(
                                {
                                    "_id":
                                        election["_id"]
                                },
                                {
                                    "$set": {
                                        "status":
                                            "CLOSED",
                                        "closed_at":
                                            datetime.now(timezone.utc),
                                        "closed_by":
                                            st.session_state.admin_username
                                    }
                                }
                            )

                            st.success(
                                "Polling closed."
                            )

                            st.rerun()

                # --------------------------------
                # DECLARE RESULTS
                # --------------------------------

                with col3:

                    if current_status == "CLOSED":

                        if st.button(
                            "🏆 Declare Results",
                            key=f"declare_{election_id}",
                            use_container_width=True
                        ):

                            elections_col.update_one(
                                {
                                    "_id":
                                        election["_id"]
                                },
                                {
                                    "$set": {
                                        "status":
                                            "RESULTS_DECLARED",
                                        "results_declared_at":
                                            datetime.now(timezone.utc),
                                        "results_declared_by":
                                            st.session_state.admin_username
                                    }
                                }
                            )

                            st.success(
                                "Results declared."
                            )

                            st.rerun()


# ============================================================
# CANDIDATE MANAGEMENT
# ============================================================

elif menu == "👥 Candidate Management":

    st.header(
        "👥 Candidate Management"
    )

    elections = list(
        elections_col.find({
            "status": {
                "$in": [
                    "DRAFT",
                    "OPEN"
                ]
            }
        }).sort(
            "created_at",
            -1
        )
    )

    if not elections:

        st.warning(
            "Create an election before adding candidates."
        )

    else:

        election_options = {
            str(e["_id"]):
                e["title"]
            for e in elections
        }

        selected_election_id = st.selectbox(
            "Select Election",
            options=list(
                election_options.keys()
            ),
            format_func=lambda x:
                election_options[x]
        )

        selected_election_oid = safe_object_id(
            selected_election_id
        )

        if selected_election_oid is None:

            st.error(
                "Invalid election ID."
            )

        else:

            selected_election = elections_col.find_one({
                "_id": selected_election_oid
            })

            selected_election = repair_election_constituency(
                selected_election
            )

            if not selected_election:
                st.error("Election not found.")
                st.stop()

            election_constituency = selected_election.get(
                "constituency",
                ""
            )

            if election_constituency:
                st.info(
                    f"🗳️ Election Constituency: **{election_constituency}**"
                )
            else:
                st.error(
                    "❌ This election has no constituency. "
                    "Set it in Election Management before adding candidates."
                )

            st.divider()

            # --------------------------------
            # Add Candidate
            # --------------------------------

            st.subheader(
                "➕ Add Candidate"
            )

            with st.form(
                "candidate_form"
            ):

                candidate_name = st.text_input(
                    "Candidate Name"
                )

                party = st.text_input(
                    "Party"
                )

                constituency = st.text_input(
                    "Candidate Constituency",
                    value=election_constituency,
                    help=(
                        "Must match the selected election constituency. "
                        "Only candidates in the election constituency can appear on the ballot."
                    )
                )

                symbol = st.file_uploader(
                    "Party Symbol",
                    type=[
                        "png",
                        "jpg",
                        "jpeg"
                    ]
                )

                photo = st.file_uploader(
                    "Candidate Photo",
                    type=[
                        "png",
                        "jpg",
                        "jpeg"
                    ],
                    help=(
                        "Shown on the ballot and on the results "
                        "page if this candidate wins."
                    )
                )

                add_candidate = st.form_submit_button(
                    "Add Candidate",
                    use_container_width=True
                )

            if add_candidate:

                if not candidate_name.strip():

                    st.error(
                        "Candidate name is required."
                    )

                elif not constituency.strip():

                    st.error(
                        "Candidate constituency is required."
                    )

                elif not constituencies_match(
                    constituency,
                    election_constituency
                ):

                    st.error(
                        "❌ Candidate constituency does not match the election constituency. "
                        f"Election: {election_constituency or 'Not Set'} | "
                        f"Candidate: {constituency.strip() or 'Not Set'}"
                    )

                else:

                    symbol_file_id = None

                    photo_file_id = None

                    try:

                        if symbol:

                            symbol_file_id = fs.put(
                                symbol.read(),
                                filename=symbol.name,
                                content_type=symbol.type
                            )

                        if photo:

                            photo_file_id = fs.put(
                                photo.read(),
                                filename=photo.name,
                                content_type=photo.type
                            )

                        candidate = {

                            "election_id":
                                selected_election_oid,

                            "name":
                                candidate_name.strip(),

                            "party":
                                party.strip(),

                            "constituency":
                                constituency.strip(),

                            "email":
                                None,

                            "phone":
                                None,

                            "manifesto":
                                "",

                            "symbol_file":
                                symbol_file_id,

                            "photo_file":
                                photo_file_id,

                            # Candidates added directly by an officer
                            # are trusted immediately — no review step.
                            "status":
                                "APPROVED",

                            "applied_at":
                                datetime.now(timezone.utc),

                            "created_at":
                                datetime.now(timezone.utc),

                            "created_by":
                                st.session_state.admin_username,

                            "reviewed_by":
                                st.session_state.admin_username,

                            "reviewed_at":
                                datetime.now(timezone.utc),
                        }

                        candidates_col.insert_one(
                            candidate
                        )

                        st.success(
                            "Candidate added successfully."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            "Failed to add candidate."
                        )

                        st.exception(e)

            st.divider()

            # --------------------------------
            # Candidate list
            # --------------------------------

            st.subheader(
                "📋 Candidates"
            )

            candidates = get_candidates_for_election(
                selected_election_oid
            )

            if not candidates:

                st.info(
                    "No candidates added."
                )

            else:

                candidate_data = []

                for candidate in candidates:

                    candidate_data.append({

                        "ID":
                            str(candidate["_id"]),

                        "Name":
                            candidate.get(
                                "name",
                                ""
                            ),

                        "Party":
                            candidate.get(
                                "party",
                                ""
                            ),

                        "Constituency":
                            candidate.get(
                                "constituency",
                                ""
                            ),

                        "Constituency Match":
                            (
                                "YES"
                                if constituencies_match(
                                    candidate.get("constituency"),
                                    election_constituency
                                )
                                else "NO"
                            ),

                        "Status":
                            candidate.get(
                                "status",
                                "APPROVED"
                            ),

                        "Created":
                            format_datetime(
                                candidate.get(
                                    "created_at"
                                )
                                or candidate.get(
                                    "applied_at"
                                )
                            )
                    })

                df = pd.DataFrame(
                    candidate_data
                )

                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

                # --------------------------------
                # Candidate details
                # --------------------------------

                st.divider()

                st.subheader(
                    "🔎 Candidate Details"
                )

                candidate_ids = {
                    str(candidate["_id"]):
                        candidate
                    for candidate in candidates
                }

                selected_candidate_id = st.selectbox(
                    "Select Candidate",
                    options=list(
                        candidate_ids.keys()
                    ),
                    format_func=lambda x:
                        candidate_ids[x].get(
                            "name",
                            "Unknown"
                        )
                )

                selected_candidate = candidate_ids[
                    selected_candidate_id
                ]

                d1, d2 = st.columns(2)

                with d1:

                    st.write(
                        f"**Name:** "
                        f"{selected_candidate.get('name', '')}"
                    )

                    st.write(
                        f"**Party:** "
                        f"{selected_candidate.get('party', '')}"
                    )

                    st.write(
                        f"**Election Constituency:** "
                        f"{election_constituency or 'Not Set'}"
                    )

                    st.write(
                        f"**Candidate Constituency:** "
                        f"{selected_candidate.get('constituency', '')}"
                    )

                    if constituencies_match(
                        selected_candidate.get("constituency"),
                        election_constituency
                    ):
                        st.success("✅ Constituency Match")
                    else:
                        st.error("❌ Constituency Mismatch")

                with d2:

                    symbol_id = selected_candidate.get(
                        "symbol_file"
                    )

                    if symbol_id:

                        try:

                            symbol_data = fs.get(
                                symbol_id
                            ).read()

                            st.image(
                                symbol_data,
                                caption="Party Symbol",
                                width=180
                            )

                        except Exception:
                            st.warning(
                                "Unable to load party symbol."
                            )

                    else:

                        st.info(
                            "No party symbol uploaded."
                        )

                    photo_id = selected_candidate.get(
                        "photo_file"
                    )

                    if photo_id:

                        try:

                            photo_data = fs.get(
                                photo_id
                            ).read()

                            st.image(
                                photo_data,
                                caption="Candidate Photo",
                                width=180
                            )

                        except Exception:
                            st.warning(
                                "Unable to load candidate photo."
                            )

                    else:

                        st.info(
                            "No candidate photo uploaded."
                        )


# ============================================================
# AUTHENTICATION LOGS
# ============================================================

elif menu == "🔐 Authentication Logs":

    st.header(
        "🔐 Authentication Monitoring"
    )

    total_attempts = auth_logs_col.count_documents({})

    successful = auth_logs_col.count_documents({
        "status": "SUCCESS"
    })

    failed = auth_logs_col.count_documents({
        "status": "FAIL"
    })

    spoof = auth_logs_col.count_documents({
        "status": "SPOOF_DETECTED"
    })

    locked = auth_logs_col.count_documents({
        "status": "LOCKED"
    })

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Total",
            total_attempts
        )

    with col2:
        st.metric(
            "Success",
            successful
        )

    with col3:
        st.metric(
            "Failed",
            failed
        )

    with col4:
        st.metric(
            "Spoof",
            spoof
        )

    with col5:
        st.metric(
            "Locked",
            locked
        )

    st.divider()

    # --------------------------------
    # Log filters
    # --------------------------------

    filter_status = st.selectbox(
        "Filter Status",
        [
            "ALL",
            "SUCCESS",
            "FAIL",
            "SPOOF_DETECTED",
            "LOCKED",
            "LOGOUT"
        ]
    )

    if filter_status == "ALL":

        logs = list(
            auth_logs_col.find().sort(
                "attempt_time",
                -1
            ).limit(100)
        )

    else:

        logs = list(
            auth_logs_col.find({
                "status":
                    filter_status
            }).sort(
                "attempt_time",
                -1
            ).limit(100)
        )

    if logs:

        log_data = []

        for log in logs:

            similarity = log.get(
                "similarity"
            )

            if isinstance(
                similarity,
                (int, float)
            ):

                similarity_display = (
                    f"{similarity:.4f}"
                )

            else:

                similarity_display = (
                    similarity
                    if similarity is not None
                    else ""
                )

            log_data.append({

                "Username":
                    log.get(
                        "username",
                        ""
                    ),

                "Voter ID":
                    log.get(
                        "voter_id",
                        ""
                    ),

                "Time":
                    format_datetime(
                        log.get(
                            "attempt_time"
                        )
                    ),

                "Similarity":
                    similarity_display,

                "Liveness":
                    log.get(
                        "liveness_label",
                        ""
                    ),

                "Status":
                    log.get(
                        "status",
                        ""
                    ),

                "Auth Type":
                    log.get(
                        "auth_type",
                        ""
                    ),

                "IP":
                    log.get(
                        "ip_address",
                        ""
                    )
            })

        df = pd.DataFrame(
            log_data
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No authentication attempts recorded."
        )


# ============================================================
# RESULTS
# ============================================================

elif menu == "🏆 Results":

    st.header(
        "🏆 Election Results"
    )

    elections = list(
        elections_col.find({
            "status":
                "RESULTS_DECLARED"
        }).sort(
            "results_declared_at",
            -1
        )
    )

    if not elections:

        st.info(
            "Results are not available yet."
        )

    else:

        election_map = {
            str(e["_id"]):
                e["title"]
            for e in elections
        }

        selected_id = st.selectbox(
            "Select Election",
            options=list(
                election_map.keys()
            ),
            format_func=lambda x:
                election_map[x]
        )

        selected_election_oid = safe_object_id(
            selected_id
        )

        if selected_election_oid is None:

            st.error(
                "Invalid election ID."
            )

        else:

            selected_election = elections_col.find_one({
                "_id":
                    selected_election_oid
            })

            selected_election = repair_election_constituency(
                selected_election
            )

            if selected_election:

                st.write(
                    f"**Election:** "
                    f"{selected_election.get('title', '')}"
                )

                st.write(
                    f"**Status:** "
                    f"{selected_election.get('status', '')}"
                )

                st.write(
                    f"**Election Constituency:** "
                    f"{selected_election.get('constituency', 'N/A')}"
                )

                st.write(
                    f"**Declared:** "
                    f"{format_datetime(selected_election.get('results_declared_at'))}"
                )

                st.divider()

            # --------------------------------
            # Tally votes
            # --------------------------------

            pipeline = [

                {
                    "$match": {
                        "election_id":
                            selected_election_oid
                    }
                },

                {
                    "$group": {

                        "_id":
                            "$candidate_id",

                        "total": {
                            "$sum": 1
                        }
                    }
                },

                {
                    "$lookup": {

                        "from":
                            "candidates",

                        "localField":
                            "_id",

                        "foreignField":
                            "_id",

                        "as":
                            "candidate"
                    }
                },

                {
                    "$sort": {
                        "total": -1
                    }
                }
            ]

            results = list(
                votes_col.aggregate(
                    pipeline
                )
            )

            if not results:

                st.info(
                    "No votes have been recorded."
                )

            else:

                result_data = []

                for result in results:

                    candidate_list = result.get(
                        "candidate",
                        []
                    )

                    if not candidate_list:
                        continue

                    candidate = candidate_list[0]

                    # Results are also restricted to the election constituency.
                    if not constituencies_match(
                        candidate.get("constituency"),
                        selected_election.get("constituency")
                    ):
                        continue

                    result_data.append({

                        "Candidate":
                            candidate.get(
                                "name",
                                ""
                            ),

                        "Party":
                            candidate.get(
                                "party",
                                ""
                            ),

                        "Constituency":
                            candidate.get(
                                "constituency",
                                ""
                            ),

                        "Votes":
                            result.get(
                                "total",
                                0
                            )
                    })

                if result_data:

                    df = pd.DataFrame(
                        result_data
                    )

                    # --------------------------------
                    # Vote count
                    # --------------------------------

                    st.subheader(
                        "📊 Vote Count"
                    )

                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True
                    )

                    # --------------------------------
                    # Vote distribution
                    # --------------------------------

                    st.subheader(
                        "📈 Vote Distribution"
                    )

                    fig = px.bar(
                        df,
                        x="Candidate",
                        y="Votes",
                        title="Candidate-wise Vote Count",
                        text="Votes"
                    )

                    fig.update_traces(
                        textposition="outside"
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

                    # --------------------------------
                    # Vote percentage
                    # --------------------------------

                    st.subheader(
                        "🥧 Vote Percentage"
                    )

                    fig2 = px.pie(
                        df,
                        names="Candidate",
                        values="Votes",
                        title="Vote Distribution"
                    )

                    st.plotly_chart(
                        fig2,
                        use_container_width=True
                    )

                    # --------------------------------
                    # Download CSV
                    # --------------------------------

                    csv = df.to_csv(
                        index=False
                    )

                    st.download_button(
                        label="⬇️ Download Results CSV",
                        data=csv,
                        file_name="election_results.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                else:

                    st.info(
                        "No candidate records were found "
                        "for the recorded votes."
                    )