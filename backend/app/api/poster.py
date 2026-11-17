import asyncio
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from PIL import Image

from app.config import POSTER_DIR, POSTER_THUMB_DIR

import logging
log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/poster")

# Poster file names are new hashes whenever the image changes, so a file never changes: browsers may cache forever
CACHE_HEADERS = { "Cache-Control": "public, max-age=31536000, immutable" }

# size=thumb: for grids and rows (cards are at most ~250 px high, x2 for Retina)
THUMB_BOX = (800, 600)
THUMB_QUALITY = 82

def _make_thumbnail(source: Path, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(f".{os.getpid()}.tmp")
    with Image.open(source) as img:
        img.thumbnail(THUMB_BOX)
        img.convert("RGB").save(temporary, format="JPEG", quality=THUMB_QUALITY, optimize=True)
    temporary.replace(target)   # atomic: parallel requests never see a half-written file

@router.get("/{poster_file_name}")
async def get_poster(poster_file_name: str, size: Optional[Literal["thumb"]] = None):
    """The poster as stored (default, used by the tvOS app) or a small, cached version (size=thumb)."""
    file_path = (POSTER_DIR / poster_file_name).resolve()
    if file_path.parent != POSTER_DIR.resolve() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Poster file not found on disk")

    if size == "thumb":
        thumb_path = POSTER_THUMB_DIR / poster_file_name
        if not thumb_path.is_file():
            try:
                await asyncio.to_thread(_make_thumbnail, file_path, thumb_path)
            except Exception:
                log.exception(f"Could not create a thumbnail of {poster_file_name}, sending the original")
                return FileResponse(file_path, headers=CACHE_HEADERS)
        return FileResponse(thumb_path, headers=CACHE_HEADERS)

    return FileResponse(file_path, headers=CACHE_HEADERS)
