#!/usr/bin/env python3
"""One-off migration: brings an existing pinea database to the current state, so the app code
doesn't have to deal with old data formats anymore.

- adds columns that the current schema (backend/app/db/database.py) has but the database doesn't
- release_date: plain years (e.g. 2004) -> unix seconds (January 1st, UTC)
- people.role: missing or unknown -> ACTOR
- movies.title: missing -> taken from the file name
- removes links to movies / people / collections that don't exist anymore
- clears references to deleted movies (extras) and series (episodes, serie extras)

A backup of the database is written next to it first. Safe to run more than once.

Usage (on the server, stop the service first):
    sudo systemctl stop pinea
    sudo -u pineaserver /usr/local/pinea.server/current/.venv/bin/python \\
        /usr/local/pinea.server/current/scripts/migrate-data.py [--dry-run] [DB_PATH]
    sudo systemctl start pinea

DB_PATH defaults to <PINEA_ROOT or /usr/local/pinea.server>/data/db/database.sqlite.
"""
import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.db.database import missing_columns # noqa: E402  compares with the schema the app expects
from app.scanner.text import smart_title    # noqa: E402  how the scanner names new files

DEFAULT_ROOT = Path(os.environ.get("PINEA_ROOT", "/usr/local/pinea.server"))

def year_to_unix(year: int) -> int:
    return int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())

def migrate(db: sqlite3.Connection) -> list[str]:
    done: list[str] = []

    def run(description: str, sql: str, params: tuple = ()):
        count = db.execute(sql, params).rowcount
        if count:
            done.append(f"{description}: {count}")

    for table, column, column_type in missing_columns(db):
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
        done.append(f"added column {table}.{column} {column_type}")

    years = db.execute("SELECT id, release_date FROM movies WHERE release_date > 0 AND release_date < 10000").fetchall()
    db.executemany("UPDATE movies SET release_date = ? WHERE id = ?", [(year_to_unix(year), movie_id) for movie_id, year in years])
    if years:
        done.append(f"release_date year -> unix seconds: {len(years)}")

    untitled = db.execute("SELECT id, file_location FROM movies WHERE title IS NULL OR title = ''").fetchall()
    db.executemany("UPDATE movies SET title = ? WHERE id = ?", [(smart_title(Path(location).stem), movie_id) for movie_id, location in untitled])
    if untitled:
        done.append(f"movie titles from file names: {len(untitled)}")

    run("people without a valid role -> ACTOR", "UPDATE people SET role = 'ACTOR' WHERE role IS NULL OR role NOT IN ('ACTOR', 'DIRECTOR')")

    run("people links of deleted movies/people", "DELETE FROM movies__people WHERE movie_id NOT IN (SELECT id FROM movies) OR person_id NOT IN (SELECT id FROM people)")
    run("collection links of deleted movies/collections", "DELETE FROM movies__collections WHERE movie_id NOT IN (SELECT id FROM movies) OR collection_id NOT IN (SELECT id FROM collections)")
    run("extras of deleted movies", "UPDATE movies SET is_extra_of_movie_id = NULL, extra_type = NULL WHERE is_extra_of_movie_id IS NOT NULL AND is_extra_of_movie_id NOT IN (SELECT id FROM movies)")
    run("episodes of deleted series", "UPDATE movies SET is_episode_of_serie_id = NULL WHERE is_episode_of_serie_id IS NOT NULL AND is_episode_of_serie_id NOT IN (SELECT id FROM series)")
    run("serie extras of deleted series", "UPDATE movies SET is_extra_of_serie_id = NULL WHERE is_extra_of_serie_id IS NOT NULL AND is_extra_of_serie_id NOT IN (SELECT id FROM series)")

    # Schema versions are no longer used (database.py has the whole schema)
    db.execute("PRAGMA user_version = 0")
    return done

def report_leftovers(db: sqlite3.Connection):
    """Things the script doesn't fix on its own."""
    checks = {
        "collections without title": "SELECT COUNT(*) FROM collections WHERE title IS NULL",
        "series without title": "SELECT COUNT(*) FROM series WHERE title IS NULL",
        "people without name": "SELECT COUNT(*) FROM people WHERE name IS NULL",
        "unknown library types": "SELECT COUNT(*) FROM libraries WHERE type NOT IN ('MOVIES', 'SERIES', 'VIDEOS')",
        "unknown extra types": "SELECT COUNT(*) FROM movies WHERE extra_type IS NOT NULL AND extra_type NOT IN ('TRAILER', 'BEHIND_THE_SCENES', 'MAKING_OFF')",
    }
    for description, sql in checks.items():
        count = db.execute(sql).fetchone()[0]
        if count:
            print(f"  ! {description}: {count} (not changed, check by hand)")
    integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        print(f"  ! integrity_check: {integrity}")

def main():
    parser = argparse.ArgumentParser(description="Bring an existing pinea database to the current state.")
    parser.add_argument("db_path", nargs="?", type=Path, default=DEFAULT_ROOT / "data/db/database.sqlite")
    parser.add_argument("--dry-run", action="store_true", help="show what would change, change nothing")
    args = parser.parse_args()

    if not args.db_path.is_file():
        sys.exit(f"No database at {args.db_path}")

    # Autocommit mode + explicit BEGIN: then ALTER TABLE is part of the transaction too (SQLite can
    # roll back schema changes), so --dry-run really changes nothing.
    db = sqlite3.connect(args.db_path, isolation_level=None)
    if not args.dry_run:
        backup_path = args.db_path.with_name(f"{args.db_path.name}.before-migration-{time.strftime('%Y%m%d-%H%M%S')}")
        backup = sqlite3.connect(backup_path)
        db.backup(backup)
        backup.close()
        print(f"Backup: {backup_path}")

    try:
        db.execute("BEGIN IMMEDIATE")
        done = migrate(db)
        report_leftovers(db)
        db.execute("ROLLBACK" if args.dry_run else "COMMIT")
    except Exception:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        db.close()

    if not done:
        print("Nothing to migrate, the database is up to date.")
        return
    print("Would change:" if args.dry_run else "Changed:")
    for line in done:
        print(f"  - {line}")

if __name__ == "__main__":
    main()
