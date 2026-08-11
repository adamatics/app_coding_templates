"""FastAPI application: API + static frontend in one process (spec §2, §12). CHASSIS.

Responsibilities:
* migrate/seed on startup (works against an empty, mounted DATA_DIR);
* serve the built React app (Vite `base: './'`) alongside the API. AdaLab serves the app
  under `/apps/<slug>/` with `stripped_prefix: true`, so the backend only ever sees stripped
  paths (`/`, `/assets/...`, `/api/...`); the frontend discovers its own base path from the
  URL at runtime (see `frontend/src/lib/basepath.ts`), so no injection is needed here;
* translate service-layer errors into clean HTTP responses.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from .config import settings
from .db import SessionLocal, init_db
from .routers import admin, export, public
from .seed_demo import seed_demo_data
from .services import ServiceError

STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if settings.demo_mode:
        with SessionLocal() as session:
            seed_demo_data(session)
    yield


app = FastAPI(
    title=settings.exercise_title,
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(ServiceError)
async def _service_error_handler(_request: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(public.router)
app.include_router(admin.router)
app.include_router(export.router)


@app.get("/api/health", tags=["public"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# --- static frontend --------------------------------------------------------
def _serve_index() -> HTMLResponse | FileResponse:
    if INDEX_HTML.is_file():
        return FileResponse(INDEX_HTML)
    return HTMLResponse(
        "<h1>Frontend not built</h1><p>Run <code>npm run build</code> in "
        "<code>frontend/</code> (the Containerfile does this automatically).</p>",
        status_code=200,
    )


@app.get("/", include_in_schema=False)
def index():
    return _serve_index()


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    """Serve real static files if they exist; otherwise the SPA shell (client routing)."""
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    if STATIC_DIR.is_dir():
        candidate = (STATIC_DIR / full_path).resolve()
        static_root = STATIC_DIR.resolve()
        if candidate.is_file() and os.path.commonpath([candidate, static_root]) == str(static_root):
            return FileResponse(candidate)
    return _serve_index()
