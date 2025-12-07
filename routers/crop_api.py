# routers/crop_api.py
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from services.crop_pipeline import crop_image
from services.presets import PRESETS
from Cropanywhere.error_codes import ERR_INTERNAL

router = APIRouter(prefix="/api", tags=["cropper"])

@router.post("/crop")
async def crop_endpoint(
    file: UploadFile = File(...),
    preset: str = Form("auto"),
):
    try:
        preset = preset.lower().strip()

        if preset not in PRESETS:
            return JSONResponse(
                {
                    "error": f"Unknown preset '{preset}'. "
                             f"Valid presets: {list(PRESETS.keys())}",
                    "error_code": ERR_INTERNAL,
                },
                status_code=400,
            )

        file_bytes = await file.read()
        result, msg, code = crop_image(file_bytes, preset=preset)

        if not result:
            return JSONResponse(
                {"error": msg, "error_code": code},
                status_code=400,
            )

        # save
        out_path = f"static/results/crop_{abs(hash(file_bytes))}.png"
        result.save(out_path)

        return {
            "url": "/" + out_path,
            "preset": preset,
            "error_code": 0,
        }

    except Exception as e:
        return JSONResponse(
            {"error": str(e), "error_code": ERR_INTERNAL},
            status_code=500,
        )
