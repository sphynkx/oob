from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from config import get_config
from db import init_database, close_database
from routes.auth_routes import router as auth_router
from routes.health_routes import router as health_router
from routes.ui_routes import router as ui_router


@asynccontextmanager
async def lifespan(app):
    await init_database()
    try:
        yield
    finally:
        await close_database()


cfg = get_config()
app = FastAPI(title="oob Auth Service", version="0.1.0", lifespan=lifespan)

cors_origins = cfg.get("CORS_ORIGINS", ["*"])
if isinstance(cors_origins, str):
    cors_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
allow_origins = ["*"] if not cors_origins or cors_origins == ["*"] else cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(health_router, tags=["health"])
app.include_router(ui_router, tags=["ui"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
