# Backlog

## Creating a library for a folder that already has one

**Where:** `PUT /api/library` (`backend/app/api/library.py`, `create_library`)

`libraries.media_folder` is `UNIQUE`, so a second library for the same folder fails with an
`IntegrityError` and the web UI only gets a 500. Catch the conflict and answer with a clear error
(e.g. 409 "This folder already has a library"), and show it in the library dialog.

## Changing the media root folder

**Where:** `POST /api/settings` (`backend/app/api/settings.py`, setting `MEDIA_ROOT_FOLDER`)

All `libraries.media_folder` and `movies.file_location` paths are relative to `MEDIA_ROOT_FOLDER`.
Saving a different root today just changes the setting: existing libraries then point into the new
root, files are missing, and the orphan cleanup may delete movies (its safety guards usually stop it).
When libraries exist, a root change needs a decision: refuse it, or delete the libraries with all their
movies and posters first (ask the user in the UI).
