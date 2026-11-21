from fastapi import APIRouter
import aiosqlite
from typing import List

from app.config import DB_PATH
from app.models.person import PersonWithStats

router = APIRouter(prefix="/api/people")

@router.get("/{library_id}", response_model=List[PersonWithStats])
async def get_people_of_library(library_id: int):
    """All people of a library with the number of their titles (extras don't count), sorted by name."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
"""
SELECT p.*, COUNT(m.id) movie_count
FROM people p
JOIN movies__people mp ON mp.person_id = p.id
JOIN movies m ON m.id = mp.movie_id AND m.is_extra_of_movie_id IS NULL
WHERE p.library_id = ?
GROUP BY p.id
ORDER BY p.name COLLATE NOCASE ASC
""", (library_id,)) as cursor:
            rows = await cursor.fetchall()

        return [dict(row) for row in rows]
