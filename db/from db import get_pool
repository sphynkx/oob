from db import get_pool


async def create_session_placeholder(user_id, user_agent, ip, expires_at):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO sessions (user_id, refresh_token_hash, user_agent, ip, expires_at)
            VALUES ($1, 'pending', $2, $3, $4)
            RETURNING id, user_id, created_at, expires_at
            """,
            user_id,
            user_agent,
            ip,
            expires_at,
        )
        return dict(row)


async def set_session_token_hash(session_id, token_hash):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sessions SET refresh_token_hash=$1 WHERE id=$2",
            token_hash,
            session_id,
        )


async def get_session_by_id(session_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_id, refresh_token_hash, user_agent, ip,
                   created_at, last_used_at, expires_at, revoked_at
            FROM sessions
            WHERE id=$1
            """,
            session_id,
        )
        return dict(row) if row else None


async def touch_session(session_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sessions SET last_used_at=NOW() WHERE id=$1",
            session_id,
        )


async def rotate_session(session_id, new_hash, new_expires_at):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE sessions
            SET refresh_token_hash=$1, expires_at=$2, last_used_at=NOW()
            WHERE id=$3
            """,
            new_hash,
            new_expires_at,
            session_id,
        )


async def revoke_session(session_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sessions SET revoked_at=NOW() WHERE id=$1 AND revoked_at IS NULL",
            session_id,
        )


async def revoke_all_sessions_for_user(user_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sessions SET revoked_at=NOW() WHERE user_id=$1 AND revoked_at IS NULL",
            user_id,
        )
