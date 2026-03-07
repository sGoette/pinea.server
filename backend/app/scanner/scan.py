import aiosqlite
from pathlib import Path

from app.config import DB_PATH, GET_MEDIA_ROOT_FOLDER
from app.scanner.jobs import ScanJob
from app.models.library import Library
from app.scanner.library import scan_library
from app.scanner.metadata import fetch_movie_metadata
from app.models.movie import Movie

async def scan_libraries(job: ScanJob):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")

        if job.movie_id:
            movie_cursor = await db.execute("SELECT * FROM movies WHERE id = ?", (job.movie_id,))
            movie_row = await movie_cursor.fetchone()

            if movie_row:
                movie = Movie(**movie_row)
                library_cursor = await db.execute("SELECT * FROM libraries WHERE id = ?", (movie.library_id,))
                library_row = await library_cursor.fetchone()

                if library_row:
                    library = Library(**library_row)
                    absolute_movie_path = Path(await GET_MEDIA_ROOT_FOLDER()) / movie.file_location
                    await fetch_movie_metadata(movie=movie, absolute_path=absolute_movie_path, library=library, update_poster=True)

            return

        if job.library_id:
            cursor = await db.execute("SELECT * FROM libraries WHERE id = ?", (job.library_id,))
        else: 
            cursor = await db.execute("SELECT * FROM libraries")

        rows = await cursor.fetchall()
        await cursor.close()

        libraries = [Library(**dict(row)) for row in rows]

        for library in libraries:
            await scan_library(library=library, ignore_existing_metadata=job.ignore_existing_metadata)