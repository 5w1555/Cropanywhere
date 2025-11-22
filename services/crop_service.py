# services/crop_service.py
import io
import os
from PIL import Image

# import your existing monster pipeline
from cropper import get_face_and_landmarks, auto_crop, save_image

def process_image_bytes(file_bytes: bytes) -> str:
    """
    Takes uploaded bytes → runs your entire heavy pipeline → returns output path.
    """

    # Load PIL from in-memory bytes
    pil_img = Image.open(io.BytesIO(file_bytes))

    # Save a temporary input file because your code expects file paths
    os.makedirs("originals", exist_ok=True)
    temp_input_path = "originals/temp_upload.png"
    pil_img.save(temp_input_path)

    # FACE DETECTION
    box, landmarks, _, pil_img2, metadata = get_face_and_landmarks(
        temp_input_path,
        conf_threshold=0.3
    )

    if box is None:
        raise ValueError("No face detected in the image.")

    # AUTO CROP
    cropped_img = auto_crop(
        pil_img2,
        frontal_margin=20,
        profile_margin=20,
        box=box,
        landmarks=landmarks,
        metadata=metadata,
        lip_offset=50,
        neck_offset=50
    )

    if cropped_img is None:
        raise ValueError("Cropping failed — see logs.")

    # SAVE OUTPUT
    os.makedirs("static/results", exist_ok=True)

    output_path = f"static/results/crop_{abs(hash(file_bytes))}.png"

    save_image(
        cropped_img,
        output_path,
        metadata,
        output_format="PNG"
    )

    return output_path
