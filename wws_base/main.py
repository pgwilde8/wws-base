from fastapi import FastAPI, Request, APIRouter, Form, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.hash import bcrypt
from openai import OpenAI
from pathlib import Path
import os
import time
from typing import Optional, Dict

# define app first
app = FastAPI(title="WebWise Solutions Base Template")

# optional: define a router if you want to group routes
router = APIRouter()
templates = Jinja2Templates(directory="/srv/projects/wws-base/wws_base/templates")

# Database connection
try:
    from dotenv import load_dotenv
    base_dir = Path(__file__).resolve().parent.parent
    load_dotenv(base_dir / ".env")
except ImportError:
    pass

# Fallback manual load if dotenv isn't installed
if not os.getenv("DATABASE_URL"):
    base_dir = Path(__file__).resolve().parent.parent
    dotenv_path = base_dir / ".env"
    if dotenv_path.exists():
        for line in dotenv_path.read_text().splitlines():
            if line.strip().startswith("DATABASE_URL="):
                os.environ["DATABASE_URL"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=False, future=True) if DATABASE_URL else None
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
SESSION_COOKIE = os.getenv("SESSION_COOKIE_NAME", "wws_session")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_MINUTES", "120")) * 60
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# mount static folder
app.mount("/static", StaticFiles(directory="/srv/projects/wws-base/wws_base/static"), name="static")

# session helpers
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


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.verify(plain, hashed)
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
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return user


def _run_assistant_message(message: str, thread_id: Optional[str]) -> Dict:
    if not openai_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OpenAI client not configured")
    if not ASSISTANT_ID:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Assistant ID missing")
    if not message or len(message.strip()) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message required")
    if len(message) > 1000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message too long")

    thread = None
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

# public home page
@router.get("/")
def home_page(request: Request):
    testimonials = []
    if engine:
        with engine.begin() as conn:
            rows = conn.execute(text("""
                SELECT id, client_name, testimonial_text, rating, event_type, created_at
                FROM webwise.testimonials
                WHERE is_approved = true
                ORDER BY created_at DESC
            """))
            testimonials = [dict(r._mapping) for r in rows]
    return templates.TemplateResponse("public/index.html", {"request": request, "testimonials": testimonials})

@router.get("/about")
def about_page(request: Request):
    return templates.TemplateResponse("public/about.html", {"request": request})

@router.get("/services")
def services_page(request: Request):
    return templates.TemplateResponse("public/services.html", {"request": request})

@router.get("/faq")
def faq_page(request: Request):
    return templates.TemplateResponse("public/faq.html", {"request": request})

@router.get("/contact")
def contact_page(request: Request):
    return templates.TemplateResponse("public/contact.html", {"request": request})

@router.get("/privacy-policy")
def privacy_policy(request: Request):
    return templates.TemplateResponse("public/privacy-policy.html", {"request": request})

@router.get("/terms-of-service")
def terms_of_service(request: Request):
    return templates.TemplateResponse("public/term-of-service.html", {"request": request})

# login choice page
@router.get("/login")
def login_choice(request: Request):
    return templates.TemplateResponse("auth/login-choice.html", {"request": request})

# admin login
@router.get("/login/admin")
def admin_login_page(request: Request):
    return templates.TemplateResponse("auth/admin-login.html", {"request": request})

@router.post("/auth/admin")
def auth_admin(request: Request, username: str = Form(...), password: str = Form(...)):
    user = get_user_by_email(username)
    if not user or user.get("role") != "admin" or not user.get("is_active"):
        return templates.TemplateResponse("auth/admin-login.html", {"request": request, "error": "Invalid credentials"})
    if not verify_password(password, user.get("password_hash", "")):
        return templates.TemplateResponse("auth/admin-login.html", {"request": request, "error": "Invalid credentials"})

    session_token = sign_session({"uid": user["id"], "role": user["role"], "email": user["email"]})
    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(SESSION_COOKIE, session_token, httponly=True, secure=False, samesite="lax", max_age=SESSION_TTL_SECONDS)
    return response

# client login
@router.get("/login/client")
def client_login_page(request: Request):
    return templates.TemplateResponse("auth/client-login.html", {"request": request})

