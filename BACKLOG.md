# Backlog

## Character name and billing order for people in a movie

**Goal:** Store which character an actor plays in a movie and their billing order, so clients can
show "Keanu Reeves as Neo" and sort the cast by importance instead of alphabetically.

**Status:** Started, then postponed until after the FreeBSD → Linux migration. The work in progress
is in `git stash` ("WIP: movies__people character/order"). Restore it with `git stash list` and `git stash pop`.

### What the stash contains
- `db/database.py`: adds `character STRING` and `order INTEGER` to `movies__people`.
- `api/movie.py`: `GET /api/movie/{id}/people` selects `mp.character`, `mp.order`.
- `models/person.py`: `Person` gets `character: Optional[str]`, `order: Optional[int]`.
- `models/metadata.py`: `PersonMetadata` gets `character`, `order` (with `= None` defaults).

### What's wrong with it / still to do
1. **Rename `order`.** It is a reserved SQL keyword. `CREATE TABLE` fails with a syntax error, even
   when the table already exists, so the server won't start. Use `sort_order` (and `character TEXT`).
2. **DB migration.** `CREATE TABLE IF NOT EXISTS` never adds columns to existing databases. Add an
   explicit migration, e.g. check `PRAGMA table_info(movies__people)` and run
   `ALTER TABLE movies__people ADD COLUMN ...`. A good time to introduce `PRAGMA user_version` for
   schema versioning.
3. **Model defaults.** `Person.character` / `Person.order` need `= None`. Without defaults pydantic v2
   treats them as required, which breaks `GET /api/person/{id}` and every `Person(**row)` in the
   scanner (`add_person_to_movie.py`, `set_subfolder_as_person.py`).
4. **Write the values.** `add_person_to_movie` must insert/update `character` and `sort_order` from
   `PersonMetadata`. Scrapers (`__pinea.py` in the media folders, and the example in
   `app/scrapers/imdb`) must fill them.
5. **Sorting.** `/api/movie/{id}/people` should probably `ORDER BY mp.sort_order IS NULL, mp.sort_order, p.name`.
6. **tvOS app.** The people response gets new fields. Update the app's model to use them.
   Extra fields are harmless for older app versions.

## Series view with seasons and episodes in the web UI

**Status:** Later. The tvOS app already has a season view; rebuild that here.

Today, episodes of a SERIES library show up as a flat list under "All". The backend already has
`GET /api/series/{library_id}` (with `seasons_count`) and `GET /api/serie/{id}/episodes`
(ordered by season, episode).
