from fastapi import APIRouter, Depends, HTTPException, status

from services.auth_sessions_service import list_user_sessions_service, revoke_user_session_service
from utils.security_ut import get_current_user

router = APIRouter(prefix="/auth")


@router.get("/sessions")
async def list_sessions(user=Depends(get_current_user)):
    items = await list_user_sessions_service(user["id"])
    return items


@router.post("/sessions/{session_id}/revoke", status_code=204)
async def revoke_session(session_id: int, user=Depends(get_current_user)):
    try:
        await revoke_user_session_service(user["id"], session_id)
        return
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
