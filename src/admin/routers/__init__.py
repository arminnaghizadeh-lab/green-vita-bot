from fastapi import APIRouter

from src.admin.routers import auth, dashboard, health, users


def get_root_router() -> APIRouter:
    root = APIRouter()
    root.include_router(auth.router)
    root.include_router(health.router)
    root.include_router(dashboard.router)
    root.include_router(users.router)
    return root
