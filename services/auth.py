from datetime import datetime, timezone

import numpy as np
import streamlit as st

from services.face import (
    detect_faces,
    crop_face,
    generate_embedding,
    cosine_similarity
)


def log_auth_attempt(
    collections,
    voter_id,
    status,
    auth_type,
    similarity=None
):
    """
    Write one row to auth_logs so the Admin > Authentication
    Logs screen has real data for voter logins and face-auth
    attempts (previously only admin logins were logged).

    status: "SUCCESS" or "FAIL"
    auth_type: "VOTER_LOGIN" or "FACE_AUTH"
    """

    try:
        collections["auth_logs"].insert_one({
            "voter_id": voter_id,
            "username": None,
            "attempt_time": datetime.now(timezone.utc),
            "status": status,
            "auth_type": auth_type,
            "similarity": similarity
        })
    except Exception:
        # Logging must never block the actual login/vote flow.
        pass


def authenticate_face(
    live_image,
    enrolled_embedding,
    processor,
    model,
    threshold=0.85
):
    """
    Authenticate a live face against the enrolled
    DINOv2 face embedding.
    """

    if enrolled_embedding is None:
        st.error(
            "No enrolled face embedding found for this voter."
        )
        return False, 0.0

    try:
        enrolled_embedding = np.asarray(
            enrolled_embedding,
            dtype=np.float32
        )

        # -----------------------------------------
        # Detect face
        # -----------------------------------------

        faces = detect_faces(live_image)

        if len(faces) == 0:
            st.warning(
                "No face detected. Please look directly at the camera."
            )
            return False, 0.0

        if len(faces) > 1:
            st.warning(
                "Multiple faces detected. "
                "Only one person should be visible."
            )
            return False, 0.0

        # -----------------------------------------
        # Crop detected face
        # -----------------------------------------

        face_box = faces[0]["box"]

        live_face = crop_face(
            live_image,
            face_box
        )

        if live_face is None:
            st.error(
                "Unable to crop the detected face."
            )
            return False, 0.0

        # -----------------------------------------
        # Generate DINOv2 embedding
        # -----------------------------------------

        live_embedding = generate_embedding(
            live_face,
            processor,
            model
        )

        # -----------------------------------------
        # Compare embeddings
        # -----------------------------------------

        similarity = cosine_similarity(
            live_embedding,
            enrolled_embedding
        )

        authenticated = similarity >= threshold

        return authenticated, similarity

    except Exception as e:

        st.error(
            f"Face authentication error: {e}"
        )

        return False, 0.0