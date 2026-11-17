from fastapi import APIRouter, HTTPException
from typing import List
import aiosqlite

from app.models.movie import Movie
from app.models.serie import SerieDTO
from app.config import DB_PATH

router = APIRouter(prefix="/api/serie")

@router.get("/{serie_id}", response_model=SerieDTO)
async def get_serie(serie_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
SELECT id, title, poster_file_name, library_id,
    (SELECT COUNT(DISTINCT season) FROM movies WHERE is_episode_of_serie_id = series.id AND season IS NOT NULL) AS seasons_count
FROM series
WHERE id = ?
""", (serie_id,)) as cursor:
            row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Serie not found")
    return dict(row)

@router.get("/{serie_id}/episodes", response_model=List[Movie])
async def get_episodes(serie_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM movies WHERE is_episode_of_serie_id = ? ORDER BY season ASC, episode ASC", (serie_id,)) as cursor: 
            rows = await cursor.fetchall()

            if not rows:
                return []
            
            return [dict(row) for row in rows]