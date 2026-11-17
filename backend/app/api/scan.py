from fastapi import APIRouter, HTTPException, Request
from app.scanner.jobs import ScanJob

router = APIRouter(prefix="/api/scan")

@router.post("/start")
async def start_scan(request: Request, library_id: int | None = None, ignore_existing_metadata: bool = False, movie_id: int | None = None, force_cleanup: bool = False, reset_metadata: bool = False):
    """reset_metadata (needs library_id): rebuild, i.e. forget all scraped/folder metadata of the library, then scan it."""
    if reset_metadata and (library_id is None or movie_id is not None):
        raise HTTPException(status_code=400, detail="reset_metadata needs a library_id (and no movie_id)")
    scanner = request.app.state.scanner
    scanner.submit(ScanJob(library_id=library_id, ignore_existing_metadata=ignore_existing_metadata, movie_id=movie_id, force_cleanup=force_cleanup, reset_metadata=reset_metadata))
    return {"status": "scan queued"}

@router.get("/status")
async def scan_status(request: Request):
    scanner = request.app.state.scanner
    job = scanner.current_job
    return {
        "running": scanner.pending_jobs > 0,
        "pending_jobs": scanner.pending_jobs,
        "library_id": job.library_id if job else None,
        "movie_id": job.movie_id if job else None,
    }
