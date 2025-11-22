<p align="center">
  <img src="static/favicon.ico" width="64" alt="CropAnyware logo"/>
</p>

<h1 align="center">CropAnyware</h1>

## Overview

CropAnyware is a fast, fault-tolerant, face-aware cropping engine with a lightweight FastAPI web interface.

It provides intelligent automatic cropping using RetinaFace detection and tuned strategies (frontal, profile, bust, chin-weighted), with accurate color handling and robust performance on imperfect real-world images.

The project functions as:

* a **self-hosted image processing toolkit**
* the core of a **future SaaS service**

Compact architecture. No Node. No build pipeline. Deploys anywhere.

---

## Features

* RetinaFace-based face detection
* Smart cropping strategies (frontal, profile, bust, chin-weighted)
* Batch-safe and fault-tolerant pipeline
* ICC-aware, color-accurate handling
* HEIC/RAW support via Pillow plugins
* FastAPI backend + Jinja2 templates
* Vanilla JS front-end
* Preview + result export
* REST API for automation

---

## Prerequisites

* Python **3.10+** (tested with the CPU-only pipeline)
* A C/C++ build chain for scientific packages (e.g., `build-essential` on Debian/Ubuntu)
* Optional system libraries for extended formats:

  * HEIC/HEIF: `libheif`/`libde265` (required by `pillow-heif`)
  * RAW: `libraw` if you plan to enable `rawpy`

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt \
  torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
  retinaface opencv-python pillow-heif rawpy piexif
```

* `pillow-heif` and `rawpy` are optional but recommended for HEIC/RAW ingestion. If you skip them, those formats will fall back to basic handling.
* The app stores temporary uploads and outputs under `static/previews` and `static/outputs`; they are created automatically.

## RetinaFace weights

The face detector loads `retinaface_resnet50.pt` from the repository root when available and otherwise downloads pretrained weights.

* Fast path (online): the first run will download weights automatically through `retinaface.pre_trained_models.get_model`.
* Offline/manual cache: place `retinaface_resnet50.pt` next to `cropper.py` to skip network access. You can pre-cache it with:

```bash
python - <<'PY'
from retinaface.pre_trained_models import get_model
from pathlib import Path
import torch

weights_path = Path.cwd() / "retinaface_resnet50.pt"
model = get_model("resnet50_2020-07-20", max_size=2048, device="cpu")
model.eval()
torch.save(model.model.state_dict(), weights_path)
print(f"Saved {weights_path}")
PY
```

## Running the FastAPI server

Development (auto-reload):

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000` for the landing page and `http://localhost:8000/crop` for the cropper UI. Static assets are served from `/static` via FastAPI's built-in `StaticFiles` mount.

## Using the web UI

1. Visit `/crop`.
2. Choose a preset, adjust margin/aspect ratio/filters, and drag-drop images.
3. **Preview** sends the first image to `/api/crop/preview` and shows before/after thumbnails.
4. **Process All** sends the batch to `/api/crop/process` and returns a ZIP link with cropped results.

## API endpoints

* `GET /api/hello` — simple health/hello response.
* `POST /api/crop/preview` — multipart form with `file`, `preset_label`, `margin`, `filter_name`, `intensity`, `aspect_ratio`, `rotate`; returns preview URLs.
* `POST /api/crop/process` — multipart form with `files` (one or many) plus the same options; returns a ZIP download URL and counters.

Example preview request:

```bash
curl -X POST http://localhost:8000/api/crop/preview \
  -F preset_label="Frontal" \
  -F margin=30 \
  -F aspect_ratio="4:5" \
  -F rotate=true \
  -F file=@/path/to/input.jpg
```

## Production deployment tips

* Use a process manager with Uvicorn workers (Gunicorn example):

```bash
gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 main:app
```

* Keep `/static` behind a reverse proxy (e.g., NGINX) for efficient asset and ZIP delivery; FastAPI already mounts the directory.
* Persist `static/outputs` if you need to keep generated ZIPs beyond a single process restart.
* Set `UVICORN_LOG_LEVEL=info` and consider turning off `--reload` in production.

## Troubleshooting

* **HEIC not loading**: install `pillow-heif` and ensure `libheif`/`libde265` are present; restart after installation.
* **RAW files rejected**: install `rawpy` (and system `libraw`) so optional RAW decoding is enabled.
* **Model download blocked**: pre-save `retinaface_resnet50.pt` as shown above or copy an existing checkpoint into the repository root to avoid runtime downloads.

---

## License

All rights reserved.

This software is provided for evaluation only. Commercial use, redistribution, modification, or integration into other products is prohibited without prior written permission from the owner.
