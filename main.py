from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from services.presets import PRESETS, get_preset_labels

from datetime import datetime, timedelta
from time import time
from pathlib import Path
from typing import List, Optional
import uvicorn
import logging
import json
import os
import shutil
import tempfile
import io

from PIL import Image, ImageOps

from services.crop_pipeline import crop_image
from services.presets import PRESETS
from config import get_preset_labels  # UI display



from error_codes import (
    ERR_CROP_FAIL,
    ERR_INTERNAL,
    ERR_NO_FACE,
    ERR_READ_FAIL,
    ERR_SAVE_FAIL,
)

# --------------------------------------------------------------------
# Directories / Static
# --------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
DATA_PATH = BASE_DIR / "data" / "projects.json"

PREVIEW_DIR = STATIC_DIR / "previews"
OUTPUT_DIR = STATIC_DIR / "outputs"
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("uvicorn.error")

PREVIEW_RETENTION_HOURS = int(os.getenv("PREVIEW_RETENTION_HOURS", "48"))
OUTPUT_RETENTION_HOURS = int(os.getenv("OUTPUT_RETENTION_HOURS", "168"))  # 1 week


# --------------------------------------------------------------------
# File Cleanup
# --------------------------------------------------------------------
def cleanup_directory(path: Path, max_age_hours: int) -> None:
    """Remove files older than the retention window."""

    if max_age_hours <= 0:
        logger.info("Skipping cleanup for %s (disabled).", path)
        return

    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    removed = 0

    for item in path.iterdir():
        try:
            mtime = datetime.utcfromtimestamp(item.stat().st_mtime)
            if mtime < cutoff:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
                removed += 1
        except Exception as exc:
            logger.warning("Failed cleanup %s: %s", item, exc)

    if removed:
        logger.info("Cleaned %s old asset(s) from %s", removed, path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_directory(PREVIEW_DIR, PREVIEW_RETENTION_HOURS)
    cleanup_directory(OUTPUT_DIR, OUTPUT_RETENTION_HOURS)
    yield


app = FastAPI(title="Marwane Wafik - Portfolio", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

from routers.preview_router import preview_router
app.include_router(preview_router)



# --------------------------------------------------------------------
# Project Loader
# --------------------------------------------------------------------
def load_projects():
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load projects.json: {e}")
        return []


projects_data = load_projects()


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{time() - start:.3f}s"
    return response


# --------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "projects": projects_data[:2],
            "year": 2025,
            "title": "Home | Marwane Wafik",
        },
    )


@app.get("/projects", response_class=HTMLResponse)
async def projects(request: Request):
    return templates.TemplateResponse(
        "projects.html",
        {
            "request": request,
            "projects": projects_data,
            "year": 2025,
            "title": "Projects | Marwane Wafik",
        },
    )


@app.get("/projects/{slug}", response_class=HTMLResponse)
async def project_detail(request: Request, slug: str):
    project = next((p for p in projects_data if p["slug"] == slug), None)
    return templates.TemplateResponse(
        "project_detail.html",
        {
            "request": request,
            "project": project,
            "error": project is None,
            "title": project["title"] if project else "Project not found",
            "year": 2025,
        },
    )


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(
        "about.html",
        {"request": request, "title": "About | Marwane Wafik", "year": 2025},
    )


@app.on_event("startup")
async def startup_cleanup():
    cleanup_directory(PREVIEW_DIR, PREVIEW_RETENTION_HOURS)
    cleanup_directory(OUTPUT_DIR, OUTPUT_RETENTION_HOURS)


@app.get("/api/hello")
async def api_hello(name: str = "Marwane"):
    return {"message": f"Hello, {name}!"}

@app.get("/crop", response_class=HTMLResponse)
async def crop_page(request: Request):
    return templates.TemplateResponse(
        "crop.html",
        {
            "request": request,
            "title": "CropAnywhere",
            "year": 2025,
            "preset_labels": get_preset_labels(),  
            "presets_json": PRESETS,               
        },
    )



# --------------------------------------------------------------------
# Util: ratio conversion
# --------------------------------------------------------------------
def parse_ratio(r: Optional[str]) -> Optional[float]:
    if not r:
        return None
    s = r.strip().lower()
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


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")


# --------------------------------------------------------------------
# PREVIEW
# --------------------------------------------------------------------
@app.post("/api/crop/preview")
async def api_crop_preview(
    preset_label: str = Form(...),
    margin: int = Form(30),
    filter_name: str = Form("None"),
    intensity: int = Form(50),
    aspect_ratio: Optional[str] = Form(None),
    rotate: bool = Form(True),
    file: UploadFile = File(...),
):
    try:
        file_bytes = await file.read()
        ratio = parse_ratio(aspect_ratio)

        img, msg, code = crop_image(
            file_bytes,
            preset=preset_label,
            margin=margin,
            ratio=ratio,
            rotate=rotate,
            filter_name=filter_name,
            intensity=intensity,
        )

        import uuid
        uid = uuid.uuid4().hex

        before_path = PREVIEW_DIR / f"{uid}_before.png"
        after_path = PREVIEW_DIR / f"{uid}_after.png"

        before = ImageOps.exif_transpose(Image.open(io.BytesIO(file_bytes)))
        before.thumbnail((720, 720))
        before.save(before_path)

        if img:
            img.thumbnail((720, 720))
            img.save(after_path)
            return {
                "message": msg,
                "before_url": f"/static/previews/{before_path.name}",
                "after_url": f"/static/previews/{after_path.name}",
                "error_code": 0,
            }

        return {
            "error": msg,
            "before_url": f"/static/previews/{before_path.name}",
            "after_url": None,
            "error_code": code,
        }

    except Exception as e:
        return JSONResponse({"error": f"❌ Preview failed: {e}", "error_code": 500})


# --------------------------------------------------------------------
# BATCH PROCESS
# --------------------------------------------------------------------
@app.post("/api/crop/process")
async def api_crop_process(
    preset_label: str = Form(...),
    margin: int = Form(30),
    filter_name: str = Form("None"),
    intensity: int = Form(50),
    aspect_ratio: Optional[str] = Form(None),
    rotate: bool = Form(True),
    files: List[UploadFile] = File(...),
):
    if not files:
        return {"error": "❌ No files uploaded.", "processed": 0, "total": 0, "error_code": ERR_READ_FAIL}

    ratio = parse_ratio(aspect_ratio)
    import uuid

    run_id = uuid.uuid4().hex
    job_dir = OUTPUT_DIR / run_id
    job_dir.mkdir(exist_ok=True)

    processed = 0
    last_error = 0

    for f in files:
        file_bytes = await f.read()
        img, _, code = crop_image(
            file_bytes,
            preset=preset_label,
            margin=margin,
            ratio=ratio,
            rotate=rotate,
            filter_name=filter_name,
            intensity=intensity,
        )

        if img:
            img.save(job_dir / f"{Path(f.filename).stem}_cropped.png")
            processed += 1
        else:
            last_error = code

    if processed == 0:
        shutil.rmtree(job_dir, ignore_errors=True)
        return {"error": "❌ No faces detected.", "processed": 0, "total": len(files), "error_code": last_error or ERR_NO_FACE}

    zip_path = shutil.make_archive(str(job_dir), "zip", job_dir)
    shutil.rmtree(job_dir, ignore_errors=True)

    return {"message": f"✅ Processed {processed}/{len(files)}!", "zip_url": f"/static/outputs/{Path(zip_path).name}", "processed": processed, "total": len(files), "error_code": 0}


# --------------------------------------------------------------------
# SERVER ENTRY
# --------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
