import io
from datetime import date, datetime, timezone

import bcrypt
import streamlit as st

from models.loader import load_ocr_model

from services.ocr import extract_text

from services.face import (
    detect_faces,
    crop_face,
    draw_face_boxes,
    generate_embedding,
    face_to_png_bytes,
    image_to_pil
)

from services.face_match import (
    verify_faces
)

from services.db import (
    get_database,
    get_collections
)

from utils.theme import apply_theme, page_header

from utils.text_utils import (
    verify_registration_data
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Voter Registration",
    page_icon="📝",
    layout="wide"
)

apply_theme()


# ============================================================
# PAGE TITLE
# ============================================================

page_header(
    "Voter Registration",
    subtitle="OCR document check, YOLOv8 face detection and live face "
             "matching — reviewed by an election officer before approval.",
    kicker="New voter",
    icon="📝"
)


# ============================================================
# INITIAL SESSION STATE
# ============================================================

if "id_verified" not in st.session_state:
    st.session_state.id_verified = False

if "face_matched" not in st.session_state:
    st.session_state.face_matched = False

if "ocr_text" not in st.session_state:
    st.session_state.ocr_text = ""

if "ocr_score" not in st.session_state:
    st.session_state.ocr_score = 0.0

if "id_face_bytes" not in st.session_state:
    st.session_state.id_face_bytes = None

if "live_face_bytes" not in st.session_state:
    st.session_state.live_face_bytes = None

if "face_similarity" not in st.session_state:
    st.session_state.face_similarity = 0.0


# ============================================================
# REGISTRATION FORM
# ============================================================

with st.form(
    "registration_form"
):

    st.subheader(
        "👤 Registration Details"
    )

    # --------------------------------------------------------
    # Name
    # --------------------------------------------------------

    name = st.text_input(
        "Full Name"
    )

    # --------------------------------------------------------
    # Voter ID
    # --------------------------------------------------------

    voter_id = st.text_input(
        "Voter ID"
    )

    # --------------------------------------------------------
    # Email
    # --------------------------------------------------------

    email = st.text_input(
        "Email"
    )

    # --------------------------------------------------------
    # Phone
    # --------------------------------------------------------

    phone = st.text_input(
        "Phone Number"
    )

    # --------------------------------------------------------
    # DOB
    # 1960 - 2050
    # --------------------------------------------------------

    dob = st.date_input(
        "Date of Birth",
        min_value=date(
            1960,
            1,
            1
        ),
        max_value=date(
            2050,
            12,
            31
        ),
        value=date(
            2004,
            2,
            18
        )
    )

    # --------------------------------------------------------
    # Constituency
    # --------------------------------------------------------

    constituency = st.text_input(
        "Constituency"
    )

    # --------------------------------------------------------
    # Password
    # --------------------------------------------------------

    password = st.text_input(
        "Password",
        type="password"
    )

    # --------------------------------------------------------
    # ID Card
    # --------------------------------------------------------

    id_card = st.file_uploader(
        "Upload ID Card / Photo",
        type=[
            "jpg",
            "jpeg",
            "png"
        ]
    )

    # --------------------------------------------------------
    # Start verification
    # --------------------------------------------------------

    submitted = st.form_submit_button(
        "🔍 Verify ID + Detect Face",
        use_container_width=True
    )


# ============================================================
# STEP 1 — FORM VALIDATION + OCR + ID FACE
# ============================================================

