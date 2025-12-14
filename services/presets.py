# services/presets.py

"""
Preset configuration for Cropanyware.

- Presets are UX-level shortcuts.
- They reference a crop "method" by key.
- Methods themselves live in the crop pipeline (and ultimately cropper.py).
"""

from services.registry import CROP_METHODS

PRESETS = {
    "auto": {
        "label": "Auto Crop",
        "method": "auto",
        "params": { "frontal_margin": 20, "profile_margin": 20 },
        "rotate": True,
        "ratio": None,
    },
    "headbust": {
        "label": "Head & Bust",
        "method": "head_bust",  # canonical
        "params": { "margin": 40 },
        "rotate": True,
        "ratio": None,
    },
    "frontal": {
        "label": "Frontal Only",
        "method": "frontal_lips_down",
        "params": { "lip_offset": 50 },
        "rotate": True,
        "ratio": None,
    },
    "profile": {
        "label": "Profile Only",
        "method": "profile_neck",
        "params": { "neck_offset": 50 },
        "rotate": True,
        "ratio": None,
    },
    "chin": {
        "label": "Chin + Neck",
        "method": "chin_down",
        "params": { "chin_offset": 20 },
        "rotate": True,
        "ratio": None,
    },
    "nose": {
        "label": "Face / Nose Box",
        "method": "nose_centered",
        "params": {},
        "rotate": True,
        "ratio": None,
    },
    "belowlips": {
        "label": "Below Lips",
        "method": "below_lips",
        "params": { "offset": 10 },
        "rotate": True,
        "ratio": None,
    },
}

from typing import List, Dict

def get_preset_labels() -> List[Dict[str, str]]:
    """
    Returns presets formatted for UI dropdown:
    [
      {"key": "auto", "label": "Auto Crop"},
      {"key": "headbust", "label": "Head & Bust"},
      ...
    ]
    """
    return [
        {
            "key": key,
            "label": cfg.get("label", key.replace("_", " ").title())
        }
        for key, cfg in PRESETS.items()
    ]

