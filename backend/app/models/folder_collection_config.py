from pydantic import BaseModel
from pathlib import Path
from typing import Optional

class FolderCollectionConfig(BaseModel):
    """Content of a __pinea.json. The closest one above a file decides how that file is scanned.
    Missing keys fall back to the defaults, so a config only needs the keys it changes."""
    subfoldersAreCollections: bool = False
    subfoldersArePeople: bool = False
    folderPeople: list[str] = []
    useScraper: bool = False
    potential_collections: list[str] = []
    folder_is_collection: bool = False  # the config's own folder is a collection (poster: image "collection" next to it)


class FolderCollectionConfig_Path(BaseModel):
    data: FolderCollectionConfig
    currentPath: Path               # folder of the __pinea.json
    childPath: Optional[Path]       # subfolder of currentPath on the way to the file (None = file is in currentPath)


class LibraryFolderConfig(BaseModel):
    """A __pinea.json that decides how files of a library are scanned (GET /api/library/{id}/configs)."""
    folder: str                     # relative to MEDIA_ROOT_FOLDER ("" = the media root itself)
    above_library: bool             # the config sits above the library folder (it applies to the library's root)
    config: Optional[FolderCollectionConfig] = None   # None when the file can't be read (see error)
    error: Optional[str] = None
    has_scraper_file: bool          # __pinea.py exists next to it (needed when useScraper is true)
