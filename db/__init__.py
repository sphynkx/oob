from pathlib import Path

import asyncpg

from config import get_config

POOL = None


async def init_database():
    global POOL
    cfg = get_config()
    POOL = await asyncpg.create_pool(dsn=cfg["DATABASE_URL"], min_size=1, max_size=10)
    if cfg["APPLY_SCHEMA_ON_START"]:
        async with POOL.acquire() as conn:
            await _apply_schema_from_file(conn)


async def close_database():
    global POOL
    if POOL is not None:
        await POOL.close()
        POOL = None


async def _apply_schema_from_file(conn):
    schema_path = Path("install/schema.sql")
    if not schema_path.exists():
        return
    sql = schema_path.read_text(encoding="utf-8")
    if not sql.strip():
        return
    await conn.execute(sql)


def get_pool():
    return POOL
