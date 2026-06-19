import os
import pathlib
import requests
import time
import re
import urllib.parse
import sqlite3
import logging

# Configuration
MUSIC_LIBRARY_BASE = pathlib.Path(os.path.expanduser("~/.audiophile_server/artist_art"))
DB_PATH = MUSIC_LIBRARY_BASE.parent / "mbid_cache.db"
FANART_API_KEY = os.getenv("FANART_TV_PROJECT_API_KEY")
FANART_CLIENT_API_KEY = os.getenv("FANART_TV_CLIENT_API_KEY")
USER_AGENT = "AudiophileDLNAServer/1.0.0 ( ecog@outlook.de )"
_MB_ROOT = "https://musicbrainz.org/ws/2/artist/"

REQUEST_DELAY = 1.2
_RETRY_STATUSES = {429, 502, 503, 504}
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0

MUSIC_LIBRARY_BASE.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ArtistArtCache")


# --- DATABASE INIT ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mbid_cache (
                artist_name TEXT PRIMARY KEY,
                mbid TEXT NOT NULL,
                created_at REAL,
                last_accessed REAL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mbid_accessed ON mbid_cache(last_accessed)"
        )


init_db()


def sanitize_filename(filename: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", filename)


def get_musicbrainz_id(artist_name: str) -> str:
    """Cache-first MusicBrainz ID lookup."""
    now = time.time()

    # 1. Check Local SQLite Cache
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT mbid FROM mbid_cache WHERE artist_name = ?", (artist_name,)
        )
        row = cursor.fetchone()
        if row:
            # Update last accessed timestamp
            cursor.execute(
                "UPDATE mbid_cache SET last_accessed = ? WHERE artist_name = ?",
                (now, artist_name),
            )
            logger.info(f"CACHE HIT: MBID for '{artist_name}' -> {row[0]}")
            return row[0]

    # 2. Cache Miss: Fetch from API with Retry Logic
    logger.info(f"CACHE MISS: Querying MusicBrainz for '{artist_name}'...")
    for attempt in range(1, _MAX_RETRIES + 1):
        time.sleep(REQUEST_DELAY)  # Rate limit compliance
        try:
            response = requests.get(
                _MB_ROOT,
                headers={"User-Agent": USER_AGENT},
                params={"query": artist_name, "fmt": "json", "limit": 1},
            )

            if response.status_code in _RETRY_STATUSES:
                logger.warning(
                    f"MB API {response.status_code}. Retrying ({attempt}/{_MAX_RETRIES})..."
                )
                time.sleep(_BACKOFF_BASE**attempt)
                continue

            response.raise_for_status()
            data = response.json()

            if not data.get("artists"):
                raise ValueError(f"Artist '{artist_name}' not found.")

            mbid = data["artists"][0]["id"]

            # 3. Store in Cache
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO mbid_cache (artist_name, mbid, created_at, last_accessed) VALUES (?, ?, ?, ?)",
                    (artist_name, mbid, now, now),
                )
            return mbid

        except Exception as e:
            if attempt == _MAX_RETRIES:
                logger.error(f"Failed to fetch MBID for '{artist_name}': {e}")
                raise


def download_file(url: str, destination_path: pathlib.Path):
    temp_path = destination_path.with_suffix(".tmp")
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True)
        response.raise_for_status()
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        temp_path.rename(destination_path)
    except Exception as e:
        logger.error(f"Failed to download asset {url}: {e}")
        if temp_path.exists():
            temp_path.unlink()


def get_artist_assets(name: str):
    """Retrieves artist assets, downloading them if they don't exist locally."""
    safe_name = sanitize_filename(name)
    artist_folder = MUSIC_LIBRARY_BASE / safe_name
    artist_folder.mkdir(parents=True, exist_ok=True)

    local_files = {
        "background": {"file": "fanart.jpg", "path": artist_folder / "fanart.jpg"},
        "thumbnail": {"file": "folder.jpg", "path": artist_folder / "folder.jpg"},
        "logo": {"file": "logo.png", "path": artist_folder / "logo.png"},
    }

    missing_assets = [
        key for key, val in local_files.items() if not val["path"].exists()
    ]
    url_safe_name = urllib.parse.quote(safe_name)

    if missing_assets:
        try:
            artist_id = get_musicbrainz_id(name)
            fanart_url = f"https://webservice.fanart.tv/v3.2/music/{artist_id}"
            fanart_resp = requests.get(fanart_url, params={"api_key": FANART_API_KEY})

            if fanart_resp.status_code == 200:
                api_data = fanart_resp.json()
                if "background" in missing_assets and api_data.get("artistbackground"):
                    download_file(
                        api_data["artistbackground"][0]["url"],
                        local_files["background"]["path"],
                    )
                if "thumbnail" in missing_assets and api_data.get("artistthumb"):
                    download_file(
                        api_data["artistthumb"][0]["url"],
                        local_files["thumbnail"]["path"],
                    )
                if "logo" in missing_assets:
                    logos = api_data.get("hdmusiclogo") or api_data.get("musiclogo")
                    if logos and isinstance(logos, list):
                        download_file(logos[0]["url"], local_files["logo"]["path"])
        except Exception as e:
            logger.error(f"Asset discovery failed for '{name}': {e}")

    # Return relative URLs to be handled by the frontend proxy
    return {
        "source": "api_fetched_and_cached" if missing_assets else "local_cache",
        "background": (
            f"/artist-art/{url_safe_name}/fanart.jpg"
            if local_files["background"]["path"].exists()
            else ""
        ),
        "thumbnail": (
            f"/artist-art/{url_safe_name}/folder.jpg"
            if local_files["thumbnail"]["path"].exists()
            else ""
        ),
        "logo": (
            f"/artist-art/{url_safe_name}/logo.png"
            if local_files["logo"]["path"].exists()
            else ""
        ),
    }
