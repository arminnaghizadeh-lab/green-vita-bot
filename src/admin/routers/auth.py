from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.admin.auth import SESSION_KEY, verify_password
from src.core.config import get_settings

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="src/admin/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get(SESSION_KEY):
        return RedirectResponse("/dashboard/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None},
    )


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    settings = get_settings()

    if (
        username.strip() == settings.admin_username
        and verify_password(password, settings.admin_password_hash)
    ):
        request.session[SESSION_KEY] = True
        return RedirectResponse("/dashboard/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "نام کاربری یا رمز عبور اشتباه است."},
        status_code=401,
    )


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