if submitted:

    # ========================================================
    # RESET PREVIOUS VERIFICATION
    # ========================================================

    st.session_state.id_verified = False
    st.session_state.face_matched = False
    st.session_state.ocr_text = ""
    st.session_state.ocr_score = 0.0
    st.session_state.id_face_bytes = None
    st.session_state.live_face_bytes = None
    st.session_state.face_similarity = 0.0


    # ========================================================
    # REQUIRED FIELDS
    # ========================================================

    required_fields = {

        "Full Name":
            name.strip(),

        "Voter ID":
            voter_id.strip(),

        "Email":
            email.strip(),

        "Phone Number":
            phone.strip(),

        "Constituency":
            constituency.strip(),

        "Password":
            password
    }


    missing_fields = [
        label
        for label, value
        in required_fields.items()
        if not value
    ]


    if missing_fields:

        st.error(
            "Please complete: "
            +
            ", ".join(
                missing_fields
            )
            +
            "."
        )

        st.stop()


    # ========================================================
    # PASSWORD CHECK
    # ========================================================

    if len(password) < 8:

        st.error(
            "Password must be at least 8 characters long."
        )

        st.stop()


    # ========================================================
    # DUPLICATE CHECK (before running OCR / face pipeline)
    # ========================================================

    try:

        db = get_database()
        collections = get_collections(db)

        existing = collections["voters"].find_one({
            "$or": [
                {"voter_id": voter_id.strip()},
                {"email": email.strip().lower()}
            ]
        })

    except Exception as e:

        st.error("Database connection failed.")
        st.exception(e)
        st.stop()

    if existing:

        st.error(
            "A voter with this Voter ID or Email "
            "is already registered."
        )

        st.stop()


    # ========================================================
    # IMAGE CHECK
    # ========================================================

    if id_card is None:

        st.error(
            "Please upload your ID card/photo."
        )

        st.stop()


    # ========================================================
    # GET IMAGE BYTES
    # ========================================================

    try:

        image_bytes = id_card.getvalue()

    except Exception as e:

        st.error(
            "Unable to read the uploaded image."
        )

        st.exception(e)

        st.stop()


    if not image_bytes:

        st.error(
            "Uploaded image is empty."
        )

        st.stop()


    # ========================================================
    # ORIGINAL ID PHOTO
    # ========================================================

    st.divider()

    st.subheader(
        "🪪 Uploaded ID Card / Photo"
    )

    st.image(
        image_bytes,
        caption="Uploaded ID Card",
        use_container_width=True
    )


    # ========================================================
    # STEP 1 — OCR
    # ========================================================

    st.divider()

    st.subheader(
        "🔎 Step 1 — OCR"
    )

    with st.spinner(
        "Detecting and reading all text from ID card..."
    ):

        try:

            processor, model = (
                load_ocr_model()
            )

            extracted_text = extract_text(
                io.BytesIO(
                    image_bytes
                ),
                processor,
                model
            )

        except Exception as e:

            st.error(
                "OCR failed."
            )

            st.exception(e)

            st.stop()


    # ========================================================
    # OCR RESULT
    # ========================================================

    if not extracted_text:

        st.error(
            "❌ No readable text was detected."
        )

        st.stop()


    st.session_state.ocr_text = (
        extracted_text
    )


    st.text_area(
        "All Detected OCR Text",
        extracted_text,
        height=250
    )


    # ========================================================
    # STEP 2 — VERIFY NAME + VOTER ID
    # ========================================================

    st.subheader(
        "✅ Step 2 — Registration Data Verification"
    )

    st.caption(
        "Only the entered Full Name and Voter ID "
        "are compared with the OCR text."
    )


    with st.spinner(
        "Checking Name and Voter ID..."
    ):

        try:

            verification = (
                verify_registration_data(
                    name=name,
                    voter_id=voter_id,
                    ocr_text=extracted_text,
                    threshold=0.85
                )
            )

        except Exception as e:

            st.error(
                "OCR verification failed."
            )

            st.exception(e)

            st.stop()


    name_score = (
        verification[
            "name_score"
        ]
    )

    voter_id_score = (
        verification[
            "voter_id_score"
        ]
    )

    name_verified = (
        verification[
            "name_verified"
        ]
    )

    voter_id_verified = (
        verification[
            "voter_id_verified"
        ]
    )

    id_verified = (
        verification[
            "verified"
        ]
    )


    # ========================================================
    # DISPLAY OCR SCORES
    # ========================================================

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Name Similarity",
            f"{name_score * 100:.2f}%"
        )

    with col2:

        st.metric(
            "Voter ID Similarity",
            f"{voter_id_score * 100:.2f}%"
        )


    # ========================================================
    # NAME RESULT
    # ========================================================

    if name_verified:

        st.success(
            "✅ Full Name matched with OCR."
        )

        st.caption(
            "OCR match: "
            +
            str(
                verification[
                    "name_match"
                ]
            )
        )

    else:

        st.error(
            "❌ Full Name does not match the OCR text."
        )


    # ========================================================
    # VOTER ID RESULT
    # ========================================================

    if voter_id_verified:

        st.success(
            "✅ Voter ID matched with OCR."
        )

        st.caption(
            "OCR match: "
            +
            str(
                verification[
                    "voter_id_match"
                ]
            )
        )

    else:

        st.error(
            "❌ Voter ID does not match the OCR text."
        )


    # ========================================================
    # STOP IF OCR VERIFICATION FAILED
    # ========================================================

    if not id_verified:

        st.error(
            "❌ ID verification failed."
        )

        st.warning(
            "Both Full Name and Voter ID must match "
            "the detected OCR text."
        )

        st.stop()


    st.success(
        "✅ Full Name and Voter ID successfully verified."
    )


    # ========================================================
    # STORE OCR SCORE
    # ========================================================

    st.session_state.ocr_score = min(
        name_score,
        voter_id_score
    )


    # ========================================================
    # STEP 3 — YOLOv8 FACE DETECTION
    # ========================================================

    st.divider()

    st.subheader(
        "👤 Step 3 — YOLOv8 ID Photo Face Detection"
    )

    with st.spinner(
        "Detecting face using YOLOv8..."
    ):

        try:

            id_faces = detect_faces(
                io.BytesIO(
                    image_bytes
                )
            )

        except Exception as e:

            st.error(
                "YOLOv8 face detection failed."
            )

            st.exception(e)

            st.stop()


    st.write(
        f"Faces detected in ID photo: **{len(id_faces)}**"
    )


    # ========================================================
    # NO FACE
    # ========================================================

    if len(id_faces) == 0:

        st.error(
            "❌ No face detected in the ID photo."
        )

        st.stop()


    # ========================================================
    # MULTIPLE FACES
    # ========================================================

    if len(id_faces) > 1:

        st.error(
            "❌ Multiple faces detected."
        )

        st.warning(
            "Please upload an image containing only one face."
        )

        annotated = draw_face_boxes(
            io.BytesIO(
                image_bytes
            ),
            id_faces
        )

        st.image(
            annotated,
            caption="YOLOv8 Face Detection",
            use_container_width=True
        )

        st.stop()


    # ========================================================
    # DRAW ID FACE
    # ========================================================

    annotated_id = draw_face_boxes(
        io.BytesIO(
            image_bytes
        ),
        id_faces
    )

    st.image(
        annotated_id,
        caption="YOLOv8 ID Photo Face Detection",
        use_container_width=True
    )


    # ========================================================
    # CROP ID FACE
    # ========================================================

    id_face_box = (
        id_faces[0][
            "box"
        ]
    )


    id_face = crop_face(
        io.BytesIO(
            image_bytes
        ),
        id_face_box
    )


    if id_face is None:

        st.error(
            "❌ Could not crop the ID face."
        )

        st.stop()


    # ========================================================
    # DISPLAY ID FACE
    # ========================================================

    st.success(
        "✅ One face detected in ID photo."
    )

    st.image(
        id_face,
        caption="Registered ID Face",
        width=250
    )


    # ========================================================
    # SAVE ID FACE
    # ========================================================

    st.session_state.id_face_bytes = (
        face_to_png_bytes(id_face)
    )

    st.session_state.id_verified = True


    # ========================================================
    # SAVE REGISTRATION DETAILS
    # ========================================================

    st.session_state.registration_data = {

        "name":
            name.strip(),

        "voter_id":
            voter_id.strip(),

        "email":
            email.strip().lower(),

        "phone":
            phone.strip(),

        "dob":
            dob,

        "constituency":
            constituency.strip(),

        "password":
            password,

        "ocr_text":
            extracted_text,

        "ocr_confidence":
            min(
                name_score,
                voter_id_score
            ),

        "face_image":
            st.session_state.id_face_bytes,

        "face_box":
            id_face_box,

        "face_verified":
            False
    }


    st.success(
        "✅ ID verification completed."
    )


