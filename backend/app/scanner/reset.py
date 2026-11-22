import aiosqlite
from pathlib import Path

from app.config import DB_PATH, GET_MEDIA_ROOT_FOLDER
from app.models.library import Library
from app.scanner.cleanup import _folder_has_entries
from app.scanner.text import smart_title

from app.api.websocket_manager import ws_manager
from app.models.notification import Notification, NOTIFICATION_TYPE

import logging
log = logging.getLogger(__name__)

async def reset_library_metadata(library: Library) -> bool:
    """Forget everything scrapers and folder configs produced for this library, so the next scan
    starts like on a new library. Movie rows and their file data (duration, resolution, added date)
    stay. Returns False (and changes nothing) if the library folder is missing or empty: an
    unmounted share must not wipe the metadata."""
    library_folder = Path(await GET_MEDIA_ROOT_FOLDER()) / library.media_folder
    if not _folder_has_entries(library_folder):
        log.warning(f"[Reset] Folder of library {library.id} ({library_folder}) is missing or empty (not mounted?). Not resetting its metadata.")
        return False

    async with aiosqlite.connect(DB_PATH) as db:
        movies_of_library = "SELECT id FROM movies WHERE library_id = ?"
        await db.execute(f"DELETE FROM movies__people WHERE movie_id IN ({movies_of_library})", (library.id,))
        await db.execute(f"DELETE FROM movies__collections WHERE movie_id IN ({movies_of_library})", (library.id,))

        async with db.execute("SELECT id, file_location FROM movies WHERE library_id = ?", (library.id,)) as cursor:
            rows = await cursor.fetchall()
        # Same state as a newly found file (see scanner/movie.py add_movie_to_db)
        await db.executemany("""
UPDATE movies SET
    title = ?, poster_file_name = NULL, still_file_name = NULL, metadata_last_updated = NULL, release_date = NULL,
    is_extra_of_movie_id = NULL, extra_type = NULL,
    is_episode_of_serie_id = NULL, episode = NULL, season = NULL, is_extra_of_serie_id = NULL
WHERE id = ?
""", [(smart_title(Path(file_location).stem), movie_id) for movie_id, file_location in rows])

        await db.execute("DELETE FROM people WHERE library_id = ?", (library.id,))
        await db.execute("DELETE FROM collections WHERE library_id = ?", (library.id,))
        await db.execute("DELETE FROM series WHERE library_id = ?", (library.id,))
        await db.commit()

    log.info(f"[Reset] Metadata of library {library.id} reset ({len(rows)} movies)")
    await ws_manager.broadcast(Notification(type=NOTIFICATION_TYPE.MOVIES_UPDATED))
    await ws_manager.broadcast(Notification(type=NOTIFICATION_TYPE.COLLECTIONS_UPDATED))
    return True
