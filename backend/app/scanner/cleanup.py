import os
import aiosqlite
from pathlib import Path
from app.config import DB_PATH, GET_MEDIA_ROOT_FOLDER, POSTER_DIR
from app.models.collection import Collection
from app.models.library import Library

from app.api.websocket_manager import ws_manager
from app.models.notification import Notification, NOTIFICATION_TYPE

import logging
log = logging.getLogger(__name__)

async def cleanup_orphaned_posters():
    poster_file_names: list[str] = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT poster_file_name FROM movies WHERE poster_file_name IS NOT NULL") as movie_poster_cursor:
            movie_poster_rows = await movie_poster_cursor.fetchall()
            poster_file_names.extend([str(row["poster_file_name"]) for row in movie_poster_rows if row["poster_file_name"]])

        async with db.execute("SELECT poster_file_name FROM collections WHERE poster_file_name IS NOT NULL") as collection_poster_cursor: 
            collection_poster_rows = await collection_poster_cursor.fetchall()
            poster_file_names.extend([str(row["poster_file_name"]) for row in collection_poster_rows if row["poster_file_name"]])

        async with db.execute("SELECT poster_file_name FROM people WHERE poster_file_name IS NOT NULL") as people_poster_cursor:
            people_poster_rows = await people_poster_cursor.fetchall()
            poster_file_names.extend([str(row["poster_file_name"]) for row in people_poster_rows if row["poster_file_name"]])

        async with db.execute("SELECT poster_file_name FROM series WHERE poster_file_name IS NOT NULL") as series_poster_cursor:
            series_poster_rows = await series_poster_cursor.fetchall()
            poster_file_names.extend([str(row["poster_file_name"]) for row in series_poster_rows if row["poster_file_name"]])

     
    referenced = set()

    for poster_file_name in poster_file_names:
        absolute_poster_path = Path(POSTER_DIR, poster_file_name).resolve()
        if absolute_poster_path.is_relative_to(POSTER_DIR):
            referenced.add(absolute_poster_path)

    removed = 0

    for entry in POSTER_DIR.iterdir():
        if entry.is_file() and entry not in referenced:
            try:
                entry.unlink()
                removed += 1
            except Exception:
                log.exception(f"[Scanner] Could not delete orphan poster {entry}:")

    if removed:
        log.info(f"[Scanner] Removed {removed} orphan posters")

# Safety net: if more than this share of a library's movies seem to be gone at once, something is
# most likely wrong with the mount or the paths (e.g. after a server migration) and not with the media.
ORPHAN_SAFETY_MAX_RATIO = 0.5
ORPHAN_SAFETY_MIN_MOVIES = 20

def _folder_has_entries(path: Path) -> bool:
    """True if path is a readable directory with at least one entry. An unmounted share usually
    shows up as a missing or empty mount point."""
    try:
        with os.scandir(path) as entries:
            return any(True for _ in entries)
    except OSError:
        return False

async def cleanup_orphaned_movies(force: bool = False):
    MEDIA_ROOT_FOLDER = Path(await GET_MEDIA_ROOT_FOLDER())

    if not _folder_has_entries(MEDIA_ROOT_FOLDER):
        log.warning(f"[Cleanup] Media root {MEDIA_ROOT_FOLDER} is missing or empty (not mounted?). Skipping orphaned movie cleanup.")
        return

    deleted_any = False
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM libraries") as library_cursor:
            libraries = [Library(**dict(row)) for row in await library_cursor.fetchall()]

        for library in libraries:
            library_folder = MEDIA_ROOT_FOLDER / library.media_folder
            if not _folder_has_entries(library_folder):
                log.warning(f"[Cleanup] Folder of library {library.id} ({library_folder}) is missing or empty (not mounted?). Skipping orphaned movie cleanup for this library.")
                continue

            async with db.execute("SELECT id, file_location FROM movies WHERE library_id = ?", (library.id,)) as movie_cursor:
                movie_rows = await movie_cursor.fetchall()

            #We formated the file_location to utf-8, might be a problem here
            orphan_ids = [row["id"] for row in movie_rows if not (MEDIA_ROOT_FOLDER / row["file_location"]).is_file()]
            if not orphan_ids:
                continue

            if not force and len(movie_rows) >= ORPHAN_SAFETY_MIN_MOVIES and len(orphan_ids) / len(movie_rows) > ORPHAN_SAFETY_MAX_RATIO:
                log.warning(
                    f"[Cleanup] {len(orphan_ids)} of {len(movie_rows)} movies of library {library.id} are missing on disk. "
                    "Refusing to delete that many at once. Check MEDIA_ROOT_FOLDER and the mounts, or start a scan with force_cleanup=true."
                )
                continue

            #TODO: add forein keys, so other objects gets deleted as well.
            await db.executemany("DELETE FROM movies WHERE id = ?", [(movie_id,) for movie_id in orphan_ids])
            await db.commit()
            deleted_any = True
            log.info(f"[Cleanup] Removed {len(orphan_ids)} orphaned movies from library {library.id}")

    if deleted_any:
        await ws_manager.broadcast(Notification(type=NOTIFICATION_TYPE.MOVIES_UPDATED))

async def cleanup_orphaned_collections ():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM collections") as collection_cursor:
            collection_rows = await collection_cursor.fetchall()

            collections = [Collection(**dict(row)) for row in collection_rows]

            for collection in collections:
                async with db.execute("SELECT * FROM movies__collections WHERE collection_id = ?", (collection.id,)) as movie__collection_cursor:
                    movie__collection_row = await movie__collection_cursor.fetchone()

                if movie__collection_row is None:
                    await db.execute("DELETE FROM collections WHERE id = ?", (collection.id,))
                    await db.commit()

        await ws_manager.broadcast(Notification(type=NOTIFICATION_TYPE.COLLECTIONS_UPDATED))