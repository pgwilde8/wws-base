from fastapi import APIRouter, Request, Form, status, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from app.core.deps import (
    templates,
    engine,
    get_user_by_email,
    hash_password,
    verify_password,
    sign_session,
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
)

router = APIRouter()


@router.get("/login")
def login_choice(request: Request):
    return templates.TemplateResponse("auth/login-choice.html", {"request": request})


@router.get("/login/admin")
def admin_login_page(request: Request):
    return templates.TemplateResponse("auth/admin-login.html", {"request": request})


@router.post("/auth/admin")
def auth_admin(request: Request, username: str = Form(...), password: str = Form(...)):
    user = get_user_by_email(username)
    if not user or user.get("role") != "admin" or not user.get("is_active"):
        return templates.TemplateResponse(
            "auth/admin-login.html", {"request": request, "error": "Invalid credentials"}
        )
    if not verify_password(password, user.get("password_hash", "")):
        return templates.TemplateResponse(
            "auth/admin-login.html", {"request": request, "error": "Invalid credentials"}
        )

    session_token = sign_session({"uid": user["id"], "role": user["role"], "email": user["email"]})
    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE, session_token, httponly=True, secure=False, samesite="lax", max_age=SESSION_TTL_SECONDS
    )
    return response


@router.get("/login/client")
def client_login_page(request: Request):
    return templates.TemplateResponse("auth/client-login.html", {"request": request})


@router.post("/auth/client")
def auth_client(request: Request, email: str = Form(...), password: str = Form(...)):
    user = get_user_by_email(email)
    if not user or user.get("role") != "client" or not user.get("is_active"):
        return templates.TemplateResponse(
            "auth/client-login.html", {"request": request, "error": "Invalid credentials"}
        )
    if not verify_password(password, user.get("password_hash", "")):
        return templates.TemplateResponse(
            "auth/client-login.html", {"request": request, "error": "Invalid credentials"}
        )

    session_token = sign_session({"uid": user["id"], "role": user["role"], "email": user["email"]})
    response = RedirectResponse(url="/clients/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE, session_token, httponly=True, secure=False, samesite="lax", max_age=SESSION_TTL_SECONDS
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/auth/register-trucker")
@router.get("/register-trucker")
def register_trucker_page(request: Request):
    return templates.TemplateResponse("auth/register-trucker.html", {"request": request})


@router.post("/auth/register-trucker")
@router.post("/register-trucker")
def register_trucker(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    mc_number: str = Form(...),
    carrier_name: str = Form(...),
    truck_identifier: str = Form(""),
):
    """Create user (role=client) and TruckerProfile in one step. MC Number = industry ID."""
    if get_user_by_email(email):
        return templates.TemplateResponse(
            "auth/register-trucker.html",
            {"request": request, "error": "Email already registered."},
        )
    if not engine:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
    try:
        password_hash = hash_password(password)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not hash password")
    with engine.begin() as conn:
        r = conn.execute(
            text("""
                INSERT INTO webwise.users (email, password_hash, role, is_active)
                VALUES (:email, :password_hash, 'client', true)
                RETURNING id
            """),
            {"email": email.strip().lower(), "password_hash": password_hash},
        )
        row = r.one()
        user_id = row.id
        conn.execute(
            text("""
                INSERT INTO webwise.trucker_profiles (user_id, display_name, mc_number, carrier_name, truck_identifier)
                VALUES (:user_id, :display_name, :mc_number, :carrier_name, :truck_identifier)
            """),
            {
                "user_id": user_id,
                "display_name": display_name.strip(),
                "mc_number": mc_number.strip(),
                "carrier_name": carrier_name.strip(),
                "truck_identifier": (truck_identifier or "").strip() or None,
            },
        )
    session_token = sign_session({"uid": user_id, "role": "client", "email": email.strip().lower()})
    response = RedirectResponse(url="/clients/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE, session_token, httponly=True, secure=False, samesite="lax", max_age=SESSION_TTL_SECONDS
    )
    return response
