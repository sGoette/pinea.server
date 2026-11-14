from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
import aiosqlite
from os import path
import re
from typing import List, Optional

from app.config import DB_PATH
from app.models.movie import Movie
from app.models.person import Person
from app.config import GET_MEDIA_ROOT_FOLDER

router = APIRouter(prefix="/api/movie")

@router.get("/{movie_id}", response_model=Movie)
async def get_movie(movie_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)) as cursor:
            movie = await cursor.fetchone()

    if movie is None: 
        raise HTTPException(status_code=404, detail="Movie not found")
    
    return dict(movie)

CHUNK_SIZE = 1024 * 1024 * 10  # 10 MB per chunk

RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")

class RangeNotSatisfiable(Exception):
    pass

def parse_range(header: str, file_size: int) -> Optional[tuple[int, int]]:
    """Parse a single HTTP byte range into an inclusive (start, end).

    Returns None for headers we don't support (malformed, multiple ranges): the caller then
    ignores the header and sends the whole file, which RFC 9110 allows.
    Raises RangeNotSatisfiable for ranges outside the file (-> 416).
    """
    match = RANGE_RE.match(header.strip())
    if not match:
        return None
    start_str, end_str = match.groups()

    if start_str == "" and end_str == "":
        return None
    if start_str == "":
        # Suffix range "bytes=-N": the last N bytes
        suffix_length = int(end_str)
        if suffix_length == 0 or file_size == 0:
            raise RangeNotSatisfiable()
        return max(0, file_size - suffix_length), file_size - 1

    start = int(start_str)
    if end_str and int(end_str) < start:
        return None  # syntactically invalid ("bytes=200-100") -> ignore
    if start >= file_size:
        raise RangeNotSatisfiable()
    end = int(end_str) if end_str else file_size - 1
    return start, min(end, file_size - 1)  # an end past the file means "to the end"

@router.get("/{movie_id}/stream")
async def stream_movie(request: Request, movie_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)) as cursor:
            movie = await cursor.fetchone()
        MEDIA_ROOT_FOLDER = await GET_MEDIA_ROOT_FOLDER()

    if not movie or not MEDIA_ROOT_FOLDER:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    file_path = path.join(MEDIA_ROOT_FOLDER, movie["file_location"])
    if not path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    file_size = path.getsize(file_path)
    headers = { "Accept-Ranges": "bytes" }

    byte_range: Optional[tuple[int, int]] = None
    range_header = request.headers.get("range")
    if range_header:
        try:
            byte_range = parse_range(range_header, file_size)
        except RangeNotSatisfiable:
            return Response(status_code=416, headers={ **headers, "Content-Range": f"bytes */{file_size}" })

    if byte_range:
        start, end = byte_range
        length = end - start + 1

        def iter_file():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk_size = min(CHUNK_SIZE, remaining)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    yield data
                    remaining -= len(data)

        headers.update({
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(length)
        })
        return StreamingResponse(iter_file(), status_code=206, headers=headers, media_type="video/mp4")
    
    else:
        # No (usable) Range header, return entire file
        def iter_file_full():
            with open(file_path, "rb") as f:
                while True:
                    data = f.read(CHUNK_SIZE)
                    if not data:
                        break
                    yield data

        headers.update({ "Content-Length": str(file_size) })
        return StreamingResponse(iter_file_full(), headers=headers, media_type="video/mp4")


@router.get("/{movie_id}/people", response_model=List[Person])
async def get_people(movie_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
SELECT p.*
FROM people p
JOIN movies__people mp ON mp.person_id = p.id 
WHERE mp.movie_id = ?
ORDER BY p.name ASC
""", (movie_id,)) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        return []
    
    return [dict(row) for row in rows]

@router.get("/{movie_id}/extras", response_model=List[Movie])
async def get_extras(movie_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM movies WHERE is_extra_of_movie_id = ? ORDER BY title ASC", (movie_id,)) as cursor: 
            rows = await cursor.fetchall()

    if not rows: 
        return []
    
    return [dict(row) for row in rows]
