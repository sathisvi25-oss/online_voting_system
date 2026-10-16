import cv2
import torch
import numpy as np
import re

from difflib import SequenceMatcher
from PIL import (
    Image,
    ImageEnhance,
    ImageFilter
)

from models.loader import (
    load_text_detector,
    DEVICE
)


# ============================================================
# CONFIGURATION
# ============================================================

TARGET_WIDTH = 1600

MIN_CONFIDENCE = 0.20

MIN_TEXT_LENGTH = 1

DETECTION_OVERLAP = 0.45


# ============================================================
# CONVERT INPUT TO PIL
# ============================================================

def convert_to_pil(image):

    if image is None:
        return None

    if isinstance(
        image,
        Image.Image
    ):

        return image.convert(
            "RGB"
        )

    try:

        if hasattr(
            image,
            "seek"
        ):
            image.seek(0)

        return Image.open(
            image
        ).convert(
            "RGB"
        )

    except Exception as e:

        raise RuntimeError(
            f"Unable to read image: {e}"
        )


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = str(text).upper()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# RESIZE
# ============================================================

def resize_image(frame):

    h, w = frame.shape[:2]

    if w < TARGET_WIDTH:

        scale = (
            TARGET_WIDTH / w
        )

        frame = cv2.resize(
            frame,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC
        )

    return frame


# ============================================================
# IMAGE ENHANCEMENT
# ============================================================

def enhance_for_detection(frame):

    frame = resize_image(
        frame.copy()
    )

    # --------------------------------------------------------
    # LAB + CLAHE
    # --------------------------------------------------------

    lab = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2LAB
    )

    l, a, b = cv2.split(
        lab
    )

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    l = clahe.apply(
        l
    )

    enhanced = cv2.cvtColor(
        cv2.merge(
            (l, a, b)
        ),
        cv2.COLOR_LAB2BGR
    )

    # --------------------------------------------------------
    # Mild denoise
    # --------------------------------------------------------

    enhanced = cv2.bilateralFilter(
        enhanced,
        5,
        35,
        35
    )

    # --------------------------------------------------------
    # Mild sharpen
    # --------------------------------------------------------

    blur = cv2.GaussianBlur(
        enhanced,
        (0, 0),
        1.0
    )

    enhanced = cv2.addWeighted(
        enhanced,
        1.15,
        blur,
        -0.15,
        0
    )

    return enhanced


# ============================================================
# DETECTION IMAGE VARIANTS
# ============================================================

def get_detection_variants(
    frame
):

    enhanced = enhance_for_detection(
        frame
    )

    original = resize_image(
        frame.copy()
    )

    return [
        original,
        enhanced
    ]


# ============================================================
# BOX CONVERSION
# ============================================================

def get_box(
    detection,
    original_shape,
    processed_shape
):

    polygon = detection[0]

    confidence = float(
        detection[2]
    )

    xs = [
        float(p[0])
        for p in polygon
    ]

    ys = [
        float(p[1])
        for p in polygon
    ]

    x1 = int(
        min(xs)
    )

    y1 = int(
        min(ys)
    )

    x2 = int(
        max(xs)
    )

    y2 = int(
        max(ys)
    )

    scale_x = (
        original_shape[1]
        /
        processed_shape[1]
    )

    scale_y = (
        original_shape[0]
        /
        processed_shape[0]
    )

    x1 = int(
        x1 * scale_x
    )

    y1 = int(
        y1 * scale_y
    )

    x2 = int(
        x2 * scale_x
    )

    y2 = int(
        y2 * scale_y
    )

    x1 = max(
        0,
        x1
    )

    y1 = max(
        0,
        y1
    )

    x2 = min(
        original_shape[1],
        x2
    )

    y2 = min(
        original_shape[0],
        y2
    )

    return {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "confidence": confidence
    }


# ============================================================
# IOU
# ============================================================

def calculate_iou(
    a,
    b
):

    ax1, ay1 = a["x1"], a["y1"]
    ax2, ay2 = a["x2"], a["y2"]

    bx1, by1 = b["x1"], b["y1"]
    bx2, by2 = b["x2"], b["y2"]

    ix1 = max(
        ax1,
        bx1
    )

    iy1 = max(
        ay1,
        by1
    )

    ix2 = min(
        ax2,
        bx2
    )

    iy2 = min(
        ay2,
        by2
    )

    if (
        ix2 <= ix1
        or
        iy2 <= iy1
    ):
        return 0.0

    intersection = (
        (ix2 - ix1)
        *
        (iy2 - iy1)
    )

    area_a = (
        (ax2 - ax1)
        *
        (ay2 - ay1)
    )

    area_b = (
        (bx2 - bx1)
        *
        (by2 - by1)
    )

    union = (
        area_a
        +
        area_b
        -
        intersection
    )

    if union <= 0:
        return 0.0

    return (
        intersection / union
    )


