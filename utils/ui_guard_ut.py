from datetime import datetime, timezone
from typing import Iterable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

from config import get_config
from db.sessions_db import get_session_by_id
from db.users_db import get_user_by_id
from utils.security_ut import (
    get_refresh_cookie_name,
    parse_refresh_token,
    verify_refresh_token_hash,
)


def _csv_to_set(val: Optional[str]) -> set[str]:
    if not val:
        return set()
    return {p.strip() for p in val.split(",") if p.strip()}


async def _get_user_from_refresh_cookie(request: Request) -> Optional[dict]:
    """
    Read user from HttpOnly refresh cookie without rotating it.
    Returns user dict or None.
    """
    cookie_name = get_refresh_cookie_name()
    token = request.cookies.get(cookie_name)
    if not token:
        return None

    try:
        session_id, _ = parse_refresh_token(token)
    except Exception:
        return None

    session = await get_session_by_id(session_id)
    if not session:
        return None

    if session.get("revoked_at"):
        return None

    expires_at = session.get("expires_at")
    if not expires_at or expires_at <= datetime.now(timezone.utc):
        return None

    if not verify_refresh_token_hash(token, session.get("refresh_token_hash") or ""):
        return None

    user_id = session.get("user_id")
    if not user_id:
        return None

    user = await get_user_by_id(int(user_id))
    return user


def get_user_from_refresh_cookie_request_sync_state(request: Request) -> Optional[dict]:
    """
    Helper for UI routers: obtain user from request.state if middleware already set it.
    If not set (e.g., POST), this returns None. Routers can re-check via async _get_user_from_refresh_cookie.
    """
    return getattr(request.state, "user", None)


class UiAuthRedirectMiddleware(BaseHTTPMiddleware):
    """
    Server-side guard for UI HTML routes.
    Uses refresh cookie to detect authenticated browser sessions.
    Redirects:
      - "/" -> /dashboard if authenticated; else /login
      - protected prefixes -> /login if not authenticated
      - /login or /register -> /dashboard if authenticated
    Skips API and static paths.
    Also attaches request.state.user for convenience on HTML routes.
    """

    def __init__(self, app):
        super().__init__(app)
        cfg = get_config()

        self.public_paths = _csv_to_set(
            cfg.get(
                "UI_PUBLIC_PATHS",
                "/login,/register,/health,/static,/docs,/openapi.json,/redoc,/favicon.ico",
            )
        )
        self.protected_prefixes = _csv_to_set(
            cfg.get("UI_PROTECTED_PREFIXES", "/dashboard,/products")
        )
        self.skip_prefixes = _csv_to_set(cfg.get("UI_SKIP_PREFIXES", "/api,/auth"))
        self.enable_root_redirect = str(cfg.get("UI_ROOT_REDIRECT", "true")).lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path or "/"

        def _starts_with(prefixes: Iterable[str]) -> bool:
            for p in prefixes:
                if p and path.startswith(p):
                    return True
            return False

        if _starts_with(self.skip_prefixes):
            return await call_next(request)

        ## Attach user on all HTML routes (GET/POST/etc.)
        user = await _get_user_from_refresh_cookie(request)
        setattr(request.state, "user", user)

        ## Root redirect
        if self.enable_root_redirect and path == "/":
            if getattr(request.state, "user", None):
                return RedirectResponse(url="/dashboard", status_code=302)
            return RedirectResponse(url="/login", status_code=302)

        ## Public paths
        if path in self.public_paths:
            if path in ("/login", "/register") and getattr(request.state, "user", None):
                return RedirectResponse(url="/dashboard", status_code=302)
            return await call_next(request)

        ## Protected prefixes
        if _starts_with(self.protected_prefixes):
            if not getattr(request.state, "user", None):
                return RedirectResponse(url="/login", status_code=302)
            return await call_next(request)

        ## Default allow
        return await call_next(request)
