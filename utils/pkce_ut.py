import base64
import hashlib
import os


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def create_code_verifier() -> str:
    return _b64u(os.urandom(64))


def create_code_challenge_s256(code_verifier: str) -> str:
    h = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return _b64u(h)
