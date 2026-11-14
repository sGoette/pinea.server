from fastapi import APIRouter, HTTPException

from app.models.update import UpdateStatus
from app.services.updater import updater, UpdateError

router = APIRouter(prefix="/api/update")

@router.get("/status", response_model=UpdateStatus)
async def get_update_status():
    return updater.status()

@router.post("/check", response_model=UpdateStatus)
async def check_for_update():
    return await updater.check()

@router.post("/install", response_model=UpdateStatus)
async def install_update():
    try:
        return await updater.start_install()
    except UpdateError as e:
        raise HTTPException(status_code=409, detail=str(e))
