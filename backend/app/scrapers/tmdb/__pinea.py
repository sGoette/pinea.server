"""pinea scraper for The Movie Database (https://www.themoviedb.org).

Copy this file and __pinea.json into a media folder. Every video below that folder uses it
(unless a closer folder has its own scraper). Put your TMDB API key below.

Movies:  the title (and year) come from the file name, e.g.
             Casino Royale (2006).mp4, Casino.Royale.2006.1080p.BluRay.mkv
Series:  (library type SERIES) the show comes from the file name before SxxEyy, or from the
         folder above "Season 1", e.g.  The Simpsons/Season 1/S01E02 Homer.mp4
IDs:     a TMDB or IMDb id in the file name skips the search:
             Casino Royale {tmdb-36557}.mp4, [tmdbid-36557], Casino Royale-tt0381061.mp4

This product uses the TMDB API but is not endorsed or certified by TMDB.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import re
import time

import requests

from app.models.metadata import Metadata, PersonMetadata, SearchResult, SerieData
from app.models.collection import CollectionData
from app.models.library import Library, LIBRARY_TYPE
from app.models.person import ROLE

import logging
log = logging.getLogger(__name__)

# --- Settings ---------------------------------------------------------------------------------

# API key (v3) or API read access token (v4, starts with "eyJ"): https://www.themoviedb.org/settings/api
TMDB_API_KEY = ""

# Language of titles and posters, e.g. "en-US", "de-DE", "de-CH", "fr-FR"
LANGUAGE = "en-US"

# Number of actors stored per movie / episode (in billing order)
MAX_CAST = 20

# Number of search hits shown in the web UI
MAX_SEARCH_RESULTS = 20

# TMDB names collections "James Bond Collection". True stores "James Bond".
STRIP_COLLECTION_SUFFIX = True

INCLUDE_ADULT = False

# ----------------------------------------------------------------------------------------------

API_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/"
POSTER_SIZE = "w780"          # stored posters (the server scales to max 1200 px)
PROFILE_SIZE = "h632"         # people
THUMBNAIL_SIZE = "w342"       # search hits in the web UI
STILL_SIZE = "w780"           # episode stills (16:9)

_session = requests.Session()

# --- Public scraper interface -----------------------------------------------------------------

def search(absolute_path: Path, library: Library, query: Optional[str] = None) -> list[SearchResult]:
    """Search hits for a file, best first. `query` (manual search from the web UI) replaces the
    title from the file name. For series the season/episode always come from the file."""
    is_series = library.type == LIBRARY_TYPE.SERIES
    season, episode = _parse_episode(absolute_path) if is_series else (None, None)
    episode_suffix = f"/{season}/{episode}" if season is not None and episode is not None else ""

    source = query if query else absolute_path.stem

    # Explicit ids
    tmdb_id = _find_tmdb_id(source)
    if tmdb_id:
        return [_details_as_search_result("tv" if is_series else "movie", tmdb_id, episode_suffix)]

    imdb_id = _find_imdb_id(source)
    if imdb_id:
        found = _get(f"/find/{imdb_id}", external_source="imdb_id")
        hits = found.get("tv_results" if is_series else "movie_results") or []
        if hits:
            return [_search_result("tv" if is_series else "movie", hit, episode_suffix) for hit in hits]
        episode_hits = found.get("tv_episode_results") or [] if is_series else []
        if episode_hits:
            hit = episode_hits[0]
            return [_details_as_search_result("tv", hit["show_id"], f"/{hit['season_number']}/{hit['episode_number']}")]

    if is_series:
        candidates = [query] if query else [_series_title_from_path(absolute_path)]
    else:
        candidates = [query] if query else [absolute_path.stem]

    for candidate in candidates:
        title, year = _parse_title_and_year(candidate or "")
        if not title:
            continue
        results = _search("tv" if is_series else "movie", title, year, episode_suffix)
        if results:
            return results[:MAX_SEARCH_RESULTS]

    return []

def fetch_metadata(search_result: SearchResult, potential_collections: list[str]) -> Optional[Metadata]:
    parts = search_result.id.split("/")
    kind = parts[0]

    if kind == "movie" and len(parts) == 2:
        return _movie_metadata(int(parts[1]), potential_collections)

    if kind == "tv" and len(parts) in (2, 4):
        show_id = int(parts[1])
        season = int(parts[2]) if len(parts) == 4 else None
        episode = int(parts[3]) if len(parts) == 4 else None
        return _episode_metadata(show_id, season, episode)

    log.warning(f"[TMDB] Unknown search result id {search_result.id}")
    return None

# --- TMDB requests ----------------------------------------------------------------------------

def _get(path: str, **params) -> dict:
    key = TMDB_API_KEY.strip()
    if not key:
        raise RuntimeError(f"TMDB_API_KEY is not set in {__file__}")

    headers = { "accept": "application/json" }
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"
    else:
        params["api_key"] = key
    params.setdefault("language", LANGUAGE)

    for attempt in range(3):
        response = _session.get(API_URL + path, params=params, headers=headers, timeout=20)
        if response.status_code == 429 and attempt < 2:
            # Rate limited (~50 requests/s): wait and retry
            try:
                time.sleep(min(float(response.headers.get("Retry-After", "1")), 10))
            except ValueError:
                time.sleep(1)
            continue
        response.raise_for_status()
        return response.json()
    return {}

def _search(kind: str, title: str, year: Optional[int], episode_suffix: str) -> list[SearchResult]:
    params: dict = { "query": title, "include_adult": str(INCLUDE_ADULT).lower() }
    hits: list[dict] = []
    if year:
        params["primary_release_year" if kind == "movie" else "first_air_date_year"] = year
        hits = _get(f"/search/{kind}", **params).get("results") or []
        params.pop("primary_release_year", None)
        params.pop("first_air_date_year", None)
    if not hits:
        hits = _get(f"/search/{kind}", **params).get("results") or []

    # TMDB sorts by relevance and popularity. Move exact title matches (+ matching year) to the top.
    wanted = _normalize(title)
    def rank(hit: dict) -> int:
        names = { _normalize(hit.get("title") or hit.get("name") or ""), _normalize(hit.get("original_title") or hit.get("original_name") or "") }
        score = 0
        if wanted in names:
            score += 2
        if year and _year_of(hit.get("release_date") or hit.get("first_air_date")) == year:
            score += 1
        return -score
    hits = sorted(hits, key=rank)  # stable: equal scores keep TMDB's order

    return [_search_result(kind, hit, episode_suffix) for hit in hits]

def _details_as_search_result(kind: str, tmdb_id: int, episode_suffix: str) -> SearchResult:
    return _search_result(kind, _get(f"/{kind}/{tmdb_id}"), episode_suffix)

def _search_result(kind: str, hit: dict, episode_suffix: str) -> SearchResult:
    name = hit.get("title") or hit.get("name") or ""
    original_name = hit.get("original_title") or hit.get("original_name")
    return SearchResult(
        id=f"{kind}/{hit['id']}" + (episode_suffix if kind == "tv" else ""),
        name=name,
        original_name=original_name if original_name and original_name != name else None,
        release_date=_unix_date(hit.get("release_date") or hit.get("first_air_date")),
        poster_url=_image(hit.get("poster_path"), THUMBNAIL_SIZE),
        overview=hit.get("overview") or None,
    )

def _movie_metadata(movie_id: int, potential_collections: list[str]) -> Metadata:
    movie = _get(f"/movie/{movie_id}", append_to_response="credits")
    credits = movie.get("credits") or {}
    genres = [genre["name"] for genre in movie.get("genres") or []]

    collections: list[CollectionData] = []
    tmdb_collection = movie.get("belongs_to_collection")
    if tmdb_collection and tmdb_collection.get("name"):
        collections.append(CollectionData(title=_collection_title(tmdb_collection["name"]), poster_url=_image(tmdb_collection.get("poster_path"), POSTER_SIZE)))

    # potential_collections (from __pinea.json): genres with one of these names become collections
    genres_lower = { genre.lower() for genre in genres }
    for name in potential_collections:
        if name.lower() in genres_lower:
            collections.append(CollectionData(title=name))

    return Metadata(
        movie_title=movie.get("title"),
        release_date=_unix_date(movie.get("release_date")),
        poster_url=_image(movie.get("poster_path"), POSTER_SIZE),
        genres=genres,
        collections=collections,
        people=_people(cast=credits.get("cast") or [], crew=credits.get("crew") or []),
    )

def _episode_metadata(show_id: int, season: Optional[int], episode: Optional[int]) -> Metadata:
    show = _get(f"/tv/{show_id}")
    show_poster = _image(show.get("poster_path"), POSTER_SIZE)
    metadata = Metadata(
        serie=SerieData(title=show.get("name") or "", poster_url=show_poster),
        genres=[genre["name"] for genre in show.get("genres") or []],
        poster_url=show_poster,
    )
    if season is None or episode is None:
        return metadata

    metadata.season = str(season)
    metadata.episode = episode

    # Posters are 2:3 in the clients: use the season poster, not the (16:9) episode still
    season_info = next((s for s in show.get("seasons") or [] if s.get("season_number") == season), None)
    if season_info and season_info.get("poster_path"):
        metadata.poster_url = _image(season_info["poster_path"], POSTER_SIZE)

    try:
        details = _get(f"/tv/{show_id}/season/{season}/episode/{episode}", append_to_response="credits")
    except requests.HTTPError:
        log.warning(f"[TMDB] Episode S{season}E{episode} of show {show_id} not found")
        return metadata

    credits = details.get("credits") or {}
    guests = credits.get("guest_stars") or details.get("guest_stars") or []
    metadata.movie_title = details.get("name")
    metadata.still_url = _image(details.get("still_path"), STILL_SIZE)
    metadata.release_date = _unix_date(details.get("air_date"))
    metadata.people = _people(cast=credits.get("cast") or [], guests=guests, crew=credits.get("crew") or details.get("crew") or [])
    return metadata

def _people(cast: list[dict], crew: list[dict], guests: list[dict] = []) -> list[PersonMetadata]:
    """Actors in billing order (cast first, then guest stars), then the directors."""
    by_order = lambda member: member.get("order", 9999)
    people: list[PersonMetadata] = []
    seen: set[int] = set()
    for member in sorted(cast, key=by_order) + sorted(guests, key=by_order):
        if len(people) >= MAX_CAST:
            break
        if member.get("id") in seen or not member.get("name"):
            continue
        seen.add(member["id"])
        people.append(PersonMetadata(
            name=member["name"],
            character=member.get("character") or None,
            sort_order=len(people),
            role=ROLE.ACTOR,
            poster_url=_image(member.get("profile_path"), PROFILE_SIZE),
        ))

    for member in crew:
        if member.get("job") == "Director" and member.get("name"):
            people.append(PersonMetadata(
                name=member["name"],
                role=ROLE.DIRECTOR,
                poster_url=_image(member.get("profile_path"), PROFILE_SIZE),
            ))
    return people

# --- Helpers ----------------------------------------------------------------------------------

_RELEASE_TAGS = re.compile(
    r"\b(2160p|1080p|1080i|720p|576p|480p|uhd|hdr10|bluray|blu-ray|bdrip|brrip|webrip|web-dl|webdl|hdtv|dvdrip|remux|"
    r"x264|x265|h264|h265|hevc|avc|aac|ac3|dts|atmos|truehd|10bit|proper|repack|extended|unrated|directors\.?cut|imax)\b.*$",
    re.IGNORECASE)
_YEAR = re.compile(r"(?<=[\s._\-(\[])((?:19|20)\d{2})(?=$|[\s._\-)\]])")
_EPISODE = re.compile(r"[Ss](\d{1,2})[\s._-]*[Ee](\d{1,3})|\b(\d{1,2})x(\d{2,3})\b")
_SEASON_FOLDER = re.compile(r"^(season|staffel|saison|temporada|stagione|s)[\s._-]*(\d{1,2})$", re.IGNORECASE)

def _find_tmdb_id(text: str) -> Optional[int]:
    match = re.search(r"tmdb(?:id)?[-=\s:]?(\d+)", text, re.IGNORECASE)
    return int(match.group(1)) if match else None

def _find_imdb_id(text: str) -> Optional[str]:
    match = re.search(r"\b(tt\d{7,8})\b", text) or re.search(r"(tt\d{7,8})", text)
    return match.group(1) if match else None

def _parse_title_and_year(text: str) -> tuple[str, Optional[int]]:
    text = re.sub(r"\{[^}]*\}|\[[^\]]*\]", " ", text)         # {tmdb-1}, [1080p], ...
    text = re.sub(r"-(trailer|behindthescenes|makingoff)$", "", text, flags=re.IGNORECASE)
    if text.count(" ") == 0 and ("." in text or "_" in text):
        text = re.sub(r"[._]", " ", text)                      # Casino.Royale.2006
    text = _RELEASE_TAGS.sub("", text)

    # The last plausible year: "Blade Runner 2049 (2017)", "2001 A Space Odyssey 1968".
    # A year at the very start is part of the title ("1917", "2012").
    year: Optional[int] = None
    max_year = datetime.now().year + 2
    for match in reversed(list(_YEAR.finditer(text))):
        candidate = int(match.group(1))
        if candidate <= max_year:
            year = candidate
            text = text[:match.start()]
            break

    title = re.sub(r"[\s._\-(]+$", "", text).strip()
    title = re.sub(r"\s+", " ", title)
    return title, year

def _parse_episode(path: Path) -> tuple[Optional[int], Optional[int]]:
    match = _EPISODE.search(path.stem)
    if match:
        if match.group(1):
            return int(match.group(1)), int(match.group(2))
        return int(match.group(3)), int(match.group(4))

    # "Season 2/E05 Title.mp4", "Season 2/05 Title.mp4"
    season_match = _SEASON_FOLDER.match(path.parent.name)
    episode_match = re.match(r"^(?:e|ep|episode)?[\s._-]*(\d{1,3})\b", path.stem, re.IGNORECASE)
    if season_match and episode_match:
        return int(season_match.group(2)), int(episode_match.group(1))
    return None, None

def _series_title_from_path(path: Path) -> str:
    match = _EPISODE.search(path.stem)
    if match:
        before = path.stem[:match.start()]
        title, _ = _parse_title_and_year(before)
        if len(title) > 1:
            return before

    folder = path.parent
    if _SEASON_FOLDER.match(folder.name):
        folder = folder.parent
    return folder.name

def _normalize(text: str) -> str:
    return re.sub(r"[^\w]+", "", text.lower())

def _collection_title(name: str) -> str:
    if STRIP_COLLECTION_SUFFIX:
        name = re.sub(r"\s*(-\s*)?(collection|filmreihe|saga)$", "", name, flags=re.IGNORECASE).strip() or name
    return name

def _image(path: Optional[str], size: str) -> Optional[str]:
    return f"{IMAGE_URL}{size}{path}" if path else None

def _unix_date(date: Optional[str]) -> Optional[int]:
    if not date:
        return None
    try:
        return int(datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        return None

def _year_of(date: Optional[str]) -> Optional[int]:
    return int(date[:4]) if date and len(date) >= 4 and date[:4].isdigit() else None
