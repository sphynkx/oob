from datetime import UTC, datetime, timedelta

import httpx

from config import get_config
from db.sessions_db import create_session_placeholder, set_session_token_hash
from db.users_db import ensure_user_for_oauth
from utils.security_ut import (
    create_access_token,
    generate_refresh_token_for_session,
    get_security_config,
    hash_refresh_token,
)


async def build_google_auth_url(state: str) -> str:
    cfg = get_config()
    base = cfg["OAUTH_GOOGLE_AUTH_URL"]
    params = {
        "client_id": cfg["OAUTH_GOOGLE_CLIENT_ID"],
        "redirect_uri": cfg["OAUTH_GOOGLE_REDIRECT_URI"],
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    ## Build query string safely via httpx.QueryParams
    qp = httpx.QueryParams(params)
    return f"{base}?{qp}"


async def exchange_code_for_tokens(code: str) -> dict:
    cfg = get_config()
    token_url = cfg["OAUTH_GOOGLE_TOKEN_URL"]
    data = {
        "code": code,
        "client_id": cfg["OAUTH_GOOGLE_CLIENT_ID"],
        "client_secret": cfg["OAUTH_GOOGLE_CLIENT_SECRET"],
        "redirect_uri": cfg["OAUTH_GOOGLE_REDIRECT_URI"],
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(token_url, data=data, headers={"Accept": "application/json"})
        r.raise_for_status()
        return r.json()


async def fetch_userinfo(access_token: str) -> dict:
    cfg = get_config()
    url = cfg["OAUTH_GOOGLE_USERINFO_URL"]
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            url, headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        )
        r.raise_for_status()
        return r.json()


async def complete_google_login(userinfo: dict, user_agent: str | None, ip: str | None) -> dict:
    """
    Upsert user and create our access/refresh session like regular password login.
    Returns dict with access_token, refresh_token and cookie flags.
    """
    email = (userinfo.get("email") or "").strip().lower()
    name = userinfo.get("name") or ""
    avatar = userinfo.get("picture") or None
    if not email:
        raise ValueError("Google account has no verified email")

    ## Upsert local user (no password for OAuth users)
    user = await ensure_user_for_oauth(email=email, name=name, avatar_url=avatar)

    sec = get_security_config()
    now = datetime.now(UTC)
    refresh_expires_at = now + timedelta(days=sec["REFRESH_TOKEN_EXPIRES_DAYS"])

    ## Create session placeholder with proper expires_at (NOT NULL)
    placeholder = await create_session_placeholder(
        user["id"], user_agent or "", ip, refresh_expires_at
    )
    session_id = placeholder["id"]

    ## Rotate refresh token
    refresh_token = generate_refresh_token_for_session(session_id)
    refresh_hash = hash_refresh_token(refresh_token)
    await set_session_token_hash(session_id, refresh_hash)

    ## Access token (JWT)
    access_token = create_access_token(user["id"])

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "refresh_max_age": int(sec["REFRESH_TOKEN_EXPIRES_DAYS"] * 24 * 60 * 60),
        "cookie_secure": sec["COOKIE_SECURE"],
        "cookie_samesite": sec["COOKIE_SAMESITE"],
        "cookie_domain": sec["COOKIE_DOMAIN"],
    }
