"""
Self-update from the GitHub "main-build" release, which CI publishes on every commit to main
(.github/workflows/build-main.yml).

Install flow:
  1. GET <UPDATE_BASE_URL>/version.json: name, commit, sha256 of the tarball
  2. download the tarball and verify its sha256
  3. extract it into releases/<name>/ (the tarball contains exactly one top level folder <name>)
  4. create releases/<name>/.venv, pip install the requirements, sanity check
  5. write data/update/pending (path of the previous release), switch the `current` symlink
  6. SIGTERM ourselves. systemd (Restart=always) runs scripts/linux/pinea-run.sh again,
     which starts the new release.
  7. When the new release has started, finalize_pending_update() removes the pending marker.
     If it fails to start 3 times in a row, pinea-run.sh points `current` back at the previous
     release and writes data/update/rolled_back.

Only works on a Linux install made by scripts/linux/install.sh (releases/ + current symlink).
"""
import asyncio
import hashlib
import json
import os
import re
import shutil
import signal
import sys
import tarfile
import time
from collections import deque
from pathlib import Path
from typing import Optional

import requests

from app.config import (
    BASE_DIR, VERSION_FILE, RELEASES_DIR, CURRENT_LINK, UPDATE_STATE_DIR,
    UPDATE_BASE_URL, UPDATE_TARBALL_NAME, UPDATE_VERSION_NAME,
)
from app.models.update import VersionInfo, UpdateStatus, UpdateResult, UPDATE_STATE

import logging
log = logging.getLogger(__name__)

KEEP_RELEASES = 3   # current + 2 older ones for manual rollback
RELEASE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
BUSY_STATES = {UPDATE_STATE.CHECKING, UPDATE_STATE.DOWNLOADING, UPDATE_STATE.INSTALLING, UPDATE_STATE.RESTARTING}

PENDING_FILE = UPDATE_STATE_DIR / "pending"
ATTEMPTS_FILE = UPDATE_STATE_DIR / "attempts"
ROLLED_BACK_FILE = UPDATE_STATE_DIR / "rolled_back"
LAST_RESULT_FILE = UPDATE_STATE_DIR / "last_result.json"


class UpdateError(Exception):
    pass


