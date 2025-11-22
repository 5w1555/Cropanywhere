# main.py

from contextlib import asynccontextmanager
from fastapi.responses import FileResponse
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import uvicorn
import logging
from time import time
from pathlib import Path
from typing import List, Optional
import json
import os
import shutil
import tempfile
from functools import lru_cache

from PIL import Image, ImageOps

from config import get_preset_labels, key_for_label, get_preset_by_key
from cropper import (
    get_face_and_landmarks,
    auto_crop,
    head_bust_crop,
    apply_aspect_ratio_filter,
    apply_filter,
)

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
DATA_PATH = BASE_DIR / "data" / "projects.json"

PREVIEW_DIR = STATIC_DIR / "previews"
OUTPUT_DIR = STATIC_DIR / "outputs"
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("uvicorn.error")


# Retention (in hours) for generated assets; keep downloads longer than previews
PREVIEW_RETENTION_HOURS = int(os.getenv("PREVIEW_RETENTION_HOURS", "48"))
OUTPUT_RETENTION_HOURS = int(os.getenv("OUTPUT_RETENTION_HOURS", "168"))  # one week


def cleanup_directory(path: Path, max_age_hours: int) -> None:
    """Remove files older than the retention window."""

    if max_age_hours <= 0:
        logger.info(
            "Skipping cleanup for %s because retention is disabled (<=0 hours)", path
        )
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
            logger.warning("Failed to evaluate %s for cleanup: %s", item, exc)
    if removed:
        logger.info("Cleaned %s old asset(s) from %s", removed, path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup/shutdown tasks using FastAPI's lifespan context."""

    cleanup_directory(PREVIEW_DIR, PREVIEW_RETENTION_HOURS)
    cleanup_directory(OUTPUT_DIR, OUTPUT_RETENTION_HOURS)
    yield


app = FastAPI(title="Marwane Wafik - Portfolio", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


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
    process_time = time() - start
    response.headers["X-Process-Time"] = f"{process_time:.3f}s"
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    featured = projects_data[:2]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "projects": featured,
            "name": "Visitor",
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
            "title": "Projects | Marwane Wafik",
            "year": 2025,
        },
    )


@app.get("/projects/{slug}", response_class=HTMLResponse)
async def project_detail(request: Request, slug: str):
    project = next((p for p in projects_data if p["slug"] == slug), None)
    if not project:
        return templates.TemplateResponse(
            "project_detail.html",
            {
                "request": request,
                "error": True,
                "title": "Project not found",
                "year": 2025,
            },
        )
    return templates.TemplateResponse(
        "project_detail.html",
        {
            "request": request,
            "project": project,
            "title": project["title"],
            "year": 2025,
        },
    )


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(
        "about.html",
        {
            "request": request,
            "title": "About | Marwane Wafik",
            "year": 2025,
        },
    )

@app.on_event("startup")
async def startup_cleanup():
    """Remove stale preview and output artifacts on startup."""

    cleanup_directory(PREVIEW_DIR, PREVIEW_RETENTION_HOURS)
    cleanup_directory(OUTPUT_DIR, OUTPUT_RETENTION_HOURS)


@app.get("/api/hello")
async def api_hello(name: str = "Marwane"):
    return {"message": f"Hello, {name}!"}


@app.get("/crop", response_class=HTMLResponse)
async def crop_page(request: Request):
    preset_labels = get_preset_labels()
    return templates.TemplateResponse(
        "crop.html",
        {
            "request": request,
            "title": "CropAnywhere",
            "year": 2025,
            "preset_labels": preset_labels,
        },
    )


def parse_ratio(r: Optional[str]) -> Optional[float]:
    if r is None:
        return None
    if isinstance(r, str):
        s = r.strip().lower()
        if s in ("", "none", "null"):
            return None
        if ":" in s:
            w, h = s.split(":", 1)
            try:
                return float(w) / float(h)
            except Exception:
                return None
        try:
            return float(s)
        except Exception:
            return None
    return None


