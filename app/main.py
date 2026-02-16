from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

# Load env before any app.routes import (so app.core.deps sees os.getenv)
try:
    from dotenv import load_dotenv
    base_dir = Path(__file__).resolve().parent.parent
    load_dotenv(base_dir / ".env")
except ImportError:
    pass

import os
if not os.getenv("DATABASE_URL"):
    base_dir = Path(__file__).resolve().parent.parent
    dotenv_path = base_dir / ".env"
    if dotenv_path.exists():
        for line in dotenv_path.read_text().splitlines():
            if line.strip().startswith("DATABASE_URL="):
                os.environ["DATABASE_URL"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

from app.routes import public_router, auth_router, admin_router, client_router, legal_router, ingest_router, api_router
from app.core.deps import templates

app = FastAPI(title="Green Candle Dispatch")

_BASE_DIR = Path(__file__).resolve().parent

# Map status codes to error template paths
_ERROR_TEMPLATES = {
    401: "errors/401.html",
    403: "errors/403.html",
    404: "errors/404.html",
    500: "errors/500.html",
    503: "errors/503.html",
}


def _wants_html(request: Request) -> bool:
    """Return True if the client prefers HTML (e.g. browser navigation)."""
    accept = (request.headers.get("accept") or "").lower()
    return "text/html" in accept and "application/json" not in accept.split(",")[0]


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/") or not _wants_html(request):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    template = _ERROR_TEMPLATES.get(exc.status_code, "errors/500.html")
    try:
        return templates.TemplateResponse(
            template,
            {"request": request, "detail": exc.detail},
            status_code=exc.status_code,
        )
    except Exception:
        return templates.TemplateResponse("errors/500.html", {"request": request}, status_code=500)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    if request.url.path.startswith("/api/") or not _wants_html(request):
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    return templates.TemplateResponse("errors/500.html", {"request": request}, status_code=500)
app.mount("/static", StaticFiles(directory=str(_BASE_DIR / "static")), name="static")

app.include_router(public_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(client_router)
app.include_router(legal_router)
app.include_router(ingest_router, prefix="/api/ingest", tags=["ingest"])
app.include_router(api_router)  # Scout heartbeat, etc.


@app.get("/test-error/{code}")
async def test_error(code: int):
    """Temporary: view error pages for design audit. Remove before production."""
    raise HTTPException(status_code=code)


@app.get("/{full_path:path}")
async def catch_all_404(request: Request, full_path: str):
    """Catch unmatched routes and return HTML 404 (Starlette returns JSON by default)."""
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    if not _wants_html(request):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return templates.TemplateResponse("errors/404.html", {"request": request}, status_code=404)


PORT = int(os.getenv("PORT", "8990"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
