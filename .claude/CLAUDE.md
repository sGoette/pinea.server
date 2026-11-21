# pinea.server

Self-hosted media server. Scans media folders on a file server, writes movies/series/collections/people
into SQLite, generates/fetches poster images and streams video files. A small React web UI is
used for settings, library management and triggering scans. The main client is a **tvOS app**
(separate repo, not here) that discovers the server via Bonjour (`_pinea._tcp`) and uses the REST API.

## Tech stack

- **Backend**: Python (FastAPI + uvicorn, aiosqlite, pydantic v2, zeroconf, Pillow, requests, Levenshtein).
  Requires Python ≥ 3.11 (`StrEnum`). Local dev venv uses 3.14 (`.venv/`).
- **External binaries**: `ffprobe` (video metadata) and `ffmpeg` (poster frame grabs), called via subprocess.
- **Frontend**: React 19 + MUI 7 + react-router 7, TypeScript, bundled with webpack/babel into `dist/frontend`.
- **DB**: single SQLite file, WAL mode. No ORM, raw SQL everywhere. Schema changes: `migrate()` in `db/database.py` (`PRAGMA user_version`).
- `package.json` only contains the web UI and its build tools. `@mui/material` + `@emotion/*` are needed
  as peer dependencies of `@mui/icons-material`.

## Repository layout

```
backend/
  requirements.txt          # pinned Python deps (NOTE: Pillow missing, but it is imported)
  app/
    main.py                 # FastAPI app, lifespan (init_db, scanner thread, zeroconf), SPA serving
    config.py               # paths (BASE_DIR, DB_PATH, POSTER_DIR, LOG_FILE), settings getters, constants
    logging_setup.py        # rotating file log -> data/pinea.log (truncated on every start)
    db/database.py          # get_db(), init_db(): CREATE TABLE IF NOT EXISTS for all tables
    api/                    # one router per file (see endpoints below)
    models/                 # pydantic models (API response shapes + scanner DTOs)
    scanner/
      worker.py             # ScannerWorker: own thread + asyncio loop + queue of ScanJob
      jobs.py               # ScanJob(library_id?, ignore_existing_metadata, movie_id?, force_cleanup)
      scan.py               # entry: single movie rescan, one library, or all libraries
      library.py            # os.walk library folder, process each video file
      movie.py              # insert movie row (ffprobe for duration/size/codec)
      metadata.py           # __pinea.json configs, dynamic scraper loading, posters, series
      media.py              # ffprobe/ffmpeg wrappers, poster hash names
      cleanup.py            # delete orphaned movies / collections / poster files after each scan
      metadata_functions/   # helpers: collections, people, posters, extras
    scanner/scraper.py      # load the closest __pinea.py, call search() (also used by the match API)
    scrapers/tmdb/          # TMDB scraper (__pinea.py + __pinea.json), copied into media folders by the user
    services/bonjour.py     # Bonjour/zeroconf: advertised IP, valid mDNS host name, ServiceInfo (port 4000)
    services/updater.py     # self-update from GitHub (see Deployment)
frontend/
  public/index.html
  src/App.tsx               # WebSocket context + ToastProvider, single route -> LibraryBrowser
  src/LibraryBrowser.tsx    # main page: top bar, grid, URL state, data loading, scan actions
  src/MediaCard.tsx         # MovieCard / CollectionCard (poster grid; VIDEOS libraries use 16:9 cards)
  src/PlayerOverlay.tsx     # fullscreen <video> overlay (?play=<id>), closes with ✕ / Esc / back
  src/MovieDetail.tsx       # movie detail page (?movie=<id>): header, cast & crew, extras, collections, details
  src/PersonDetail.tsx      # person page (?person=<id>): photo, name, their titles
  src/JustifiedGrid.tsx     # justified rows (each poster in its own ratio); gridLayout.ts picks grid/justified per library type
  src/SerieDetail.tsx       # serie page (?serie=) with seasons, season page (&season=) with the episode list
  src/DetailPage.tsx        # shared frame (back, poster tint) + header of detail pages
  src/MatchDialog.tsx       # "Find match": all scraper hits for a movie, pick one to apply
  src/LibraryDialog.tsx, SettingsDialog.tsx, UpdatePanel.tsx, Folder.tsx (folder picker), Dialog.tsx, Toast.tsx
  src/useScanStatus.ts      # polls /api/scan/status while a scan runs
  src/format.ts             # posterUrl, formatDuration, formatYear, pluralize
  src/styles.css            # design tokens (CSS variables), buttons, inputs, segmented control
  src/types/                # TS mirrors of backend models
scripts/release.sh          # builds the release tarball + VERSION.json/version.json (used by CI)
scripts/linux/              # install.sh, pinea.service, pinea-run.sh (Linux/systemd)
scripts/filesystem          # sketch of the intended media folder layout (incl. series/seasons)
.github/workflows/          # build-main.yml: build + publish every push to main
webpack.config.js           # one config: --mode production (build) / development (dev server)
```

