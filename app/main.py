from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

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

from app.routes import public_router, auth_router, admin_router, client_router, legal_router, ingest_router

app = FastAPI(title="Green Candle Dispatch")

_BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(_BASE_DIR / "static")), name="static")

app.include_router(public_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(client_router)
app.include_router(legal_router)
app.include_router(ingest_router)  # Chrome Extension ingestion endpoint

PORT = int(os.getenv("PORT", "8990"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
