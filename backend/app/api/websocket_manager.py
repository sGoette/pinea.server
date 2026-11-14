import asyncio
import threading
from typing import Optional, Set
from fastapi import WebSocket
from app.models.notification import Notification, NOTIFICATION_TYPE

import logging
log = logging.getLogger(__name__)

# Notifications of the same type within this window are sent once. A scan otherwise sends
# MOVIES_UPDATED for every single file, and every client reloads its lists each time.
COALESCE_SECONDS = 1.5

class WSManager:
    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None  # the server's main event loop
        self._pending: Set[NOTIFICATION_TYPE] = set()
        self._pending_lock = threading.Lock()  # broadcast() is also called from the scanner thread
        self._flush_scheduled = False

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Called once at startup with the main event loop, which owns the WebSocket connections."""
        self._loop = loop

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, message: Notification) -> None:
        """Queue a notification. Safe to call from any thread or event loop. Same types are coalesced."""
        if self._loop is None:  # not started via the app lifespan (e.g. scripts): send right away
            await self._send(message)
            return

        with self._pending_lock:
            self._pending.add(message.type)
            if self._flush_scheduled:
                return
            self._flush_scheduled = True
        self._loop.call_soon_threadsafe(self._loop.call_later, COALESCE_SECONDS, self._start_flush)

    def _start_flush(self) -> None:
        asyncio.ensure_future(self._flush())

    async def _flush(self) -> None:
        with self._pending_lock:
            types = sorted(self._pending)
            self._pending.clear()
            self._flush_scheduled = False
        for notification_type in types:
            await self._send(Notification(type=notification_type))

    async def _send(self, message: Notification) -> None:
        async with self._lock:
            clients = list(self._clients)

        dead: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_text(message.model_dump_json())
            except Exception:
                log.exception("Unable to send data")
                dead.append(client)

        if dead:
            async with self._lock:
                for client in dead:
                    self._clients.discard(client)

ws_manager = WSManager()
