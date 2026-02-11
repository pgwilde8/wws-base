"""
Shared dependencies for routes: db engine, templates, session, auth helpers.
Import these in route modules so main.py stays minimal.
"""
import os
import time
from pathlib import Path
from typing import Optional, Dict

from typing import Generator

from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import bcrypt as _bcrypt
from openai import OpenAI

# Env and paths (assume main.py or app has already loaded dotenv)
_BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
SESSION_COOKIE = os.getenv("SESSION_COOKIE_NAME", "wws_session")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_MINUTES", "120")) * 60
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

engine = create_engine(DATABASE_URL, echo=False, future=True) if DATABASE_URL else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
templates = Jinja2Templates(directory=str(_BASE_DIR / "templates"))


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a DB session for ORM (e.g. RevenueService, Negotiation)."""
    if not SessionLocal:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(SECRET_KEY, salt="wws-session")


def sign_session(data: Dict) -> str:
    return _serializer().dumps(data)


def read_session(token: str) -> Optional[Dict]:
    if not token:
        return None
    try:
        return _serializer().loads(token, max_age=SESSION_TTL_SECONDS)
    except (BadSignature, SignatureExpired):
        return None


def hash_password(plain: str) -> str:
    """Hash for registration/bootstrap. Uses bcrypt directly (passlib incompatible with bcrypt 4.1+)."""
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        if not isinstance(hashed, bytes):
            hashed = hashed.encode("utf-8")
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed)
    except Exception:
        return hashed == plain


def get_user_by_email(email: str) -> Optional[Dict]:
    if not engine:
        return None
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT id, email, password_hash, role, is_active, created_at, last_login
            FROM webwise.users
            WHERE email = :email
        """), {"email": email}).mappings().first()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    if not engine:
        return None
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT id, email, password_hash, role, is_active, created_at, last_login
            FROM webwise.users
            WHERE id = :id
        """), {"id": user_id}).mappings().first()
        return dict(row) if row else None


def current_user(request: Request) -> Optional[Dict]:
    token = request.cookies.get(SESSION_COOKIE)
    data = read_session(token)
    if not data:
        return None
    user = get_user_by_id(data.get("uid"))
    if not user or not user.get("is_active"):
        return None
    return user


def require_admin(user: Optional[Dict] = Depends(current_user)) -> Dict:
    """
    Require admin authentication. Raises HTTPException if not authenticated or not admin.
    For HTML routes, check authentication manually and redirect to /admin/login.
    """
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def run_assistant_message(message: str, thread_id: Optional[str]) -> Dict:
    if not openai_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OpenAI client not configured")
    if not ASSISTANT_ID:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Assistant ID missing")
    if not message or len(message.strip()) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message required")
    if len(message) > 1000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message too long")

    if not thread_id:
        thread = openai_client.beta.threads.create()
        thread_id = thread.id

    openai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message.strip(),
    )

    run = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID,
    )

    start = time.time()
    while True:
        time.sleep(0.5)
        run_status = openai_client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id,
        )
        if run_status.status == "completed":
            break
        if run_status.status in {"failed", "cancelled", "expired"}:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Assistant run failed")
        if time.time() - start > 30:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Assistant timeout")

    msgs = openai_client.beta.threads.messages.list(thread_id=thread_id, limit=5, order="desc")
    reply = ""
    for m in msgs.data:
        if m.role == "assistant" and m.content:
            parts = []
            for c in m.content:
                if getattr(c, "type", None) == "text":
                    parts.append(c.text.value)
            reply = "".join(parts).strip()
            if reply:
                break

    if not reply:
        reply = "Sorry, no response generated."
    return {"reply": reply, "thread_id": thread_id}
