from fastapi import APIRouter
from typing import List

from app.db.database import fetch_all
from app.models.serie import SerieDTO

router = APIRouter(prefix="/api/series")

# SerieDTO: the serie + the number of its seasons (also used by api/serie.py)
SERIE_DTO_SELECT = """
SELECT id, title, poster_file_name, library_id,
    (SELECT COUNT(DISTINCT season) FROM movies WHERE is_episode_of_serie_id = series.id AND season IS NOT NULL) AS seasons_count
FROM series
"""

@router.get("/{library_id}", response_model=List[SerieDTO])
async def get_series(library_id: int):
    return await fetch_all(SERIE_DTO_SELECT + "WHERE library_id = ? ORDER BY title COLLATE NOCASE", (library_id,))
