from pydantic import BaseModel
from typing import Optional
from enum import StrEnum

class VersionInfo(BaseModel):
    name: str                           # release folder name, e.g. "main-1a2b3c4"
    commit: Optional[str] = None        # full git sha
    commit_date: Optional[str] = None   # ISO 8601
    message: Optional[str] = None       # commit subject
    built_at: Optional[str] = None      # ISO 8601
    sha256: Optional[str] = None        # of the tarball (only in the published version.json)

class UPDATE_STATE(StrEnum):
    IDLE = 'IDLE'
    CHECKING = 'CHECKING'
    DOWNLOADING = 'DOWNLOADING'
    INSTALLING = 'INSTALLING'
    RESTARTING = 'RESTARTING'
    ERROR = 'ERROR'

class UpdateResult(BaseModel):
    success: bool
    version: Optional[str] = None
    message: str
    at: int                             # unix timestamp

class UpdateStatus(BaseModel):
    supported: bool
    unsupported_reason: Optional[str] = None
    current: Optional[VersionInfo] = None
    latest: Optional[VersionInfo] = None
    update_available: bool = False
    last_checked: Optional[int] = None
    state: UPDATE_STATE
    message: Optional[str] = None
    log: list[str] = []
    last_result: Optional[UpdateResult] = None
