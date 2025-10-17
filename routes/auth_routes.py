from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth_service import (
    login_user_service,
    logout_all_service,
    logout_current_service,
    refresh_token_service,
    register_user_service,
)
from utils.schemas_ut import LoginRequest, LogoutRequest, MeResponse, RegisterRequest, TokenResponse
from utils.security_ut import (
    get_current_user,
    get_refresh_cookie_name,
    get_user_from_token,
)

router = APIRouter()


@router.post("/register", response_model=MeResponse, status_code=201)
async def register(payload: RegisterRequest):
    try:
        user = await register_user_service(payload.email, payload.password, payload.name)
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "avatar_url": user["avatar_url"],
            "role": user.get("role"),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, response: Response):
    try:
        user_agent = request.headers.get("user-agent", "")
        client_ip = request.client.host if request.client else None
        tokens = await login_user_service(payload.email, payload.password, user_agent, client_ip)
        cookie_name = get_refresh_cookie_name()
        response.set_cookie(
            key=cookie_name,
            value=tokens["refresh_token"],
            httponly=True,
            secure=tokens["cookie_secure"],
            samesite=tokens["cookie_samesite"],
            domain=tokens["cookie_domain"],
            path="/",
            max_age=tokens["refresh_max_age"],
        )
        return {"access_token": tokens["access_token"], "token_type": "bearer"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response):
    cookie_name = get_refresh_cookie_name()
    refresh_token = request.cookies.get(cookie_name)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token"
        )
    try:
        result = await refresh_token_service(refresh_token)
        response.set_cookie(
            key=cookie_name,
            value=result["refresh_token"],
            httponly=True,
            secure=result["cookie_secure"],
            samesite=result["cookie_samesite"],
            domain=result["cookie_domain"],
            path="/",
            max_age=result["refresh_max_age"],
        )
        return {"access_token": result["access_token"], "token_type": "bearer"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


## Current-session logout doesnt require Bearer; it uses refresh cookie only.
## "Logout all" still requires Bearer and user identity.
@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    payload: LogoutRequest | None = None,
    authorization: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
):
    if payload and payload.all:
        ## Requires Bearer to identify the user
        if authorization is None or not authorization.credentials:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        user = await get_user_from_token(authorization.credentials)
        await logout_all_service(user["id"])
        return Response(status_code=204)

    ## Current session logout via refresh cookie
    cookie_name = get_refresh_cookie_name()
    refresh_token = request.cookies.get(cookie_name)
    if not refresh_token:
        return Response(status_code=204)
    await logout_current_service(refresh_token)
    return Response(status_code=204)


@router.get("/me", response_model=MeResponse)
async def me(user=Depends(get_current_user)):
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "avatar_url": user["avatar_url"],
        "role": user.get("role"),
    }
