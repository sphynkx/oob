import os
import uuid

import pytest
from fastapi.testclient import TestClient

from main import app


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
def test_register_duplicate_email_returns_400():
    email = f"dup_{uuid.uuid4().hex[:6]}@example.com"
    password = "Passw0rd!"
    name = "Test User"

    with TestClient(app) as client:
        r1 = client.post(
            "/auth/register", json={"email": email, "password": password, "name": name}
        )
        assert r1.status_code == 201, r1.text

        r2 = client.post(
            "/auth/register", json={"email": email, "password": password, "name": name}
        )
        assert r2.status_code == 400, r2.text
        assert "Email" in r2.text or "registered" in r2.text


@pytest.mark.integration
def test_login_wrong_password_returns_401():
    email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    password_ok = "Passw0rd!"
    password_bad = "wrong-pass"
    name = "Test User"

    with TestClient(app) as client:
        r = client.post(
            "/auth/register", json={"email": email, "password": password_ok, "name": name}
        )
        assert r.status_code == 201, r.text

        r = client.post("/auth/login", json={"email": email, "password": password_bad})
        assert r.status_code == 401, r.text


@pytest.mark.integration
def test_refresh_without_cookie_returns_401():
    with TestClient(app) as client:
        r = client.post("/auth/refresh")
        assert r.status_code == 401, r.text
        assert "Missing refresh token" in r.text


@pytest.mark.integration
def test_logout_all_requires_bearer_and_succeeds_with_bearer():
    email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    password = "Passw0rd!"
    name = "Test User"

    with TestClient(app) as client:
        r = client.post("/auth/register", json={"email": email, "password": password, "name": name})
        assert r.status_code == 201, r.text

        r = client.post("/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        access = r.json().get("access_token")
        assert access

        ## Missing bearer -> 401
        r = client.post("/auth/logout", json={"all": True})
        assert r.status_code == 401, r.text

        ## With bearer -> 204
        r = client.post("/auth/logout", json={"all": True}, headers=_bearer(access))
        assert r.status_code == 204, r.text


@pytest.mark.integration
def test_buyer_cannot_create_product_returns_403():
    email = f"buyer_{uuid.uuid4().hex[:6]}@example.com"
    password = "Passw0rd!"
    name = "Buyer User"

    with TestClient(app) as client:
        ## Register buyer (default role is buyer)
        r = client.post("/auth/register", json={"email": email, "password": password, "name": name})
        assert r.status_code == 201, r.text

        r = client.post("/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        access = r.json().get("access_token")
        assert access

        ## Try to create product as buyer -> 403
        payload = {
            "title": "should be forbidden",
            "description": "buyer cannot create products",
            "price": 1.0,
            "currency": "USD",
            "image_url": None,
        }
        r = client.post("/api/products", headers=_bearer(access), json=payload)
        assert r.status_code == 403, r.text


@pytest.mark.integration
def test_products_pagination_limits():
    with TestClient(app) as client:
        r = client.get("/api/products?limit=1&offset=0")
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        assert len(items) <= 1

        r = client.get("/api/products?limit=100&offset=0")
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        assert len(items) <= 100


@pytest.mark.integration
def test_create_product_empty_title_returns_400_for_seller_if_env_present():
    seller_email = os.getenv("SELLER_EMAIL")
    seller_password = os.getenv("SELLER_PASSWORD")
    if not seller_email or not seller_password:
        pytest.skip("SELLER_EMAIL/SELLER_PASSWORD not set")

    with TestClient(app) as client:
        r = client.post("/auth/login", json={"email": seller_email, "password": seller_password})
        assert r.status_code == 200, r.text
        access = r.json().get("access_token")
        assert access

        payload = {
            "title": "",
            "description": "invalid because title is empty",
            "price": 2.5,
            "currency": "USD",
            "image_url": None,
        }
        r = client.post("/api/products", headers=_bearer(access), json=payload)
        ## Service checks that title is truthy -> ValueError -> 400
        assert r.status_code == 400, r.text


@pytest.mark.integration
def test_stats_mine_changes_after_create_and_delete_for_seller_if_env_present():
    seller_email = os.getenv("SELLER_EMAIL")
    seller_password = os.getenv("SELLER_PASSWORD")
    if not seller_email or not seller_password:
        pytest.skip("SELLER_EMAIL/SELLER_PASSWORD not set")

    with TestClient(app) as client:
        ## Login seller
        r = client.post("/auth/login", json={"email": seller_email, "password": seller_password})
        assert r.status_code == 200, r.text
        access = r.json().get("access_token")
        assert access

        ## Get stats before
        r = client.get("/api/products/stats", headers=_bearer(access))
        assert r.status_code == 200, r.text
        before = r.json()
        before_mine = int(before.get("mine") or before.get("products_total") or 0)
        before_total = int(before.get("total") or 0)

        ## Create product
        payload = {
            "title": f"stats product {uuid.uuid4().hex[:6]}",
            "description": "temporary product for stats",
            "price": 3.14,
            "currency": "USD",
            "image_url": None,
        }
        r = client.post("/api/products", headers=_bearer(access), json=payload)
        assert r.status_code in (201, 200), r.text
        item = r.json()
        pid = item["id"]

        ## Stats after create: mine +1, total >= before_total
        r = client.get("/api/products/stats", headers=_bearer(access))
        assert r.status_code == 200, r.text
        after_create = r.json()
        mine_after = int(after_create.get("mine") or after_create.get("products_total") or 0)
        total_after = int(after_create.get("total") or 0)
        assert mine_after == before_mine + 1
        assert total_after >= before_total

        ## Delete product
        r = client.delete(f"/api/products/{pid}", headers=_bearer(access))
        assert r.status_code in (204, 200), r.text

        ## Stats after delete: mine returns to before_mine (allowing slight race tolerance on total)
        r = client.get("/api/products/stats", headers=_bearer(access))
        assert r.status_code == 200, r.text
        after_delete = r.json()
        mine_after_del = int(after_delete.get("mine") or after_delete.get("products_total") or 0)
        assert mine_after_del == before_mine
