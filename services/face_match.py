import torch
import torch.nn.functional as F

from PIL import Image, ImageOps

from models.loader import (
    DEVICE,
    load_face_embedding_model
)


# ============================================================
# CREATE EMBEDDING
# ============================================================

def get_face_embedding(face_image):

    if not isinstance(
        face_image,
        Image.Image
    ):
        raise TypeError(
            "Face image must be a PIL Image."
        )

    face_image = face_image.convert(
        "RGB"
    )

    # Neutralize color casts (e.g. a blue-tinted IR/webcam capture
    # compared against a normally-lit ID photo). DINOv2 is a general
    # image backbone, not a face-recognition model, so it is sensitive
    # to color differences that have nothing to do with identity.
    # Flattening both images to grayscale (replicated across the 3
    # channels the model expects) removes that noise and lets the
    # comparison focus on facial structure instead of lighting/color.
    face_image = ImageOps.grayscale(
        face_image
    ).convert("RGB")

    processor, model = (
        load_face_embedding_model()
    )

    inputs = processor(
        images=face_image,
        return_tensors="pt"
    )

    inputs = {
        key: value.to(DEVICE)
        for key, value in inputs.items()
    }

    with torch.no_grad():

        outputs = model(
            **inputs
        )

        # Mean-pool over all patch tokens (skip the CLS token at
        # index 0) instead of using the CLS token alone. For a
        # general-purpose backbone like DINOv2, the CLS token is
        # tuned for whole-image classification and tends to blur
        # together similar faces; averaging the patch tokens keeps
        # more of the fine-grained, per-region detail (eyes, nose,
        # mouth) that face *verification* actually depends on, which
        # in practice gives noticeably better separation between
        # "same person" and "different person" scores.
        embedding = (
            outputs.last_hidden_state[:, 1:, :].mean(dim=1)
        )

        embedding = F.normalize(
            embedding,
            p=2,
            dim=1
        )

    return embedding.squeeze(
        0
    ).cpu()


# ============================================================
# COMPARE FACES
# ============================================================

def compare_faces(
    id_face,
    live_face
):

    id_embedding = (
        get_face_embedding(
            id_face
        )
    )

    live_embedding = (
        get_face_embedding(
            live_face
        )
    )

    similarity = (
        F.cosine_similarity(
            id_embedding.unsqueeze(0),
            live_embedding.unsqueeze(0),
            dim=1
        )
        .item()
    )

    return similarity


# ============================================================
# VERIFY
# ============================================================

def verify_faces(
    id_face,
    live_face,
    threshold=0.55
):
    """
    threshold default lowered from 0.75 to 0.55.

    0.75 was calibrated for nothing in particular — DINOv2 is a
    general-purpose vision backbone, not a dedicated face-recognition
    model, so its cosine similarities for two photos of the *same*
    person (different camera, lighting, angle) routinely land in the
    0.45-0.70 range rather than the 0.9+ you'd see from a real
    face-recognition model. A 0.75 bar was rejecting genuine matches.
    0.55 is a reasonable starting point with the grayscale +
    mean-pooled embedding above, but you should tune it against a
    few real registration attempts — pass an explicit threshold=
    from the caller to override without editing this file.
    """

    similarity = compare_faces(
        id_face,
        live_face
    )

    matched = (
        similarity >= threshold
    )

    return matched, similarity