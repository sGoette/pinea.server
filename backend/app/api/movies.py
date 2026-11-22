from fastapi import APIRouter
from typing import List

from app.db.database import fetch_all
from app.models.movie import Movie

router = APIRouter(prefix="/api/movies")

@router.get("/{library_id}", response_model=List[Movie])
async def get_movies(library_id: int):
    return await fetch_all("SELECT * FROM movies WHERE is_extra_of_movie_id IS NULL AND library_id = ? ORDER BY title ASC", (library_id,))

LATEST_MOVIES_LIMIT = 20

@router.get("/{library_id}/latest", response_model=List[Movie])
async def get_latest_movies(library_id: int):
    """The newest titles of a library (no extras), newest first. added_date is when the scanner first found the file."""
    # id as tie breaker: a scan adds many files within the same second
    return await fetch_all("""
SELECT * FROM movies
WHERE is_extra_of_movie_id IS NULL AND library_id = ?
ORDER BY added_date DESC, id DESC
LIMIT ?
""", (library_id, LATEST_MOVIES_LIMIT))

@router.get("/collection/{collection_id}", response_model=List[Movie])
async def get_movies_of_collection(collection_id: int):
    return await fetch_all("""
SELECT m.*
FROM movies m
JOIN movies__collections mc ON mc.movie_id = m.id
WHERE mc.collection_id = ?
AND m.is_extra_of_movie_id IS NULL
ORDER BY m.title ASC
""", (collection_id,))

@router.get("/person/{person_id}", response_model=List[Movie])
async def get_movies_of_person(person_id: int):
    return await fetch_all("""
SELECT m.*
FROM movies m
JOIN movies__people mp ON mp.movie_id = m.id
WHERE mp.person_id = ?
AND m.is_extra_of_movie_id IS NULL
ORDER BY m.title ASC
""", (person_id,))
