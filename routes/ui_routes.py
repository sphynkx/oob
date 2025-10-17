from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config import get_config
from services.auth_service import (
    login_user_service,
    logout_current_service,
    register_user_service,
)
from services.products_service import (
    create_product_service,
    delete_product_service,
    get_products_stats_service,
    list_products_service,
)
from utils.csrf_ut import create_csrf_pair, verify_csrf
from utils.security_ut import get_refresh_cookie_name
from utils.ui_guard_ut import (
    _get_user_from_refresh_cookie,
    get_user_from_refresh_cookie_request_sync_state,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _set_csrf_cookie(resp: Response, token_cookie_value: str):
    cfg = get_config()
    resp.set_cookie(
        key="csrf_token",
        value=token_cookie_value,
        httponly=True,
        secure=cfg["COOKIE_SECURE"],
        samesite=cfg["COOKIE_SAMESITE"],
        domain=cfg["COOKIE_DOMAIN"],
        path="/",
        max_age=3600,
    )


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    csrf_form, csrf_cookie = create_csrf_pair()
    resp = templates.TemplateResponse(
        "login.html", {"request": request, "title": "Login", "csrf_token": csrf_form}
    )
    _set_csrf_cookie(resp, csrf_cookie)
    return resp


@router.post("/login", include_in_schema=False)
async def login_submit(request: Request):
    form = await request.form()
    csrf_form_token = form.get("csrf_token")
    csrf_cookie = request.cookies.get("csrf_token")
    if not verify_csrf(csrf_form_token, csrf_cookie):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "title": "Login", "error": "Invalid CSRF token."},
            status_code=400,
        )

    email = (form.get("email") or "").strip()
    password = form.get("password") or ""

    if not email or not password:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "title": "Login", "error": "Email and password are required."},
            status_code=400,
        )

    user_agent = request.headers.get("user-agent", "")
    client_ip = request.client.host if request.client else None

    try:
        tokens = await login_user_service(email, password, user_agent, client_ip)
        cookie_name = get_refresh_cookie_name()
        resp = RedirectResponse(url="/dashboard", status_code=303)
        resp.set_cookie(
            key=cookie_name,
            value=tokens["refresh_token"],
            httponly=True,
            secure=tokens["cookie_secure"],
            samesite=tokens["cookie_samesite"],
            domain=tokens["cookie_domain"],
            path="/",
            max_age=tokens["refresh_max_age"],
        )
        ## rotate CSRF token after auth
        csrf_form2, csrf_cookie2 = create_csrf_pair()
        _set_csrf_cookie(resp, csrf_cookie2)
        return resp
    except ValueError as e:
        csrf_form2, csrf_cookie2 = create_csrf_pair()
        resp = templates.TemplateResponse(
            "login.html",
            {"request": request, "title": "Login", "error": str(e), "csrf_token": csrf_form2},
            status_code=401,
        )
        _set_csrf_cookie(resp, csrf_cookie2)
        return resp


@router.get("/register", response_class=HTMLResponse, include_in_schema=False)
async def register_page(request: Request):
    csrf_form, csrf_cookie = create_csrf_pair()
    resp = templates.TemplateResponse(
        "register.html", {"request": request, "title": "Register", "csrf_token": csrf_form}
    )
    _set_csrf_cookie(resp, csrf_cookie)
    return resp


@router.post("/register", include_in_schema=False)
async def register_submit(request: Request):
    form = await request.form()
    csrf_form_token = form.get("csrf_token")
    csrf_cookie = request.cookies.get("csrf_token")
    if not verify_csrf(csrf_form_token, csrf_cookie):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "title": "Register", "error": "Invalid CSRF token."},
            status_code=400,
        )

    email = (form.get("email") or "").strip()
    password = form.get("password") or ""
    name = (form.get("name") or "").strip()

    if not email or not password:
        csrf_form2, csrf_cookie2 = create_csrf_pair()
        resp = templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "title": "Register",
                "error": "Email and password are required.",
                "form": {"email": email, "name": name},
                "csrf_token": csrf_form2,
            },
            status_code=400,
        )
        _set_csrf_cookie(resp, csrf_cookie2)
        return resp

    try:
        await register_user_service(email, password, name)
        return RedirectResponse(url="/login", status_code=303)
    except ValueError as e:
        csrf_form2, csrf_cookie2 = create_csrf_pair()
        resp = templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "title": "Register",
                "error": str(e),
                "form": {"email": email, "name": name},
                "csrf_token": csrf_form2,
            },
            status_code=400,
        )
        _set_csrf_cookie(resp, csrf_cookie2)
        return resp