# ============================================================
# REMOVE DUPLICATE DETECTIONS
# ============================================================

def remove_duplicate_boxes(
    boxes
):

    if not boxes:
        return []

    boxes = sorted(
        boxes,
        key=lambda x:
        x["confidence"],
        reverse=True
    )

    selected = []

    for box in boxes:

        duplicate = False

        for existing in selected:

            iou = calculate_iou(
                box,
                existing
            )

            if iou >= DETECTION_OVERLAP:

                duplicate = True
                break

        if not duplicate:

            selected.append(
                box
            )

    # --------------------------------------------------------
    # Reading order
    # --------------------------------------------------------

    selected.sort(
        key=lambda x: (
            x["y1"],
            x["x1"]
        )
    )

    return selected


# ============================================================
# DETECT ALL TEXT REGIONS
# ============================================================

def detect_text_regions(
    frame
):

    reader = load_text_detector()

    original_shape = (
        frame.shape
    )

    variants = get_detection_variants(
        frame
    )

    all_boxes = []

    for variant in variants:

        rgb = cv2.cvtColor(
            variant,
            cv2.COLOR_BGR2RGB
        )

        try:

            detections = reader.readtext(
                rgb,

                detail=1,

                paragraph=False,

                decoder="greedy",

                width_ths=0.6,

                height_ths=0.5,

                slope_ths=0.25,

                text_threshold=0.30,

                low_text=0.15,

                link_threshold=0.30,

                mag_ratio=1.2
            )

        except Exception:

            detections = []

        for detection in detections:

            if len(detection) < 3:
                continue

            easy_text = normalize_text(
                detection[1]
            )

            confidence = float(
                detection[2]
            )

            if (
                confidence
                <
                MIN_CONFIDENCE
            ):
                continue

            if len(easy_text) < MIN_TEXT_LENGTH:
                continue

            box = get_box(
                detection,
                original_shape,
                variant.shape
            )

            if (
                box["x2"]
                <=
                box["x1"]
            ):
                continue

            if (
                box["y2"]
                <=
                box["y1"]
            ):
                continue

            box["easy_text"] = (
                easy_text
            )

            all_boxes.append(
                box
            )

    return remove_duplicate_boxes(
        all_boxes
    )


# ============================================================
# PREPARE OCR CROP
# ============================================================

def prepare_crop(
    frame,
    box
):

    x1 = box["x1"]
    y1 = box["y1"]
    x2 = box["x2"]
    y2 = box["y2"]

    width = (
        x2 - x1
    )

    height = (
        y2 - y1
    )

    # --------------------------------------------------------
    # Controlled padding
    # --------------------------------------------------------

    pad_x = max(
        12,
        int(width * 0.08)
    )

    pad_y = max(
        10,
        int(height * 0.25)
    )

    x1 = max(
        0,
        x1 - pad_x
    )

    y1 = max(
        0,
        y1 - pad_y
    )

    x2 = min(
        frame.shape[1],
        x2 + pad_x
    )

    y2 = min(
        frame.shape[0],
        y2 + pad_y
    )

    crop = frame[
        y1:y2,
        x1:x2
    ]

    if crop.size == 0:
        return None

    return crop


# ============================================================
# OCR CROP VARIANTS
# ============================================================

