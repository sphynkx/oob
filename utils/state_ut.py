import os
from typing import Tuple
import hmac
import base64
from hashlib import sha256

from config import get_config


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign(value: bytes, secret: bytes) -> str:
    sig = hmac.new(secret, value, sha256).digest()
    return _b64u(sig)


def create_state() -> str:
    cfg = get_config()
    secret = cfg["CSRF_SECRET"].encode("utf-8")
    rnd = os.urandom(32)
    payload = _b64u(rnd)
    sig = _sign(rnd, secret)
    return f"{payload}.{sig}"


def verify_state(state: str) -> bool:
    if not state or "." not in state:
        return False
    payload, sig = state.split(".", 1)
    try:
        rnd = _b64u_decode(payload)
    except Exception:
        return False
    cfg = get_config()
    secret = cfg["CSRF_SECRET"].encode("utf-8")
    expected = _sign(rnd, secret)
    return hmac.compare_digest(sig, expected)

