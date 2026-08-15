"""Admin authentication routes."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from src.admin.auth import SESSION_KEY, authenticate
from src.core.config import get_settings


router = APIRouter(tags=["authentication"])
templates = Jinja2Templates(directory="src/admin/templates")


@router.get("/login")
async def login_page(request: Request):
    if request.session.get(SESSION_KEY) is True:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": None,
        },
    )


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    settings = get_settings()

    if not authenticate(username, password, settings):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "نام کاربری یا رمز عبور اشتباه است.",
            },
            status_code=401,
        )

    request.session[SESSION_KEY] = True
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
