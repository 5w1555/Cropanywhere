# services/crop_service.py
import io
import os
from PIL import Image

from cropper import (
    get_face_and_landmarks,
    auto_crop,
    head_bust_crop,
    crop_frontal_image,
    crop_profile_image,
    crop_chin_image,
    crop_nose_image,
    crop_below_lips_image,
    save_image,
)

# --------------------
# PRESET DEFINITIONS
# --------------------
PRESETS = {
    "auto": {
        "fn": auto_crop,
        "params": {
            "frontal_margin": 20,
            "profile_margin": 20,
            "lip_offset": 50,
            "neck_offset": 50,
        }
    },

    "headbust": {
        "fn": head_bust_crop,  # special signature uses input_path
        "params": {
            "margin": 40,
            "target_ratio": None,
            "conf_threshold": 0.3,
        }
    },

    "frontal": {
        "fn": crop_frontal_image,
        "params": {
            "margin": 20,
            "lip_offset": 50,
        }
    },

    "profile": {
        "fn": crop_profile_image,
        "params": {
            "margin": 20,
            "neck_offset": 50,
        }
    },

    "chin": {
        "fn": crop_chin_image,
        "params": {
            "margin": 20,
            "chin_offset": 20,
        }
    },

    "nose": {
        "fn": crop_nose_image,
        "params": {
            "margin": 0
        }
    },

    "belowlips": {
        "fn": crop_below_lips_image,
        "params": {
            "margin": 20,
            "offset": 10,
        }
    }
}


def process_image_bytes(file_bytes: bytes, preset: str = "auto") -> str:
    """
    - Loads image
    - Runs face detection
    - Dispatches to preset crop function
    - Saves output
    """

    preset = preset.lower().strip()
    cfg = PRESETS.get(preset)
    if not cfg:
        raise ValueError(f"Unknown preset '{preset}'")

    # Save input temporarily, because head_bust_crop requires path
    os.makedirs("originals", exist_ok=True)
    temp_input_path = "originals/temp_upload.png"
    Image.open(io.BytesIO(file_bytes)).save(temp_input_path)

    # Face detection (always required except headbust auto reload)
    box, landmarks, _, pil_img, metadata = get_face_and_landmarks(
        temp_input_path, conf_threshold=0.3
    )

    if box is None:
        raise ValueError("No face detected.")

    fn = cfg["fn"]
    params = cfg["params"]

    # -------------------
    # DISPATCH LOGIC
    # -------------------

    if fn.__name__ == "head_bust_crop":
        # This function only expects input_path
        cropped = fn(temp_input_path, **params)

    else:
        # All other functions operate on PIL + metadata
        cropped = fn(
            pil_img,
            box=box,
            landmarks=landmarks,
            metadata=metadata,
            **params
        )

    if cropped is None:
        raise ValueError("Cropping failed.")

    # Save to results
    os.makedirs("static/results", exist_ok=True)
    output_path = f"static/results/crop_{abs(hash(file_bytes))}.png"

    save_image(cropped, output_path, metadata, output_format="PNG")
    return output_path
