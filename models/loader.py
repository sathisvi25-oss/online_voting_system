import streamlit as st
import torch
import easyocr

from transformers import (
    TrOCRProcessor,
    VisionEncoderDecoderModel,
    AutoImageProcessor,
    AutoModel
)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print(f"[INFO] Device: {DEVICE}")


# ============================================================
# TrOCR
# ============================================================

@st.cache_resource
def load_ocr_model():

    print("[INFO] Loading TrOCR...")

    processor = TrOCRProcessor.from_pretrained(
        "microsoft/trocr-base-printed",
        use_fast=False
    )

    model = VisionEncoderDecoderModel.from_pretrained(
        "microsoft/trocr-base-printed"
    )

    model = model.to(DEVICE)
    model.eval()

    print("[INFO] TrOCR loaded.")

    return processor, model


# ============================================================
# EasyOCR TEXT DETECTOR
# ============================================================

@st.cache_resource
def load_text_detector():

    print("[INFO] Loading EasyOCR...")

    reader = easyocr.Reader(
        ["en"],
        gpu=torch.cuda.is_available()
    )

    print("[INFO] EasyOCR loaded.")

    return reader


# ============================================================
# DINOv2 FACE EMBEDDING
# ============================================================

@st.cache_resource
def load_face_embedding_model():

    print("[INFO] Loading DINOv2...")

    processor = AutoImageProcessor.from_pretrained(
        "facebook/dinov2-base"
    )

    model = AutoModel.from_pretrained(
        "facebook/dinov2-base"
    )

    model = model.to(DEVICE)
    model.eval()

    print("[INFO] DINOv2 loaded.")

    return processor, model