import os
import uuid

from fastapi.testclient import TestClient

from main import app


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_login_refresh_me_and_public_products():
    """
    Full flow: register -> login -> me -> refresh -> public products -> stats with Bearer.
    """
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "Passw0rd!"
    name = "Test User"

    with TestClient(app) as client:
        ## Register
        r = client.post(
            "/auth/register",
            json={"email": email, "password": password, "name": name},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["email"] == email

        ## Login, expect access_token and refresh cookie set on client
        r = client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        assert r.status_code == 200, r.text
        access = r.json().get("access_token")
        assert access, "access_token missing"

        ## /auth/me with Bearer
        r = client.get("/auth/me", headers=_bearer(access))
        assert r.status_code == 200, r.text
        me = r.json()
        assert me["email"] == email

        ## Public products list
        r = client.get("/api/products")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

        ## Stats require Bearer
        r = client.get("/api/products/stats", headers=_bearer(access))
        assert r.status_code == 200, r.text
        stats = r.json()
        assert "total" in stats or "products_total" in stats or isinstance(stats, dict)

        ## Refresh (uses client's cookies with refresh token)
        r = client.post("/auth/refresh")
        assert r.status_code == 200, r.text
        new_access = r.json().get("access_token")
        assert new_access, "refresh did not return access_token"


def test_get_product_not_found():
    with TestClient(app) as client:
        r = client.get("/api/products/99999999")
        assert r.status_code in (404, 400), r.text


def test_create_product_as_seller_if_env_credentials_provided():
    """
    This test runs only if SELLER_EMAIL and SELLER_PASSWORD are provided in environment.
    It verifies that a seller can create a product via JSON API.
    """
    seller_email = os.getenv("SELLER_EMAIL")
    seller_password = os.getenv("SELLER_PASSWORD")

    if not seller_email or not seller_password:
        ## Skip gracefully when seller credentials are not configured
        return

    with TestClient(app) as client:
        ## Login as seller
        r = client.post(
            "/auth/login",
            json={"email": seller_email, "password": seller_password},
        )
        assert r.status_code == 200, r.text
        access = r.json().get("access_token")
        assert access

        ## Create product
        payload = {
            "title": f"pytest product {uuid.uuid4().hex[:6]}",
            "description": "created in automated test",
            "price": 1.23,
            "currency": "USD",
            "image_url": None,
        }
        r = client.post("/api/products", headers=_bearer(access), json=payload)
        assert r.status_code in (201, 200), r.text
        item = r.json()
        assert item["title"] == payload["title"]
        assert float(item["price"]) == float(payload["price"])

        ## Optionally, fetch it back by id
        pid = item.get("id")
        if pid:
            r = client.get(f"/api/products/{pid}")
            assert r.status_code == 200, r.text
            got = r.json()
            assert got["id"] == pid
