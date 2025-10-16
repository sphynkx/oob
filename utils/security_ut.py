import bcrypt
import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import get_config
from db.users_db import get_user_by_id

_auth_scheme = HTTPBearer(auto_error=True)


def get_security_config():
    cfg = get_config()
    return {
        "JWT_SECRET": cfg["JWT_SECRET"],
        "JWT_ALGORITHM": cfg["JWT_ALGORITHM"],
        "ACCESS_TOKEN_EXPIRES_MINUTES": cfg["ACCESS_TOKEN_EXPIRES_MINUTES"],
        "REFRESH_TOKEN_EXPIRES_DAYS": cfg["REFRESH_TOKEN_EXPIRES_DAYS"],
        "REFRESH_COOKIE_NAME": cfg["REFRESH_COOKIE_NAME"],
        "BCRYPT_ROUNDS": cfg["BCRYPT_ROUNDS"],
        "COOKIE_SECURE": cfg["COOKIE_SECURE"],
        "COOKIE_SAMESITE": cfg["COOKIE_SAMESITE"],
        "COOKIE_DOMAIN": cfg["COOKIE_DOMAIN"],
    }


def get_refresh_cookie_name():
    return get_security_config()["REFRESH_COOKIE_NAME"]


def hash_password(password):
    rounds = get_security_config()["BCRYPT_ROUNDS"]
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password, password_hash):
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id):
    sec = get_security_config()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=sec["ACCESS_TOKEN_EXPIRES_MINUTES"])).timestamp()),
    }
    token = jwt.encode(payload, sec["JWT_SECRET"], algorithm=sec["JWT_ALGORITHM"])
    return token


def generate_refresh_token_for_session(session_id):
    random_part = secrets.token_urlsafe(32)
    return f"{session_id}.{random_part}"


def parse_refresh_token(token):
    try:
        parts = token.split(".", 1)
        session_id = int(parts[0])
        secret_part = parts[1]
        return session_id, secret_part
    except Exception:
        raise ValueError("Invalid refresh token format")


def hash_refresh_token(token):
    rounds = get_security_config()["BCRYPT_ROUNDS"]
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(token.encode("utf-8"), salt).decode("utf-8")


def verify_refresh_token_hash(token, token_hash):
    try:
        return bcrypt.checkpw(token.encode("utf-8"), token_hash.encode("utf-8"))
    except Exception:
        return False


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_auth_scheme)):
    sec = get_security_config()
    token = credentials.credentials
    try:
        payload = jwt.decode(token, sec["JWT_SECRET"], algorithms=[sec["JWT_ALGORITHM"]])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user = await get_user_by_id(int(sub))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
