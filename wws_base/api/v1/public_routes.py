from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="/srv/projects/wws-base/wws_base/app/templates")


@router.get("/")
def home_page(request: Request):
    return templates.TemplateResponse("public/index.html", {"request": request})

@router.get("/terms")
def terms_page(request: Request):
    return templates.TemplateResponse("public/term-of-service.html", {"request": request})

@router.get("/privacy")
def privacy_page(request: Request):
    return templates.TemplateResponse("public/privacy-policy.html", {"request": request})    

@router.get("/faq")
def faq_page(request: Request):
    return templates.TemplateResponse("public/faq.html", {"request": request}) 

@router.get("/about")
def about_page(request: Request):
    return templates.TemplateResponse("public/about.html", {"request": request}) 

@router.get("/services")
def services_page(request: Request):
    return templates.TemplateResponse("public/services.html", {"request": request})    

@router.get("/contact")
def contact_page(request: Request):
    return templates.TemplateResponse("public/contact.html", {"request": request})

@router.post("/contact/submit")
def contact_submit(request: Request, name: str = Form(...), email: str = Form(...), message: str = Form(...)):
    # later you’ll forward this or save to DB
    return {"status": "received", "name": name}

@router.get("/login ")
def login_page(request: Request):
    return templates.TemplateResponse("public/login.html", {"request": request})   

@router.get("/testimonials-submit")
def testimonials_submit_page(request: Request):
    return templates.TemplateResponse("public/testimonials-submit.html", {"request": request}) 

@router.get("/testimonials")
def testimonials_page(request: Request):
    return templates.TemplateResponse("public/testimonials.html", {"request": request})               