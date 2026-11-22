import os
from pathlib import Path
from typing import Optional

from app.config import GET_MEDIA_ROOT_FOLDER, VIDEO_EXTENSIONS
from app.models.library import Library
from app.scanner.movie import process_movie
from app.scanner.metadata import fetch_movie_metadata
from app.scanner.metadata_functions.folder_collection_config import CONFIG_FILE_NAME

from app.api.websocket_manager import ws_manager
from app.models.notification import Notification, NOTIFICATION_TYPE

import logging
log = logging.getLogger(__name__)

def config_scan_root(library_path: Path, config_path: Path) -> Optional[Path]:
    """Where to start walking for the files of one __pinea.json, or None when none of them are in the library."""
    if library_path.is_relative_to(config_path):
        # Config above (or at) the library folder: it reaches the library only if no config sits in between
        folder = library_path.parent
        while folder != config_path and folder.is_relative_to(config_path):
            if (folder / CONFIG_FILE_NAME).is_file():
                return None
            folder = folder.parent
        return library_path
    if config_path.is_relative_to(library_path):
        return config_path
    return None

async def scan_library(library: Library, ignore_existing_metadata: bool, config_folder: Optional[str] = None):
    """config_folder (relative to MEDIA_ROOT_FOLDER): only the files whose closest __pinea.json is in that folder."""
    MEDIA_ROOT_FOLDER = Path(await GET_MEDIA_ROOT_FOLDER()).resolve()
    absolute_library_path = (MEDIA_ROOT_FOLDER / library.media_folder).resolve()

    walk_root: Optional[Path] = absolute_library_path
    config_path: Optional[Path] = None
    if config_folder is not None:
        config_path = (MEDIA_ROOT_FOLDER / config_folder).resolve()
        walk_root = config_scan_root(absolute_library_path, config_path) if (config_path / CONFIG_FILE_NAME).is_file() else None
        if walk_root is None:
            log.warning(f"[Scanner] {config_path / CONFIG_FILE_NAME} doesn't decide about any file of library {library.id}")
            return
        log.info(f"[Scanner] Scanning the files of {config_path / CONFIG_FILE_NAME} in library {library.id}")
    else:
        log.info(f"[Scanner] Scanning library {library.id}: {absolute_library_path}")

    for dirpath, dirnames, filenames in os.walk(walk_root):
        if config_path is not None and Path(dirpath).resolve() != config_path and CONFIG_FILE_NAME in filenames:
            dirnames[:] = [] # an own __pinea.json: this folder and everything below belong to that one
            continue
        for filename in filenames:
            if not os.path.splitext(filename)[1].lower() in VIDEO_EXTENSIONS:
                continue
            
            absolute_file_path = Path(dirpath).resolve() / filename
            movie = await process_movie(absolute_file_path=absolute_file_path, library_id=library.id)

            if movie and (movie.metadata_last_updated is None or ignore_existing_metadata):
                await fetch_movie_metadata(movie=movie, absolute_path=absolute_file_path, library=library)
    
    await ws_manager.broadcast(Notification(type=NOTIFICATION_TYPE.LIBRARIES_UPDATED))