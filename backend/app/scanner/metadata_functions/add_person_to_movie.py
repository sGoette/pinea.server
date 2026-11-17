import aiosqlite

from app.config import DB_PATH
from app.models.movie import Movie
from app.models.metadata import PersonMetadata
from app.models.person import Person, ROLE
from app.scanner.metadata_functions.get_poster_from_url import get_poster_from_url

async def add_person_to_movie(person_metadata: PersonMetadata, movie: Movie):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT * FROM people WHERE name = ? COLLATE NOCASE AND library_id = ?", (person_metadata.name, movie.library_id)) as select_cursor:
            person_row = await select_cursor.fetchone()

        if person_row is None:
            role = person_metadata.role or ROLE.ACTOR
            async with db.execute("INSERT INTO people (name, role, library_id) VALUES (?, ?, ?)", (person_metadata.name, role, movie.library_id)) as insert_cursor:
                person_id = insert_cursor.lastrowid
            await db.commit()
            person = Person(id=person_id, name=person_metadata.name, poster_file_name=None, role=role)
        else:
            person = Person(**person_row)

        # A person can show up twice for one movie (e.g. actor and director): keep the character
        # and the smallest (= most prominent) sort order.
        await db.execute("""
INSERT INTO movies__people (movie_id, person_id, character, sort_order) VALUES (?, ?, ?, ?)
ON CONFLICT (movie_id, person_id) DO UPDATE SET
    character = COALESCE(movies__people.character, excluded.character),
    sort_order = CASE
        WHEN movies__people.sort_order IS NULL THEN excluded.sort_order
        WHEN excluded.sort_order IS NULL THEN movies__people.sort_order
        ELSE MIN(movies__people.sort_order, excluded.sort_order)
    END
""", (movie.id, person.id, person_metadata.character, person_metadata.sort_order))
        await db.commit()

        if person.poster_file_name is None and person_metadata.poster_url:
            poster_file_name = get_poster_from_url(url=person_metadata.poster_url)

            if poster_file_name:
                await db.execute("UPDATE people SET poster_file_name = ? WHERE id = ?", (poster_file_name, person.id))
                await db.commit()
