from fastapi import APIRouter
from typing import List

from app.db.database import fetch_all
from app.models.library import Library

router = APIRouter(prefix="/api/libraries")

@router.get("", response_model=List[Library])
async def get_libraries():
    return await fetch_all("SELECT * FROM libraries ORDER BY name ASC")
