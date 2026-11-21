import json
import os
from pathlib import Path
from typing import Optional

from app.config import GET_MEDIA_ROOT_FOLDER
from app.models.folder_collection_config import FolderCollectionConfig, FolderCollectionConfig_Path, LibraryFolderConfig

CONFIG_FILE_NAME = "__pinea.json"
SCRAPER_FILE_NAME = "__pinea.py"

def load_config(folder: Path) -> FolderCollectionConfig:
    with (folder / CONFIG_FILE_NAME).open("r", encoding="utf-8") as f:
        return FolderCollectionConfig(**json.load(f))

def closest_config_folder(start_path: Path, media_root: Path) -> Optional[tuple[Path, Optional[Path]]]:
    """(folder of the closest __pinea.json, its subfolder on the way to start_path). Never looks above media_root."""
    current = start_path.parent if start_path.is_file() else start_path
    child: Optional[Path] = None
    while True:
        if (current / CONFIG_FILE_NAME).is_file():
            return current, child
        if current == media_root or current.parent == current:
            return None
        child = current
        current = current.parent

async def find_closest_config(start_path: Path) -> Optional[FolderCollectionConfig_Path]:
    """The closest __pinea.json above a file. Only this one decides how the file is scanned:
    configs further up don't add anything to it."""
    media_root = Path(await GET_MEDIA_ROOT_FOLDER()).resolve()
    found = closest_config_folder(start_path.resolve(), media_root)
    if found is None:
        return None
    folder, child = found
    return FolderCollectionConfig_Path(data=load_config(folder), currentPath=folder, childPath=child)

def list_library_configs(media_root: Path, library_path: Path) -> list[LibraryFolderConfig]:
    """Every __pinea.json that decides about files of the library: the ones inside the library folder,
    plus the closest one above it when the library folder has none of its own. Blocking (walks the folder)."""
    folders: list[tuple[Path, bool]] = []
    if not (library_path / CONFIG_FILE_NAME).is_file() and library_path != media_root:
        above = closest_config_folder(library_path.parent, media_root)
        if above is not None:
            folders.append((above[0], True))

    for dirpath, dirnames, filenames in os.walk(library_path):
        dirnames.sort()
        if CONFIG_FILE_NAME in filenames:
            folders.append((Path(dirpath), False))

    configs: list[LibraryFolderConfig] = []
    for folder, above_library in folders:
        config: Optional[FolderCollectionConfig] = None
        error: Optional[str] = None
        try:
            config = load_config(folder)
        except Exception as e:
            error = str(e)
        configs.append(LibraryFolderConfig(
            folder=folder.relative_to(media_root).as_posix() if folder != media_root else "",
            above_library=above_library,
            config=config,
            error=error,
            has_scraper_file=(folder / SCRAPER_FILE_NAME).is_file(),
        ))
    return configs
