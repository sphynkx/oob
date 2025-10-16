import base64
import hmac
import os
from hashlib import sha256
from typing import Tuple

from config import get_config


def _sign(value: bytes, secret: bytes) -> str:
    sig = hmac.new(secret, value, sha256).digest()
    return base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def create_csrf_pair() -> Tuple[str, str]:
    """
    Returns (form_token, cookie_value). They are identical (double-submit).
    """
    cfg = get_config()
    secret = cfg["CSRF_SECRET"].encode("utf-8")
    nonce = os.urandom(32)
    payload = _b64u(nonce)
    sig = _sign(nonce, secret)
    token = f"{payload}.{sig}"
    return token, token


def verify_csrf(token_from_form: str, token_from_cookie: str) -> bool:
    if not token_from_form or not token_from_cookie:
        return False
    if token_from_form != token_from_cookie:
        return False
    try:
        payload, sig = token_from_form.split(".", 1)
        nonce = _b64u_decode(payload)
    except Exception:
        return False
    cfg = get_config()
    secret = cfg["CSRF_SECRET"].encode("utf-8")
    expected = _sign(nonce, secret)
    return hmac.compare_digest(sig, expected)