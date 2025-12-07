"""
Cropanyware - Crop Registry
This module provides a unified crop registry and helper functions
to generate multiple crop variants from cropper.py.

Your UI should import from here, not from cropper.py directly.
"""

# ==============================
# Imports
# ==============================

from typing import Dict, Any, Optional
from PIL import Image

# Import everything FROM cropper.py (your main crop engine)
from cropper import (
    crop_frontal_image,
    crop_profile_image,
    head_bust_crop,
    crop_chin_image,
    crop_nose_image,
    crop_below_lips_image,
    auto_crop,
    process_color_profile,
    get_face_and_landmarks,
    is_frontal_face
)

# ==============================
# Crop Registry
# ==============================

CROP_METHODS: Dict[str, Dict[str, Any]] = {
    "auto": {
        "fn": auto_crop,
        "params": {
            "frontal_margin": 40,
            "profile_margin": 40,
            "lip_offset": 50,
            "neck_offset": 50
        },
        "label": "Auto-detect orientation",
        "desc": "Automatically selects frontal or profile crop based on facial orientation."
    },

    "head_bust": {
        "fn": head_bust_crop,
        "params": {
            "margin": 40,
            "target_ratio": None
        },
        "label": "Head + Bust Portrait",
        "desc": "Classic portrait crop capturing head, shoulders, and upper torso."
    },

    "frontal_lips_down": {
        "fn": crop_frontal_image,
        "params": {
            "margin": 40,
            "lip_offset": 50
        },
        "label": "Frontal Crop (Lips Down)",
        "desc": "Centered crop starting slightly above lips down to the bottom of the frame."
    },

    "below_lips": {
        "fn": crop_below_lips_image,
        "params": {
            "margin": 20,
            "offset": 10
        },
        "label": "Half-face Down",
        "desc": "Starts just below the lips, focusing attention on clothing and body composition."
    },

    "chin_down": {
        "fn": crop_chin_image,
        "params": {
            "margin": 20,
            "chin_offset": 20
        },
        "label": "Chin to Bottom",
        "desc": "Crop emphasizing the chin and everything below – perfect for outfits."
    },

    "profile_neck": {
        "fn": crop_profile_image,
        "params": {
            "margin": 40,
            "neck_offset": 50
        },
        "label": "Profile Bust",
        "desc": "Side-facing crop using neck line to anchor composition and clarity."
    },

    "nose_centered": {
        "fn": crop_nose_image,
        "params": {
            "margin": 0
        },
        "label": "Centered Upper Face",
        "desc": "Bounding-box crop that centers on the nose and eyes – ideal for IDs and model cards."
    }
}

# ==============================
# Variant Generator
# ==============================

def generate_crop_variants(
    pil_img: Image.Image,
    box: Optional[list],
    landmarks: Optional[dict],
    metadata: dict
) -> Dict[str, Image.Image]:
    """
    Generate all crop variants from CROP_METHODS.

    Returns:
        dict: {method_name: PIL.Image}
    """
    variants = {}
    for method, cfg in CROP_METHODS.items():
        fn = cfg["fn"]
        params = cfg.get("params", {})

        try:
            if method == "auto":
                img = fn(
                    pil_img,
                    frontal_margin=params.get("frontal_margin", 40),
                    profile_margin=params.get("profile_margin", 40),
                    box=box,
                    landmarks=landmarks,
                    metadata=metadata,
                    lip_offset=params.get("lip_offset", 50),
                    neck_offset=params.get("neck_offset", 50)
                )
            else:
                img = fn(
                    pil_img,
                    box=box,
                    landmarks=landmarks,
                    metadata=metadata,
                    **params
                )

            if isinstance(img, Image.Image):
                variants[method] = img

        except Exception as e:
            print(f"[Variant '{method}' failed]: {e}")

    return variants


# ==============================
# Debug helper
# ==============================

def list_methods():
    """Print available crop methods for debugging."""
    for key, info in CROP_METHODS.items():
        print(f"- {key}: {info['label']} — {info['desc']}")
