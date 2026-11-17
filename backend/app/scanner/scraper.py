"""Loading and calling the scrapers (`__pinea.py`) that live in the media folders.

Contract of a scraper module:
    search(absolute_path: Path, library: Library, query: str | None = None) -> list[SearchResult]
        Best match first. `query` is set when a user searches manually in the web UI.
        Older scrapers without the `query` parameter still work (manual queries are then ignored).
    fetch_metadata(search_result: SearchResult, potential_collections: list[str]) -> Metadata | None

SearchResult / Metadata may be the models from app.models.metadata or look-alikes with the same fields.
"""
import importlib.util
import inspect
from pathlib import Path
from types import ModuleType
from typing import Optional

from app.models.library import Library
from app.models.metadata import SearchResult
from app.models.folder_collection_config import FolderCollectionConfig_Path
from app.scanner.metadata_functions.folder_collection_config import find_folder_collection_config

SCRAPER_FILE_NAME = "__pinea.py"

def closest_scraper_config(configs: list[FolderCollectionConfig_Path]) -> Optional[FolderCollectionConfig_Path]:
    """configs are ordered from the file's folder upwards, so the first one with useScraper is the closest."""
    return next((config for config in configs if config.data.useScraper), None)

async def find_scraper_config(absolute_path: Path) -> Optional[FolderCollectionConfig_Path]:
    return closest_scraper_config(await find_folder_collection_config(absolute_path))

def load_scraper(folder: Path) -> ModuleType:
    scraper_file = folder / SCRAPER_FILE_NAME
    spec = importlib.util.spec_from_file_location("pinea_scraper", scraper_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Can not load scraper {scraper_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run_search(scraper: ModuleType, absolute_path: Path, library: Library, query: Optional[str] = None) -> list[SearchResult]:
    """Blocking (scrapers use requests). Results are converted to app SearchResults."""
    kwargs: dict = { "absolute_path": absolute_path, "library": library }
    if query and "query" in inspect.signature(scraper.search).parameters:
        kwargs["query"] = query
    results = scraper.search(**kwargs) or []
    return [to_search_result(result) for result in results]

def to_search_result(result) -> SearchResult:
    if isinstance(result, SearchResult):
        return result
    if isinstance(result, dict):
        return SearchResult.model_validate(result)
    return SearchResult.model_validate(result, from_attributes=True)
