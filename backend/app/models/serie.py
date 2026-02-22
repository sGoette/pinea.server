from pydantic import BaseModel
from typing import Optional

class Serie(BaseModel):
    id: int
    title: str
    poster_file_name: Optional[str] = None
    library_id: int

class SerieDTO(Serie):
    seasons_count: int