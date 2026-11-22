from fastapi import APIRouter, HTTPException, Request
from typing import List
import aiosqlite
from app.config import DB_PATH
from app.db.database import fetch_all
from app.models.setting import Setting
from app.services.bonjour import MAX_NAME_BYTES, NameInUseError, rename_service, service_display_name

import logging
log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings")

@router.get("", response_model=List[Setting])
async def get_settings():
    return await fetch_all("SELECT * FROM settings ORDER BY key ASC")

@router.post("")
async def post_settings(request: Request, settings: List[Setting]):
    for setting in settings:
        if setting.key == "SERVER_NAME":
            setting.value = (setting.value or "").strip()
            await _apply_server_name(request, setting.value)

    async with aiosqlite.connect(DB_PATH) as db:
        for setting in settings:
            await db.execute("UPDATE settings SET value = ? WHERE key = ?", (setting.value, setting.key))
        await db.commit()

    return {"detail": "Settings updated successfully"}

async def _apply_server_name(request: Request, new_name: str) -> None:
    """Validate the new server name and re-announce it via Bonjour right away, before anything is saved."""
    if not new_name:
        raise HTTPException(status_code=400, detail="The server name must not be empty.")
    if len(new_name.encode("utf-8")) > MAX_NAME_BYTES:
        raise HTTPException(status_code=400, detail=f"The server name is too long (max. {MAX_NAME_BYTES} bytes).")

    zeroconf = getattr(request.app.state, "zeroconf", None)
    current = getattr(request.app.state, "service_info", None)
    if zeroconf is None or current is None or service_display_name(current) == new_name:
        return

    try:
        request.app.state.service_info = await rename_service(zeroconf, current, new_name)
    except NameInUseError:
        raise HTTPException(status_code=409, detail=f"Another server on the network is already called “{new_name}”.")
