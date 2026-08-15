from fastapi import APIRouter

from src.admin.routers import auth, dashboard, health


def get_root_router() -> APIRouter:
    root = APIRouter()
    root.include_router(auth.router)
    root.include_router(health.router)
    root.include_router(dashboard.router)
    return root