# ============================================================
# STEP 4 — LIVE CAMERA
# ============================================================

if st.session_state.id_verified:

    st.divider()

    st.subheader(
        "📷 Step 4 — Live Face Capture"
    )

    st.write(
        "Look directly at the camera and capture "
        "a clear photo of your face."
    )


    # ========================================================
    # SHOW REGISTERED FACE
    # ========================================================

    left, right = st.columns(2)

    with left:

        if st.session_state.id_face_bytes:

            st.image(
                st.session_state.id_face_bytes,
                caption="ID Card Face",
                width=250
            )


    # ========================================================
    # CAMERA
    # ========================================================

    with right:

        live_photo = st.camera_input(
            "Capture Live Face"
        )


    # ========================================================
    # LIVE PHOTO RECEIVED
    # ========================================================

    if live_photo is not None:

        live_bytes = (
            live_photo.getvalue()
        )


        # ====================================================
        # STEP 5 — YOLOv8 LIVE FACE
        # ====================================================

        st.divider()

        st.subheader(
            "👤 Step 5 — YOLOv8 Live Face Detection"
        )


        with st.spinner(
            "Detecting face in live photo..."
        ):

            try:

                live_faces = detect_faces(
                    io.BytesIO(
                        live_bytes
                    )
                )

            except Exception as e:

                st.error(
                    "Live face detection failed."
                )

                st.exception(e)

                st.stop()


        st.write(
            f"Faces detected in live photo: "
            f"**{len(live_faces)}**"
        )


        # ====================================================
        # NO LIVE FACE
        # ====================================================

        if len(live_faces) == 0:

            st.error(
                "❌ No face detected in live photo."
            )

            st.stop()


        # ====================================================
        # MULTIPLE LIVE FACES
        # ====================================================

        if len(live_faces) > 1:

            st.error(
                "❌ Multiple faces detected."
            )

            st.warning(
                "Only one person should be visible."
            )

            st.image(
                draw_face_boxes(
                    io.BytesIO(live_bytes),
                    live_faces
                ),
                caption="YOLOv8 Live Face Detection",
                use_container_width=True
            )

            st.stop()


        # ====================================================
        # DISPLAY LIVE YOLO
        # ====================================================

        annotated_live = draw_face_boxes(
            io.BytesIO(live_bytes),
            live_faces
        )


        st.image(
            annotated_live,
            caption="YOLOv8 Live Face Detection",
            use_container_width=True
        )


        # ====================================================
        # CROP LIVE FACE
        # ====================================================

        live_face_box = (
            live_faces[0][
                "box"
            ]
        )


        live_face = crop_face(
            io.BytesIO(live_bytes),
            live_face_box
        )


        if live_face is None:

            st.error(
                "❌ Could not crop the live face."
            )

            st.stop()


        # ====================================================
        # DISPLAY LIVE FACE
        # ====================================================

        st.image(
            live_face,
            caption="Live Camera Face",
            width=250
        )


        # ====================================================
        # STEP 6 — FACE MATCHING
        # ====================================================

        st.divider()

        st.subheader(
            "🔐 Step 6 — ID Face vs Live Face Matching"
        )


        # ====================================================
        # LOAD REGISTERED FACE
        # ====================================================

        registered_face = None

        if st.session_state.id_face_bytes:

            from PIL import Image

            registered_face = (
                Image.open(
                    io.BytesIO(
                        st.session_state.id_face_bytes
                    )
                )
                .convert("RGB")
            )


        if registered_face is None:

            st.error(
                "Registered face is missing."
            )

            st.stop()


        # ====================================================
        # MATCH
        # ====================================================

        with st.spinner(
            "Comparing ID-card face and live camera face..."
        ):

            try:

                matched, similarity = (
                    verify_faces(
                        registered_face,
                        image_to_pil(live_face),
                        threshold=0.75
                    )
                )

            except Exception as e:

                st.error(
                    "Face matching failed."
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


        # ====================================================
        # MATCH RESULT
        # ========================================================

        if matched:

            st.success(
                "✅ FACE MATCHED SUCCESSFULLY"
            )

            st.write(
                "The ID-card face and live-camera face "
                "passed the configured similarity threshold."
            )


            # ------------------------------------------------
            # Convert live face to bytes
            # ------------------------------------------------

            live_face_bytes = (
                face_to_png_bytes(live_face)
            )


            # ------------------------------------------------
            # Save matching state
            # ------------------------------------------------

            st.session_state.live_face_bytes = (
                live_face_bytes
            )

            st.session_state.face_similarity = (
                similarity
            )

            st.session_state.face_matched = True


            # ------------------------------------------------
            # Update registration data
            # ------------------------------------------------

            if "registration_data" in st.session_state:

                st.session_state.registration_data[
                    "live_face_image"
                ] = live_face_bytes

                st.session_state.registration_data[
                    "face_similarity"
                ] = similarity

                st.session_state.registration_data[
                    "face_verified"
                ] = True


        else:

            st.session_state.face_matched = False

            st.error(
                "❌ FACE NOT MATCHED"
            )

            st.warning(
                "The captured live face did not meet "
                "the configured similarity threshold."
            )


# ============================================================
# FINAL VERIFICATION SUMMARY
# ============================================================

if (
    st.session_state.id_verified
    and
    st.session_state.face_matched
):

    st.divider()

    st.subheader(
        "✅ Verification Summary"
    )


    col1, col2, col3 = st.columns(3)


    with col1:

        st.success(
            "OCR Verified"
        )

        st.caption(
            "Name + Voter ID"
        )


    with col2:

        st.success(
            "ID Face Verified"
        )

        st.caption(
            "YOLOv8"
        )


    with col3:

        st.success(
            "Live Face Matched"
        )

        st.caption(
            f"{st.session_state.face_similarity * 100:.2f}%"
        )


    # ========================================================
    # FINAL SCORES
    # ========================================================

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "OCR Verification",
            f"{st.session_state.ocr_score * 100:.2f}%"
        )

    with col2:

        st.metric(
            "Face Similarity",
            f"{st.session_state.face_similarity * 100:.2f}%"
        )


    # ========================================================
    # COMPLETE REGISTRATION
    # ========================================================

    st.success(
        "🎉 Identity verification completed."
    )

    st.info(
        "Name + Voter ID OCR verification and "
        "ID-photo vs live-face verification are complete."
    )


    # ========================================================
    # FINAL BUTTON
    # ========================================================

    if st.button(
        "✅ Complete Registration",
        use_container_width=True
    ):

        reg_data = st.session_state.get(
            "registration_data"
        )

        if not reg_data:

            st.error(
                "Registration data is missing. "
                "Please restart the registration process."
            )

            st.stop()

        # ----------------------------------------------------
        # Connect to database
        # ----------------------------------------------------

        try:

            db = get_database()
            collections = get_collections(db)

        except Exception as e:

            st.error("Database connection failed.")
            st.exception(e)
            st.stop()

        # ----------------------------------------------------
        # Re-check duplicates right before writing
        # (covers the case where someone else registered the
        # same voter_id/email while this session was verifying)
        # ----------------------------------------------------

        existing = collections["voters"].find_one({
            "$or": [
                {"voter_id": reg_data["voter_id"]},
                {"email": reg_data["email"]}
            ]
        })

        if existing:

            st.error(
                "A voter with this Voter ID or Email "
                "is already registered."
            )

            st.stop()

        # ----------------------------------------------------
        # Hash the password — never store it in plain text
        # ----------------------------------------------------

        password_hash = bcrypt.hashpw(
            reg_data["password"].encode("utf-8"),
            bcrypt.gensalt()
        )

        # ----------------------------------------------------
        # Face embedding used for authentication at vote time.
        # Generated from the live camera capture (not the ID
        # photo) so it is compared against future live captures
        # of the same kind.
        # ----------------------------------------------------

        face_embedding = None

        live_face_bytes = st.session_state.get(
            "live_face_bytes"
        )

        if live_face_bytes:

            try:

                embedding = generate_embedding(
                    io.BytesIO(live_face_bytes)
                )

                face_embedding = embedding.tolist()

            except Exception as e:

                st.error(
                    "Could not generate the face embedding "
                    "needed for future voting."
                )

                st.exception(e)

                st.stop()

        if face_embedding is None:

            st.error(
                "Face verification data is missing. "
                "Please complete Step 4/5/6 again."
            )

            st.stop()

        # ----------------------------------------------------
        # Convert DOB (a `date`) to a `datetime` — MongoDB /
        # BSON cannot store bare `date` objects.
        # ----------------------------------------------------

        dob_value = reg_data["dob"]

        if isinstance(dob_value, date) and not isinstance(
            dob_value, datetime
        ):
            dob_value = datetime(
                dob_value.year,
                dob_value.month,
                dob_value.day
            )

        # ----------------------------------------------------
        # Build the voter document
        # ----------------------------------------------------

        voter_document = {

            "name": reg_data["name"],
            "voter_id": reg_data["voter_id"],
            "email": reg_data["email"],
            "phone": reg_data["phone"],
            "dob": dob_value,
            "constituency": reg_data["constituency"],

            "password_hash": password_hash,

            "ocr_text": reg_data["ocr_text"],
            "ocr_confidence": reg_data["ocr_confidence"],

            "id_face_image": reg_data["face_image"],
            "live_face_image": live_face_bytes,

            "face_embedding": face_embedding,
            "face_similarity": st.session_state.get(
                "face_similarity", 0.0
            ),

            "is_verified": False,
            "rejected": False,
            "has_voted": False,

            "reg_date": datetime.now(timezone.utc)
        }

        # ----------------------------------------------------
        # Insert
        # ----------------------------------------------------

        try:

            collections["voters"].insert_one(
                voter_document
            )

        except Exception as e:

            # Most likely a unique-index violation on
            # voter_id / email under a race condition.
            st.error(
                "Registration could not be saved. "
                "The Voter ID or Email may already be in use."
            )

            st.exception(e)

            st.stop()

        # ----------------------------------------------------
        # Success — reset the flow for a fresh registration
        # ----------------------------------------------------

        st.session_state.registration_complete = True

        for key in (
            "id_verified",
            "face_matched",
            "ocr_text",
            "ocr_score",
            "id_face_bytes",
            "live_face_bytes",
            "face_similarity",
            "registration_data"
        ):
            st.session_state.pop(key, None)

        st.success(
            "🎉 Registration submitted successfully."
        )

        st.info(
            "Your registration is now pending administrator "
            "approval. You will be able to log in once it "
            "has been approved."
        )