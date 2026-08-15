"""Authentication helpers for the Green Vita admin panel."""

from secrets import compare_digest

from fastapi import Request
from fastapi.responses import RedirectResponse

from src.core.config import Settings


SESSION_KEY = "admin_authenticated"


def authenticate(username: str, password: str, settings: Settings) -> bool:
    """Validate admin credentials without exposing secret values."""
    return compare_digest(username, settings.admin_username) and compare_digest(
        password, settings.admin_password
    )


def is_authenticated(request: Request) -> bool:
    """Return whether the current browser session is authenticated."""
    return request.session.get(SESSION_KEY) is True


def require_authentication(request: Request) -> RedirectResponse | None:
    """Redirect unauthenticated users to the login page."""
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return None
