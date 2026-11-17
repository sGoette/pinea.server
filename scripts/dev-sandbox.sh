#!/usr/bin/env bash
# Local test environment: fake media + own database in <repo>/.sandbox (gitignored).
# Your normal dev data (../data next to the repo) is not touched.
#
#   ./scripts/dev-sandbox.sh                 create / update the sandbox (keeps DB, posters, TMDB key)
#   ./scripts/dev-sandbox.sh --reset         start over with an empty database (keeps media + TMDB key)
#   ./scripts/dev-sandbox.sh --db FILE       use a copy of FILE as database (e.g. to test migrations on prod data)
#   TMDB_API_KEY=... ./scripts/dev-sandbox.sh   put the key into the sandbox scrapers
#
# Then: npm run dev:sandbox   ->  http://localhost:3000
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SANDBOX="$REPO/.sandbox"
DATA="$SANDBOX/data"
MEDIA="$SANDBOX/media"
PYTHON="$REPO/.venv/bin/python"
SCRAPER_SRC="$REPO/backend/app/scrapers/tmdb"

RESET=0
DB_SOURCE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --reset) RESET=1; shift ;;
        --db) DB_SOURCE="$2"; shift 2 ;;
        -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

command -v ffmpeg >/dev/null || { echo "ffmpeg is missing (brew install ffmpeg)" >&2; exit 1; }
[[ -x "$PYTHON" ]] || { echo "No Python venv at $REPO/.venv" >&2; exit 1; }

if [[ $RESET == 1 || -n "$DB_SOURCE" ]]; then
    echo "Resetting database and posters"
    rm -rf "$DATA"
fi
mkdir -p "$DATA/db" "$DATA/posters"

# --- Fake videos -------------------------------------------------------------------------------
video() { # video <relative path> <label>
    local target="$MEDIA/$1"
    [[ -f "$target" ]] && return
    mkdir -p "$(dirname "$target")"
    local hue=$(( RANDOM % 360 ))
    # 12 s, 640x360, H.264 + AAC: plays in browsers and on tvOS. Falls back to no text if drawtext has no font.
    ffmpeg -loglevel error -y -f lavfi -i "testsrc2=duration=12:size=640x360:rate=24" -f lavfi -i "sine=frequency=440:duration=12" \
        -vf "hue=h=$hue,drawtext=text='$2':fontsize=28:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=10:x=(w-text_w)/2:y=h-60" \
        -c:v libx264 -pix_fmt yuv420p -preset veryfast -c:a aac -shortest "$target" 2>/dev/null \
    || ffmpeg -loglevel error -y -f lavfi -i "testsrc2=duration=12:size=640x360:rate=24" -f lavfi -i "sine=frequency=440:duration=12" \
        -vf "hue=h=$hue" -c:v libx264 -pix_fmt yuv420p -preset veryfast -c:a aac -shortest "$target"
    echo "  + $1"
}

image() { # image <relative path>
    local target="$MEDIA/$1"
    [[ -f "$target" ]] && return
    mkdir -p "$(dirname "$target")"
    ffmpeg -loglevel error -y -f lavfi -i "gradients=size=600x900:duration=1" -frames:v 1 "$target"
    echo "  + $1"
}

echo "Fake media in $MEDIA"
# Movies (TMDB scraper)
video "Movies/Casino Royale (2006).mp4"                    "Casino Royale 2006"
video "Movies/Casino Royale (2006)-trailer.mp4"            "Trailer: Casino Royale"      # extra, not scraped
video "Movies/Casino Royale (1967).mp4"                    "Casino Royale 1967"          # same title, other year
video "Movies/The Lord of the Rings.mp4"                   "Lord of the Rings ?"         # ambiguous -> Find match
video "Movies/The.Matrix.1999.1080p.BluRay.x264.mp4"       "The Matrix"                  # release-style name
video "Movies/Blade Runner 2049 (2017).mp4"                "Blade Runner 2049"           # number in the title
video "Movies/Heat {tmdb-949}.mp4"                         "Heat (TMDB id)"              # TMDB id
video "Movies/Inception-tt1375666.mp4"                     "Inception (IMDb id)"         # IMDb id
video "Movies/Skyfall/Skyfall (2012).mp4"                  "Skyfall"                     # movie in its own folder
video "Movies/Totally Unknown Home Recording.mp4"          "No match"                    # nothing found -> frame poster
# Series (library type SERIES)
video "Series/The Office/Season 2/S02E01 The Dundies.mp4"  "The Office S02E01"
video "Series/The Office/Season 2/S02E02 Sexual Harassment.mp4" "The Office S02E02"
video "Series/Breaking Bad/Season 1/S01E01.mp4"            "Breaking Bad S01E01"
video "Series/Breaking Bad/Season 1/S01E02.mp4"            "Breaking Bad S01E02"
# Home videos (no scraper, subfolders become collections)
video "Home Videos/Summer 2025/Beach.mp4"                  "Beach"
video "Home Videos/Summer 2025/Hike.mp4"                   "Hike"
image "Home Videos/Summer 2025/folder.jpg"
video "Home Videos/Birthday/Cake.mp4"                      "Cake"

