# Pro CV Website — FastAPI skeleton

This is a minimal FastAPI website skeleton (single-file app + templates/static) to get started.

Quick start (Windows, cmd.exe):

1. Create and activate a virtual environment

   python -m venv .venv
   .venv\Scripts\activate

2. Install dependencies

   pip install -r requirements.txt

3. Run the app (development, auto-reload):

   python main.py

Or run with uvicorn directly:

   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

Open http://127.0.0.1:8000 in your browser.

Files added:
- `main.py` - FastAPI app
- `templates/index.html` - sample Jinja2 template
- `static/style.css` - minimal styling
- `requirements.txt` - dependencies

Next steps (optional):
- Add more routes and templates
- Add tests
- Add CI and Dockerfile if you want to deploy
