from db import get_pool


async def get_user_by_email(email):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, name, avatar_url, role FROM users WHERE email=$1",
            email,
        )
        return dict(row) if row else None


async def get_user_by_id(user_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, name, avatar_url, role FROM users WHERE id=$1",
            user_id,
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


async def update_user_profile(user_id: int, name: str | None = None, avatar_url: str | None = None):
    sets = []
    args = []
    if name is not None:
        sets.append("name=$%d" % (len(args) + 1))
        args.append(name)
    if avatar_url is not None:
        sets.append("avatar_url=$%d" % (len(args) + 1))
        args.append(avatar_url)
    if not sets:
        return
    args.append(user_id)
    sql = "UPDATE users SET " + ", ".join(sets) + " WHERE id=$%d" % (len(args))
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(sql, *args)


async def ensure_user_for_oauth(email: str, name: str | None, avatar_url: str | None, role: str = "buyer"):
    """
    Returns user dict. If not exists - creates with empty password_hash (blocks password login).
    If exists - updates name/avatar if changed.
    """
    existing = await get_user_by_email(email)
    if existing:
        to_update_name = name if (name and name != existing.get("name")) else None
        to_update_avatar = avatar_url if (avatar_url and avatar_url != existing.get("avatar_url")) else None
        if to_update_name is not None or to_update_avatar is not None:
            await update_user_profile(existing["id"], to_update_name, to_update_avatar)
            return await get_user_by_email(email)
        return existing

    user = await create_user(email=email, password_hash="", name=name or "", role=role)
    if avatar_url:
        await update_user_profile(user["id"], None, avatar_url)
        user = await get_user_by_email(email)
    return user

