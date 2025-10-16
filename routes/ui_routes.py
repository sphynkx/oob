from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.auth_service import (
    login_user_service,
    register_user_service,
    logout_current_service,
)
from services.products_service import (
    list_products_service,
    create_product_service,
    delete_product_service,
    get_products_stats_service,
)
from utils.security_ut import get_refresh_cookie_name
from utils.ui_guard_ut import (
    _get_user_from_refresh_cookie,
    get_user_from_refresh_cookie_request_sync_state,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "title": "Login"})


@router.post("/login", include_in_schema=False)
async def login_submit(request: Request):
    form = await request.form()
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
        return resp
    except ValueError as e:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "title": "Login", "error": str(e)},
            status_code=401,
        )


@router.get("/register", response_class=HTMLResponse, include_in_schema=False)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "title": "Register"})


@router.post("/register", include_in_schema=False)
async def register_submit(request: Request):
    form = await request.form()
    email = (form.get("email") or "").strip()
    password = form.get("password") or ""
    name = (form.get("name") or "").strip()

    if not email or not password:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "title": "Register", "error": "Email and password are required.", "form": {"email": email, "name": name}},
            status_code=400,
        )

    try:
        await register_user_service(email, password, name)
        return RedirectResponse(url="/login", status_code=303)
    except ValueError as e:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "title": "Register", "error": str(e), "form": {"email": email, "name": name}},
            status_code=400,
        )


@router.post("/logout", include_in_schema=False)
async def logout_ui(request: Request) -> Response:
    cookie_name = get_refresh_cookie_name()
    refresh_token = request.cookies.get(cookie_name)
    if refresh_token:
        try:
            await logout_current_service(refresh_token)
        except Exception:
            pass
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(key=cookie_name, path="/")
    return resp


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page(request: Request):
    user = get_user_from_refresh_cookie_request_sync_state(request)
    if user is None:
        user = await _get_user_from_refresh_cookie(request)
        if user is None:
            return RedirectResponse(url="/login", status_code=302)

    stats = await get_products_stats_service(user["id"])
    ctx = {
        "request": request,
        "title": "Dashboard",
        "me": {"id": user["id"], "email": user["email"], "name": user["name"], "role": user.get("role")},
        "stats": stats,
    }
    return templates.TemplateResponse("dashboard.html", ctx)


@router.get("/products", response_class=HTMLResponse, include_in_schema=False)
async def products_page(request: Request):
    user = get_user_from_refresh_cookie_request_sync_state(request)
    products = await list_products_service(limit=100, offset=0)
    ctx = {"request": request, "title": "Products", "me": user, "products": products}
    return templates.TemplateResponse("products.html", ctx)


@router.post("/products/{product_id}/delete", include_in_schema=False)
async def product_delete_ui(product_id: int, request: Request) -> Response:
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
    user = await _get_user_from_refresh_cookie(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)
    role = (user.get("role") or "").lower()
    if role not in ("seller", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return templates.TemplateResponse("product_new.html", {"request": request, "title": "Create product"})


@router.post("/products/new", include_in_schema=False)
async def product_new_submit(request: Request) -> Response:
    user = await _get_user_from_refresh_cookie(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)
    role = (user.get("role") or "").lower()
    if role not in ("seller", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    form = await request.form()
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
        ctx = {
            "request": request,
            "title": "Create product",
            "error": str(e),
            "form": {"title": title, "description": description, "price": price, "currency": currency, "image_url": image_url or ""},
        }
        return templates.TemplateResponse("product_new.html", ctx, status_code=400)
