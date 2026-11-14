import os
import aiosqlite
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent.resolve() #pinea.server folder
POSTER_DIR = BASE_DIR / "data/posters"
DB_PATH = BASE_DIR / "data/db/database.sqlite"

BACKEND_DIR = Path(__file__).resolve().parents[1]      # backend/app -> backend
REPO_ROOT   = BACKEND_DIR.parent                       # backend -> repo root
LOG_FILE     = BASE_DIR / "data/pinea.log"

FRONTEND_DIR = REPO_ROOT / "frontend"                  # repo_root/frontend
INDEX_HTML = FRONTEND_DIR / "index.html"

# Self-update (Linux installs only, see app/services/updater.py and scripts/linux/)
VERSION_FILE = REPO_ROOT / "VERSION.json"              # written by scripts/release.sh, missing in dev
RELEASES_DIR = BASE_DIR / "releases"
CURRENT_LINK = BASE_DIR / "current"
UPDATE_STATE_DIR = BASE_DIR / "data/update"            # shared with scripts/linux/pinea-run.sh
UPDATE_BASE_URL = os.environ.get("PINEA_UPDATE_URL", "https://github.com/sGoette/pinea.server/releases/download/main-build")
UPDATE_TARBALL_NAME = "pineaserver-main.tar.gz"
UPDATE_VERSION_NAME = "version.json"

async def GET_MEDIA_ROOT_FOLDER() -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT value FROM settings WHERE key = 'MEDIA_ROOT_FOLDER'") as cursor:
            MEDIA_ROOT_FOLDER = await cursor.fetchone()

        if MEDIA_ROOT_FOLDER:
            return str(MEDIA_ROOT_FOLDER[0])
        
        exit(1)

async def GET_SERVER_NAME() -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT value FROM settings WHERE key = 'SERVER_NAME'") as cursor:
            SERVER_NAME = await cursor.fetchone()

            if SERVER_NAME:
                return str(SERVER_NAME[0])
            
            exit(1)

COLLECTION_POSTER_CANDIDATE_NAMES = ['folder', 'cover', 'poster', 'thumb', 'thumbnail', 'collection']

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv'}