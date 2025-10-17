from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from config import get_config
from services.oauth_google_service import (
    build_google_auth_url,
    complete_google_login,
    exchange_code_for_tokens,
    fetch_userinfo,
)
from utils.security_ut import get_refresh_cookie_name
from utils.state_ut import create_state, verify_state

router = APIRouter(prefix="/oauth")


@router.get("/google/start")
async def oauth_google_start(request: Request):
    state = create_state()
    ## set short-lived state cookie (5 min)
    cfg = get_config()
    resp = RedirectResponse(
        url="/", status_code=302
    )  ## temporary, will be replaced after compute url
    resp.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=cfg["COOKIE_SECURE"],
        samesite=cfg["COOKIE_SAMESITE"],
        domain=cfg["COOKIE_DOMAIN"],
        path="/",
        max_age=300,
    )
    url = await build_google_auth_url(state)
    resp.headers["Location"] = url
    return resp


@router.get("/google/callback")
async def oauth_google_callback(request: Request):
    cfg = get_config()
    state_cookie = request.cookies.get("oauth_state", "")
    state_param = request.query_params.get("state", "")
    code = request.query_params.get("code", "")
    if (
        not code
        or not state_param
        or not state_cookie
        or state_cookie != state_param
        or not verify_state(state_param)
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state")

    try:
        tokens = await exchange_code_for_tokens(code)
        access_token = tokens.get("access_token")
        if not access_token:
            raise ValueError("No access_token from provider")
        uinfo = await fetch_userinfo(access_token)
        user_agent = request.headers.get("user-agent", "")
        client_ip = request.client.host if request.client else None
        out = await complete_google_login(uinfo, user_agent, client_ip)
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
    ## clear state cookie
    resp.delete_cookie(key="oauth_state", path="/")
    return resp
