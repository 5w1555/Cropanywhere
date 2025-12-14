# services/registry.py

from cropper import (
    auto_crop,
    head_bust_crop,
    crop_frontal_image,
    crop_profile_image,
    crop_chin_image,
    crop_nose_image,
    crop_below_lips_image,
)

# ---------------------------------------------
# 1) Canonical crop method registry
# ---------------------------------------------
CROP_METHODS = {
    "auto": auto_crop,
    "head_bust": head_bust_crop,
    "frontal_lips_down": crop_frontal_image,
    "profile_neck": crop_profile_image,
    "chin_down": crop_chin_image,
    "nose_centered": crop_nose_image,
    "below_lips": crop_below_lips_image,
}
