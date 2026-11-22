from fastapi import APIRouter, HTTPException, Request
from pathlib import Path
import asyncio
import os
import anyio
from fastapi.responses import Response, StreamingResponse
from os import path
import re
from typing import List, Optional

from app.db.database import fetch_all, fetch_one
from app.models.movie import Movie
from app.models.person import MoviePerson
from app.models.collection import Collection
from app.config import GET_MEDIA_ROOT_FOLDER
from app.models.library import Library
from app.models.metadata import SearchResult
from app.scanner.jobs import ScanJob
from app.scanner.scraper import find_scraper_config, load_scraper, run_search

import logging
log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/movie")

@router.get("/{movie_id}", response_model=Movie)
async def get_movie(movie_id: int):
    return await _get_movie_row(movie_id)

async def _get_movie_row(movie_id: int) -> dict:
    movie = await fetch_one("SELECT * FROM movies WHERE id = ?", (movie_id,))
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie

# Small chunks: the first bytes go out quickly (AVPlayer opens a new range request for every seek)
# and TCP backpressure from a full player buffer stops the reading early.
CHUNK_SIZE = 1024 * 1024

# The stream URL has no file extension, so AVPlayer goes by the Content-Type
VIDEO_MEDIA_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/x-m4v",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".wmv": "video/x-ms-wmv",
    ".flv": "video/x-flv",
}

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

class FileRangeResponse(StreamingResponse):
    """Sends bytes start..end (inclusive) of a file.

    Starlette's StreamingResponse with a sync generator never closes the generator when the client
    disconnects, so every cancelled request (AVPlayer cancels one on every seek) leaked an open file.
    Here the file is closed in `finally`. The next chunk is read in a thread while the current one is
    sent, so a slow disk / NFS read and the network send overlap instead of taking turns.
    """
    def __init__(self, file_path: str, start: int, end: int, status_code: int, headers: dict[str, str], media_type: str):
        super().__init__(content=iter(()), status_code=status_code, headers=headers, media_type=media_type)
        self.file_path = file_path
        self.start = start
        self.end = end

    async def stream_response(self, send) -> None:
        await send({ "type": "http.response.start", "status": self.status_code, "headers": self.raw_headers })

        file = await anyio.to_thread.run_sync(open, self.file_path, "rb")
        fd = file.fileno()
        position = self.start
        remaining = self.end - self.start + 1

        def read_next() -> "asyncio.Future[bytes]":
            return asyncio.ensure_future(anyio.to_thread.run_sync(os.pread, fd, min(CHUNK_SIZE, remaining), position))

        pending: Optional[asyncio.Future[bytes]] = read_next() if remaining > 0 else None
        try:
            while pending is not None:
                data = await pending
                pending = None
                if not data:
                    break  # file got shorter
                position += len(data)
                remaining -= len(data)
                if remaining > 0:
                    pending = read_next()
                await send({ "type": "http.response.body", "body": data, "more_body": True })
            await send({ "type": "http.response.body", "body": b"", "more_body": False })
        finally:
            if pending is not None and not pending.done():
                # A read is still running in its thread: close the file once it's done
                def close_after_read(future: asyncio.Future) -> None:
                    if not future.cancelled():
                        future.exception()  # retrieve it, no "exception was never retrieved" warning
                    file.close()
                pending.add_done_callback(close_after_read)
            else:
                file.close()

@router.get("/{movie_id}/stream")
async def stream_movie(request: Request, movie_id: int):
    movie = await _get_movie_row(movie_id)
    file_path = path.join(await GET_MEDIA_ROOT_FOLDER(), movie["file_location"])
    if not path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    file_size = path.getsize(file_path)
    media_type = VIDEO_MEDIA_TYPES.get(Path(file_path).suffix.lower(), "video/mp4")
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
        headers.update({ "Content-Range": f"bytes {start}-{end}/{file_size}", "Content-Length": str(end - start + 1) })
        return FileRangeResponse(file_path, start, end, status_code=206, headers=headers, media_type=media_type)

    # No (usable) Range header: the whole file
    headers.update({ "Content-Length": str(file_size) })
    return FileRangeResponse(file_path, 0, file_size - 1, status_code=200, headers=headers, media_type=media_type)


@router.get("/{movie_id}/people", response_model=List[MoviePerson])
async def get_people(movie_id: int):
    """Billing order first (people without one, e.g. from folder configs, after that by name)."""
    return await fetch_all("""
SELECT p.*, mp.character, mp.sort_order
FROM people p
JOIN movies__people mp ON mp.person_id = p.id
WHERE mp.movie_id = ?
ORDER BY mp.sort_order IS NULL, mp.sort_order, p.name COLLATE NOCASE
""", (movie_id,))

@router.get("/{movie_id}/collections", response_model=List[Collection])
async def get_collections(movie_id: int):
    return await fetch_all("""
SELECT c.*
FROM collections c
JOIN movies__collections mc ON mc.collection_id = c.id
WHERE mc.movie_id = ?
ORDER BY c.title COLLATE NOCASE
""", (movie_id,))

@router.get("/{movie_id}/extras", response_model=List[Movie])
async def get_extras(movie_id: int):
    return await fetch_all("SELECT * FROM movies WHERE is_extra_of_movie_id = ? ORDER BY title ASC", (movie_id,))

async def _movie_with_library(movie_id: int) -> tuple[Movie, Library, Path]:
    movie = Movie(**await _get_movie_row(movie_id))
    library_row = await fetch_one("SELECT * FROM libraries WHERE id = ?", (movie.library_id,))
    if library_row is None:
        raise HTTPException(status_code=404, detail="Library not found")

    absolute_path = Path(await GET_MEDIA_ROOT_FOLDER()) / movie.file_location
    return movie, Library(**library_row), absolute_path

@router.get("/{movie_id}/search", response_model=List[SearchResult])
async def search_metadata(movie_id: int, query: Optional[str] = None):
    """All hits of the closest scraper for this movie, best first. `query` replaces the title
    the scraper would take from the file name. Nothing is saved, see POST /{movie_id}/match."""
    movie, library, absolute_path = await _movie_with_library(movie_id)

    config = await find_scraper_config(absolute_path)
    if config is None:
        raise HTTPException(status_code=409, detail="No scraper is configured for this folder (useScraper in a __pinea.json).")

    try:
        # Scrapers are blocking (requests), keep them off the event loop
        scraper = await asyncio.to_thread(load_scraper, config.currentPath)
        return await asyncio.to_thread(run_search, scraper, absolute_path, library, query.strip() if query and query.strip() else None)
    except Exception as error:
        log.exception(f"Scraper search failed for movie {movie_id}")
        raise HTTPException(status_code=502, detail=f"Scraper error: {error}")

@router.post("/{movie_id}/match")
async def apply_match(request: Request, movie_id: int, search_result: SearchResult):
    """Fetch the metadata of the chosen search hit and apply it (queued as a scan job).
    The choice itself is not stored: a later full refresh searches again."""
    await _movie_with_library(movie_id)
    request.app.state.scanner.submit(ScanJob(movie_id=movie_id, search_result=search_result))
    return {"status": "scan queued"}

