# routers/crop_api.py
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse

from services.crop_service import process_image_bytes

router = APIRouter(prefix="/api", tags=["cropper"])

@router.post("/crop")
async def crop_endpoint(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        output_path = process_image_bytes(file_bytes)
        url = "/" + output_path.replace("\\", "/")
        return {"url": url}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
