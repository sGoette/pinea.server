import aiosqlite
import random
from app.config import DB_PATH

async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA foreign_keys=ON;")
    return db

async def init_db():
    db = await get_db()

    await db.execute("PRAGMA foreign_keys=ON;")

    await db.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT NOT NULL UNIQUE,
    value TEXT,
    format TEXT NOT NULL
)
""")
    
    await db.execute("""
INSERT INTO settings
( key, value, format )
VALUES
( 'MEDIA_ROOT_FOLDER', '', 'folder' ),
( 'SERVER_NAME', ?, 'text' )
ON CONFLICT(key) DO NOTHING
""", (f"Pinea Server {random.randint(1000, 9999)}",))
    
    await db.execute("""
CREATE TABLE IF NOT EXISTS libraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    media_folder TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL
)
""")
    
    await db.execute("""
CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    poster_file_name TEXT,
    library_id INTEGER NOT NULL REFERENCES libraries(id) ON DELETE CASCADE
)
""")
    
    await db.execute("""
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    file_location TEXT NOT NULL UNIQUE,
    length_in_seconds REAL,
    width INTEGER,
    height INTEGER,
    codec TEXT,
    format TEXT,
    poster_file_name TEXT,
    library_id INTEGER NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    metadata_last_updated INTEGER,
    release_date INTEGER,
    added_date INTEGER NOT NULL,
    is_extra_of_movie_id INTEGER REFERENCES movies(id),
    extra_type TEXT,
    is_episode_of_serie_id INTEGER REFERENCES series(id),
    episode INTEGER,
    season TEXT,
    is_extra_of_serie_id INTEGER REFERENCES series(id)
)
""")

    await db.execute("""
CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    poster_file_name TEXT,
    library_id INTEGER NOT NULL REFERENCES libraries(id) ON DELETE CASCADE
)
""")
    
    await db.execute("""
CREATE TABLE IF NOT EXISTS movies__collections (
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, collection_id)
)
""")
    
    await db.execute("""
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    poster_file_name TEXT,
    role TEXT,
    library_id INTEGER NOT NULL REFERENCES libraries(id) ON DELETE CASCADE
)
""")
    
    await db.execute("""
CREATE TABLE IF NOT EXISTS movies__people (
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    character TEXT,
    sort_order INTEGER,
    PRIMARY KEY (movie_id, person_id)
)
""")

    await migrate(db)

    await db.commit()
    await db.close()

async def _add_column_if_missing(db: aiosqlite.Connection, table: str, column: str, definition: str):
    async with db.execute(f"PRAGMA table_info({table})") as cursor:
        columns = [row[1] for row in await cursor.fetchall()]
    if column not in columns:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

# CREATE TABLE IF NOT EXISTS never changes existing tables. Every schema change to an existing
# table gets a step here, guarded by PRAGMA user_version. New databases already have the new
# columns from the CREATE statements above, so the steps must be idempotent.
SCHEMA_VERSION = 1

async def migrate(db: aiosqlite.Connection):
    async with db.execute("PRAGMA user_version") as cursor:
        row = await cursor.fetchone()
        version = row[0] if row else 0

    if version < 1:
        # Character name and billing order of a person in a movie
        await _add_column_if_missing(db, "movies__people", "character", "TEXT")
        await _add_column_if_missing(db, "movies__people", "sort_order", "INTEGER")

    if version < SCHEMA_VERSION:
        await db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
