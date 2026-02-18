from fastapi import APIRouter, Request, Form, Depends, status, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import (
    templates,
    engine,
    get_db,
    get_user_by_email,
    hash_password,
    verify_password,
    sign_session,
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
)
from app.models.user import User

router = APIRouter()


@router.get("/login")
def login_choice(request: Request):
    return templates.TemplateResponse("auth/login-choice.html", {"request": request})

@router.get("/admin/login")
def admin_login_page(request: Request):
    """Admin login page - accessible at both /login/admin and /admin/login"""
    return templates.TemplateResponse("admin/login.html", {"request": request})


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
    response = RedirectResponse(url="/drivers/dashboard", status_code=status.HTTP_303_SEE_OTHER)
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


@router.get("/century/register-trucker")
def century_register_trucker_page(request: Request):
    """Century flow: register page. Pass manually to drivers for Alma experience."""
    return templates.TemplateResponse("auth/century_register_trucker.html", {"request": request})


@router.post("/auth/register-trucker")
@router.post("/register-trucker")
def register_trucker(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    mc_number: str = Form(""),
    dot_number: str = Form(""),
    authority_type: str = Form("MC"),  # "MC" or "DOT"
    carrier_name: str = Form(...),
    truck_identifier: str = Form(""),
    # NEW FORM INPUTS FOR FACTORING:
    has_factoring: str = Form("no"),  # "yes" or "no" (default to "no")
    factoring_company_name: str = Form(None),  # If yes, the company name
    interested_in_otr: str = Form(None),  # If no, checkbox value (e.g., "on" or None)
):
    """
    Create user (role=client) and TruckerProfile in one step. MC Number = industry ID.
    Now includes factoring company and referral status tracking.
    """
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
    
    # 1. Determine the Referral Status and Factoring Company
    referral_status = "NONE"
    factoring_co = None

    if has_factoring == "yes" and factoring_company_name:
        factoring_co = factoring_company_name.strip()
        referral_status = "EXISTING_CLIENT"
    elif interested_in_otr:  # Checkbox was checked (value is "on" or similar)
        referral_status = "OTR_REQUESTED"
        # 💰 ALERT: This is your Money Trigger!
        # TODO: Later, add email automation here to send them the OTR link.
        # Example: send_otr_referral_email(email, mc_number)
    
    with engine.begin() as conn:
        # Insert user with factoring fields
        r = conn.execute(
            text("""
                INSERT INTO webwise.users (
                    email, 
                    password_hash, 
                    role, 
                    is_active,
                    factoring_company,
                    referral_status
                )
                VALUES (
                    :email, 
                    :password_hash, 
                    'client', 
                    true,
                    :factoring_company,
                    :referral_status
                )
                RETURNING id
            """),
            {
                "email": email.strip().lower(),
                "password_hash": password_hash,
                "factoring_company": factoring_co,
                "referral_status": referral_status
            },
        )
        row = r.one()
        user_id = row.id
        
        # Validate that at least one identifier is provided
        mc_clean = mc_number.strip() if mc_number else ""
        dot_clean = dot_number.strip() if dot_number else ""
        auth_type = authority_type.strip().upper() if authority_type else "MC"
        
        if auth_type not in ["MC", "DOT"]:
            auth_type = "MC"
        
        if auth_type == "MC" and not mc_clean:
            return templates.TemplateResponse(
                "auth/register-trucker.html",
                {"request": request, "error": "MC Number is required when MC is selected."},
            )
        if auth_type == "DOT" and not dot_clean:
            return templates.TemplateResponse(
                "auth/register-trucker.html",
                {"request": request, "error": "DOT Number is required when DOT is selected."},
            )
        
        # Insert trucker profile
        conn.execute(
            text("""
                INSERT INTO webwise.trucker_profiles (
                    user_id, 
                    display_name, 
                    mc_number,
                    dot_number,
                    authority_type,
                    carrier_name, 
                    truck_identifier
                )
                VALUES (
                    :user_id, 
                    :display_name, 
                    :mc_number,
                    :dot_number,
                    :authority_type,
                    :carrier_name, 
                    :truck_identifier
                )
            """),
            {
                "user_id": user_id,
                "display_name": display_name.strip(),
                "mc_number": mc_clean or None,
                "dot_number": dot_clean or None,
                "authority_type": auth_type,
                "carrier_name": carrier_name.strip(),
                "truck_identifier": (truck_identifier or "").strip() or None,
            },
        )
    
    # Log referral status for admin tracking
    if referral_status == "OTR_REQUESTED":
        identifier = f"{auth_type}: {dot_clean if auth_type == 'DOT' else mc_clean}"
        print(f"💰 REFERRAL ALERT: {email} ({identifier}) requested OTR referral!")
    
    # Send welcome email to new beta driver (non-blocking)
    try:
        from app.services.welcome_email import send_welcome_email_to_driver
        # Send in background thread (don't block registration)
        import threading
        threading.Thread(
            target=send_welcome_email_to_driver,
            args=(email.strip().lower(), display_name.strip()),
            daemon=True
        ).start()
    except Exception as e:
        print(f"⚠️  Welcome email failed (non-blocking): {e}")
    
    session_token = sign_session({"uid": user_id, "role": "client", "email": email.strip().lower()})
    # Send new drivers straight to setup-payment (Stripe checkout)
    response = RedirectResponse(url="/drivers/setup-payment", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE, session_token, httponly=True, secure=False, samesite="lax", max_age=SESSION_TTL_SECONDS
    )
    return response


