from fastapi import APIRouter, UploadFile, File


preview_router = APIRouter(prefix="/preview", tags=["preview"])

from typing import Dict, Tuple, Any
from PIL import Image
import io

from crop_registry import CROP_METHODS   # your registry file
from cropper import get_face_and_landmarks   # the face pipeline

import tempfile

def _bytes_to_temp(file_bytes: bytes) -> str:
    """
    Writes incoming image bytes into a temp file and returns the path.
    The file is NOT auto-deleted, because downstream functions
    (RetinaFace) may access it asynchronously.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    tmp.write(file_bytes)
    tmp.flush()
    return tmp.name


def generate_previews(file_bytes: bytes) -> Tuple[Dict[str, Image.Image], str]:
    """
    Takes raw file bytes → runs get_face_and_landmarks once →
    returns multiple crop variants based on CROP_METHODS
    """
    try:
        # Decode once (expensive)
        pil_img = Image.open(io.BytesIO(file_bytes)).convert("RGB")

        # Path for detectors that require disk access
        img_path = _bytes_to_temp(file_bytes)

        box, lm, cv_img, pil_img, meta = get_face_and_landmarks(
            img_path,
            conf_threshold=0.3,
            apply_rotation=False,  # faster preview
        )

        if box is None:
            return None, "No face detected"

        variants: Dict[str, Image.Image] = {}

        for key, cfg in CROP_METHODS.items():
            fn = cfg["fn"]
            params = cfg.get("params", {})

            try:
                # HEAD BUST → only uses path
                if key == "head_bust":
                    out = fn(
                        img_path,
                        margin=params.get("margin", 40),
                        target_ratio=params.get("target_ratio"),
                    )

                # FRONTAL CROPS → require landmarks, no box
                elif key in ("frontal_lips_down", "below_lips"):
                    out = fn(
                        pil_img,
                        landmarks=lm,
                        metadata=meta,
                        **params
                    )

                # PROFILE CROPS → require box, no landmarks
                elif key in ("profile_neck", "chin_down"):
                    out = fn(
                        pil_img,
                        box=box,
                        metadata=meta,
                        **params
                    )

                # AUTO METHOD → uses both
                elif key == "auto":
                    out = fn(
                        pil_img,
                        box=box,
                        landmarks=lm,
                        metadata=meta,
                        **params
                    )

                else:
                    print(f"[Preview] Unknown crop method '{key}'")
                    out = None

                if out:
                    variants[key] = out

            except Exception as e:
                print(f"[Preview/{key}] failed: {e}")

        return variants, "OK"

    except Exception as e:
        return None, f"Preview failed: {e}"
