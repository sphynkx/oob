from db.sessions_db import get_session_by_id, list_sessions_for_user, revoke_session


async def list_user_sessions_service(user_id):
    return await list_sessions_for_user(user_id)


async def revoke_user_session_service(user_id, session_id):
    session = await get_session_by_id(session_id)
    if not session or session["user_id"] != user_id:
        raise PermissionError("Forbidden")
    await revoke_session(session_id)
