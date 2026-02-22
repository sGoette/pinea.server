from pydantic import BaseModel
from typing import Optional

from app.models.collection import CollectionData

class PersonMetadata(BaseModel):
    name: str
    poster_url: Optional[str] = None

class SerieData(BaseModel):
    title: str
    poster_url: Optional[str] = None
    
class Metadata(BaseModel):
    movie_title: Optional[str] = None
    genres: list[str] = []
    tags: list[str] = []
    collections: list[CollectionData] = []
    poster_url: Optional[str] = None
    people: list[PersonMetadata] = []
    serie: Optional[SerieData] = None
    season: Optional[str] = None
    episode: Optional[int] = None
    release_date: Optional[int] = None

class SearchResult(BaseModel):
    id: str
    name: str
