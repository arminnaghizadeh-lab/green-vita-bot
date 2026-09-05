from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from src.admin.auth import SESSION_KEY
from src.admin.routers import auth, booking, dashboard, push, smart_bio, visits
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

@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    from fastapi.responses import FileResponse
    return FileResponse(
        "src/admin/static/sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )



app.include_router(auth.router)
app.include_router(dashboard.router, prefix="/dashboard")
app.include_router(visits.router)
app.include_router(smart_bio.router)
app.include_router(push.router)
app.include_router(booking.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return RedirectResponse("/dashboard/", status_code=302)
