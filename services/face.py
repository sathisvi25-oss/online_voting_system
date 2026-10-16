import os
from pathlib import Path

import cv2
import numpy as np
import streamlit as st
import torch
from PIL import Image
from ultralytics import YOLO


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "yolov8n-face.pt"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# =========================================================
# YOLO FACE MODEL
# =========================================================

@st.cache_resource
def load_face_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"YOLO face model not found:\n{MODEL_PATH}"
        )

    model = YOLO(str(MODEL_PATH))
    return model


# =========================================================
# IMAGE CONVERSION
# =========================================================

def image_to_cv2(image):
    """
    Convert Streamlit UploadedFile / PIL / numpy image
    to OpenCV BGR numpy array.
    """

    if image is None:
        return None

    # Streamlit UploadedFile
    if hasattr(image, "getvalue"):
        image_bytes = image.getvalue()

        arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        return frame

    # PIL Image
    if isinstance(image, Image.Image):
        rgb = np.array(image.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    # NumPy image
    if isinstance(image, np.ndarray):

        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

        return image.copy()

    raise TypeError(
        f"Unsupported image type: {type(image)}"
    )


def image_to_pil(image):
    """
    Convert image to PIL RGB format.
    """

    if image is None:
        return None

    if isinstance(image, Image.Image):
        return image.convert("RGB")

    frame = image_to_cv2(image)

    if frame is None:
        return None

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    return Image.fromarray(rgb)


# =========================================================
# FACE DETECTION
# =========================================================

def detect_faces(image, conf=0.40):
    """
    Detect faces using YOLOv8-face.

    Returns:
        [
            {
                "box": (x1, y1, x2, y2),
                "confidence": float
            }
        ]
    """

    frame = image_to_cv2(image)

    if frame is None:
        return []

    model = load_face_model()

    results = model.predict(
        source=frame,
        conf=conf,
        imgsz=640,
        verbose=False
    )

    faces = []

    if not results:
        return faces

    result = results[0]

    if result.boxes is None:
        return faces

    for box in result.boxes:

        xyxy = box.xyxy[0].cpu().numpy()

        x1, y1, x2, y2 = map(int, xyxy)

        confidence = float(
            box.conf[0].cpu().item()
        )

        # Keep coordinates inside image
        h, w = frame.shape[:2]

        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(0, min(x2, w))
        y2 = max(0, min(y2, h))

        if x2 > x1 and y2 > y1:
            faces.append(
                {
                    "box": (x1, y1, x2, y2),
                    "confidence": confidence
                }
            )

    return faces


# =========================================================
# FACE CROPPING
# =========================================================

def crop_face(image, box, padding=0.35, out_size=320):
    """
    Crop one detected face with context padding, normalized to a
    fixed square size.

    padding is a FRACTION of the detected box's width/height (not a
    fixed pixel count). A fixed pixel padding gives wildly different
    amounts of surrounding context on a high-res ID photo (where the
    face box might be 800px wide) versus a small live-webcam frame
    (where the face box might be 150px wide) — the ID crop ends up
    almost all face, the live crop ends up with a lot of extra
    forehead/chin/shoulders. That inconsistency alone can drag a
    genuine same-person match well below a realistic similarity
    threshold. Padding as a fraction of the box size keeps the two
    crops comparable regardless of source resolution.

    The crop is then resized to a fixed out_size x out_size square,
    so every face handed to the embedding model has the same
    resolution/aspect ratio, whatever the original detection box or
    camera resolution was.
    """

    frame = image_to_cv2(image)

    if frame is None:
        return None

    x1, y1, x2, y2 = box

    h, w = frame.shape[:2]

    box_w = x2 - x1
    box_h = y2 - y1

    pad_x = int(box_w * padding)
    pad_y = int(box_h * padding)

    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)

    x2 = min(w, x2 + pad_x)
    y2 = min(h, y2 + pad_y)

    face = frame[y1:y2, x1:x2]

    if face.size == 0:
        return None

    face = cv2.resize(
        face,
        (out_size, out_size),
        interpolation=cv2.INTER_AREA
    )

    return face


# =========================================================
# FACE ENCODING (numpy/OpenCV -> PNG bytes)
# =========================================================

def face_to_png_bytes(face):
    """
    Encode a cropped face (as returned by crop_face, a BGR
    OpenCV numpy array) to PNG-formatted bytes.

    crop_face() returns a numpy.ndarray, not a PIL Image, so
    it has no .save() method — this is the correct way to
    turn it into bytes for storage / session_state.
    """

    if face is None:
        return None

    success, buffer = cv2.imencode(".png", face)

    if not success:
        return None

    return buffer.tobytes()


# =========================================================
# FACE DRAWING
# =========================================================

def draw_face_boxes(image, faces=None):
    """
    Draw detected face boxes on image.

    If `faces` is not supplied, runs detection internally.
    Callers that already have a faces list (from an earlier
    detect_faces call) should pass it in to avoid running
    YOLO twice on the same image.
    """

    frame = image_to_cv2(image)

    if frame is None:
        return None

    if faces is None:
        faces = detect_faces(frame)

    output = frame.copy()

    for face in faces:

        x1, y1, x2, y2 = face["box"]
        confidence = face["confidence"]

        cv2.rectangle(
            output,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        cv2.putText(
            output,
            f"Face {confidence:.2f}",
            (x1, max(25, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

    return output


# =========================================================
# FACE COUNTING
# =========================================================

def count_faces(image):
    return len(detect_faces(image))


def has_single_face(image):
    return count_faces(image) == 1


# =========================================================
# DINOV2 FACE EMBEDDING
# =========================================================

def generate_embedding(image, processor=None, model=None):
    """
    Generate a 768-dimensional DINOv2 embedding.
    """

    if image is None:
        raise ValueError("Image is None")

    # Load DINOv2 automatically if not provided
    if processor is None or model is None:

        from models.loader import load_face_embedding_model

        processor, model = load_face_embedding_model()

    pil_image = image_to_pil(image)

    if pil_image is None:
        raise ValueError(
            "Could not convert image to PIL format"
        )

    inputs = processor(
        images=pil_image,
        return_tensors="pt"
    )

    inputs = {
        key: value.to(DEVICE)
        for key, value in inputs.items()
    }

    with torch.no_grad():

        outputs = model(**inputs)

        # DINOv2 CLS token
        embedding = outputs.last_hidden_state[:, 0, :]

        # L2 normalization
        embedding = torch.nn.functional.normalize(
            embedding,
            p=2,
            dim=1
        )

    return embedding[0].cpu().numpy().astype(
        np.float32
    )


# =========================================================
# COSINE SIMILARITY
# =========================================================

def cosine_similarity(embedding1, embedding2):
    """
    Calculate cosine similarity between two embeddings.

    Returns:
        float from approximately -1 to 1
    """

    a = np.asarray(
        embedding1,
        dtype=np.float32
    ).flatten()

    b = np.asarray(
        embedding2,
        dtype=np.float32
    ).flatten()

    if a.size == 0 or b.size == 0:
        return 0.0

    if a.size != b.size:
        raise ValueError(
            f"Embedding size mismatch: "
            f"{a.size} vs {b.size}"
        )

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    similarity = np.dot(a, b) / (
        norm_a * norm_b
    )

    return float(similarity)