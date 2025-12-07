# services/presets.py

"""
Preset configuration for Cropanyware.

- Presets are UX-level shortcuts.
- They reference a crop "method" by key.
- Methods themselves live in the crop pipeline (and ultimately cropper.py).
"""

PRESETS = {
    # ------------------------------------------------------------------
    # Smart / default behavior
    # ------------------------------------------------------------------
    "auto": {
        "label": "Auto Crop",
        "description": "Automatically chooses between frontal/profile bust based on face orientation.",
        "method": "auto",          # maps to auto_crop
        "params": {
            "frontal_margin": 20,
            "profile_margin": 20,
            "lip_offset": 50,
            "neck_offset": 50,
        },
        "ratio": None,             # e.g. "4:5", "1:1", etc.
        "rotate": True,
    },

    # ------------------------------------------------------------------
    # Head & Bust
    # ------------------------------------------------------------------
    "headbust": {
        "label": "Head & Bust",
        "description": "Centered crop from hairline to upper torso with safe margins.",
        "method": "headbust",      # maps to head_bust_crop
        "params": {
            "margin": 40,
            "conf_threshold": 0.3,
        },
        "ratio": None,
        "rotate": True,
    },

    # ------------------------------------------------------------------
    # Orientation-specific
    # ------------------------------------------------------------------
    "frontal": {
        "label": "Frontal Only",
        "description": "Frontal bust crop from slightly above lips downwards.",
        "method": "frontal",
        "params": {
            "margin": 20,
            "lip_offset": 50,
        },
        "ratio": None,
        "rotate": True,
    },

    "profile": {
        "label": "Profile Only",
        "description": "Side-profile crop from below jawline to bottom.",
        "method": "profile",
        "params": {
            "margin": 20,
            "neck_offset": 50,
        },
        "ratio": None,
        "rotate": True,
    },

    # ------------------------------------------------------------------
    # Feature crops
    # ------------------------------------------------------------------
    "chin": {
        "label": "Chin + Neck",
        "description": "Crop starting at the chin and downwards.",
        "method": "chin",
        "params": {
            "margin": 20,
            "chin_offset": 20,
        },
        "ratio": None,
        "rotate": True,
    },

    "nose": {
        "label": "Face / Nose Box",
        "description": "Tight bounding-box crop around the face.",
        "method": "nose",
        "params": {
            "margin": 0,
        },
        "ratio": None,
        "rotate": True,
    },

    "belowlips": {
        "label": "Below Lips",
        "description": "Starts just under the mouth, goes to the bottom.",
        "method": "belowlips",
        "params": {
            "margin": 20,
            "offset": 10,
        },
        "ratio": None,
        "rotate": True,
    },

    # ------------------------------------------------------------------
    # Example “portrait-ready” preset reusing auto method
    # ------------------------------------------------------------------
    "portrait_4x5": {
        "label": "Portrait 4:5",
        "description": "Auto bust crop constrained to 4:5 aspect ratio (good for product models).",
        "method": "auto",
        "params": {
            "frontal_margin": 20,
            "profile_margin": 20,
            "lip_offset": 40,
            "neck_offset": 40,
        },
        "ratio": "4:5",
        "rotate": True,
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

