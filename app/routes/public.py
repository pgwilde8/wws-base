import os
from fastapi import APIRouter, Request, Form, Body, HTTPException, BackgroundTasks, status, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from fastapi.responses import HTMLResponse, JSONResponse
from app.services.load_board import LoadBoardService
from app.services.email import parse_broker_reply, send_contact_form_email, send_factoring_referral_email
from app.services.storage import upload_bol, get_presigned_url, convert_bol_image_to_pdf
from app.services.email import send_bol_email
#from app.core.templates import templates
from app.core.deps import templates, engine, run_assistant_message

router = APIRouter()
@router.get("/beta", response_class=HTMLResponse)
def beta_page(request: Request):
    return templates.TemplateResponse("public/beta.html", {"request": request})

def _get_home_context(request: Request):
    testimonials = []
    if engine:
        try:
            with engine.begin() as conn:
                rows = conn.execute(text("""
                    SELECT id, client_name, testimonial_text, rating, event_type, created_at
                    FROM webwise.testimonials
                    WHERE is_approved = true
                    ORDER BY created_at DESC
                """))
                testimonials = [dict(r._mapping) for r in rows]
        except ProgrammingError:
            pass  # table/schema not created yet; show page with no testimonials
    return {"request": request, "testimonials": testimonials}


@router.get("/")
def home_page(request: Request):
    return templates.TemplateResponse("public/index.html", _get_home_context(request))


@router.get("/index.html")
def index_html(request: Request):
    return templates.TemplateResponse("public/index.html", _get_home_context(request))


@router.get("/about")
def about_page(request: Request):
    return templates.TemplateResponse("public/about.html", {"request": request})


@router.get("/services")
def services_page(request: Request):
    return templates.TemplateResponse("public/services.html", {"request": request})

@router.get("/fleet-builder", response_class=HTMLResponse)
async def fleet_builder_page(request: Request):
    return templates.TemplateResponse("public/fleet-builder.html", {"request": request})

@router.get("/faq")
def faq_page(request: Request):
    return templates.TemplateResponse("public/faq.html", {"request": request})


@router.get("/pricing")
def pricing_page(request: Request):
    return templates.TemplateResponse("public/pricing.html", {"request": request})


@router.get("/century/pricing")
def century_pricing_page(request: Request):
    """Century flow: pricing page with Century Finance partner copy. Pass manually to drivers."""
    return templates.TemplateResponse("public/century_pricing.html", {"request": request})


@router.get("/pricing/products")
def pricing_products_page(request: Request):
    """Secondary pricing page: Call Packs, Fuel Packs, Broker Subscription. Stripe price IDs from env/code."""
    return templates.TemplateResponse("public/pricing-products.html", {"request": request})


@router.get("/pricing/checkout")
def pricing_checkout_redirect(request: Request, product: str = ""):
    """Start Stripe Checkout for an add-on product. Redirects to Stripe or back to products page on failure."""
    product_slug = (product or "").strip().lower()
    base_url = (os.getenv("BASE_URL") or str(request.base_url)).rstrip("/")
    success_url = f"{base_url}/pricing/products?success=1"
    cancel_url = f"{base_url}/pricing/products?canceled=1"
    from app.services.stripe_checkout import create_addon_checkout_session, ADDON_PRICE_IDS
    if product_slug not in ADDON_PRICE_IDS:
        return RedirectResponse(url="/pricing/products?error=invalid", status_code=303)
    checkout_url = create_addon_checkout_session(product_slug, success_url, cancel_url)
    if not checkout_url:
        return RedirectResponse(url=f"/contact?product={product_slug}", status_code=303)
    return RedirectResponse(url=checkout_url, status_code=303)


@router.get("/test/bol-upload")
@router.get("/bolupload")
def bol_upload_test_page(request: Request):
    """Test page for BOL uploads to Spaces. In production, this will be behind driver auth."""
    return templates.TemplateResponse("public/bolupload.html", {"request": request})


