from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from config import get_config
from services.oauth_twitter_service import (
    build_twitter_auth_url,
    exchange_code_for_tokens,
    fetch_userinfo,
    complete_twitter_login,
)
from utils.state_ut import create_state, verify_state
from utils.pkce_ut import create_code_verifier, create_code_challenge_s256
from utils.security_ut import get_refresh_cookie_name

router = APIRouter(prefix="/oauth")


@router.get("/twitter/start")
async def oauth_twitter_start(request: Request):
    cfg = get_config()
    state = create_state()
    code_verifier = create_code_verifier()
    code_challenge = create_code_challenge_s256(code_verifier)

    url = await build_twitter_auth_url(state, code_challenge)

    resp = RedirectResponse(url=url, status_code=302)
    resp.set_cookie(
        key="oauth_state_tw",
        value=state,
        httponly=True,
        secure=cfg["COOKIE_SECURE"],
        samesite=cfg["COOKIE_SAMESITE"],
        domain=cfg["COOKIE_DOMAIN"],
        path="/",
        max_age=300,
    )
    resp.set_cookie(
        key="oauth_tw_pkce",
        value=code_verifier,
        httponly=True,
        secure=cfg["COOKIE_SECURE"],
        samesite=cfg["COOKIE_SAMESITE"],
        domain=cfg["COOKIE_DOMAIN"],
        path="/",
        max_age=300,
    )
    return resp


@router.get("/twitter/callback")
async def oauth_twitter_callback(request: Request):
    cfg = get_config()
    state_cookie = request.cookies.get("oauth_state_tw", "")
    state_param = request.query_params.get("state", "")
    code = request.query_params.get("code", "")
    code_verifier = request.cookies.get("oauth_tw_pkce", "")

    if not code or not code_verifier or not state_param or not state_cookie or state_cookie != state_param or not verify_state(state_param):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state or PKCE")

    try:
        tokens = await exchange_code_for_tokens(code, code_verifier)
        access_token = tokens.get("access_token")
        if not access_token:
            raise ValueError("No access_token from provider")
        uinfo = await fetch_userinfo(access_token)
        user_agent = request.headers.get("user-agent", "")
        client_ip = request.client.host if request.client else None
        out = await complete_twitter_login(uinfo, user_agent, client_ip)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"OAuth failed: {e}")

    cookie_name = get_refresh_cookie_name()
    resp = RedirectResponse(url="/dashboard", status_code=303)
    resp.set_cookie(
        key=cookie_name,
        value=out["refresh_token"],
        httponly=True,
        secure=out["cookie_secure"],
        samesite=out["cookie_samesite"],
        domain=out["cookie_domain"],
        path="/",
        max_age=out["refresh_max_age"],
    )
    resp.delete_cookie(key="oauth_state_tw", path="/")
    resp.delete_cookie(key="oauth_tw_pkce", path="/")
    return resp

