import asyncio
from fastapi import APIRouter, HTTPException, Request
import aiosqlite

from app.config import DB_PATH
from app.models.collection import Collection
from app.models.notification import Notification, NOTIFICATION_TYPE
from app.api.websocket_manager import ws_manager
from app.scanner.metadata_functions.get_poster_from_url import save_poster_image

import logging
log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/collection")

MAX_POSTER_BYTES = 25 * 1024 * 1024

async def _get_collection(db: aiosqlite.Connection, collection_id: int) -> dict:
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM collections WHERE id = ?", (collection_id,)) as cursor:
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return dict(row)

@router.put("/{collection_id}/poster", response_model=Collection)
async def set_collection_poster(collection_id: int, request: Request):
    """Body: the image file itself (any format Pillow reads), not multipart. Replaces the poster.
    The old poster file is removed by the cleanup after the next scan."""
    async with aiosqlite.connect(DB_PATH) as db:
        await _get_collection(db, collection_id)

    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_POSTER_BYTES:
            raise HTTPException(status_code=413, detail=f"The image is larger than {MAX_POSTER_BYTES // (1024 * 1024)} MB")
    if not data:
        raise HTTPException(status_code=400, detail="No image in the request body")

    try:
        poster_file_name = await asyncio.to_thread(save_poster_image, bytes(data), f"collection-{collection_id}")
    except Exception:
        log.exception(f"Could not read the uploaded poster of collection {collection_id}")
        raise HTTPException(status_code=400, detail="This file is not an image pinea can read")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE collections SET poster_file_name = ? WHERE id = ?", (poster_file_name, collection_id))
        await db.commit()
        collection = await _get_collection(db, collection_id)

    await ws_manager.broadcast(Notification(type=NOTIFICATION_TYPE.COLLECTIONS_UPDATED))
    return collection

@router.delete("/{collection_id}/poster", response_model=Collection)
async def remove_collection_poster(collection_id: int):
    """Removes the poster. The next scan of the collection's movies picks one again (folder image or scraper)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await _get_collection(db, collection_id)
        await db.execute("UPDATE collections SET poster_file_name = NULL WHERE id = ?", (collection_id,))
        await db.commit()
        collection = await _get_collection(db, collection_id)

    await ws_manager.broadcast(Notification(type=NOTIFICATION_TYPE.COLLECTIONS_UPDATED))
    return collection
