from fastapi import APIRouter, Request
from app.scanner.jobs import ScanJob

router = APIRouter(prefix="/api/scan")

@router.post("/start")
async def start_scan(request: Request, library_id: int | None = None, ignore_existing_metadata: bool = False, movie_id: int | None = None, force_cleanup: bool = False):
    scanner = request.app.state.scanner
    scanner.submit(ScanJob(library_id=library_id, ignore_existing_metadata=ignore_existing_metadata, movie_id=movie_id, force_cleanup=force_cleanup))
    return {"status": "scan queued"}