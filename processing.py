import os
import threading
import queue
import concurrent.futures
import multiprocessing

from cropper import (
    get_face_and_landmarks,
    is_frontal_face,
    crop_frontal_image,
    crop_profile_image,
    crop_chin_image,
    crop_nose_image,
    crop_below_lips_image,
    auto_crop,
    apply_aspect_ratio_filter,
    apply_filter,
    save_image,
)


# ----------------------------
# Dedicated RetinaFace queue worker
# ----------------------------
class FaceDetectionWorker:
    """Keeps one model in memory, processes detection requests sequentially."""
    def __init__(self):
        self.task_q = queue.Queue()
        self.result_q = queue.Queue()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        while True:
            item = self.task_q.get()
            if item is None:
                break
            filename, args = item
            try:
                result = get_face_and_landmarks(*args)
                self.result_q.put((filename, result, None))
            except Exception as e:
                self.result_q.put((filename, None, e))
            finally:
                self.task_q.task_done()

    def submit(self, filename, *args):
        self.task_q.put((filename, args))

    def get_result(self):
        return self.result_q.get()

    def shutdown(self):
        self.task_q.put(None)
        self.thread.join(timeout=2)


# ----------------------------
# Cropping logic
# ----------------------------
def process_image(filename, detection_result, output_folder,
                  frontal_margin, profile_margin, use_frontal, use_profile,
                  crop_style, filter_name, filter_intensity, aspect_ratio):
    """Do cropping + filtering + save based on detection result."""
    input_path, box, landmarks, _, pil_img, metadata = detection_result
    output_path = os.path.join(output_folder, f"cropped_{filename}")

    if box is None or landmarks is None:
        print(f"{filename}: No face detected. Skipping...")
        return 0

    crop_functions = {
        "frontal": lambda: (
            crop_frontal_image(pil_img, frontal_margin, landmarks, metadata, lip_offset=50)
            if use_frontal and is_frontal_face(landmarks)
            else auto_crop(pil_img, frontal_margin, profile_margin, box, landmarks, metadata, lip_offset=50, neck_offset=50)
        ),
        "profile": lambda: (
            crop_profile_image(pil_img, profile_margin, 50, box, metadata)
            if use_profile else None
        ),
        "chin": lambda: crop_chin_image(pil_img, frontal_margin, box, metadata, chin_offset=20),
        "nose": lambda: crop_nose_image(pil_img, box, landmarks, metadata, margin=0),
        "below_lips": lambda: crop_below_lips_image(pil_img, frontal_margin, landmarks, metadata, offset=10),
        "auto": lambda: auto_crop(pil_img, frontal_margin, profile_margin, box, landmarks, metadata, lip_offset=50, neck_offset=50),
    }

    try:
        cropped_img = crop_functions.get(crop_style, lambda: None)()
        if cropped_img and aspect_ratio:
            cropped_img = apply_aspect_ratio_filter(cropped_img, aspect_ratio)
        if cropped_img:
            cropped_img = apply_filter(cropped_img, filter_name, filter_intensity)
            save_image(cropped_img, output_path, metadata)
        else:
            print(f"{filename}: Cropping failed. Skipping...")
    except Exception as e:
        print(f"{filename}: error during crop/save: {e}")
        return 0
    return 1


# ----------------------------
# Main threaded controller
# ----------------------------
def process_images_threaded(
    input_folder,
    output_folder,
    frontal_margin,
    profile_margin,
    sharpen=True,
    use_frontal=True,
    use_profile=True,
    progress_callback=None,
    cancel_func=None,
    apply_rotation=True,
    crop_style="auto",
    filter_name="None",
    filter_intensity=50,
    aspect_ratio=None,
):
    os.makedirs(output_folder, exist_ok=True)
    valid_exts = (".jpg", ".jpeg", ".png", ".heic")
    filenames = [f for f in os.listdir(input_folder) if f.lower().endswith(valid_exts)]
    total = len(filenames)
    if not total:
        print("No valid images found.")
        return 0, 0

    # Start detection worker (one RetinaFace model)
    detector = FaceDetectionWorker()

    # Submit detection tasks
    for fn in filenames:
        input_path = os.path.join(input_folder, fn)
        detector.submit(fn, input_path, sharpen, apply_rotation)

    processed = 0
    max_workers = min(4, multiprocessing.cpu_count())
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []

        for _ in range(total):
            filename, result, err = detector.get_result()
            if err:
                print(f"{filename}: detection error {err}")
                continue
            if cancel_func and cancel_func():
                break

            # Schedule crop/save in parallel
            fut = executor.submit(
                process_image,
                filename,
                (os.path.join(input_folder, filename), *result),
                output_folder,
                frontal_margin,
                profile_margin,
                use_frontal,
                use_profile,
                crop_style,
                filter_name,
                filter_intensity,
                aspect_ratio,
            )
            futures.append(fut)

        for fut in concurrent.futures.as_completed(futures):
            processed += fut.result()
            if progress_callback:
                progress_callback(processed, total, "Processed")

    detector.shutdown()
    print(f"✅ Done: {processed}/{total} images processed.")
    return processed, total
