from fastapi import APIRouter, HTTPException
from typing import List

from app.api.series import SERIE_DTO_SELECT
from app.db.database import fetch_all, fetch_one
from app.models.movie import Movie
from app.models.serie import SerieDTO

router = APIRouter(prefix="/api/serie")

@router.get("/{serie_id}", response_model=SerieDTO)
async def get_serie(serie_id: int):
    serie = await fetch_one(SERIE_DTO_SELECT + "WHERE id = ?", (serie_id,))
    if serie is None:
        raise HTTPException(status_code=404, detail="Serie not found")
    return serie

@router.get("/{serie_id}/episodes", response_model=List[Movie])
async def get_episodes(serie_id: int):
    return await fetch_all("SELECT * FROM movies WHERE is_episode_of_serie_id = ? ORDER BY season ASC, episode ASC", (serie_id,))