# --- Folder configs + scrapers -----------------------------------------------------------------
cat > "$MEDIA/Home Videos/__pinea.json" <<'JSON'
{
    "subfoldersAreCollections": true,
    "subfoldersArePeople": false,
    "folderPeople": [],
    "useScraper": false,
    "potential_collections": []
}
JSON

for folder in Movies Series; do
    target="$MEDIA/$folder/__pinea.py"
    # Keep a key that is already in the sandbox copy, unless a new one is passed in
    key="${TMDB_API_KEY:-}"
    if [[ -z "$key" && -f "$target" ]]; then
        key="$(sed -n 's/^TMDB_API_KEY = "\(.*\)"$/\1/p' "$target")"
    fi
    cp "$SCRAPER_SRC/__pinea.json" "$MEDIA/$folder/__pinea.json"
    cp "$SCRAPER_SRC/__pinea.py" "$target"   # always the current scraper from the repo
    if [[ -n "$key" ]]; then
        KEY="$key" "$PYTHON" -c 'import os,re,sys; p=sys.argv[1]; s=open(p).read(); open(p,"w").write(re.sub(r"^TMDB_API_KEY = \".*\"$", "TMDB_API_KEY = \"" + os.environ["KEY"] + "\"", s, count=1, flags=re.M))' "$target"
    fi
done

# --- Database ----------------------------------------------------------------------------------
if [[ -n "$DB_SOURCE" ]]; then
    echo "Copying database $DB_SOURCE"
    "$PYTHON" -c 'import sqlite3,sys; src=sqlite3.connect(sys.argv[1]); dst=sqlite3.connect(sys.argv[2]); src.backup(dst)' "$DB_SOURCE" "$DATA/db/database.sqlite"
fi

# Create / migrate the schema, point the media root at the sandbox and use an own Bonjour name
# (a copied prod DB would otherwise announce itself with the prod server's name)
PINEA_DATA_ROOT="$SANDBOX" "$PYTHON" - "$MEDIA" "$REPO/backend" <<'PY'
import asyncio, sqlite3, sys
sys.path.insert(0, sys.argv[2])
from app.db.database import init_db
from app.config import DB_PATH
asyncio.run(init_db())
db = sqlite3.connect(DB_PATH)
db.execute("UPDATE settings SET value = ? WHERE key = 'MEDIA_ROOT_FOLDER'", (sys.argv[1],))
db.execute("UPDATE settings SET value = 'Pinea Sandbox' WHERE key = 'SERVER_NAME'")
db.commit()
version = db.execute("PRAGMA user_version").fetchone()[0]
libraries = db.execute("SELECT COUNT(*) FROM libraries").fetchone()[0]
print(f"Database {DB_PATH} (schema version {version}, {libraries} libraries)")
PY

echo
if grep -q '^TMDB_API_KEY = ""' "$MEDIA/Movies/__pinea.py"; then
    echo "TMDB key missing: put it into $MEDIA/Movies/__pinea.py and $MEDIA/Series/__pinea.py"
    echo "or rerun with TMDB_API_KEY=... $0"
else
    echo "TMDB key is set in the sandbox scrapers."
fi
echo
echo "Start: npm run dev:sandbox   ->  http://localhost:3000"
echo "Add libraries in the UI: Movies (type Movies), Series (type Series), Home Videos (type Videos)."
