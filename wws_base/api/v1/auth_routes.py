from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates

router = APIRouter()  # this must exist or import fails
templates = Jinja2Templates(directory="/srv/projects/wws-base/wws_base/app/templates")


@router.get("/login/admin")
def admin_login_page(request: Request):
    return templates.TemplateResponse("auth/admin-login.html", {"request": request})

@router.post("/auth/admin")
def auth_admin(username: str = Form(...), password: str = Form(...)):
    return {"status": "ok", "role": "admin", "user": username}


