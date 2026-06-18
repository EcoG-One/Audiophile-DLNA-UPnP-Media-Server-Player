import os
import pathlib
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MUSIC_LIBRARY_BASE = os.path.expanduser("~/.audiophile_server/artist_art")
FANART_API_KEY = "FANART_TV_CLIENT_API_KEY"
USER_AGENT = "AudiofileDLNAServer/1.0.0 ( ecog@outlook.de )"

# Serve the music directory statically so React can load the saved local images directly
# e.g., http://localhost:8080/media/Daft Punk/fanart.jpg
MUSIC_LIBRARY_BASE.mkdir(exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MUSIC_LIBRARY_BASE)), name="media")


def get_musicbrainz_id(artist_name: str) -> str:
    """Queries MusicBrainz to find a reliable unique ID for the artist."""
    url = "https://musicbrainz.org"
    headers = {"User-Agent": USER_AGENT}
    params = {"query": artist_name, "fmt": "json", "limit": 1}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="MusicBrainz API connection failed")
    
    data = response.json()
    if not data.get("artists"):
        raise HTTPException(status_code=404, detail=f"Artist '{artist_name}' not found")
    return data["artists"]["id"]


def download_file(url: str, destination_path: pathlib.Path):
    """Downloads a binary image asset from a URL and saves it to disk safely."""
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True)
        if response.status_code == 200:
            with open(destination_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
    except Exception as e:
        print(f"Failed to download asset {url}: {e}")


@app.get("/api/artist/assets")
def get_artist_assets(name: str):
    """
    Checks the local folder structure first. If image assets (fanart, logo, thumb)
    do not exist locally, it queries APIs, downloads them, and saves them to disk.
    """
    # Create standardized folder structure: .../MusicLibrary/Artist Name/
    artist_folder = MUSIC_LIBRARY_BASE / name
    artist_folder.mkdir(exist_ok=True)

    # Standardized filenames matching media manager convention
    local_files = {
        "background": {"file": "fanart.jpg", "path": artist_folder / "fanart.jpg"},
        "thumbnail": {"file": "folder.jpg", "path": artist_folder / "folder.jpg"},
        "logo": {"file": "logo.png", "path": artist_folder / "logo.png"}
    }

    # Check what is missing locally
    missing_assets = [key for key, val in local_files.items() if not val["path"].exists()]

    # If everything is stored locally, return local relative URLs immediately
    if not missing_assets:
        return {
            "source": "local_cache",
            "background": f"http://localhost:8080/media/{name}/fanart.jpg",
            "thumbnail": f"http://localhost:8080/media/{name}/folder.jpg",
            "logo": f"http://localhost:8080/media/{name}/logo.png"
        }

    # Fetch data remotely for whatever is missing
    try:
        mbid = get_musicbrainz_id(name)
        fanart_url = f"https://fanart.tv{mbid}"
        fanart_resp = requests.get(fanart_url, params={"api_key": FANART_API_KEY})

        if fanart_resp.status_code == 200:
            api_data = fanart_resp.json()

            # Map the Fanart.tv payload arrays to our missing local structures
            if "background" in missing_assets and api_data.get("artistbackground"):
                download_file(api_data["artistbackground"]["url"], local_files["background"]["path"])

            if "thumbnail" in missing_assets and api_data.get("artistthumb"):
                download_file(api_data["artistthumb"]["url"], local_files["thumbnail"]["path"])

            if "logo" in missing_assets:
                logos = api_data.get("hdmusiclogo") or api_data.get("musiclogo")
                if logos:
                    download_file(logos["url"], local_files["logo"]["path"])

    except Exception as network_error:
        # If the network or API fails, still try to render what we have locally
        print(f"Network asset discovery failed: {network_error}")

    # Final pass: Build the response URLs using local files (or fallback to empty strings if both lookups failed)
    return {
        "source": "api_fetched_and_cached" if missing_assets else "local_cache",
        "background": f"http://localhost:8080/media/{name}/fanart.jpg" if local_files["background"]["path"].exists() else "",
        "thumbnail": f"http://localhost:8080/media/{name}/folder.jpg" if local_files["thumbnail"]["path"].exists() else "",
        "logo": f"http://localhost:8080/media/{name}/logo.png" if local_files["logo"]["path"].exists() else ""
    }
