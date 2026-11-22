import requests
from typing import Optional
from PIL import Image, ImageOps
from io import BytesIO

import logging
log = logging.getLogger(__name__)

from app.scanner.media import get_file_hash
from app.config import POSTER_DIR

def save_poster_image(data: bytes, source: str) -> str:
    """Stores image bytes as a poster in POSTER_DIR (max 1200 px, JPEG) and returns its file name.
    Raises an exception (PIL.UnidentifiedImageError, OSError, ...) when the data isn't a readable image."""
    poster_file_name = f"{get_file_hash(source)}.jpg"
    with Image.open(BytesIO(data)) as img:
        img = ImageOps.exif_transpose(img)  # photos from phones are often rotated via EXIF only
        img.thumbnail((1200, 1200))
        img.convert('RGB').save(POSTER_DIR / poster_file_name, format="JPEG", quality=100)
    return poster_file_name

def get_poster_from_url(url: str) -> Optional[str]:
    try: 
        response = requests.get(url)
        response.raise_for_status()

        return save_poster_image(response.content, source=url)
    except requests.HTTPError as error:
        # Missing images (404 etc.) are normal for optional pictures like people photos
        log.warning(f"Poster not loaded, HTTP {error.response.status_code if error.response is not None else '?'}: {url}")
        return None
    except Exception:
        log.exception("Error loading poster from URL: ")
        return None