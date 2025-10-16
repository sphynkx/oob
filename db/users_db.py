from db import get_pool


async def get_user_by_email(email):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, name, avatar_url, role FROM users WHERE email=$1",
            email,
        )
        return dict(row) if row else None


async def create_user(email, password_hash, name, role: str = "buyer"):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (email, password_hash, name, role)
            VALUES ($1, $2, $3, $4)
            RETURNING id, email, password_hash, name, avatar_url, role
            """,
            email,
            password_hash,
            name,
            role,
        )
        return dict(row)


async def get_user_by_id(user_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, name, avatar_url, role FROM users WHERE id=$1",
            user_id,
        )
        return dict(row) if row else None
