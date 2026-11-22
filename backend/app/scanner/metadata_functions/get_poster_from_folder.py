from pathlib import Path
from typing import Optional
from app.scanner.metadata_functions.get_poster_from_url import save_poster_image

import logging
log = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

def find_image_in_folder(folder_path: Path, candidate_names: list[str]) -> Optional[Path]:
    """First image in the folder whose name (without extension, any case) is one of candidate_names."""
    for path in sorted(Path(folder_path).iterdir()):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS and path.stem.lower() in candidate_names:
            return path
    return None

def get_poster_from_folder(folder_path: Path, candidate_names:list[str]) -> Optional[str]:
    image = find_image_in_folder(folder_path, candidate_names)
    return get_poster_from_file_name(image) if image else None

def get_poster_from_file_name(file_name: Path) -> Optional[str]:
    if not file_name.is_file():
        return None
    try:
        return save_poster_image(file_name.read_bytes(), source=str(file_name))
    except Exception:
        log.exception(f"Could not read the image {file_name}")
        return None
