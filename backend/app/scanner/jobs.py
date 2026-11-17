from dataclasses import dataclass
from typing import Optional

from app.models.metadata import SearchResult

@dataclass
class ScanJob:
    library_id: Optional[int] = None
    ignore_existing_metadata: bool = False
    movie_id: Optional[int] = None
    force_cleanup: bool = False # bypass the "too many movies missing at once" safety check
    reset_metadata: bool = False # with library_id: forget all metadata of the library first, then scan (rebuild)
    search_result: Optional[SearchResult] = None # with movie_id: use this scraper hit instead of searching (manual match)
