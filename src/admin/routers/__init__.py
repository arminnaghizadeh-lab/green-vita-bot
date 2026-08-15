from fastapi import APIRouter

from src.admin.routers import auth, dashboard, health, users, visits


def get_root_router() -> APIRouter:
    root = APIRouter()
    root.include_router(auth.router)
    root.include_router(health.router)
    root.include_router(dashboard.router)
    root.include_router(users.router)
    root.include_router(visits.router)
    return root