def create_ocr_variants(
    crop
):

    variants = []

    # --------------------------------------------------------
    # Original RGB
    # --------------------------------------------------------

    rgb = cv2.cvtColor(
        crop,
        cv2.COLOR_BGR2RGB
    )

    variants.append(
        rgb
    )

    # --------------------------------------------------------
    # Grayscale + CLAHE
    # --------------------------------------------------------

    gray = cv2.cvtColor(
        crop,
        cv2.COLOR_BGR2GRAY
    )

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    gray = clahe.apply(
        gray
    )

    variants.append(
        cv2.cvtColor(
            gray,
            cv2.COLOR_GRAY2RGB
        )
    )

    # --------------------------------------------------------
    # Contrast enhanced RGB
    # --------------------------------------------------------

    enhanced = Image.fromarray(
        rgb
    )

    enhanced = ImageEnhance.Contrast(
        enhanced
    ).enhance(
        1.20
    )

    enhanced = ImageEnhance.Sharpness(
        enhanced
    ).enhance(
        1.30
    )

    enhanced = enhanced.filter(
        ImageFilter.SHARPEN
    )

    variants.append(
        np.array(
            enhanced
        )
    )

    return variants


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_ocr_text(
    text
):

    if not text:
        return ""

    text = str(text)

    text = text.replace(
        "\n",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# TEXT QUALITY SCORE
# ============================================================

def text_quality(
    text
):

    text = clean_ocr_text(
        text
    )

    if not text:
        return 0.0

    alnum = sum(
        c.isalnum()
        for c in text
    )

    total = len(
        text
    )

    if total == 0:
        return 0.0

    alpha_ratio = (
        alnum / total
    )

    length_score = min(
        len(text) / 12.0,
        1.0
    )

    return (
        0.65 * alpha_ratio
        +
        0.35 * length_score
    )


# ============================================================
# SIMILARITY
# ============================================================

def text_similarity(
    a,
    b
):

    a = normalize_text(a)
    b = normalize_text(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


# ============================================================
# TR OCR SINGLE CROP
# ============================================================

def recognize_crop(
    crop,
    processor,
    model,
    easy_text=""
):

    if crop is None:
        return ""

    variants = create_ocr_variants(
        crop
    )

    candidates = []

    for variant in variants:

        try:

            pil_image = Image.fromarray(
                variant
            ).convert(
                "RGB"
            )

            width, height = (
                pil_image.size
            )

            # ------------------------------------------------
            # Upscale small text
            # ------------------------------------------------

            target_height = 96

            scale = max(
                2.5,
                target_height
                /
                max(
                    height,
                    1
                )
            )

            new_width = max(
                220,
                int(
                    width * scale
                )
            )

            new_height = max(
                64,
                int(
                    height * scale
                )
            )

            pil_image = pil_image.resize(
                (
                    new_width,
                    new_height
                ),
                Image.Resampling.LANCZOS
            )

            pixel_values = processor(
                images=pil_image,
                return_tensors="pt"
            ).pixel_values

            pixel_values = (
                pixel_values.to(
                    DEVICE
                )
            )

            with torch.no_grad():

                generated_ids = (
                    model.generate(
                        pixel_values,
                        max_new_tokens=64,
                        num_beams=4,
                        early_stopping=True
                    )
                )

            text = processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0]

            text = clean_ocr_text(
                text
            )

            if text:

                quality = text_quality(
                    text
                )

                agreement = (
                    text_similarity(
                        text,
                        easy_text
                    )
                    if easy_text
                    else 0.0
                )

                score = (
                    0.60 * quality
                    +
                    0.40 * agreement
                )

                candidates.append(
                    (
                        score,
                        text
                    )
                )

        except Exception:

            continue


    # --------------------------------------------------------
    # If TrOCR failed
    # --------------------------------------------------------

    if not candidates:

        return clean_ocr_text(
            easy_text
        )


    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    best_text = candidates[0][1]

    # --------------------------------------------------------
    # Avoid obvious garbage
    # --------------------------------------------------------

    if (
        text_quality(best_text)
        < 0.30
        and
        easy_text
    ):

        return clean_ocr_text(
            easy_text
        )

    return best_text


# ============================================================
# MAIN OCR
# ============================================================

def extract_text(
    image,
    processor,
    model
):

    pil_image = convert_to_pil(
        image
    )

    if pil_image is None:
        return ""

    rgb = np.array(
        pil_image
    )

    frame = cv2.cvtColor(
        rgb,
        cv2.COLOR_RGB2BGR
    )

    boxes = detect_text_regions(
        frame
    )

    results = []

    for box in boxes:

        crop = prepare_crop(
            frame,
            box
        )

        if crop is None:
            continue

        easy_text = box.get(
            "easy_text",
            ""
        )

        text = recognize_crop(
            crop,
            processor,
            model,
            easy_text
        )

        text = clean_ocr_text(
            text
        )

        if text:
            results.append(
                text
            )

    # --------------------------------------------------------
    # Remove duplicate OCR lines
    # --------------------------------------------------------

    unique_results = []

    seen_normalized = []

    for text in results:

        normalized = normalize_text(
            text
        )

        duplicate = False

        for previous in (
            seen_normalized
        ):

            if (
                text_similarity(
                    normalized,
                    previous
                )
                >= 0.92
            ):

                duplicate = True
                break

        if duplicate:
            continue

        unique_results.append(
            text
        )

        seen_normalized.append(
            normalized
        )

    return "\n".join(
        unique_results
    )


# ============================================================
# OCR WITH DETAILS
# ============================================================

def extract_text_with_details(
    image,
    processor,
    model
):

    pil_image = convert_to_pil(
        image
    )

    if pil_image is None:

        return [], None

    rgb = np.array(
        pil_image
    )

    frame = cv2.cvtColor(
        rgb,
        cv2.COLOR_RGB2BGR
    )

    boxes = detect_text_regions(
        frame
    )

    results = []

    for box in boxes:

        crop = prepare_crop(
            frame,
            box
        )

        if crop is None:
            continue

        text = recognize_crop(
            crop,
            processor,
            model,
            box.get(
                "easy_text",
                ""
            )
        )

        if not text:
            continue

        results.append(
            {
                "text": text,

                "box": (
                    box["x1"],
                    box["y1"],
                    box["x2"],
                    box["y2"]
                ),

                "confidence":
                    box["confidence"],

                "easy_text":
                    box.get(
                        "easy_text",
                        ""
                    )
            }
        )

    return (
        results,
        frame
    )