class Updater:
    def __init__(self) -> None:
        self.state: UPDATE_STATE = UPDATE_STATE.IDLE
        self.message: Optional[str] = None
        self.log: deque[str] = deque(maxlen=200)
        self.latest: Optional[VersionInfo] = None
        self.last_checked: Optional[int] = None
        self.last_result: Optional[UpdateResult] = None
        self._task: Optional[asyncio.Task] = None

    # ---------- status ----------

    def current_version(self) -> Optional[VersionInfo]:
        try:
            return VersionInfo(**json.loads(VERSION_FILE.read_text(encoding="utf-8")))
        except Exception:
            return None # dev checkout or a release built before VERSION.json existed

    def unsupported_reason(self) -> Optional[str]:
        if not sys.platform.startswith("linux") and os.environ.get("PINEA_UPDATER_ENABLED") != "1":
            return "Self-update is only available on Linux installs."
        if not CURRENT_LINK.is_symlink() or not RELEASES_DIR.is_dir():
            return "Not an installed server (no releases/ folder or 'current' symlink). Use git in development."
        if not CURRENT_LINK.resolve().is_relative_to(RELEASES_DIR.resolve()):
            return "The 'current' symlink does not point into releases/."
        if not os.access(RELEASES_DIR, os.W_OK) or not os.access(BASE_DIR, os.W_OK):
            return "The server user has no write access to the install folder."
        return None

    def update_available(self) -> bool:
        if self.latest is None:
            return False
        current = self.current_version()
        return current is None or current.commit != self.latest.commit

    def status(self) -> UpdateStatus:
        reason = self.unsupported_reason()
        return UpdateStatus(
            supported=reason is None,
            unsupported_reason=reason,
            current=self.current_version(),
            latest=self.latest,
            update_available=self.update_available(),
            last_checked=self.last_checked,
            state=self.state,
            message=self.message,
            log=list(self.log),
            last_result=self.last_result,
        )

    def _set_state(self, state: UPDATE_STATE, message: Optional[str] = None) -> None:
        self.state = state
        self.message = message
        if message:
            self.log.append(message)
            log.info(f"[Updater] {message}")

    # ---------- check ----------

    async def check(self) -> UpdateStatus:
        if self.state in BUSY_STATES:
            return self.status()

        self._set_state(UPDATE_STATE.CHECKING)
        try:
            self.latest = await asyncio.to_thread(self._fetch_latest)
            self.last_checked = int(time.time())
            self._set_state(UPDATE_STATE.IDLE)
        except Exception as e:
            log.exception("[Updater] Update check failed")
            self._set_state(UPDATE_STATE.ERROR, f"Update check failed: {e}")
        return self.status()

    def _fetch_latest(self) -> VersionInfo:
        response = requests.get(f"{UPDATE_BASE_URL}/{UPDATE_VERSION_NAME}", timeout=15, headers={"Cache-Control": "no-cache"})
        if response.status_code == 404:
            raise UpdateError("No published build found.")
        response.raise_for_status()

        latest = VersionInfo(**response.json())
        if not latest.commit or not latest.sha256 or not RELEASE_NAME_RE.match(latest.name):
            raise UpdateError("The published version.json is incomplete or invalid.")
        return latest

    # ---------- install ----------

    async def start_install(self) -> UpdateStatus:
        reason = self.unsupported_reason()
        if reason:
            raise UpdateError(reason)
        if self.state in BUSY_STATES or (self._task and not self._task.done()):
            raise UpdateError("An update is already running.")

        await self.check()
        if self.state == UPDATE_STATE.ERROR:
            raise UpdateError(self.message or "Update check failed.")
        if not self.update_available() or self.latest is None:
            raise UpdateError("Already up to date.")

        self.log.clear()
        self._set_state(UPDATE_STATE.DOWNLOADING, f"Downloading {self.latest.name}")
        self._task = asyncio.create_task(self._install(self.latest))
        return self.status()

    async def _install(self, target: VersionInfo) -> None:
        tarball_path = RELEASES_DIR / f".download-{target.name}.tar.gz"
        release_dir: Optional[Path] = None
        try:
            await asyncio.to_thread(self._download, target, tarball_path)

            self._set_state(UPDATE_STATE.INSTALLING, "Extracting")
            release_dir = await asyncio.to_thread(self._extract, tarball_path, target)

            self._set_state(UPDATE_STATE.INSTALLING, "Installing Python dependencies (this can take a few minutes)")
            venv_python = release_dir / ".venv/bin/python"
            await self._run([sys.executable, "-m", "venv", str(release_dir / ".venv")])
            await self._run([str(venv_python), "-m", "pip", "install", "--disable-pip-version-check", "--no-input",
                             "-r", str(release_dir / "backend/requirements.txt")])

            self._set_state(UPDATE_STATE.INSTALLING, "Checking the new release")
            await self._run([str(venv_python), "-m", "compileall", "-q", str(release_dir / "backend/app")])
            await self._run([str(venv_python), "-c", "import fastapi, uvicorn, aiosqlite, pydantic, zeroconf, PIL, Levenshtein, requests, websockets"])

            self._activate(release_dir)
            self._set_state(UPDATE_STATE.RESTARTING, f"Restarting into {target.name}")
            # Give the UI a moment to fetch the status, then let systemd restart us into the new release.
            asyncio.get_running_loop().call_later(2, os.kill, os.getpid(), signal.SIGTERM)

        except Exception as e:
            log.exception("[Updater] Update failed")
            self._set_state(UPDATE_STATE.ERROR, f"Update failed: {e}")
            if release_dir and release_dir.exists() and release_dir.resolve() != CURRENT_LINK.resolve():
                shutil.rmtree(release_dir, ignore_errors=True)
        finally:
            tarball_path.unlink(missing_ok=True)

    def _download(self, target: VersionInfo, destination: Path) -> None:
        sha256 = hashlib.sha256()
        with requests.get(f"{UPDATE_BASE_URL}/{UPDATE_TARBALL_NAME}", stream=True, timeout=(15, 120)) as response:
            response.raise_for_status()
            with destination.open("wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
                    sha256.update(chunk)

        if sha256.hexdigest() != target.sha256:
            raise UpdateError("Checksum mismatch. A new build was probably published during the download, please try again.")

    def _extract(self, tarball_path: Path, target: VersionInfo) -> Path:
        final_dir = RELEASES_DIR / target.name
        staging_dir = RELEASES_DIR / f".staging-{target.name}"

        if final_dir.exists() and final_dir.resolve() == CURRENT_LINK.resolve():
            raise UpdateError(f"{target.name} is already the running release.")

        shutil.rmtree(staging_dir, ignore_errors=True)
        staging_dir.mkdir()
        try:
            with tarfile.open(tarball_path, "r:gz") as tar:
                members = tar.getmembers()
                top_level = {Path(m.name).parts[0] for m in members if Path(m.name).parts}
                if top_level != {target.name}:
                    raise UpdateError(f"Unexpected tarball layout: {sorted(top_level)}")

                if hasattr(tarfile, "data_filter"):
                    tar.extractall(staging_dir, filter="data")
                else:
                    for m in members: # Python without extraction filters: reject anything unusual
                        if m.name.startswith("/") or ".." in Path(m.name).parts or m.islnk() or m.issym() or m.isdev():
                            raise UpdateError(f"Unsafe tarball entry: {m.name}")
                    tar.extractall(staging_dir)

            extracted = staging_dir / target.name
            for required in ("backend/app/main.py", "backend/requirements.txt", "frontend/index.html", "VERSION.json"):
                if not (extracted / required).is_file():
                    raise UpdateError(f"Release is missing {required}")

            if final_dir.exists():
                shutil.rmtree(final_dir) # leftover of an earlier failed or rolled back attempt
            os.rename(extracted, final_dir)
            return final_dir
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

    async def _run(self, cmd: list[str]) -> None:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "PIP_NO_CACHE_DIR": "1"},
        )
        assert proc.stdout
        async for line in proc.stdout:
            text = line.decode(errors="replace").rstrip()
            if text:
                self.log.append(text)
        returncode = await proc.wait()
        if returncode != 0:
            raise UpdateError(f"Command failed with exit code {returncode}: {Path(cmd[0]).name} {' '.join(cmd[1:3])} ...")

    def _activate(self, release_dir: Path) -> None:
        previous = CURRENT_LINK.resolve()
        UPDATE_STATE_DIR.mkdir(parents=True, exist_ok=True)
        ATTEMPTS_FILE.unlink(missing_ok=True)
        ROLLED_BACK_FILE.unlink(missing_ok=True)
        PENDING_FILE.write_text(f"{previous}\n")

        tmp_link = BASE_DIR / ".current.tmp"
        tmp_link.unlink(missing_ok=True)
        os.symlink(release_dir, tmp_link)
        os.replace(tmp_link, CURRENT_LINK) # atomic switch

    # ---------- startup ----------

    def finalize_pending_update(self) -> None:
        """Called once the server has started successfully."""
        if self.unsupported_reason():
            return
        try:
            current = self.current_version()
            current_name = current.name if current else CURRENT_LINK.resolve().name

            if ROLLED_BACK_FILE.exists():
                failed_name = Path(ROLLED_BACK_FILE.read_text().strip()).name
                ROLLED_BACK_FILE.unlink()
                self._save_result(UpdateResult(success=False, version=failed_name, at=int(time.time()),
                                               message=f"{failed_name} failed to start and was rolled back to {current_name}."))
            elif PENDING_FILE.exists():
                PENDING_FILE.unlink()
                ATTEMPTS_FILE.unlink(missing_ok=True)
                self._save_result(UpdateResult(success=True, version=current_name, at=int(time.time()),
                                               message=f"Updated to {current_name}."))
                self._prune_releases()
            elif LAST_RESULT_FILE.exists():
                self.last_result = UpdateResult(**json.loads(LAST_RESULT_FILE.read_text()))
        except Exception:
            log.exception("[Updater] Could not finalize pending update")

    def _save_result(self, result: UpdateResult) -> None:
        self.last_result = result
        log.info(f"[Updater] {result.message}")
        UPDATE_STATE_DIR.mkdir(parents=True, exist_ok=True)
        LAST_RESULT_FILE.write_text(result.model_dump_json())

    def _prune_releases(self) -> None:
        current = CURRENT_LINK.resolve()
        releases = sorted(
            (d for d in RELEASES_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")),
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )
        for old in releases[KEEP_RELEASES:]:
            if old.resolve() != current:
                log.info(f"[Updater] Removing old release {old.name}")
                shutil.rmtree(old, ignore_errors=True)


updater = Updater()
