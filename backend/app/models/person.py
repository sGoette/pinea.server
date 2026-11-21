from pydantic import BaseModel
from enum import StrEnum
from typing import Optional

class ROLE(StrEnum):
    ACTOR = 'ACTOR'
    DIRECTOR = 'DIRECTOR'


class Person(BaseModel):
    id: int
    name: str
    poster_file_name: Optional[str]
    role: ROLE

class MoviePerson(Person):
    """A person as part of one movie (GET /api/movie/{id}/people)."""
    character: Optional[str] = None
    sort_order: Optional[int] = None

class PersonWithStats(Person):
    """A person of a library (GET /api/people/{library_id}) with the number of their titles."""
    movie_count: int
