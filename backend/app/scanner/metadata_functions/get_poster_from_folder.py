from pathlib import Path
from typing import Optional
from PIL import Image

from app.scanner.media import get_file_hash
from app.config import POSTER_DIR

import logging
log = logging.getLogger(__name__)

def get_poster_from_folder(folder_path: Path, candidate_names:list[str]) -> Optional[str]:
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
    for path in Path(folder_path).iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS and path.stem.lower() in candidate_names:
            return get_poster_from_file_name(path)
    
    return None

def get_poster_from_file_name(file_name: Path) -> Optional[str]:
    log.warning(file_name)
    if file_name.is_file():
        poster_file_name = f"{get_file_hash(str(file_name))}.jpg"
        output_path = POSTER_DIR / poster_file_name
        with Image.open(file_name) as img:
            img.thumbnail((1200, 1200))
            rgb_im = img.convert('RGB')
            rgb_im.save(output_path, format='JPEG', quality=100)
            return poster_file_name
    
    return None