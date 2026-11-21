"""Green Vita project compatibility bindings for the invoice module."""
from fastapi import HTTPException, Request

from src.db.base import Base  # noqa: F401
from src.admin.dependencies import get_session  # noqa: F401
from src.admin.auth import SESSION_KEY


def require_admin(request: Request) -> None:
    """Require the existing Green Vita admin session."""
    if not request.session.get(SESSION_KEY):
        raise HTTPException(status_code=401, detail="unauthorized")