@router.post("/test/convert-bol-jpg", response_class=HTMLResponse)
async def convert_existing_bol_jpg(
    request: Request,
    jpg_key: str = Form(...),
    bucket: str = Form("greencandle"),
):
    """
    Convert an existing JPG BOL in Spaces to PDF format.
    Useful if you uploaded a JPG before the auto-convert feature was added.
    """
    try:
        bucket, pdf_key = convert_bol_image_to_pdf(bucket, jpg_key)
        presigned_url = get_presigned_url(bucket, pdf_key)
        
        return templates.TemplateResponse(
            "public/partials/bol_upload_result.html",
            {
                "request": request,
                "success": True,
                "bucket": bucket,
                "file_key": pdf_key,
                "presigned_url": presigned_url,
                "email_sent": False,
                "email_message": f"Converted JPG to PDF: {jpg_key} → {pdf_key}",
            },
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse(
            "public/partials/bol_upload_result.html",
            {
                "request": request,
                "success": False,
                "error": str(e),
            },
        )


@router.post("/test/upload-bol", response_class=HTMLResponse)
async def test_upload_bol(
    request: Request,
    mc_number: str = Form(...),
    load_id: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Test endpoint: Upload BOL to Spaces (private), convert to PDF, email to allstarincome@gmail.com.
    Returns bucket/key and presigned URL.
    In production, this will be behind driver authentication.
    """
    try:
        # 1. Upload to Spaces (images auto-converted to PDF)
        bucket, file_key = await upload_bol(file, mc_number, load_id)
        presigned_url = get_presigned_url(bucket, file_key)
        
        # 2. Email the BOL PDF to allstarincome@gmail.com
        email_result = send_bol_email(
            to_email="allstarincome@gmail.com",
            bucket=bucket,
            file_key=file_key,
            mc_number=mc_number,
            load_id=load_id,
            subject=f"BOL Upload - Load {load_id} (MC: {mc_number})"
        )
        
        email_status = email_result.get("status", "unknown")
        email_message = email_result.get("message", "")
        
        return templates.TemplateResponse(
            "public/partials/bol_upload_result.html",
            {
                "request": request,
                "success": True,
                "bucket": bucket,
                "file_key": file_key,
                "presigned_url": presigned_url,
                "file_size": file.size if hasattr(file, "size") else "unknown",
                "email_sent": email_status == "success",
                "email_message": email_message,
            },
        )
    except Exception as e:
        import traceback
        error_detail = str(e)
        traceback.print_exc()
        return templates.TemplateResponse(
            "public/partials/bol_upload_result.html",
            {
                "request": request,
                "success": False,
                "error": error_detail,
            },
        )


@router.get("/token")
@router.get("/our-token")
@router.get("/candle")
def token_page(request: Request):
    """The $CANDLE Token page - explains tokenomics, Automation Fuel, and the debit card."""
    import os
    candle_dex_url = os.getenv("CANDLE_DEX_URL", "https://app.uniswap.org/swap?chain=base")
    return templates.TemplateResponse("public/our-token.html", {"request": request, "candle_dex_url": candle_dex_url})


@router.get("/protocol")
def protocol_page(request: Request):
    """The Green Candle Protocol page - explains the 2.5% fee and how it builds equity."""
    return templates.TemplateResponse("public/protocol.html", {"request": request})


@router.get("/contact")
def contact_page(request: Request):
    return templates.TemplateResponse("public/contact.html", {"request": request})


@router.post("/contact")
def contact_form_submit(
    request: Request,
    name: str = Form(""),
    email: str = Form(""),
    message: str = Form(""),
):
    """
    Receive contact form data and email it to CONTACT_RECIPIENT_EMAIL (contact@gcdloads.com).
    """
    if not email or "@" not in email:
        return templates.TemplateResponse(
            "public/contact.html",
            {"request": request, "error": "Please enter a valid email address."},
        )
    result = send_contact_form_email(
        name=(name or "").strip(),
        user_email=email.strip(),
        message=(message or "").strip(),
    )
    if result.get("status") == "success":
        return templates.TemplateResponse(
            "public/contact.html",
            {"request": request, "success": "Thanks! We'll get back to you within one business day."},
        )
    return templates.TemplateResponse(
        "public/contact.html",
        {"request": request, "error": result.get("message", "Failed to send. Please try emailing us directly.")},
    )


@router.get("/privacy-policy")
def privacy_policy(request: Request):
    return templates.TemplateResponse("legal/privacy.html", {"request": request})


@router.get("/terms-of-service")
def terms_of_service(request: Request):
    return templates.TemplateResponse("public/term-of-service.html", {"request": request})


@router.get("/testimonials")
def testimonials_page(request: Request):
    testimonials = []
    if engine:
        try:
            with engine.begin() as conn:
                result = conn.execute(text("""
                    SELECT id, client_name, email, client_location, website_url,
                           event_type, rating, testimonial_text, created_at
                    FROM webwise.testimonials
                    WHERE is_approved = true
                    ORDER BY created_at DESC
                """))
                testimonials = [dict(row._mapping) for row in result]
        except ProgrammingError:
            pass  # table/schema not created yet
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
    rating: int = Form(None),
):
    if not engine:
        return templates.TemplateResponse("public/testimonials-submit.html", {
            "request": request,
            "error": True,
            "message": "Database not configured",
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
                "testimonial_text": testimonial_text,
            })

        return templates.TemplateResponse("public/testimonials-submit.html", {
            "request": request,
            "success": True,
            "message": "Thank you! Your testimonial has been submitted and will be reviewed shortly.",
        })
    except Exception as e:
        return templates.TemplateResponse("public/testimonials-submit.html", {
            "request": request,
            "error": True,
            "message": f"An error occurred: {str(e)}",
        })


@router.post("/api/chat")
async def chat_api(payload: dict):
    """
    Chat endpoint using OpenAI Responses API.
    
    Payload:
        - message: User's message (required)
        - response_id: Previous response ID for threading (optional, for new conversations)
    
    Returns:
        - reply: Assistant's response
        - response_id: Response ID to use for next message (for threading)
    """
    try:
        from app.core.chat_responses import run_responses_chat, get_greeting
        
        message = (payload.get("message") if payload else "") or ""
        response_id = payload.get("response_id") if payload else None
        
        # If no message and no response_id, send greeting
        if not message and not response_id:
            return get_greeting()
        
        result = run_responses_chat(message=message, response_id=response_id)
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions (they have proper status codes)
        raise
    except Exception as e:
        # Catch any other exceptions and return a proper error
        import traceback
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"Chat API error: {error_type}: {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat service error: {error_msg}"
        )


@router.get("/api/chat/greeting")
async def chat_greeting():
    """
    Get a greeting message for new chat sessions.
    
    Returns:
        - reply: Greeting message
        - response_id: Response ID to use for first user message
    """
    try:
        from app.core.chat_responses import get_greeting
        return get_greeting()
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"Greeting API error: {error_type}: {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Greeting service error: {error_msg}"
        )


@router.get("/apply/factoring", response_class=HTMLResponse)
def apply_factoring_redirect(request: Request):
    """Legacy public form — redirect to signup flow (register → setup-payment → Stripe)."""
    return RedirectResponse(url="/register-trucker", status_code=302)




@router.get("/driver/factoring-application", response_class=HTMLResponse)
def factoring_application_redirect(request: Request):
    """Legacy / public link: send to public apply flow (no login required)."""
    return RedirectResponse(url="/apply/factoring", status_code=302)


@router.get("/find-loads", response_class=HTMLResponse)
async def find_loads(request: Request):
    loads = await LoadBoardService.fetch_current_loads()
    
    # We pass the loads to a "partial" template
    # HTMX will take this HTML and swap it into the dashboard
    return templates.TemplateResponse(
        "public/partials/load_list.html", 
        {"request": request, "loads": loads}
    )


@router.get("/test-loads", response_class=HTMLResponse)
def test_loads_page(request: Request):
    """
    Test page for Chrome Extension scraping.
    Contains a simple HTML table that the extension can scrape.
    """
    return templates.TemplateResponse("public/test_loads.html", {"request": request})


@router.post("/webhook/email/broker-reply", response_class=JSONResponse)
async def handle_broker_reply_email(request: Request, body: dict = Body(...), background_tasks: BackgroundTasks = None):
    """
    Webhook endpoint for mxroute to POST broker reply emails.
    When a broker replies to a negotiation email, mxroute can forward it here.
    
    Expected payload format (adjust based on mxroute webhook format):
    {
        "from": "broker@example.com",
        "subject": "Re: Load Negotiation",
        "body": "Yes, I can do $2,500",
        "negotiation_id": 123,  # extracted from email headers or body
        "load_id": "LOAD-456"
    }
    """
    if not engine:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Extract email data (adjust based on mxroute webhook format)
    email_from = body.get("from", "")
    email_subject = body.get("subject", "")
    email_body = body.get("body", "")
    negotiation_id = body.get("negotiation_id") or body.get("negotiationId")
    load_id = body.get("load_id") or body.get("loadId")
    
    # If negotiation_id not in payload, try to extract from email headers/body
    if not negotiation_id:
        # Try to parse from email body (we added tracking info when sending)
        import re
        neg_match = re.search(r'Negotiation ID:\s*(\d+)', email_body)
        if neg_match:
            negotiation_id = int(neg_match.group(1))
    
    if not negotiation_id:
        return JSONResponse(
            status_code=400,
            content={"error": "negotiation_id not found in email"}
        )
    
    # Parse the broker reply to determine status
    parsed = parse_broker_reply(email_body, email_subject)
    
    # Update negotiation status
    with engine.begin() as conn:
        # Check if negotiation exists
        neg = conn.execute(
            text("SELECT id, status FROM webwise.negotiations WHERE id = :id"),
            {"id": negotiation_id}
        ).fetchone()
        
        if not neg:
            return JSONResponse(
                status_code=404,
                content={"error": f"Negotiation {negotiation_id} not found"}
            )
        
        # Update status based on parsed reply
        new_status = parsed["status_hint"]  # "replied", "won", or "lost"
        
        update_data = {
            "id": negotiation_id,
            "status": new_status,
            "broker_reply": email_body[:1000],  # Store first 1000 chars
            "broker_email": email_from
        }
        
        # If they provided a rate, store it
        if parsed.get("extracted_rate"):
            update_data["final_rate"] = parsed["extracted_rate"]
        
        # Get trucker_id before update (for notifications)
        neg_row = conn.execute(
            text("SELECT trucker_id FROM webwise.negotiations WHERE id = :id"),
            {"id": negotiation_id}
        ).fetchone()
        trucker_id = neg_row[0] if neg_row else None
        
        conn.execute(
            text("""
                UPDATE webwise.negotiations
                SET status = :status,
                    broker_reply = :broker_reply,
                    broker_email = :broker_email,
                    final_rate = COALESCE(:final_rate, final_rate),
                    updated_at = now()
                WHERE id = :id
            """),
            update_data
        )
        
        # SAFETY CHECK: If broker said yes with a rate, mark as PENDING_APPROVAL
        # Driver must confirm - this prevents AI from accepting bad loads
        if new_status == "pending_approval" and parsed.get("extracted_rate"):
            final_rate = parsed["extracted_rate"]
            
            # Get negotiation details for driver notification
            origin = None
            destination = None
            neg_details = conn.execute(
                text("SELECT origin, destination FROM webwise.negotiations WHERE id = :id"),
                {"id": negotiation_id}
            ).fetchone()
            if neg_details:
                origin, destination = neg_details[0], neg_details[1]
            
            if trucker_id:
                # Create PENDING_APPROVAL notification with confirmation action
                # Store negotiation_id in message format for easy parsing: "NEG_ID:123|message"
                route_info = f"{origin} → {destination}" if (origin and destination) else "Route TBD"
                message = f"NEG_ID:{negotiation_id}|⚠️ Broker replied: ${final_rate:,.2f} for {route_info}. Review and confirm."
                conn.execute(
                    text("""
                        INSERT INTO webwise.notifications (trucker_id, message, notif_type, is_read)
                        VALUES (:trucker_id, :message, 'PENDING_APPROVAL', false)
                    """),
                    {
                        "trucker_id": trucker_id,
                        "message": message,
                    },
                )
    
    return JSONResponse({
        "status": "success",
        "negotiation_id": negotiation_id,
        "parsed_status": new_status,
        "extracted_rate": parsed.get("extracted_rate"),
        "confidence": parsed.get("confidence")
    })
