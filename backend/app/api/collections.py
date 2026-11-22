from fastapi import APIRouter
from typing import List

from app.db.database import fetch_all
from app.models.collection import CollectionWithStats

router = APIRouter(prefix="/api/collections")

@router.get("/{library_id}", response_model=List[CollectionWithStats])
async def get_collections(library_id: int):
    return await fetch_all("""
SELECT c.*,
(
    SELECT COUNT(*)
    FROM movies__collections mc
    JOIN movies m ON mc.movie_id = m.id
    WHERE mc.collection_id = c.id
    AND m.is_extra_of_movie_id IS NULL
) movie_count
FROM collections c
WHERE library_id = ?
ORDER BY c.title ASC
""", (library_id,))
