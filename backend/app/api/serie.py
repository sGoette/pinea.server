from fastapi import APIRouter
from typing import List
import aiosqlite

from app.models.movie import Movie
from app.config import DB_PATH

router = APIRouter(prefix="/api/serie")

@router.get("/{serie_id}/episodes", response_model=List[Movie])
async def get_episodes(serie_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM movies WHERE is_episode_of_serie_id = ? ORDER BY season ASC, episode ASC", (serie_id,)) as cursor: 
            rows = await cursor.fetchall()

            if not rows:
                return []
            
            return [dict(row) for row in rows]