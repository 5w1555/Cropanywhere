# services/crop_pipeline.py

import tempfile
from typing import Optional, Union, Dict, Any

from cropper import (
    get_face_and_landmarks,
    auto_crop,
    head_bust_crop,
    crop_frontal_image,
    crop_profile_image,
    crop_chin_image,
    crop_nose_image,
    crop_below_lips_image,
    apply_aspect_ratio_filter,
    apply_filter,
)

from services.presets import PRESETS


# ---------------------------------------------------------
# Method registry (pure crop operations)
# ---------------------------------------------------------
CROP_METHODS = {
    "auto": auto_crop,
    "headbust": head_bust_crop,
    "frontal": crop_frontal_image,
    "profile": crop_profile_image,
    "chin": crop_chin_image,
    "nose": crop_nose_image,
    "belowlips": crop_below_lips_image,
}


def _parse_ratio(r: Optional[Union[str, float]]) -> Optional[float]:
    """
    Accept:
      None, "", "none", "null"       -> None
      "4:5", "16:9"                  -> float ratio
      "1.33", 1.33                   -> float ratio
    """
    if r is None:
        return None
    if isinstance(r, (int, float)):
        return float(r)

    s = str(r).strip().lower()
    if s in ("", "none", "null"):
        return None

    if ":" in s:
        try:
            w, h = s.split(":", 1)
            return float(w) / float(h)
        except Exception:
            return None

    try:
        return float(s)
    except Exception:
        return None


def _save_bytes_to_temp(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
        tmp.write(file_bytes)
        return tmp.name


def crop_image(
    file_bytes: bytes,
    preset: str = "auto",
    margin: Optional[int] = None,
    ratio: Optional[Union[str, float]] = None,
    rotate: bool = True,
    filter_name: str = "None",
    intensity: int = 50,
):
    """
    Unified crop operation for all callers (web UI, Shopify, etc.)

    Args:
        file_bytes: uploaded image bytes
        preset: preset key from services.presets.PRESETS
        margin: optional override for margin
        ratio: optional override for aspect ratio (string or float)
        rotate: whether to allow face-rotation correction
        filter_name: post-filter name
        intensity: filter strength

    Returns:
        (PIL.Image or None, message:str, error_code:int)
    """

    key = preset.lower().strip()
    cfg = PRESETS.get(key)

    if not cfg:
        return None, f"Unknown preset '{preset}'", 1005

    method_key: str = cfg.get("method", "auto")
    method = CROP_METHODS.get(method_key)

    if method is None:
        return None, f"Unknown crop method '{method_key}' for preset '{preset}'", 1005

    # Effective ratio: UI override wins, else preset default
    eff_ratio = _parse_ratio(ratio if ratio is not None else cfg.get("ratio"))

    # Effective rotate: UI override wins, else preset default
    eff_rotate = rotate if rotate is not None else bool(cfg.get("rotate", True))

    # Save bytes → temp file (needed by RetinaFace pipeline / head_bust)
    img_path = _save_bytes_to_temp(file_bytes)

    params: Dict[str, Any] = dict(cfg.get("params", {}))

    # ------------------------------------------------------------------
    # Head & bust method (works from image path only)
    # ------------------------------------------------------------------
    if method_key == "headbust":
        # Margin override if provided
        if margin is not None:
            params["margin"] = margin

        margin_val = params.get("margin", 40)
        conf_thr = params.get("conf_threshold", 0.3)

        bust = head_bust_crop(
            img_path,
            margin=margin_val,
            target_ratio=eff_ratio,
            conf_threshold=conf_thr,
        )
        if bust is None:
            return None, "❌ No face detected.", 1001
        out = bust

    # ------------------------------------------------------------------
    # All other methods rely on face detection first
    # ------------------------------------------------------------------
    else:
        box, lm, cv_img, pil_img, meta = get_face_and_landmarks(
            img_path,
            conf_threshold=0.3,
            apply_rotation=eff_rotate,
        )
        if box is None:
            return None, "❌ No face detected.", 1001

        # Map generic margin override into method-specific params
        if margin is not None:
            # Auto: uses both frontal + profile
            if method_key == "auto":
                params["frontal_margin"] = margin
                params["profile_margin"] = margin
            # Frontal/profile: use single "margin"
            elif method_key in ("frontal", "profile"):
                params["margin"] = margin
            # Others: also have "margin"
            else:
                if "margin" in params:
                    params["margin"] = margin

        # Call method
        if method_key == "auto":
            out = auto_crop(
                pil_img,
                box=box,
                landmarks=lm,
                metadata=meta,
                **params,
            )
        elif method_key == "frontal":
            out = crop_frontal_image(
                pil_img,
                landmarks=lm,
                metadata=meta,
                **params,
            )
        elif method_key == "profile":
            out = crop_profile_image(
                pil_img,
                box=box,
                metadata=meta,
                **params,
            )
        elif method_key == "chin":
            out = crop_chin_image(
                pil_img,
                box=box,
                metadata=meta,
                **params,
            )
        elif method_key == "nose":
            out = crop_nose_image(
                pil_img,
                box=box,
                landmarks=lm,
                metadata=meta,
                **params,
            )
        elif method_key == "belowlips":
            out = crop_below_lips_image(
                pil_img,
                landmarks=lm,
                metadata=meta,
                **params,
            )
        else:
            return None, f"Unsupported method '{method_key}'", 1005

        if out is None:
            return None, "❌ Crop failed.", 1003

        # Apply preset/UI ratio if set
        if eff_ratio:
            out = apply_aspect_ratio_filter(out, eff_ratio)

    if out is None:
        return None, "❌ Crop failed.", 1003

    # Post filter
    out = apply_filter(out, filter_name, intensity)
    return out, "Done.", 0