@router.post("/century/register-trucker")
def century_register_trucker(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    mc_number: str = Form(""),
    dot_number: str = Form(""),
    authority_type: str = Form("MC"),
    carrier_name: str = Form(...),
    truck_identifier: str = Form(""),
    has_factoring: str = Form("no"),
    factoring_company_name: str = Form(None),
    interested_in_otr: str = Form(None),
):
    """Century flow: same as register_trucker but redirects to /century/onboarding/welcome."""
    err_tpl = "auth/century_register_trucker.html"
    if get_user_by_email(email):
        return templates.TemplateResponse(err_tpl, {"request": request, "error": "Email already registered."})
    if not engine:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
    try:
        password_hash = hash_password(password)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not hash password")
    referral_status = "NONE"
    factoring_co = None
    if has_factoring == "yes" and factoring_company_name:
        factoring_co = factoring_company_name.strip()
        referral_status = "EXISTING_CLIENT"
    elif interested_in_otr:
        referral_status = "OTR_REQUESTED"
    with engine.begin() as conn:
        r = conn.execute(
            text("""
                INSERT INTO webwise.users (email, password_hash, role, is_active, factoring_company, referral_status)
                VALUES (:email, :password_hash, 'client', true, :factoring_company, :referral_status)
                RETURNING id
            """),
            {"email": email.strip().lower(), "password_hash": password_hash, "factoring_company": factoring_co, "referral_status": referral_status},
        )
        row = r.one()
        user_id = row.id
        mc_clean = mc_number.strip() if mc_number else ""
        dot_clean = dot_number.strip() if dot_number else ""
        auth_type = authority_type.strip().upper() if authority_type else "MC"
        if auth_type not in ["MC", "DOT"]:
            auth_type = "MC"
        if auth_type == "MC" and not mc_clean:
            return templates.TemplateResponse(err_tpl, {"request": request, "error": "MC Number is required when MC is selected."})
        if auth_type == "DOT" and not dot_clean:
            return templates.TemplateResponse(err_tpl, {"request": request, "error": "DOT Number is required when DOT is selected."})
        conn.execute(
            text("""
                INSERT INTO webwise.trucker_profiles (user_id, display_name, mc_number, dot_number, authority_type, carrier_name, truck_identifier)
                VALUES (:user_id, :display_name, :mc_number, :dot_number, :authority_type, :carrier_name, :truck_identifier)
            """),
            {
                "user_id": user_id,
                "display_name": display_name.strip(),
                "mc_number": mc_clean or None,
                "dot_number": dot_clean or None,
                "authority_type": auth_type,
                "carrier_name": carrier_name.strip(),
                "truck_identifier": (truck_identifier or "").strip() or None,
            },
        )
    try:
        from app.services.welcome_email import send_welcome_email_to_driver
        import threading
        threading.Thread(target=send_welcome_email_to_driver, args=(email.strip().lower(), display_name.strip()), daemon=True).start()
    except Exception as e:
        print(f"Welcome email failed: {e}")
    session_token = sign_session({"uid": user_id, "role": "client", "email": email.strip().lower()})
    response = RedirectResponse(url="/century/onboarding/welcome", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(SESSION_COOKIE, session_token, httponly=True, secure=False, samesite="lax", max_age=SESSION_TTL_SECONDS)
    return response


@router.get("/register")
async def register_page(request: Request, ref: str = None):
    # Pass the ref code to the template so it can be included in the form hidden field
    return templates.TemplateResponse("auth/register.html", {"request": request, "ref_code": ref})

@router.post("/register")
async def register(
    # ... existing fields ...
    ref_code: str = Form(None), # <--- Capture this
    db: Session = Depends(get_db)
):
    # 1. Find who referred them
    referrer_id = None
    if ref_code:
        referrer = db.query(User).filter(User.referral_code == ref_code).first()
        if referrer:
            referrer_id = referrer.referral_code # Store the CODE, not the ID, for easier lookup

    # 2. Create User with 'referred_by'
    new_user = User(
        # ... existing fields ...
        referred_by=referrer_id
    )
    # ... save to DB ...    
