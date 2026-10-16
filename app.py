import streamlit as st

from utils.theme import apply_theme, page_header, feature_card, stepper

st.set_page_config(
    page_title="Online Voting System",
    page_icon="🗳️",
    layout="wide"
)

apply_theme()

# -----------------------------
# Session initialization
# -----------------------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "voter_id" not in st.session_state:
    st.session_state.voter_id = None

if "face_verified" not in st.session_state:
    st.session_state.face_verified = False

if "vote_cast" not in st.session_state:
    st.session_state.vote_cast = False


# -----------------------------
# Hero
# -----------------------------

page_header(
    "Vote with confidence, from anywhere",
    subtitle="Your ID is checked with OCR, your face is verified against it, "
             "and your ballot is recorded once — with a receipt to prove it.",
    kicker="Secure Digital Elections",
    icon="🗳️"
)

# -----------------------------
# Trust strip
# -----------------------------

t1, t2, t3, t4 = st.columns(4)

with t1:
    st.metric("Identity checks", "3", "OCR + 2 face scans")

with t2:
    st.metric("Ballots per voter", "1", "enforced in the database")

with t3:
    st.metric("Officer review", "Required", "before any account is active")

with t4:
    st.metric("Results", "Published", "once officially declared")

st.markdown("")

# -----------------------------
# Where to start
# -----------------------------

st.markdown("#### Where would you like to start?")

col1, col2, col3 = st.columns(3)

with col1:
    feature_card(
        "📝",
        "Register",
        "Upload an ID card, verify it with OCR, and enroll your face — "
        "reviewed by an election officer before approval."
    )
    if st.button("Start Registration", use_container_width=True):
        st.switch_page("pages/1_Register.py")

with col2:
    feature_card(
        "🔐",
        "Login &amp; Vote",
        "Sign in with your Voter ID, confirm your identity with a live "
        "face capture, then cast one secure, receipted ballot."
    )
    if st.button("Go to Login", use_container_width=True):
        st.switch_page("pages/2_Login.py")

with col3:
    feature_card(
        "📊",
        "Results",
        "Once an election officer declares results, the tally and vote "
        "distribution are published here for anyone to see."
    )
    if st.button("View Results", use_container_width=True):
        st.switch_page("pages/4_Results.py")

st.markdown("")
st.divider()

# -----------------------------
# How it works
# -----------------------------

st.markdown("#### How it works")

stepper([
    ("Register", "Upload your ID, pass OCR and face checks, and submit for review."),
    ("Get approved", "An election officer verifies your details before your account opens."),
    ("Log in", "Sign in with your Voter ID and password."),
    ("Verify", "A live camera capture is matched against your enrolled face."),
    ("Vote", "Choose a candidate or NOTA and receive a receipt ID."),
])

st.markdown("")

st.markdown(
"""<div class="vs-card">
<h4 style="margin-bottom:0.3rem;">Built on independent checks, not trust</h4>
<p>
Every registration is checked against the ID document you upload before
a human ever sees it, and every vote is tied to a face verified live at
the ballot — so the results published on this site reflect real,
one-person-one-vote turnout.
</p>
</div>""",
    unsafe_allow_html=True
)

st.markdown(
"""<div class="vs-footnote">
⚠️ Prototype / educational election system — do not use this
implementation as-is for a public election.
</div>""",
    unsafe_allow_html=True
)
