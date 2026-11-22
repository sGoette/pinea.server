import aiosqlite
from pathlib import Path

from app.config import DB_PATH
from app.models.person import ROLE
from app.scanner.metadata_functions.get_poster_from_folder import get_poster_from_folder

async def set_subfolder_as_person(person_name: str, path: Path, library_id: int, movie_id: int, poster_candidate_names: list[str]):
    """Links a person from a folder config to the movie. Creates the person if needed; the photo is an
    image in `path` named like the person (only when the person has none yet)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, poster_file_name FROM people WHERE name = ? COLLATE NOCASE AND library_id = ?", (person_name, library_id)) as cursor:
            row = await cursor.fetchone()

        if row is None:
            poster_file_name = get_poster_from_folder(folder_path=path, candidate_names=poster_candidate_names)
            cursor = await db.execute("INSERT INTO people (name, poster_file_name, role, library_id) VALUES (?, ?, ?, ?)", (person_name, poster_file_name, ROLE.ACTOR, library_id))
            person_id = cursor.lastrowid
        else:
            person_id, poster_file_name = row
            if poster_file_name is None:
                poster_file_name = get_poster_from_folder(folder_path=path, candidate_names=poster_candidate_names)
                if poster_file_name:
                    await db.execute("UPDATE people SET poster_file_name = ? WHERE id = ?", (poster_file_name, person_id))

        # A link from the scraper (with character and billing order) stays as it is
        await db.execute("INSERT OR IGNORE INTO movies__people (movie_id, person_id) VALUES (?, ?)", (movie_id, person_id))
        await db.commit()
