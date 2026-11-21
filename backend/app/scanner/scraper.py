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
from app.scanner.metadata_functions.folder_collection_config import find_closest_config, SCRAPER_FILE_NAME

async def find_scraper_config(absolute_path: Path) -> Optional[FolderCollectionConfig_Path]:
    """The closest __pinea.json decides: when it doesn't set useScraper, the file has no scraper
    (a scraper further up doesn't count)."""
    config = await find_closest_config(absolute_path)
    return config if config and config.data.useScraper else None

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
