import os
from pathlib import Path

from dotenv import load_dotenv

_loaded = False
_cache = None


def _parse_bool(val, default=False):
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def _parse_list(val, default=None):
    if default is None:
        default = []
    if val is None:
        return default
    s = str(val).strip()
    if not s:
        return default
    parts = [x.strip() for x in s.split(",")]
    return [p for p in parts if p]


def _build_db_url():
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "oob01")
    user = os.getenv("DB_USER", "oob")
    pwd = os.getenv("DB_PASSWORD", "")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{name}"


def get_config():
    global _loaded, _cache
    if not _loaded:
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(override=False)
        _loaded = True

    ## UI guard env
    ui_public_paths = os.getenv(
        "UI_PUBLIC_PATHS",
        "/login,/register,/health,/static,/docs,/openapi.json,/redoc,/favicon.ico",
    )
    ui_protected_prefixes = os.getenv("UI_PROTECTED_PREFIXES", "/dashboard,/products")
    ui_skip_prefixes = os.getenv("UI_SKIP_PREFIXES", "/api,/auth")
    ui_root_redirect = os.getenv("UI_ROOT_REDIRECT", "true")

    ## CSRF
    csrf_secret = os.getenv("CSRF_SECRET", "change_me_in_prod_csrf")

    ## Google OAuth
    google_auth_url = os.getenv("OAUTH_GOOGLE_AUTH_URL", "https://accounts.google.com/o/oauth2/v2/auth")
    google_token_url = os.getenv("OAUTH_GOOGLE_TOKEN_URL", "https://oauth2.googleapis.com/token")
    google_userinfo_url = os.getenv("OAUTH_GOOGLE_USERINFO_URL", "https://openidconnect.googleapis.com/v1/userinfo")

    ## Twitter OAuth 2.0 with PKCE
    twitter_auth_url = os.getenv("OAUTH_TWITTER_AUTH_URL", "https://twitter.com/i/oauth2/authorize")
    twitter_token_url = os.getenv("OAUTH_TWITTER_TOKEN_URL", "https://api.twitter.com/2/oauth2/token")
    twitter_userinfo_url = os.getenv("OAUTH_TWITTER_USERINFO_URL", "https://api.twitter.com/2/users/me")
    twitter_scopes = os.getenv("OAUTH_TWITTER_SCOPES", "tweet.read users.read offline.access")
    twitter_allow_pseudo_email = _parse_bool(os.getenv("OAUTH_TWITTER_ALLOW_PSEUDO_EMAIL", "false"), False)
    oauth_pseudo_email_domain = os.getenv("OAUTH_PSEUDO_EMAIL_DOMAIN", "")  # example: twitter.local

    cfg = {
        "PORT": int(os.getenv("PORT", "8010")),
        "APP_ENV": os.getenv("APP_ENV", "dev"),

        "DATABASE_URL": _build_db_url(),
        "APPLY_SCHEMA_ON_START": _parse_bool(os.getenv("APPLY_SCHEMA_ON_START", "true"), True),

        "JWT_SECRET": os.getenv("JWT_SECRET", "change_me_in_prod"),
        "JWT_ALGORITHM": os.getenv("JWT_ALGORITHM", "HS256"),
        "ACCESS_TOKEN_EXPIRES_MINUTES": int(os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", "15")),
        "REFRESH_TOKEN_EXPIRES_DAYS": int(os.getenv("REFRESH_TOKEN_EXPIRES_DAYS", "30")),
        "REFRESH_COOKIE_NAME": os.getenv("REFRESH_COOKIE_NAME", "refresh_token"),
        "BCRYPT_ROUNDS": int(os.getenv("BCRYPT_ROUNDS", "12")),

        "COOKIE_SECURE": _parse_bool(os.getenv("COOKIE_SECURE", "false")),
        "COOKIE_SAMESITE": os.getenv("COOKIE_SAMESITE", "lax"),
        "COOKIE_DOMAIN": os.getenv("COOKIE_DOMAIN", "") or None,

        "CORS_ORIGINS": _parse_list(os.getenv("CORS_ORIGINS", "*")),

        ## OAuth Google
        "OAUTH_GOOGLE_CLIENT_ID": os.getenv("OAUTH_GOOGLE_CLIENT_ID", ""),
        "OAUTH_GOOGLE_CLIENT_SECRET": os.getenv("OAUTH_GOOGLE_CLIENT_SECRET", ""),
        "OAUTH_GOOGLE_REDIRECT_URI": os.getenv(
            "OAUTH_GOOGLE_REDIRECT_URI",
            "http://localhost:8010/oauth/google/callback",
        ),
        "OAUTH_GOOGLE_AUTH_URL": google_auth_url,
        "OAUTH_GOOGLE_TOKEN_URL": google_token_url,
        "OAUTH_GOOGLE_USERINFO_URL": google_userinfo_url,

        ## OAuth Twitter
        "OAUTH_TWITTER_CLIENT_ID": os.getenv("OAUTH_TWITTER_CLIENT_ID", ""),
        "OAUTH_TWITTER_CLIENT_SECRET": os.getenv("OAUTH_TWITTER_CLIENT_SECRET", ""),
        "OAUTH_TWITTER_REDIRECT_URI": os.getenv(
            "OAUTH_TWITTER_REDIRECT_URI",
            "http://localhost:8010/oauth/twitter/callback",
        ),
        "OAUTH_TWITTER_AUTH_URL": twitter_auth_url,
        "OAUTH_TWITTER_TOKEN_URL": twitter_token_url,
        "OAUTH_TWITTER_USERINFO_URL": twitter_userinfo_url,
        "OAUTH_TWITTER_SCOPES": twitter_scopes,
        "OAUTH_TWITTER_ALLOW_PSEUDO_EMAIL": twitter_allow_pseudo_email,
        "OAUTH_PSEUDO_EMAIL_DOMAIN": oauth_pseudo_email_domain,

        ## UI guard
        "UI_PUBLIC_PATHS": ui_public_paths,
        "UI_PROTECTED_PREFIXES": ui_protected_prefixes,
        "UI_SKIP_PREFIXES": ui_skip_prefixes,
        "UI_ROOT_REDIRECT": ui_root_redirect,

        ## CSRF
        "CSRF_SECRET": os.getenv("CSRF_SECRET", "XXXXXXXXXX"),
    }

    cors = cfg["CORS_ORIGINS"]
    if cors == ["*"] or len(cors) == 0:
        cfg["CORS_ORIGINS"] = ["*"]

    _cache = cfg
    return cfg

