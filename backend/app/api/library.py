import asyncio
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, Request
import aiosqlite
from app.scanner.jobs import ScanJob
from app.config import DB_PATH, GET_MEDIA_ROOT_FOLDER
from app.db.database import fetch_one
from app.models.folder_collection_config import LibraryFolderConfig
from app.scanner.metadata_functions.folder_collection_config import list_library_configs
from app.models.library import Library, LibraryCreate
from app.models.notification import Notification, NOTIFICATION_TYPE
from app.api.websocket_manager import ws_manager

router = APIRouter(prefix="/api/library")

@router.get("/{library_id}", response_model=Library)
async def get_library(library_id: int):
    library = await fetch_one("SELECT * FROM libraries WHERE id = ?", (library_id,))
    if library is None:
        raise HTTPException(status_code=404, detail="Library not found")
    return library

@router.get("/{library_id}/configs", response_model=List[LibraryFolderConfig])
async def get_library_configs(library_id: int):
    """The __pinea.json files that decide how the files of this library are scanned, sorted by folder."""
    library = await get_library(library_id)
    media_root = Path(await GET_MEDIA_ROOT_FOLDER()).resolve()
    library_path = (media_root / library["media_folder"]).resolve()
    if not library_path.is_dir():
        return []
    return await asyncio.to_thread(list_library_configs, media_root, library_path)

@router.put("", response_model=Library)
async def create_library(request: Request, library: LibraryCreate):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO libraries (name, media_folder, type) VALUES (?, ?, ?)", (library.name, library.media_folder, library.type))
        await db.commit()
        library_id = cursor.lastrowid

    request.app.state.scanner.submit(ScanJob(library_id=library_id))
    await ws_manager.broadcast(Notification(type=NOTIFICATION_TYPE.LIBRARIES_UPDATED))
    return Library(id=library_id, name=library.name, media_folder=library.media_folder, type=library.type)
    
@router.post("", response_model=Library)
async def update_library(library: Library):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE libraries SET name = ?, media_folder = ?, type = ? WHERE id = ?", (library.name, library.media_folder, library.type, library.id))
        await db.commit()

    await ws_manager.broadcast(Notification(type=NOTIFICATION_TYPE.LIBRARIES_UPDATED))
    return library

@router.delete("/{library_id}")
async def delete_library(request: Request,library_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        # Cascades to movies, collections, series and people. Their poster files are removed by
        # the cleanup after the scan queued below.
        await db.execute("PRAGMA foreign_keys = ON;")
        cursor = await db.execute("DELETE FROM libraries WHERE id = ?", (library_id,))
        await db.commit()
        rowcount = cursor.rowcount

    if rowcount == 0:
        raise HTTPException(status_code=404, detail="Library not found")
    
    scanner = request.app.state.scanner
    scanner.submit(ScanJob(library_id=library_id))
    await ws_manager.broadcast(Notification(type=NOTIFICATION_TYPE.LIBRARIES_UPDATED))
    return {"msg": "Library deleted"}