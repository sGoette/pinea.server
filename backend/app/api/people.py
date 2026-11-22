from fastapi import APIRouter
from typing import List

from app.db.database import fetch_all
from app.models.person import PersonWithStats

router = APIRouter(prefix="/api/people")

@router.get("/{library_id}", response_model=List[PersonWithStats])
async def get_people_of_library(library_id: int):
    """All people of a library with the number of their titles (extras don't count), sorted by name."""
    return await fetch_all("""
SELECT p.*, COUNT(m.id) movie_count
FROM people p
JOIN movies__people mp ON mp.person_id = p.id
JOIN movies m ON m.id = mp.movie_id AND m.is_extra_of_movie_id IS NULL
WHERE p.library_id = ?
GROUP BY p.id
ORDER BY p.name COLLATE NOCASE ASC
""", (library_id,))
