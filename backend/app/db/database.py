import random
import sqlite3
from typing import Any, Optional

import aiosqlite

from app.config import DB_PATH

import logging
log = logging.getLogger(__name__)

# The whole schema. CREATE TABLE IF NOT EXISTS never changes an existing table: for a schema change
# on an existing database, change it here and write a one-off script like scripts/migrate-data.py.
SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT NOT NULL UNIQUE,
    value TEXT,
    format TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS libraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    media_folder TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    poster_file_name TEXT,
    library_id INTEGER NOT NULL REFERENCES libraries(id) ON DELETE CASCADE
);

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
    is_extra_of_serie_id INTEGER REFERENCES series(id),
    still_file_name TEXT
);

CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    poster_file_name TEXT,
    library_id INTEGER NOT NULL REFERENCES libraries(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS movies__collections (
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, collection_id)
);

CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    poster_file_name TEXT,
    role TEXT,
    library_id INTEGER NOT NULL REFERENCES libraries(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS movies__people (
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    character TEXT,
    sort_order INTEGER,
    PRIMARY KEY (movie_id, person_id)
);
"""

def missing_columns(db: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """(table, column, type) that SCHEMA has but the existing tables of the database don't."""
    expected = sqlite3.connect(":memory:")
    expected.executescript(SCHEMA)
    missing = []
    for (table,) in expected.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"):
        existing = { row[1] for row in db.execute(f"PRAGMA table_info({table})") }
        if existing:
            missing += [(table, row[1], row[2]) for row in expected.execute(f"PRAGMA table_info({table})") if row[1] not in existing]
    expected.close()
    return missing

async def init_db():
    db = sqlite3.connect(DB_PATH)
    try:
        missing = missing_columns(db)
    finally:
        db.close()
    if missing:
        log.error(f"The database is older than the code, missing columns: {', '.join(f'{t}.{c}' for t, c, _ in missing)}. Run scripts/migrate-data.py")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.executescript(SCHEMA)
        await db.execute("""
INSERT INTO settings (key, value, format) VALUES
    ('MEDIA_ROOT_FOLDER', '', 'folder'),
    ('SERVER_NAME', ?, 'text')
ON CONFLICT(key) DO NOTHING
""", (f"Pinea Server {random.randint(1000, 9999)}",))
        await db.commit()

async def fetch_all(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """All rows of a read query as dicts (for API responses)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def fetch_one(sql: str, params: tuple = ()) -> Optional[dict[str, Any]]:
    """The first row of a read query as a dict, or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, params) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None
