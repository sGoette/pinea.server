import aiosqlite
from pathlib import Path
from typing import Optional

import logging
log = logging.getLogger(__name__)

from app.config import DB_PATH, POSTER_DIR
from app.models.movie import Movie
from app.models.metadata import Metadata, SearchResult
from app.scanner.media import generate_poster
from app.models.collection import CollectionData
from app.models.library import Library, LIBRARY_TYPE
from app.models.serie import Serie
from app.scanner.text import smart_title
from app.scanner.scraper import load_scraper, run_search

from app.scanner.metadata_functions.folder_collection_config import find_closest_config
from app.scanner.metadata_functions.get_poster_from_folder import find_image_in_folder
from app.scanner.metadata_functions.add_collection_to_movie import add_collection_to_movie
from app.scanner.metadata_functions.set_subfolder_as_person import set_subfolder_as_person
from app.scanner.metadata_functions.get_poster_from_url import get_poster_from_url
from app.scanner.metadata_functions.add_person_to_movie import add_person_to_movie
from app.scanner.metadata_functions.get_extra_type import get_extra_type
from app.scanner.metadata_functions.get_main_movie_of_extra import get_main_movie_of_extra

from app.api.websocket_manager import ws_manager
from app.models.notification import Notification, NOTIFICATION_TYPE

# folder_is_collection: the collection's poster is an image with this name next to the __pinea.json
FOLDER_COLLECTION_POSTER_NAMES = ["collection"]

async def fetch_movie_metadata(movie: Movie, absolute_path: Path, library: Library, update_poster: bool = False, search_result: Optional[SearchResult] = None):
    """search_result: a scraper hit chosen by the user (manual match). Without it the scraper's best hit is used."""
    force_update_poster = update_poster

    extra_type, main_movie_file_name = get_extra_type(absolute_path)
    if extra_type and main_movie_file_name:
        main_movie = await get_main_movie_of_extra(absolute_file_path=absolute_path, main_movie_file_name=main_movie_file_name, extra_movie=movie, library_id=movie.library_id)
        if main_movie:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE movies SET is_extra_of_movie_id = ?, extra_type = ? WHERE id = ?", (main_movie.id, extra_type, movie.id))
                await db.commit()
            
    # Only the closest __pinea.json decides how this file is scanned
    config = await find_closest_config(absolute_path)

    # 1. Scraper (network). Not for extras: they would get the main movie's metadata.
    metadata: Optional[Metadata] = None
    scraper_config = config if config and config.data.useScraper and not extra_type else None
    if scraper_config:
        try:
            scraper = load_scraper(scraper_config.currentPath)
            chosen = search_result
            if chosen is None:
                search_results = run_search(scraper, absolute_path=absolute_path, library=library)
                chosen = search_results[0] if search_results else None
            if chosen is not None:
                metadata = scraper.fetch_metadata(search_result=chosen, potential_collections=scraper_config.data.potential_collections)
            else:
                log.info(f"[Scanner] Scraper found nothing for {absolute_path}")
        except Exception:
            log.exception(f"[Scanner] Scraper failed for {absolute_path}")

    # 2. Forget the old people and collections, they are added again below. Not when the scraper
    #    failed (e.g. no network): then the old scraper data is better than none.
    if scraper_config is None or metadata is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM movies__people WHERE movie_id = ?", (movie.id,))
            await db.execute("DELETE FROM movies__collections WHERE movie_id = ?", (movie.id,))
            await db.commit()

    # 3. Folder config
    if config:
        if config.data.folder_is_collection:
            poster = find_image_in_folder(folder_path=config.currentPath, candidate_names=FOLDER_COLLECTION_POSTER_NAMES)
            collection_data = CollectionData(title=smart_title(config.currentPath.name), poster_file_name=str(poster) if poster else None)
            await add_collection_to_movie(collection_data=collection_data, movie=movie)

        if config.data.subfoldersAreCollections and config.childPath:
            collection_data = CollectionData(title=smart_title(config.childPath.name), poster_folder=config.childPath)
            await add_collection_to_movie(collection_data=collection_data, movie=movie)

        if config.data.subfoldersArePeople and config.childPath:
            current_folder_title = smart_title(config.childPath.name)
            await set_subfolder_as_person(person_name=current_folder_title, path=config.childPath, library_id=movie.library_id, movie_id=movie.id, poster_candidate_names=[current_folder_title.lower()])

        for additional_person in config.data.folderPeople:
            await set_subfolder_as_person(person_name=additional_person, path=config.currentPath, library_id=movie.library_id, movie_id=movie.id, poster_candidate_names=[additional_person.lower()])

    # 4. Scraper metadata
    if metadata:
        try:
            await apply_metadata(movie=movie, metadata=metadata, library=library)
            if metadata.poster_url and movie.poster_file_name:
                force_update_poster = False
        except Exception:
            log.exception(f"[Scanner] Could not save the metadata of {absolute_path}")

    # Grab a frame only if there is no usable poster: none yet, or the file is gone from the poster folder
    poster_missing = movie.poster_file_name is None or not (POSTER_DIR / movie.poster_file_name).is_file()
    if ( poster_missing or force_update_poster ) and movie.length_in_seconds:
        try:
            poster_from_stil = await generate_poster(path=absolute_path, length_in_seconds=movie.length_in_seconds)
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE movies SET poster_file_name = ?, metadata_last_updated = unixepoch() WHERE id = ?", (poster_from_stil, movie.id))
                await db.commit()
        except Exception:
            log.exception(f"[Scanner] Failed to generate poster for {absolute_path}")

    await ws_manager.broadcast(Notification(type=NOTIFICATION_TYPE.MOVIES_UPDATED))

async def apply_metadata(movie: Movie, metadata: Metadata, library: Library):
    poster_file_name = movie.poster_file_name
    if metadata.poster_url:
        poster_file_name = get_poster_from_url(url=metadata.poster_url) or movie.poster_file_name

    title = metadata.movie_title or movie.title
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE movies SET title = ?, poster_file_name = ?, metadata_last_updated = unixepoch(), release_date = ? WHERE id = ?", (title, poster_file_name, metadata.release_date, movie.id))
        await db.commit()

    movie.title = title
    movie.poster_file_name = poster_file_name

    for person_metadata in metadata.people:
        await add_person_to_movie(person_metadata=person_metadata, movie=movie)

    for collection in metadata.collections:
        await add_collection_to_movie(collection_data=collection, movie=movie)

    if library.type == LIBRARY_TYPE.SERIES and metadata.serie is not None:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM series WHERE title = ? AND library_id = ?", (metadata.serie.title, library.id)) as cursor:
                serie_row = await cursor.fetchone()

            if serie_row:
                serie_id = Serie(**serie_row).id
            else:
                serie_poster_file_name = get_poster_from_url(url=metadata.serie.poster_url) if metadata.serie.poster_url else movie.poster_file_name
                serie_cursor = await db.execute("INSERT INTO series (title, poster_file_name, library_id) VALUES (?, ?, ?)", (metadata.serie.title, serie_poster_file_name, library.id))
                await db.commit()
                serie_id = serie_cursor.lastrowid

            if serie_id is not None:
                await db.execute("UPDATE movies SET is_episode_of_serie_id = ?, season = ?, episode = ? WHERE id = ?", (serie_id, metadata.season, metadata.episode, movie.id))
                await db.commit()
