import base64
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from typing import Dict

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


def _basic_auth_header(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("ascii")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _normalize_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    try:
        return str(ip_address(ip))
    except ValueError:
        return None


async def build_twitter_auth_url(state: str, code_challenge: str) -> str:
    cfg = get_config()
    base = cfg["OAUTH_TWITTER_AUTH_URL"]
    params = {
        "response_type": "code",
        "client_id": cfg["OAUTH_TWITTER_CLIENT_ID"],
        "redirect_uri": cfg["OAUTH_TWITTER_REDIRECT_URI"],
        "scope": cfg["OAUTH_TWITTER_SCOPES"],
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    qp = httpx.QueryParams(params)
    return f"{base}?{qp}"


async def exchange_code_for_tokens(code: str, code_verifier: str) -> Dict:
    cfg = get_config()
    token_url = cfg["OAUTH_TWITTER_TOKEN_URL"]

    client_id = cfg["OAUTH_TWITTER_CLIENT_ID"]
    client_secret = cfg.get("OAUTH_TWITTER_CLIENT_SECRET") or ""
    redirect_uri = cfg["OAUTH_TWITTER_REDIRECT_URI"]

    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code": code,
        "code_verifier": code_verifier,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    if client_secret:
        headers["Authorization"] = _basic_auth_header(client_id, client_secret)

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(token_url, data=data, headers=headers)
        r.raise_for_status()
        return r.json()


async def fetch_userinfo(access_token: str) -> Dict:
    cfg = get_config()
    url = cfg["OAUTH_TWITTER_USERINFO_URL"]
    params = {"user.fields": "profile_image_url,name,username"}
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()


async def complete_twitter_login(uinfo: Dict, user_agent: str | None, ip: str | None) -> Dict:
    data = (uinfo or {}).get("data") or {}
    tw_id = (data.get("id") or "").strip()
    name = data.get("name") or ""
    username = data.get("username") or ""
    avatar = data.get("profile_image_url") or None
    if not tw_id or not username:
        raise ValueError("Twitter profile is incomplete")

    cfg = get_config()
    email = None
    allow_pseudo = bool(cfg.get("OAUTH_TWITTER_ALLOW_PSEUDO_EMAIL"))
    pseudo_domain = (cfg.get("OAUTH_PSEUDO_EMAIL_DOMAIN") or "").strip()
    if allow_pseudo and pseudo_domain:
        email = f"twitter_{tw_id}@{pseudo_domain}"
    if not email:
        raise ValueError("Twitter account has no email; enable pseudo email or grant email access")

    user = await ensure_user_for_oauth(email=email, name=name or username, avatar_url=avatar)

    sec = get_security_config()
    now = datetime.now(timezone.utc)
    refresh_expires_at = now + timedelta(days=sec["REFRESH_TOKEN_EXPIRES_DAYS"])

    client_ip = _normalize_ip(ip)
    placeholder = await create_session_placeholder(user["id"], user_agent or "", client_ip, refresh_expires_at)
    session_id = placeholder["id"]

    refresh_token = generate_refresh_token_for_session(session_id)
    refresh_hash = hash_refresh_token(refresh_token)
    await set_session_token_hash(session_id, refresh_hash)

    access_token = create_access_token(user["id"])

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "refresh_max_age": int(sec["REFRESH_TOKEN_EXPIRES_DAYS"] * 24 * 60 * 60),
        "cookie_secure": sec["COOKIE_SECURE"],
        "cookie_samesite": sec["COOKIE_SAMESITE"],
        "cookie_domain": sec["COOKIE_DOMAIN"],
    }