## Running locally

```sh
npm run dev            # webpack dev server :3000 (proxies /api -> :4000) + uvicorn --reload :4000
PINEA_API=http://<server>:4000 npm run dev:frontend   # new UI against a running server's data
npm run dev:backend    # backend only: .venv/bin/python -m uvicorn app.main:app --app-dir backend --port 4000
./scripts/dev-sandbox.sh   # local test env in .sandbox/ (gitignored): fake videos, own DB, TMDB scraper copies
                           #   --reset (empty DB), --db FILE (test on a copy of a DB), TMDB_API_KEY=... to set the key
npm run dev:sandbox    # like npm run dev, but with PINEA_DATA_ROOT=.sandbox (Bonjour name "Pinea Sandbox")
npm run build          # frontend -> dist/frontend
npm run typecheck
./scripts/release.sh v0.1.7   # builds build/pineaserver-v0.1.7.tar.gz + build/version.json (wipes build/ first)
```

There are no tests and no linter config.

## Paths at runtime (config.py)

`BASE_DIR = Path(__file__).parent×4` resolves to the install root, so the code must sit at
`<root>/<something>/backend/app/config.py`. In production `<root>` is `/usr/local/pinea.server`
and the app is loaded through the `current` symlink (`--app-dir <root>/current/backend`), so
`BASE_DIR = /usr/local/pinea.server`. In dev the root is the parent of the repo folder!

| Constant      | Path                              |
|---------------|-----------------------------------|
| DB_PATH       | `<root>/data/db/database.sqlite`  |
| POSTER_DIR    | `<root>/data/posters/`            |
| LOG_FILE      | `<root>/data/pinea.log`           |
| HLS_ROOT      | `<root>/data/tmp/hls` (unused)    |
| FRONTEND_DIR  | `<repo or release>/frontend`      |

`PINEA_DATA_ROOT` overrides `<root>` (used by the sandbox).

Production layout:
```
/usr/local/pinea.server/
  current -> releases/<name>
  bin/pinea-run.sh                     (Linux, root-owned)
  releases/<name>/{backend,frontend,scripts/linux,VERSION.json,.venv,...}
  data/db/database.sqlite (+ -wal, -shm)
  data/posters/<md5>.jpg
  data/pinea.log
  logs/
  data/update/                         (self-update state)
```

## Database schema (`backend/app/db/database.py`)

All schema is created with `CREATE TABLE IF NOT EXISTS` on startup. **Adding a column to an
existing table therefore does nothing on existing databases.** Add the column to the CREATE statement
*and* a step in `migrate()` (bump `SCHEMA_VERSION`, use `_add_column_if_missing`, steps must be idempotent).
Current schema version: 1.

- **settings**(key TEXT UNIQUE, value TEXT, format TEXT): key/value config. Seeded:
  `MEDIA_ROOT_FOLDER` (absolute path, format `folder`), `SERVER_NAME` (`Pinea Server NNNN`, also the Bonjour name).
- **libraries**(id PK, name, media_folder TEXT UNIQUE, type `MOVIES|SERIES|VIDEOS`)
  `media_folder` is **relative to MEDIA_ROOT_FOLDER**.
