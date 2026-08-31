from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from src.admin.auth import SESSION_KEY
from src.admin.routers import auth, dashboard, smart_bio, visits
from src.core.config import get_settings

app = FastAPI(
    title="Green Vita Admin",
    docs_url=None,
    redoc_url=None,
)

settings = get_settings()

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.admin_session_secret or settings.secret_key,
)


app.mount(
    "/static",
    StaticFiles(directory="src/admin/static"),
    name="static",
)


app.include_router(auth.router)
app.include_router(dashboard.router, prefix="/dashboard")
app.include_router(visits.router)
app.include_router(smart_bio.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root(request: Request):
    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(directory="src/admin/templates")

    return templates.TemplateResponse(
        "smart_bio.html",
        {
            "request": request,
        },
    )
