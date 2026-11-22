from pydantic import BaseModel
from typing import Optional

from app.models.collection import CollectionData
from app.models.person import ROLE

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
    genres: list[str] = []
    tags: list[str] = []
    collections: list[CollectionData] = []
    poster_url: Optional[str] = None
    still_url: Optional[str] = None         # 16:9 image of the title itself, e.g. an episode still
    people: list[PersonMetadata] = []
    serie: Optional[SerieData] = None
    season: Optional[str] = None
    episode: Optional[int] = None
    release_date: Optional[int] = None      # unix seconds

class SearchResult(BaseModel):
    """One hit of a scraper's search(). `id` is opaque: only the scraper that returned it
    understands it. The other fields are for showing the hits in the web UI."""
    id: str
    name: str
    original_name: Optional[str] = None
    release_date: Optional[int] = None      # unix seconds
    poster_url: Optional[str] = None
    overview: Optional[str] = None
