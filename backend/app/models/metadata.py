from datetime import datetime, timezone
from pydantic import BaseModel, field_validator
from typing import Optional

from app.models.collection import CollectionData
from app.models.person import ROLE

def release_date_to_unix(value: Optional[int]) -> Optional[int]:
    """Release dates are unix seconds. Scrapers may give a plain year (e.g. 2004): that becomes January 1st."""
    if value is not None and 0 < value < 10000:
        return int(datetime(value, 1, 1, tzinfo=timezone.utc).timestamp())
    return value

class PersonMetadata(BaseModel):
    name: str
    poster_url: Optional[str] = None
    role: Optional[ROLE] = None             # used when the person is created, default ACTOR
    character: Optional[str] = None         # "James Bond"
    sort_order: Optional[int] = None        # billing order, 0 = first. None = after everyone with an order

class SerieData(BaseModel):
    title: str
    poster_url: Optional[str] = None
    
class Metadata(BaseModel):
    movie_title: Optional[str] = None
    collections: list[CollectionData] = []
    poster_url: Optional[str] = None
    still_url: Optional[str] = None         # 16:9 image of the title itself, e.g. an episode still
    people: list[PersonMetadata] = []
    serie: Optional[SerieData] = None
    season: Optional[str] = None
    episode: Optional[int] = None
    release_date: Optional[int] = None      # unix seconds

    _release_date_to_unix = field_validator("release_date")(release_date_to_unix)

class SearchResult(BaseModel):
    """One hit of a scraper's search(). `id` is opaque: only the scraper that returned it
    understands it. The other fields are for showing the hits in the web UI."""
    id: str
    name: str
    original_name: Optional[str] = None
    release_date: Optional[int] = None      # unix seconds
    poster_url: Optional[str] = None
    overview: Optional[str] = None

    _release_date_to_unix = field_validator("release_date")(release_date_to_unix)
