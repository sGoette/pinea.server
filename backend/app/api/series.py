from fastapi import APIRouter
from typing import List
import aiosqlite

from app.config import DB_PATH
from app.models.serie import SerieDTO

router = APIRouter(prefix="/api/series")

@router.get("/{library_id}", response_model=List[SerieDTO])
async def get_series(library_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT
                id,
                title,
                poster_file_name,
                library_id,
                (
                    SELECT COUNT(DISTINCT season) FROM movies WHERE is_episode_of_serie_id = series.id AND season IS NOT NULL
                ) AS seasons_count
            FROM series 
            WHERE library_id = ?
            """,
        (library_id,)) as cursor:
            rows = await cursor.fetchall()

            if not rows:
                return []
            
            return [dict(row) for row in rows]