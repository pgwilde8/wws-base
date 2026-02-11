from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text
from datetime import datetime
from typing import Dict

from app.core.deps import templates, current_user, engine

router = APIRouter()


@router.get("/legal/terms-of-service", response_class=HTMLResponse)
@router.get("/legal/tos", response_class=HTMLResponse)
def terms_of_service_page(request: Request):
    """
    Public Terms of Service page.
    Accessible to all users without authentication.
    """
    return templates.TemplateResponse("legal/tos.html", {"request": request})


@router.get("/legal/privacy", response_class=HTMLResponse)
def privacy_policy_page(request: Request):
    """
    Public Privacy Policy page.
    Accessible to all users without authentication.
    """
    return templates.TemplateResponse("legal/privacy.html", {"request": request})


@router.get("/legal/notice-of-assignment", response_class=HTMLResponse)
def notice_of_assignment_page(
    request: Request,
    user: Dict = Depends(current_user)  # REQUIRED - No optional, locks the door
):
    """
    STRICTLY PRIVATE: Notice of Assignment & Fee Authorization form.
    
    Only accessible to logged-in drivers (clients). 
    Automatically pre-fills with THEIR profile data.
    
    Security:
    - Requires authentication (redirects to login if not logged in)
    - Only shows the logged-in driver's own data
    - No query parameters allowed (prevents data leakage)
    """
    # SECURITY CHECK: Must be logged in as a client
    if not user or user.get("role") != "client":
        return RedirectResponse(url="/login/client", status_code=303)
    
    # Fetch driver's profile data from database
    if not engine:
        raise HTTPException(status_code=503, detail="Database not available")
    
    with engine.begin() as conn:
        r = conn.execute(
            text("""
                SELECT tp.mc_number, tp.carrier_name, tp.display_name
                FROM webwise.trucker_profiles tp
                WHERE tp.user_id = :uid
            """),
            {"uid": user.get("id")},
        )
        row = r.first()
        
        if not row or not row.mc_number:
            # Driver profile incomplete - redirect to complete profile
            return templates.TemplateResponse(
                "legal/notice_of_assignment.html",
                {
                    "request": request,
                    "user": user,
                    "error": "Please complete your trucker profile first. MC number is required.",
                    "carrier_company_name": "Please Complete Profile",
                    "carrier_mc_number": "MC-XXXXXX",
                    "carrier_owner_name": user.get("email", "Driver"),
                    "current_date": datetime.now().strftime("%B %d, %Y")
                }
            )
        
        # Use driver's actual profile data (NO query parameters - security)
        carrier_company_name = row.carrier_name or "Your Carrier Company Name"
        carrier_mc_number = row.mc_number
        carrier_owner_name = row.display_name or user.get("email", "Driver")
    
    current_date = datetime.now().strftime("%B %d, %Y")
    
    return templates.TemplateResponse(
        "legal/notice_of_assignment.html",
        {
            "request": request,
            "user": user,
            "carrier_company_name": carrier_company_name,
            "carrier_mc_number": carrier_mc_number,
            "carrier_owner_name": carrier_owner_name,
            "current_date": current_date
        }
    )


@router.post("/legal/notice-of-assignment/generate")
def generate_notice_of_assignment(
    request: Request,
    user: Dict = Depends(current_user)  # REQUIRED - Must be logged in
):
    """
    Generate a filled Notice of Assignment form (POST version).
    Still uses driver's profile data - form fields are ignored for security.
    Can be used for PDF generation or print-ready version.
    """
    # SECURITY CHECK: Must be logged in as a client
    if not user or user.get("role") != "client":
        return RedirectResponse(url="/login/client", status_code=303)
    
    # Always use database data, ignore form inputs (security)
    if not engine:
        raise HTTPException(status_code=503, detail="Database not available")
    
    with engine.begin() as conn:
        r = conn.execute(
            text("""
                SELECT tp.mc_number, tp.carrier_name, tp.display_name
                FROM webwise.trucker_profiles tp
                WHERE tp.user_id = :uid
            """),
            {"uid": user.get("id")},
        )
        row = r.first()
        
        if not row or not row.mc_number:
            raise HTTPException(status_code=400, detail="Trucker profile incomplete. MC number required.")
        
        carrier_company_name = row.carrier_name or "Your Carrier Company Name"
        carrier_mc_number = row.mc_number
        carrier_owner_name = row.display_name or user.get("email", "Driver")
    
    current_date = datetime.now().strftime("%B %d, %Y")
    
    return templates.TemplateResponse(
        "legal/notice_of_assignment.html",
        {
            "request": request,
            "user": user,
            "carrier_company_name": carrier_company_name,
            "carrier_mc_number": carrier_mc_number,
            "carrier_owner_name": carrier_owner_name,
            "current_date": current_date
        }
    )
