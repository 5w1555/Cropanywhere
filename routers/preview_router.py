from fastapi import APIRouter, UploadFile, File
from services.preview_pipeline import generate_previews
from PIL import Image, ImageOps
import uuid, os, io

preview_router = APIRouter(prefix="/preview", tags=["preview"])

@preview_router.post("/")
async def preview_route(file: UploadFile = File(...)):
    file_bytes = await file.read()
    variants, msg = generate_previews(file_bytes)

    if variants is None:
        return {"ok": False, "message": msg}

    PREV_DIR = "static/previews"
    os.makedirs(PREV_DIR, exist_ok=True)

    uid = uuid.uuid4().hex

    # BEFORE IMAGE
    before = ImageOps.exif_transpose(Image.open(io.BytesIO(file_bytes)))
    before_path = f"{PREV_DIR}/{uid}_before.png"
    before.thumbnail((720, 720))
    before.save(before_path)

    out = {}
    for key, img in variants.items():
        vpath = f"{PREV_DIR}/{uid}_{key}.png"
        img.thumbnail((720, 720))
        img.save(vpath)
        out[key] = f"/{vpath}"

    return {
        "ok": True,
        "message": "Preview generated",
        "before_url": f"/{before_path}",
        "variants": out
    }
