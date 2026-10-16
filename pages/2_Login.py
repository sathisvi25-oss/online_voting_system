import streamlit as st
import bcrypt

from services.db import get_database, get_collections
from services.auth import log_auth_attempt
from utils.theme import apply_theme, page_header


st.set_page_config(
    page_title="Voter Login",
    page_icon="🔐"
)

apply_theme()

page_header(
    "Voter Login",
    subtitle="Sign in with your Voter ID and password to continue to face "
             "verification and voting.",
    kicker="Step 1 of 2",
    icon="🔐"
)

# If already logged in, just send them straight to voting.
if st.session_state.get("logged_in", False):

    st.info("You are already logged in.")

    if st.button("Go to Vote", use_container_width=True):
        st.switch_page("pages/3_Vote.py")

    st.stop()


left, mid, right = st.columns([1, 2, 1])

with mid:

    st.markdown(
"""<div style="text-align:center; margin-bottom:0.9rem;">
<span class="vs-pill">Welcome back</span>
</div>""",
        unsafe_allow_html=True
    )

    with st.form("login_form"):

        voter_id_input = st.text_input("Voter ID", placeholder="e.g. TN-0042")

        password = st.text_input(
            "Password", type="password", placeholder="••••••••"
        )

        submitted = st.form_submit_button(
            "Login", use_container_width=True
        )

    st.markdown(
"""<p style="text-align:center; color:#5B6472; font-size:0.88rem;">
Not registered yet? Go to <b>Register</b> from the sidebar.
</p>""",
        unsafe_allow_html=True
    )

if submitted:

    voter_id = voter_id_input.strip()

    if not voter_id or not password:
        st.warning("Enter both Voter ID and Password.")
        st.stop()

    try:
        db = get_database()
        collections = get_collections(db)
    except Exception as e:
        st.error("Database connection failed.")
        st.exception(e)
        st.stop()

    voter = collections["voters"].find_one({
        "voter_id": voter_id
    })

    if not voter:

        log_auth_attempt(
            collections, voter_id, "FAIL", "VOTER_LOGIN"
        )

        st.error("Voter not found.")
        st.stop()

    if voter.get("rejected", False):

        log_auth_attempt(
            collections, voter_id, "FAIL", "VOTER_LOGIN"
        )

        st.error(
            "Your registration was rejected. "
            "Please contact the election office."
        )
        st.stop()

    if not voter.get("is_verified", False):

        log_auth_attempt(
            collections, voter_id, "FAIL", "VOTER_LOGIN"
        )

        st.error(
            "Your registration is not approved yet."
        )
        st.stop()

    password_hash = voter.get("password_hash")

    if not password_hash:
        st.error("This voter account has no password configured.")
        st.stop()

    if isinstance(password_hash, str):
        password_hash = password_hash.encode("utf-8")

    password_ok = bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash
    )

    if password_ok:

        log_auth_attempt(
            collections, voter_id, "SUCCESS", "VOTER_LOGIN"
        )

        st.session_state.logged_in = True
        st.session_state.voter_id = voter_id

        st.success("Login successful.")

        st.switch_page(
            "pages/3_Vote.py"
        )

    else:

        log_auth_attempt(
            collections, voter_id, "FAIL", "VOTER_LOGIN"
        )

        st.error(
            "Invalid credentials."
        )
