from fastapi import APIRouter, HTTPException

from app.db.database import fetch_one
from app.models.person import Person

router = APIRouter(prefix="/api/person")

@router.get("/{person_id}", response_model=Person)
async def get_person(person_id: int):
    person = await fetch_one("SELECT * FROM people WHERE id = ?", (person_id,))
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person
