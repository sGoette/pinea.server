from pydantic import BaseModel
from typing import Optional
from enum import StrEnum

class LIBRARY_TYPE(StrEnum):
    MOVIES = 'MOVIES'
    SERIES = 'SERIES'
    VIDEOS = 'VIDEOS'

class Library(BaseModel):
    id: int
    name: Optional[str]
    media_folder: str
    type: LIBRARY_TYPE

class LibraryCreate(BaseModel):
    name: str
    media_folder: str
    type: LIBRARY_TYPE