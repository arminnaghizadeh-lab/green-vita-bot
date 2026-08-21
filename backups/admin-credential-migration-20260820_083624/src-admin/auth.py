from fastapi import Request
from fastapi.responses import RedirectResponse
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

SESSION_KEY = "admin_authenticated"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return password_hash.verify(plain_password, hashed_password)
    except Exception:
        return False


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def require_authentication(request: Request):
    """Return a redirect response when the admin is not authenticated.

    The existing admin login flow stores a boolean value under SESSION_KEY.
    Protected admin routes can call this function and immediately return
    the redirect when authentication is missing.
    """
    if not request.session.get(SESSION_KEY):
        return RedirectResponse("/login", status_code=303)

    return None
