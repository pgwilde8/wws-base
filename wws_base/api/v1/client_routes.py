from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(directory="/srv/projects/wws-base/wws_base/templates")

@router.get("/login/client")
def client_login_page(request: Request):
    return templates.TemplateResponse("auth/client-login.html", {"request": request})

@router.post("/auth/client")
def auth_client(username: str = Form(...), password: str = Form(...)):
    # placeholder auth response for client login
    return {"status": "ok", "role": "client", "user": username}

@router.get("/dashboard")
def client_dashboard(request: Request):
    return templates.TemplateResponse("client/dashboard.html", {"request": request})
    