@router.post("/logout", include_in_schema=False)
async def logout_ui(request: Request) -> Response:
    form = await request.form()
    csrf_form_token = form.get("csrf_token")
    csrf_cookie = request.cookies.get("csrf_token")
    if not verify_csrf(csrf_form_token, csrf_cookie):
        return RedirectResponse(url="/login", status_code=303)

    cookie_name = get_refresh_cookie_name()
    refresh_token = request.cookies.get(cookie_name)
    if refresh_token:
        try:
            await logout_current_service(refresh_token)
        except Exception:
            pass
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(key=cookie_name, path="/")
    ## rotate CSRF after logout
    csrf_form2, csrf_cookie2 = create_csrf_pair()
    _set_csrf_cookie(resp, csrf_cookie2)
    return resp


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page(request: Request):
    user = get_user_from_refresh_cookie_request_sync_state(request)
    if user is None:
        user = await _get_user_from_refresh_cookie(request)
        if user is None:
            return RedirectResponse(url="/login", status_code=302)

    stats = await get_products_stats_service(user["id"])
    csrf_form, csrf_cookie = create_csrf_pair()
    ctx = {
        "request": request,
        "title": "Dashboard",
        "me": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user.get("role"),
        },
        "stats": stats,
        "csrf_token": csrf_form,
    }
    resp = templates.TemplateResponse("dashboard.html", ctx)
    _set_csrf_cookie(resp, csrf_cookie)
    return resp


@router.get("/products", response_class=HTMLResponse, include_in_schema=False)
async def products_page(request: Request):
    user = get_user_from_refresh_cookie_request_sync_state(request)
    products = await list_products_service(limit=100, offset=0)
    csrf_form, csrf_cookie = create_csrf_pair()
    ctx = {
        "request": request,
        "title": "Products",
        "me": user,
        "products": products,
        "csrf_token": csrf_form,
    }
    resp = templates.TemplateResponse("products.html", ctx)
    _set_csrf_cookie(resp, csrf_cookie)
    return resp


@router.post("/products/{product_id}/delete", include_in_schema=False)
async def product_delete_ui(product_id: int, request: Request) -> Response:
    form = await request.form()
    csrf_form_token = form.get("csrf_token")
    csrf_cookie = request.cookies.get("csrf_token")
    if not verify_csrf(csrf_form_token, csrf_cookie):
        return RedirectResponse(url="/products", status_code=303)

    user = await _get_user_from_refresh_cookie(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)
    try:
        await delete_product_service(user=user, product_id=product_id)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return RedirectResponse(url="/products", status_code=303)


@router.get("/products/new", response_class=HTMLResponse, include_in_schema=False)
async def product_new_page(request: Request):
    user = get_user_from_refresh_cookie_request_sync_state(request)
    if user is None:
        user = await _get_user_from_refresh_cookie(request)
        if user is None:
            return RedirectResponse(url="/login", status_code=302)

    role = (user.get("role") or "").lower()
    if role not in ("seller", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    csrf_form, csrf_cookie = create_csrf_pair()
    resp = templates.TemplateResponse(
        "product_new.html",
        {"request": request, "title": "Create product", "csrf_token": csrf_form},
    )
    _set_csrf_cookie(resp, csrf_cookie)
    return resp


@router.post("/products/new", include_in_schema=False)
async def product_new_submit(request: Request) -> Response:
    form = await request.form()
    csrf_form_token = form.get("csrf_token")
    csrf_cookie = request.cookies.get("csrf_token")
    if not verify_csrf(csrf_form_token, csrf_cookie):
        return RedirectResponse(url="/products", status_code=303)

    ## Read user from request.state first (middleware), then fallback to cookie
    user = get_user_from_refresh_cookie_request_sync_state(request)
    if user is None:
        user = await _get_user_from_refresh_cookie(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    role = (user.get("role") or "").lower()
    if role not in ("seller", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    title = (form.get("title") or "").strip()
    description = (form.get("description") or "").strip()
    currency = (form.get("currency") or "USD").strip() or "USD"
    image_url = (form.get("image_url") or "").strip() or None
    try:
        price_raw = form.get("price")
        price = float(price_raw) if price_raw not in (None, "") else 0.0
    except Exception:
        price = 0.0

    try:
        await create_product_service(
            user=user,
            title=title,
            description=description,
            price=price,
            currency=currency,
            image_url=image_url,
        )
        return RedirectResponse(url="/products", status_code=303)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    except Exception as e:
        csrf_form2, csrf_cookie2 = create_csrf_pair()
        ctx = {
            "request": request,
            "title": "Create product",
            "error": str(e),
            "form": {
                "title": title,
                "description": description,
                "price": price,
                "currency": currency,
                "image_url": image_url or "",
            },
            "csrf_token": csrf_form2,
        }
        resp = templates.TemplateResponse("product_new.html", ctx, status_code=400)
        _set_csrf_cookie(resp, csrf_cookie2)
        return resp