@lru_cache(maxsize=16)
def cached_preview(
    img_path: str,
    preset_label: str,
    margin: int,
    ratio: Optional[float],
    filter_name: str,
    intensity: int,
    rotate: bool,
):
    key = key_for_label(preset_label)
    method = "headbust" if key == "headbust" else "auto"
    if method == "headbust":
        cropped = head_bust_crop(img_path, int(margin), ratio, 0.3)
    else:
        box, lm, cv, pil, meta = get_face_and_landmarks(
            img_path,
            conf_threshold=0.3,
            sharpen=True,
            apply_rotation=rotate,
            model=None,
        )
        if box is None:
            return None, "❌ No face detected."
        cropped = auto_crop(
            pil,
            frontal_margin=int(margin),
            profile_margin=int(margin),
            box=box,
            landmarks=lm,
            metadata=meta,
        )
        if ratio and cropped:
            cropped = apply_aspect_ratio_filter(cropped, ratio)
    if cropped is None:
        return None, "❌ Crop failed."
    return apply_filter(cropped, filter_name, intensity), "✅ Preview generated."


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.ico")

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
        # Save upload to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        # Before image
        try:
            before_img = ImageOps.exif_transpose(Image.open(tmp_path))
            before_img.thumbnail((720, 720))
        except Exception as e:
            os.remove(tmp_path)
            return JSONResponse(
                status_code=400,
                content={"error": f"❌ Failed to load original: {e}"},
            )

        ratio = parse_ratio(aspect_ratio)
        after_img, msg = cached_preview(
            tmp_path,
            preset_label,
            margin,
            ratio,
            filter_name,
            intensity,
            rotate,
        )

        if after_img:
            after_img.thumbnail((720, 720))

        # Save preview images into static/previews
        run_id = os.path.splitext(os.path.basename(tmp_path))[0]

        before_name = f"{run_id}_before.png"
        after_name = f"{run_id}_after.png"

        before_path = PREVIEW_DIR / before_name
        after_path = PREVIEW_DIR / after_name

        before_img.save(before_path)
        if after_img:
            after_img.save(after_path)

        os.remove(tmp_path)

        if after_img is None:
            return JSONResponse(
                status_code=200,
                content={
                    "error": msg,
                    "before_url": f"/static/previews/{before_name}",
                    "after_url": None,
                },
            )

        return {
            "message": msg,
            "before_url": f"/static/previews/{before_name}",
            "after_url": f"/static/previews/{after_name}",
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"❌ Preview failed: {e}"},
        )


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
        return JSONResponse(
            status_code=400,
            content={"error": "❌ No files uploaded.", "processed": 0, "total": 0},
        )

    key = key_for_label(preset_label)
    method = "headbust" if key == "headbust" else "auto"
    ratio = parse_ratio(aspect_ratio)

    run_id = next(tempfile._get_candidate_names())
    job_dir = OUTPUT_DIR / run_id
    job_dir.mkdir(parents=True, exist_ok=True)

    total = len(files)
    processed = 0

    for f in files:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f.filename) as tmp:
                tmp.write(await f.read())
                tmp_path = tmp.name

            img_path = tmp_path

            if method == "headbust":
                bust = head_bust_crop(img_path, int(margin), ratio, 0.3)
            else:
                box, lm, cv, pil, meta = get_face_and_landmarks(
                    img_path,
                    conf_threshold=0.3,
                    sharpen=True,
                    apply_rotation=rotate,
                    model=None,
                )
                if box is None:
                    os.remove(tmp_path)
                    continue
                bust = auto_crop(
                    pil,
                    frontal_margin=int(margin),
                    profile_margin=int(margin),
                    box=box,
                    landmarks=lm,
                    metadata=meta,
                )
                if ratio and bust:
                    bust = apply_aspect_ratio_filter(bust, ratio)

            if bust is None:
                os.remove(tmp_path)
                continue

            out_img = apply_filter(bust, filter_name, intensity)

            base_name, ext = os.path.splitext(os.path.basename(f.filename))
            out_name = f"{base_name}_cropped{ext or '.png'}"
            out_path = job_dir / out_name
            out_img.save(out_path)

            processed += 1
            os.remove(tmp_path)
        except Exception:
            continue

    if processed == 0:
        shutil.rmtree(job_dir, ignore_errors=True)
        return JSONResponse(
            status_code=200,
            content={
                "error": "❌ No faces detected.",
                "processed": 0,
                "total": total,
            },
        )

    zip_base = OUTPUT_DIR / f"{run_id}_cropped"
    zip_path = shutil.make_archive(str(zip_base), "zip", job_dir)

    zip_url = f"/static/outputs/{Path(zip_path).name}"
    
    shutil.rmtree(job_dir, ignore_errors=True)

    return {
        "message": f"✅ Processed {processed}/{total}!",
        "zip_url": zip_url,
        "processed": processed,
        "total": total,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