- **movies**(id PK, title, file_location TEXT UNIQUE, length_in_seconds REAL, width, height, codec,
  format, poster_file_name, library_id → libraries CASCADE, metadata_last_updated INT (unix),
  release_date INT, added_date INT NOT NULL (file birth time, or mtime on Linux), is_extra_of_movie_id → movies,
  extra_type `TRAILER|BEHIND_THE_SCENES|MAKING_OFF`, is_episode_of_serie_id → series, episode INT,
  season TEXT, is_extra_of_serie_id → series)
  `file_location` is **relative to MEDIA_ROOT_FOLDER**. Episodes and extras are rows in `movies` too.
- **series**(id PK, title, poster_file_name, library_id → libraries CASCADE)
- **collections**(id PK, title, poster_file_name, library_id → libraries CASCADE)
- **movies__collections**(movie_id, collection_id) PK both, CASCADE
- **people**(id PK, name, poster_file_name, role `ACTOR|DIRECTOR`, library_id → libraries CASCADE)
- **movies__people**(movie_id, person_id, character TEXT, sort_order INTEGER) PK (movie_id, person_id), CASCADE.
  `character` = role name ("James Bond"), `sort_order` = billing order (0 first, NULL = folder people / directors).
  `order` is a reserved SQL keyword, hence `sort_order`.

`poster_file_name` everywhere is a bare file name inside POSTER_DIR (`md5(path+timestamp).jpg`).
Foreign keys are enforced only on connections that run `PRAGMA foreign_keys=ON`. Most API code
opens its own `aiosqlite.connect(DB_PATH)` without it.

