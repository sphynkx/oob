from datetime import UTC, datetime, timedelta
from ipaddress import ip_address

from db.sessions_db import (
    create_session_placeholder,
    get_session_by_id,
    revoke_all_sessions_for_user,
    revoke_session,
    rotate_session,
    set_session_token_hash,
)
from db.users_db import create_user, get_user_by_email, get_user_by_id
from utils.security_ut import (
    create_access_token,
    generate_refresh_token_for_session,
    get_security_config,
    hash_password,
    hash_refresh_token,
    parse_refresh_token,
    verify_password,
    verify_refresh_token_hash,
)


def _normalize_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    try:
        return str(ip_address(ip))
    except ValueError:
        return None


async def register_user_service(email, password, name):
    email_lc = (email or "").strip().lower()
    if not email_lc or not password:
        raise ValueError("Invalid email or password")
    existing = await get_user_by_email(email_lc)
    if existing:
        raise ValueError("Email already registered")
    pwd_hash = hash_password(password)
    user = await create_user(email_lc, pwd_hash, name)
    return user


async def login_user_service(email, password, user_agent, ip):
    sec = get_security_config()

    email_lc = (email or "").strip().lower()
    user = await get_user_by_email(email_lc)
    if not user or not user.get("password_hash"):
        raise ValueError("Invalid credentials")
    if not verify_password(password, user["password_hash"]):
        raise ValueError("Invalid credentials")

    now = datetime.now(UTC)
    refresh_expires_at = now + timedelta(days=sec["REFRESH_TOKEN_EXPIRES_DAYS"])

    client_ip = _normalize_ip(ip)
    placeholder = await create_session_placeholder(
        user["id"], user_agent, client_ip, refresh_expires_at
    )

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


async def refresh_token_service(refresh_token):
    sec = get_security_config()
    session_id, _ = parse_refresh_token(refresh_token)

    session = await get_session_by_id(session_id)
    if not session:
        raise ValueError("Invalid session")
    if session.get("revoked_at"):
        raise ValueError("Session revoked")
    if session["expires_at"] <= datetime.now(UTC):
        raise ValueError("Session expired")

    if not verify_refresh_token_hash(refresh_token, session["refresh_token_hash"]):
        raise ValueError("Invalid refresh token")

    new_refresh_token = generate_refresh_token_for_session(session_id)
    new_hash = hash_refresh_token(new_refresh_token)
    new_expires_at = datetime.now(UTC) + timedelta(days=sec["REFRESH_TOKEN_EXPIRES_DAYS"])
    await rotate_session(session_id, new_hash, new_expires_at)

    access_token = create_access_token(session["user_id"])

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "refresh_max_age": int(sec["REFRESH_TOKEN_EXPIRES_DAYS"] * 24 * 60 * 60),
        "cookie_secure": sec["COOKIE_SECURE"],
        "cookie_samesite": sec["COOKIE_SAMESITE"],
        "cookie_domain": sec["COOKIE_DOMAIN"],
    }


async def logout_current_service(refresh_token):
    session_id, _ = parse_refresh_token(refresh_token)
    await revoke_session(session_id)


async def logout_all_service(user_id):
    await revoke_all_sessions_for_user(user_id)


async def get_user_by_refresh_token_service(refresh_token: str):
    """
    Validates the refresh token against the stored session and returns user dict.
    This is used by UI middleware to resolve request.state.user from refresh cookie.
    """
    session_id, _ = parse_refresh_token(refresh_token)
    session = await get_session_by_id(session_id)
    if not session:
        raise ValueError("Invalid session")
    if session.get("revoked_at"):
        raise ValueError("Session revoked")
    if session["expires_at"] <= datetime.now(UTC):
        raise ValueError("Session expired")
    if not verify_refresh_token_hash(refresh_token, session["refresh_token_hash"]):
        raise ValueError("Invalid refresh token")
    user = await get_user_by_id(session["user_id"])
    return user
