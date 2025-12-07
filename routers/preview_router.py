from fastapi import APIRouter, UploadFile, File
from services.preview_pipeline import generate_previews


preview_router = APIRouter(prefix="/preview", tags=["preview"])

@preview_router.post("/")
async def preview_route(file: UploadFile = File(...)):
    """
    Receive uploaded image → generate preview crops.
    Returns dict of {method_name: base64/png URL}
    """
    file_bytes = await file.read()
    variants, msg = generate_previews(file_bytes)

    if variants is None:
        return {"ok": False, "message": msg, "variants": {}}

    # Convert PIL → temporary PNG URLs under /static/previews/
    out = {}
    import uuid, os
    from PIL import Image

    PREV_DIR = "static/previews"
    os.makedirs(PREV_DIR, exist_ok=True)

    for key, img in variants.items():
        uid = uuid.uuid4().hex
        path = f"{PREV_DIR}/{uid}.png"
        img.save(path, "PNG")
        out[key] = "/" + path  # Serve via static

    return {"ok": True, "variants": out}
