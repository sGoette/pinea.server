import aiosqlite
from pathlib import Path
from typing import Optional

from app.config import DB_PATH, COLLECTION_POSTER_CANDIDATE_NAMES
from app.models.collection import CollectionData
from app.models.movie import Movie
from app.scanner.metadata_functions.get_poster_from_folder import get_poster_from_folder, get_poster_from_file_name
from app.scanner.metadata_functions.get_poster_from_url import get_poster_from_url

from app.api.websocket_manager import ws_manager
from app.models.notification import Notification, NOTIFICATION_TYPE

def _collection_poster(collection_data: CollectionData) -> Optional[str]:
    if collection_data.poster_url:
        return get_poster_from_url(collection_data.poster_url)
    if collection_data.poster_file_name:
        return get_poster_from_file_name(Path(collection_data.poster_file_name))
    if collection_data.poster_folder:
        return get_poster_from_folder(folder_path=collection_data.poster_folder, candidate_names=COLLECTION_POSTER_CANDIDATE_NAMES)
    return None

async def add_collection_to_movie(collection_data: CollectionData, movie: Movie):
    """Links the movie to the collection with this title (any case), creating it if needed. A collection
    without a poster gets one from collection_data (a poster set in the web UI is never replaced)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, poster_file_name FROM collections WHERE title = ? COLLATE NOCASE AND library_id = ?", (collection_data.title, movie.library_id)) as cursor:
            row = await cursor.fetchone()

        if row is None:
            cursor = await db.execute("INSERT INTO collections (title, library_id) VALUES (?, ?)", (collection_data.title, movie.library_id))
            collection_id, poster_file_name = cursor.lastrowid, None
        else:
            collection_id, poster_file_name = row

        await db.execute("INSERT OR IGNORE INTO movies__collections (movie_id, collection_id) VALUES (?, ?)", (movie.id, collection_id))

        if poster_file_name is None:
            poster_file_name = _collection_poster(collection_data)
            if poster_file_name:
                await db.execute("UPDATE collections SET poster_file_name = ? WHERE id = ?", (poster_file_name, collection_id))
        await db.commit()

    await ws_manager.broadcast(Notification(type=NOTIFICATION_TYPE.MOVIES_UPDATED))
    await ws_manager.broadcast(Notification(type=NOTIFICATION_TYPE.COLLECTIONS_UPDATED))
