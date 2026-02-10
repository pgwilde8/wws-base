from fastapi import APIRouter, Request, Form
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from fastapi.responses import HTMLResponse
from app.services.load_board import LoadBoardService

from app.core.deps import templates, engine, run_assistant_message

router = APIRouter()


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
    message = (payload.get("message") if payload else "") or ""
    thread_id = payload.get("thread_id") if payload else None
    result = run_assistant_message(message, thread_id)
    return result


@router.get("/find-loads", response_class=HTMLResponse)
async def find_loads(request: Request):
    loads = await LoadBoardService.fetch_current_loads()
    
    # We pass the loads to a "partial" template
    # HTMX will take this HTML and swap it into the dashboard
    return request.app.state.templates.TemplateResponse(
        "public/partials/load_list.html", 
        {"request": request, "loads": loads}
    )    
