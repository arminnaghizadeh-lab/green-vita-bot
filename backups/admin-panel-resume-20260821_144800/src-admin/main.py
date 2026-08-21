from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from src.admin.auth import SESSION_KEY
from src.admin.routers import auth
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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root(request: Request):
    if not request.session.get(SESSION_KEY):
        return RedirectResponse("/login", status_code=303)

    return RedirectResponse("/dashboard", status_code=303)