## HTTP API (all under port 4000)

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | `{"status":"ok"}` |
| GET | `/api/settings` | list settings |
| POST | `/api/settings` | body `[Setting]`, updates values by key |
| GET | `/api/libraries` | all libraries |
| GET | `/api/library/{id}` | one library |
| GET | `/api/library/{id}/configs` | the `__pinea.json` files that decide about this library's files (`LibraryFolderConfig`: folder relative to MEDIA_ROOT_FOLDER, `above_library`, parsed config or `error`, `has_scraper_file`) |
| PUT | `/api/library` | create (`LibraryCreate`), queues a scan |
| POST | `/api/library` | update (`Library`) |
| DELETE | `/api/library/{id}` | delete (cascade), queues a scan (for cleanup) |
| GET | `/api/movies/{library_id}` | non-extra movies of library |
| GET | `/api/movies/collection/{collection_id}` | movies in a collection |
| GET | `/api/movies/person/{person_id}` | movies of a person |
| GET | `/api/movie/{id}` | one movie |
| GET | `/api/movie/{id}/stream` | file streaming with HTTP Range support (always `video/mp4`) |
| GET | `/api/movie/{id}/people` | people of a movie + `character`, `sort_order`; sorted by sort_order (NULLs last), then name |
| GET | `/api/movie/{id}/search?query=` | all hits of the closest scraper (`SearchResult`: id, name, original_name, release_date, poster_url, overview). 409 = no scraper, 502 = scraper error |
| POST | `/api/movie/{id}/match` | body `SearchResult`: queue a job that applies this hit (not stored) |
| GET | `/api/movie/{id}/extras` | extras of a movie |
| GET | `/api/movie/{id}/collections` | collections a movie belongs to |
| GET | `/api/series/{library_id}` | series + `seasons_count`, sorted by title |
| GET | `/api/serie/{id}` | one serie + `seasons_count` |
| GET | `/api/serie/{id}/episodes` | episodes ordered by season, episode |
| GET | `/api/collections/{library_id}` | collections + `movie_count` |
| GET | `/api/person/{id}` | one person |
| GET | `/api/people/{library_id}` | people of a library with `movie_count` (extras don't count), sorted by name |
| GET | `/api/poster/{file_name}?size=thumb` | poster image from POSTER_DIR. `size=thumb`: max 800×600, created on demand in `data/posters/thumbs/` (cleaned up with the posters). Cached as immutable |
| GET | `/api/filesystem/list?current_directory=` | subfolders inside MEDIA_ROOT_FOLDER (folder picker) |
| POST | `/api/scan/start?library_id=&ignore_existing_metadata=&movie_id=&force_cleanup=&reset_metadata=&config_folder=` | queue a scan job. `reset_metadata` (needs `library_id`): rebuild, see Scanning. `config_folder` (needs `library_id`): only the files of that `__pinea.json`, see Scanning |
| GET | `/api/scan/status` | `{running, pending_jobs, library_id, movie_id}` of the scanner worker |
| GET | `/api/update/status` | installed/latest version, update state, log, last result |
| POST | `/api/update/check` | fetch `version.json` of the `main-build` release |
| POST | `/api/update/install` | start self-update (409 if unsupported, busy or up to date) |
| WS | `/ws` | server push: `{"type": "LIBRARIES_UPDATED" \| "COLLECTIONS_UPDATED" \| "MOVIES_UPDATED"}` |
| GET | `/`, `/{path}` | SPA (frontend/index.html + static files) |

The tvOS app depends on these shapes. Treat response models as a public contract.

## Web UI

- **Design rules: [`design/DESIGN.md`](../design/DESIGN.md). Read it before any UI work.** The tvOS app is the design master;
  update DESIGN.md when a design decision is made. Logo: `design/logo.svg`.
- One page (`LibraryBrowser`). State lives in the URL query: `library`, `view=all|people` (default: collections), `sort=movies` (people view, default: name),
  `collection`, `movie` (detail page), `person` (person page), `serie` + `season` (SERIES libraries), `play`. Cards open the detail page; the grid stays
  mounted (hidden) behind detail pages so its scroll position survives. Reload keeps the place and the browser's back button works (it also closes the player).
- Dark theme only. Colors, radii and spacing are CSS variables in `styles.css` (the web copy of the tvOS assets, see DESIGN.md). Use them instead of hard-coded values.
- WebSocket `MOVIES_UPDATED` arrives once per file during scans, so the UI debounces refetches (800 ms).
- Posters must use absolute URLs (`/api/poster/...`, see `posterUrl()`).
- Browsers can only play what they support (mp4/h264, ...). mkv/avi etc. show a message in the player.

## Scanning & metadata

1. A `ScanJob` is queued (on library create/delete or `/api/scan/start`). The worker runs jobs serially.
2. `scan_library` walks `<MEDIA_ROOT_FOLDER>/<library.media_folder>` for `VIDEO_EXTENSIONS`.
3. New files are inserted (title = file stem title-cased, ffprobe data, `added_date`).
4. If `metadata_last_updated` is NULL (or `ignore_existing_metadata`), `fetch_movie_metadata` runs:
   - Extras: file stem ending in `-trailer|-behindthescenes|-makingoff` is linked to the main movie.
   - **Only the closest `__pinea.json`** above the file (`find_closest_config`, never above MEDIA_ROOT_FOLDER) decides
     how it is scanned. Configs further up add nothing, also no scraper. Keys (`FolderCollectionConfig`, all optional):
     `subfoldersAreCollections`, `subfoldersArePeople`, `folderPeople`, `useScraper`, `potential_collections`,
     `folder_is_collection` (the config's own folder becomes a collection, poster = image `collection.*` next to the json).
   - `useScraper` (`scanner/scraper.py`): the `__pinea.py` next to that config is only the metadata helper. Imports
     `__pinea.py` **from that media folder** and calls
     `search(absolute_path=, library=, query=None) -> [SearchResult]` (best first; `query` only for manual
     searches, scrapers without that parameter still work) and
     `fetch_metadata(search_result=, potential_collections=) -> Metadata`. A manual match (`ScanJob.search_result`)
     skips `search()`. Scrapers live in the media folders, not in this repo; `app/scrapers/tmdb` is the one we ship.
     They may import `app.models.*`. Extras are never scraped.
   - When the scraper succeeds (or there is none), the movie's `movies__people` / `movies__collections` links are
     deleted and rebuilt from folder configs + metadata. When the scraper fails, the old links stay.
   - TMDB scraper: API key in `TMDB_API_KEY` at the top of `__pinea.py`. Result ids: `movie/<id>`,
     `tv/<show>/<season>/<episode>`. Parses title/year/SxxEyy/`{tmdb-…}`/`tt…` from file names.
   - Posters: from scraper URL, from folder images (`folder/cover/poster/...`), or a random ffmpeg frame.
5. **Rebuild** (`reset_metadata`, "Rebuild metadata" in the library dialog, `scanner/reset.py`): before the scan, all
   metadata of the library is forgotten (titles back to the file name, posters, dates, extra/episode links, people,
   collections, series). Movie rows and file data stay. Skipped (no reset, no scan) when the library folder is
   missing or empty.
6. **Scan one config** (`config_folder`, "Folder configs" in the library dialog, `scan_library(config_folder=)`): walks only
   the files whose closest `__pinea.json` is that one (folders with their own `__pinea.json` are skipped) and fetches
   their metadata again. For a config above the library folder that means the whole library, unless one sits in between.
7. After every job (also when the scan failed halfway, each cleanup on its own): `cleanup_orphaned_movies` (deletes movies whose file is gone, with safety guards, see
   gotchas), then collections without (non-extra) movies, then people without movies, then poster files not referenced in the DB.

## Deployment

### Linux (target): `scripts/linux/`
- `install.sh`: run as root on Debian/Ubuntu. apt deps (python3, python3-venv, ffmpeg), system user
  `pineaserver`, downloads the latest `main-build` (or `--tarball FILE`), creates `releases/<name>/.venv`,
  installs `bin/pinea-run.sh` + `/etc/systemd/system/pinea.service`, switches `current`, restarts and
  waits for `/api/health`. Idempotent: re-run it to update. `--no-start` lets you copy an existing DB
  and posters into `data/` before the first start. `--skip-apt` skips the system packages.
  Also sets up (opt-out): **port 80 → 4000** via nftables (`/etc/nftables.d/pinea.nft`, included from
  `/etc/nftables.conf`, `table inet` = IPv4 + IPv6; `--no-port80`) and **`<hostname>.local`** via
  avahi-daemon, restricted to the default-route interface, IPv4 + IPv6 (`--no-avahi`).
- `pinea.service`: template (`@ROOT@`, `@USER@`). `Restart=always`, `StartLimitIntervalSec=0`,
  `ProtectSystem=full` + `ReadWritePaths=<root>`.
- `pinea-run.sh`: ExecStart. Lives in `<root>/bin/` (root-owned, outside releases). Handles rollback,
  then `exec current/.venv/bin/python -m uvicorn ...`. Env: `PINEA_ROOT`, `PINEA_HOST` (default empty =
  IPv4 + IPv6), `PINEA_PORT`. Only `install.sh` updates it, not the UI updater.
- Everything under `<root>` is owned by `pineaserver` (needed for self-update), except `bin/`.

### Self-update from the web UI
- CI (`.github/workflows/build-main.yml`) builds every push to `main` with `scripts/release.sh main-<sha7>`
  and publishes `pineaserver-main.tar.gz` + `version.json` (name, commit, commit_date, message, built_at,
  sha256) to the rolling pre-release / tag **`main-build`**.
- Every release contains `VERSION.json` (same fields without sha256). It's missing in dev, where
  `current` shows as unknown. Local builds with uncommitted changes get commit `<sha>-dirty`.
- `app/services/updater.py`: check → download → verify sha256 → extract to `releases/<name>` →
  venv + pip → compileall + import check → write `data/update/pending` → atomic symlink switch →
  SIGTERM itself → systemd restarts. On successful startup `main.py` lifespan calls
  `updater.finalize_pending_update()`. If the new release fails to start 3 times, `pinea-run.sh` points
  `current` back at the previous release and writes `data/update/rolled_back`. Keeps 3 releases.
- State files in `data/update/`: `pending`, `attempts`, `rolled_back`, `last_result.json`.
- API: `GET /api/update/status`, `POST /api/update/check`, `POST /api/update/install` (409 + detail on refusal).
  UI: `frontend/src/UpdatePanel.tsx` in the settings dialog (polls status, reloads when the new commit is up).
- Only enabled on Linux with the releases/current layout. For local testing on macOS set
  `PINEA_UPDATER_ENABLED=1` and `PINEA_UPDATE_URL=http://127.0.0.1:<port>` (a folder served with
  `python3 -m http.server` that contains the tarball + version.json).
- System packages (apt) are not updated by the UI updater. Re-run `install.sh` for that.
- Do **not** add new WebSocket notification types for this (or anything else) without checking the tvOS
  app: it decodes `NOTIFICATION_TYPE` and may fail on unknown values. The UI polls instead.

### Two names, don't mix them up
- **Machine host name** (the Debian hostname) → `<hostname>.local` via avahi. Used by the browser
  (`http://<hostname>.local`, port 80 forwarded) and SSH. Never changes with the server name.
- **Server name** (setting `SERVER_NAME`) → the Bonjour service name shown in the tvOS app, plus a derived
  mDNS host name for the service record (`mdns_hostname()`, e.g. `the-pinea-server.local`). Saving a new
  name re-announces the service live (`rename_service()`); a name another service already uses → 409,
  nothing saved. Names are limited to 63 bytes.

### Environment facts
- Media is mounted **read-only**. The server never writes to media folders.
- The tvOS app finds the server only via Bonjour and stores nothing on the client, so IP changes don't matter.
- This repo is **public**. Never commit personal data, hostnames, IPs, network layout, media titles or
  folder names. Keep such things in local notes and memory only.

## Known pitfalls / gotchas

- `added_date` uses `st_birthtime` where it exists (FreeBSD/macOS), otherwise `st_mtime` (Linux).
- Orphan cleanup (`scanner/cleanup.py`) skips libraries whose folder is missing or empty (not mounted)
  and refuses to delete more than 50% of a library (≥ 20 movies) unless the scan is started with
  `force_cleanup=true`. Don't weaken this: the original behaviour wiped the whole DB on a missing mount.
- `MEDIA_ROOT_FOLDER` must be the same absolute path in the DB as on the host. All other paths are relative.
- `GET_MEDIA_ROOT_FOLDER`/`GET_SERVER_NAME` call `exit(1)` when the setting row is missing.
- Names from files/folders go through `scanner/text.py:smart_title()`, not `str.title()` (which breaks
  "Don't" → "Don'T"). Collection and people lookups by name use `COLLATE NOCASE` so older entries
  with different casing still match.
- `ws_manager.broadcast()` coalesces: each notification type is sent at most once per 1.5 s, always from
  the main event loop (the scanner runs in its own thread/loop). Callers can broadcast freely.
- "Refresh metadata" (`/api/scan/start?movie_id=`) keeps an existing poster. A frame is only grabbed when
  the movie has no poster or the file is missing in `data/posters/`.
- Streaming (`api/movie.py`, `parse_range`): single byte ranges incl. suffix ranges, end clamped to the
  file size, 416 for ranges starting past the end, malformed/multi-range headers are ignored (200 + whole
  file). The tvOS app (AVPlayer) depends on this endpoint, so test playback on tvOS after changes.
- Bonjour (`services/bonjour.py`): the tvOS app resolves the service and connects to the advertised
  address. Rules: advertise the default-route interface's IPv4 (never 127.x or 169.254.x, wait up to
  60 s for the network at startup), run zeroconf only on that interface (`AsyncZeroconf(interfaces=[ip])`,
  the VM also has an internal NFS network card), and use a valid host name (letters, digits, hyphens:
  `mdns_hostname()`), never underscores. Override the IP with `PINEA_ADVERTISE_IP` if ever needed.
  The service announces IPv4 only and answers AAAA queries with an NSEC "no such record". That needs
  **zeroconf ≥ 0.150.4** (older versions put the NSEC on the service name instead of the host name, and
  Apple clients then wait ~5 s per lookup). Check: `getaddrinfo('<host>.local')` must return instantly.
- avahi can't send NSEC, so it must publish the IPv6 address (`use-ipv6=yes`); otherwise `<hostname>.local`
  lookups take ~5 s. That's why the server listens on IPv6 too. Over IPv6 the VM has a public address:
  the router's IPv6 firewall must block incoming connections (the UI has no login).
- `__WSURL__` (webpack DefinePlugin): `/ws` in production, `ws://<PINEA_API host>/ws` in dev.
- `Levenshtein` in requirements.txt isn't imported by the app, but scrapers (`__pinea.py` in the media
  folders) run in the server's Python environment and may use it. Don't remove it.
- `order` is a reserved SQL keyword.
- `release_date` is unix seconds and negative before 1970. Don't treat values < 10000 as years unless > 0.
- `scripts/release.sh` deletes `build/` on every run.
- The log file is truncated on every start (`LOG_FILE.write_text("")` in main.py).
- uvicorn exits with code 143 after a SIGTERM (it re-raises the signal). That's normal.
- `.DS_Store` files are committed. Ignore them.
