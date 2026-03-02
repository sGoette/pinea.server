import requests
from typing import Optional
from PIL import Image
from io import BytesIO

import logging
log = logging.getLogger(__name__)

from app.scanner.media import get_file_hash
from app.config import POSTER_DIR

def get_poster_from_url(url: str) -> Optional[str]:
    try: 
        response = requests.get(url)
        response.raise_for_status()

        poster_file_name = f"{get_file_hash(str(url))}.jpg"
        target = POSTER_DIR / poster_file_name

        with Image.open(BytesIO(response.content)) as img:
            img.thumbnail((1200, 1200))
            img.convert('RGB')
            img.save(target, format="JPEG", quality=100)
        return poster_file_name
    except Exception:
        log.exception("Error loading poster from URL: ")
        return None