@router.post("/auth/client")
def auth_client(request: Request, email: str = Form(...), password: str = Form(...)):
    user = get_user_by_email(email)
    if not user or user.get("role") != "client" or not user.get("is_active"):
        return templates.TemplateResponse("auth/client-login.html", {"request": request, "error": "Invalid credentials"})
    if not verify_password(password, user.get("password_hash", "")):
        return templates.TemplateResponse("auth/client-login.html", {"request": request, "error": "Invalid credentials"})

    session_token = sign_session({"uid": user["id"], "role": user["role"], "email": user["email"]})
    response = RedirectResponse(url="/clients/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(SESSION_COOKIE, session_token, httponly=True, secure=False, samesite="lax", max_age=SESSION_TTL_SECONDS)
    return response

# testimonials routes
@router.get("/testimonials")
def testimonials_page(request: Request):
    if engine:
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT id, client_name, email, client_location, website_url, 
                       event_type, rating, testimonial_text, created_at 
                FROM webwise.testimonials 
                WHERE is_approved = true 
                ORDER BY created_at DESC
            """))
            testimonials = [dict(row._mapping) for row in result]
    else:
        testimonials = []
    return templates.TemplateResponse("public/testimonials.html", {"request": request, "testimonials": testimonials})

@router.get("/testimonials/submit")
def testimonials_submit_page(request: Request):
    return templates.TemplateResponse("public/testimonials-submit.html", {"request": request})

@router.post("/testimonials/submit")
def testimonials_submit(
    request: Request,
    client_name: str = Form(...),
    testimonial_text: str = Form(...),
    email: str = Form(None),
    client_location: str = Form(None),
    website_url: str = Form(None),
    event_type: str = Form(None),
    rating: int = Form(None)
):
    if not engine:
        return templates.TemplateResponse("public/testimonials-submit.html", {
            "request": request, 
            "error": True, 
            "message": "Database not configured"
        })
    
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO webwise.testimonials 
                (client_name, email, client_location, website_url, event_type, rating, testimonial_text, is_approved) 
                VALUES (:client_name, :email, :client_location, :website_url, :event_type, :rating, :testimonial_text, false)
            """), {
                "client_name": client_name,
                "email": email or None,
                "client_location": client_location or None,
                "website_url": website_url or None,
                "event_type": event_type or None,
                "rating": rating,
                "testimonial_text": testimonial_text
            })
        
        return templates.TemplateResponse("public/testimonials-submit.html", {
            "request": request,
            "success": True,
            "message": "Thank you! Your testimonial has been submitted and will be reviewed shortly."
        })
    except Exception as e:
        return templates.TemplateResponse("public/testimonials-submit.html", {
            "request": request,
            "error": True,
            "message": f"An error occurred: {str(e)}"
        })


@router.post("/api/chat")
async def chat_api(payload: Dict):
    message = (payload.get("message") if payload else "") or ""
    thread_id = (payload.get("thread_id") if payload else None)
    result = _run_assistant_message(message, thread_id)
    return result

# logout and protected pages
@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE)
    return response


# protected pages
@router.get("/admin/dashboard", dependencies=[Depends(require_admin)])
def admin_dashboard(request: Request):
    stats = {
        "projects": 0,
        "published": 0,
        "pending": 0,
        "uptime": "99.9%",
    }
    pending = []
    if engine:
        with engine.begin() as conn:
            stats["projects"] = conn.execute(text("SELECT COUNT(*) FROM webwise.projects;")).scalar() or 0
            stats["published"] = conn.execute(text("SELECT COUNT(*) FROM webwise.testimonials WHERE is_approved = true;")); stats["published"] = stats["published"].scalar() or 0
            stats["pending"] = conn.execute(text("SELECT COUNT(*) FROM webwise.testimonials WHERE is_approved = false;")); stats["pending"] = stats["pending"].scalar() or 0
            rows = conn.execute(text("""
                SELECT id, client_name, event_type, rating, testimonial_text, created_at
                FROM webwise.testimonials
                WHERE is_approved = false
                ORDER BY created_at DESC
                LIMIT 5
            """))
            pending = [dict(r._mapping) for r in rows]
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "stats": stats, "pending": pending})


@router.post("/admin/testimonials/{testimonial_id}/approve", dependencies=[Depends(require_admin)])
def approve_testimonial(testimonial_id: int):
    if not engine:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database not configured")
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE webwise.testimonials
            SET is_approved = true
            WHERE id = :id
        """), {"id": testimonial_id})
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/testimonials/{testimonial_id}/reject", dependencies=[Depends(require_admin)])
def reject_testimonial(testimonial_id: int):
    if not engine:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database not configured")
    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM webwise.testimonials
            WHERE id = :id
        """), {"id": testimonial_id})
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/clients/dashboard")
def client_dashboard(request: Request, user: Optional[Dict] = Depends(current_user)):
    if not user or user.get("role") != "client":
        return RedirectResponse(url="/login/client", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("clients/dashboard.html", {"request": request, "user": user})


# include router into app
app.include_router(router)
