import asyncio
import threading

from app.scanner.jobs import ScanJob
from app.scanner.scan import scan_libraries

import logging
log = logging.getLogger(__name__)

from app.scanner.cleanup import cleanup_orphaned_posters, cleanup_orphaned_movies, cleanup_orphaned_collections, cleanup_orphaned_people

class ScannerWorker:
    def __init__(self):
        self.queue: asyncio.Queue[ScanJob] = asyncio.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.loop: asyncio.AbstractEventLoop | None = None
        # For /api/scan/status. Changed from the API thread (submit) and the worker thread.
        self._lock = threading.Lock()
        self.pending_jobs: int = 0                  # queued + running
        self.current_job: ScanJob | None = None

    def start(self):
        self.thread.start()

    def submit(self, job: ScanJob):
        if not self.loop:
            raise RuntimeError("Scanner worker not started")
        with self._lock:
            self.pending_jobs += 1
        asyncio.run_coroutine_threadsafe(self.queue.put(job), self.loop)

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._worker_loop())

    async def _run_cleanup(self, name: str, cleanup):
        """One failing cleanup must not skip the others."""
        try:
            await cleanup()
        except Exception:
            log.exception(f"Cleanup of {name} failed: ")

    async def _worker_loop(self):
        while True:
            job = await self.queue.get()
            self.current_job = job
            try:
                try:
                    await scan_libraries(job)
                except Exception:
                    log.exception("Scanner Error: ")

                # Cleanups run even when the scan failed halfway. They don't depend on it: the movie cleanup
                # checks the files itself and has its own guards (missing mount, too many files gone at once).
                await self._run_cleanup("orphaned movies", lambda: cleanup_orphaned_movies(force=job.force_cleanup))
                await self._run_cleanup("orphaned collections", cleanup_orphaned_collections)    # collections without movies
                await self._run_cleanup("orphaned people", cleanup_orphaned_people)              # people without movies
                await self._run_cleanup("orphaned posters", cleanup_orphaned_posters)            # last: needs the final DB state
            finally:
                self.current_job = None
                with self._lock:
                    self.pending_jobs = max(0, self.pending_jobs - 1)
                self.queue.task_done()