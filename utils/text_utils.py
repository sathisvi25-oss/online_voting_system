import re
from difflib import SequenceMatcher


# ============================================================
# BASIC NORMALIZATION
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = str(text).upper()

    text = re.sub(
        r"[^A-Z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# NAME NORMALIZATION
# ============================================================

def normalize_name(text):

    return normalize_text(
        text
    )


# ============================================================
# VOTER ID NORMALIZATION
# ============================================================

def normalize_voter_id(text):

    if not text:
        return ""

    text = str(text).upper()

    # Remove spaces and punctuation
    text = re.sub(
        r"[^A-Z0-9]",
        "",
        text
    )

    return text


# ============================================================
# CONFUSION-TOLERANT VOTER ID
# ============================================================

def voter_id_fuzzy_form(
    text
):

    text = normalize_voter_id(
        text
    )

    # Common OCR confusions
    table = str.maketrans({
        "O": "0",
        "I": "1",
        "L": "1"
    })

    return text.translate(
        table
    )


# ============================================================
# SIMILARITY
# ============================================================

def similarity(
    a,
    b
):

    if not a or not b:
        return 0.0

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


# ============================================================
# NAME MATCH
# ============================================================

def find_name_match(
    name,
    ocr_text
):

    target = normalize_name(
        name
    )

    if not target:
        return 0.0, ""


    # --------------------------------------------------------
    # Check complete OCR text
    # --------------------------------------------------------

    full_text = normalize_name(
        ocr_text
    )

    if target in full_text:

        return 1.0, target


    # --------------------------------------------------------
    # Lines
    # --------------------------------------------------------

    lines = [
        normalize_name(x)
        for x in ocr_text.split("\n")
        if x.strip()
    ]


    candidates = list(
        lines
    )


    # --------------------------------------------------------
    # Word windows
    # --------------------------------------------------------

    words = full_text.split()

    target_words = target.split()

    n = len(
        target_words
    )


    for size in range(
        max(1, n - 1),
        n + 3
    ):

        for i in range(
            0,
            len(words) - size + 1
        ):

            candidate = " ".join(
                words[
                    i:i + size
                ]
            )

            candidates.append(
                candidate
            )


    # --------------------------------------------------------
    # Best similarity
    # --------------------------------------------------------

    best_score = 0.0
    best_match = ""


    for candidate in candidates:

        score = similarity(
            target,
            candidate
        )

        if score > best_score:

            best_score = score
            best_match = candidate


    return (
        best_score,
        best_match
    )


# ============================================================
# VOTER ID MATCH
# ============================================================

def find_voter_id_match(
    voter_id,
    ocr_text
):

    target = normalize_voter_id(
        voter_id
    )

    if not target:
        return 0.0, ""


    full_id = normalize_voter_id(
        ocr_text
    )


    # --------------------------------------------------------
    # Exact match
    # --------------------------------------------------------

    if target in full_id:

        return 1.0, target


    # --------------------------------------------------------
    # Token candidates
    # --------------------------------------------------------

    raw_tokens = re.findall(
        r"[A-Z0-9]+",
        str(ocr_text).upper()
    )


    candidates = []

    candidates.extend(
        normalize_voter_id(
            x
        )
        for x in raw_tokens
    )


    # --------------------------------------------------------
    # Concatenate neighboring tokens
    # --------------------------------------------------------

    for size in range(
        2,
        4
    ):

        for i in range(
            0,
            len(raw_tokens) - size + 1
        ):

            combined = "".join(
                raw_tokens[
                    i:i + size
                ]
            )

            candidates.append(
                normalize_voter_id(
                    combined
                )
            )


    # --------------------------------------------------------
    # Compare
    # --------------------------------------------------------

    best_score = 0.0
    best_match = ""


    fuzzy_target = (
        voter_id_fuzzy_form(
            target
        )
    )


    for candidate in candidates:

        if not candidate:
            continue


        score_normal = similarity(
            target,
            candidate
        )


        score_fuzzy = similarity(
            fuzzy_target,
            voter_id_fuzzy_form(
                candidate
            )
        )


        score = max(
            score_normal,
            score_fuzzy
        )


        if score > best_score:

            best_score = score
            best_match = candidate


    return (
        best_score,
        best_match
    )


# ============================================================
# FINAL REGISTRATION VERIFICATION
# ============================================================

def verify_registration_data(
    name,
    voter_id,
    ocr_text,
    threshold=0.85
):

    name_score, name_match = (
        find_name_match(
            name,
            ocr_text
        )
    )


    voter_id_score, voter_id_match = (
        find_voter_id_match(
            voter_id,
            ocr_text
        )
    )


    name_verified = (
        name_score >= threshold
    )


    voter_id_verified = (
        voter_id_score >= threshold
    )


    return {

        "verified":
            (
                name_verified
                and
                voter_id_verified
            ),

        "name_verified":
            name_verified,

        "voter_id_verified":
            voter_id_verified,

        "name_score":
            name_score,

        "voter_id_score":
            voter_id_score,

        "name_match":
            name_match,

        "voter_id_match":
            voter_id_match
    }