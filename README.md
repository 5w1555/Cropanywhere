<p align="center">
  <img src="static/favicon.ico" width="64" alt="CropAnyware logo"/>
</p>

<h1 align="center">CropAnyware</h1>

## Overview

CropAnyware is a fast, fault-tolerant, face-aware cropping engine with a lightweight FastAPI web interface.

It provides intelligent automatic cropping using RetinaFace detection and tuned strategies (frontal, profile, bust, chin-weighted), with accurate color handling and robust performance on imperfect real-world images.

The project functions as:

- a **self-hosted image processing toolkit**
- the core of a **future SaaS service**

Compact architecture. No Node. No build pipeline. Deploys anywhere.

---

## Features

- RetinaFace-based face detection  
- Smart cropping strategies (frontal, profile, bust, chin-weighted)  
- Batch-safe and fault-tolerant pipeline  
- ICC-aware, color-accurate handling  
- HEIC/RAW support via Pillow plugins  
- FastAPI backend + Jinja2 templates  
- Vanilla JS front-end  
- Preview + result export  
- REST API for automation  

---
