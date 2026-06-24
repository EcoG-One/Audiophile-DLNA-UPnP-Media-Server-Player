import os
import pathlib
import requests
import hashlib
from pathlib import Path
from mutagen import File
from mutagen.flac import Picture
import time
import logging

logger = logging.getLogger("ArtworkHealer")

MUSIC_LIBRARY_BASE = pathlib.Path(os.path.expanduser("~/.audiophile_server/artist_art"))
DB_PATH = MUSIC_LIBRARY_BASE.parent / "mbid_cache.db"
FANART_API_KEY = os.getenv("FANART_TV_PROJECT_API_KEY")
FANART_CLIENT_API_KEY = os.getenv("FANART_TV_CLIENT_API_KEY")
USER_AGENT = "AudiophileDLNAServer/1.0.0 ( ecog@outlook.de )"
_MB_ROOT = "https://musicbrainz.org/ws/2/artist/"

class ArtworkHealer:
    @staticmethod
    def fetch_cover_art(mb_release_group_id, mb_release_id, artist, album):
        """
        Attempts to find artwork via Cover Art Archive (MusicBrainz).
        Expandable to Fanart.tv by adding an API key and secondary requests.
        """
        headers = {"User-Agent": USER_AGENT}
        image_data = None
        
        # Priority 1: Specific Release MBID
        if mb_release_id:
            try:
                url = f"https://coverartarchive.org/release/{mb_release_id}/front"
                res = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
                if res.status_code == 200:
                    image_data = res.content
            except Exception as e:
                pass
            time.sleep(1.1) # Respect Rate Limit

        # Priority 2: Master Album (Release Group) MBID
        if not image_data and mb_release_group_id:
            try:
                url = f"https://coverartarchive.org/release-group/{mb_release_group_id}/front"
                res = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
                if res.status_code == 200:
                    image_data = res.content
            except Exception as e:
                pass
            time.sleep(1.1)
            
        # Priority 3: Fallback to iTunes Search API (Highly reliable for Artist/Album text searches)
        if not image_data and artist and album:
            try:
                url = "https://itunes.apple.com/search"
                params = {"term": f"{artist} {album}", "entity": "album", "limit": 1}
                res = requests.get(url, params=params, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("resultCount", 0) > 0:
                        # Grab the highest resolution 600x600 image
                        art_url = data["results"][0]["artworkUrl100"].replace("100x100bb", "600x600bb")
                        img_res = requests.get(art_url, timeout=10)
                        if img_res.status_code == 200:
                            image_data = img_res.content
            except Exception as e:
                pass
            time.sleep(1.1)

        return image_data

    @staticmethod
    def embed_artwork(file_path, image_data):
        """Safely writes binary image data directly into the audio file metadata."""
        try:
            audio = File(file_path)
            if audio is None:
                return False

            ext = file_path.suffix.lower()
            mime_type = "image/jpeg" # Assuming downloaded APIs return JPEG
            
            # 1. FLAC Embedding
            if ext == '.flac':
                pic = Picture()
                pic.type = 3  # 3 = Front Cover
                pic.mime = mime_type
                pic.desc = "Front Cover"
                pic.data = image_data
                audio.clear_pictures()
                audio.add_picture(pic)
                audio.save()
                return True
                
            # 2. MP3 / ID3 Embedding
            elif ext == '.mp3':
                from mutagen.id3 import ID3, APIC
                if audio.tags is None:
                    audio.add_tags()
                audio.tags.add(
                    APIC(encoding=3, mime=mime_type, type=3, desc='Cover', data=image_data)
                )
                audio.save()
                return True
                
            # 3. M4A / ALAC / MP4 Embedding
            elif ext in ['.m4a', '.mp4', '.alac']:
                from mutagen.mp4 import MP4Cover
                if audio.tags is None:
                    audio.add_tags()
                # 13 is JPEG, 14 is PNG
                audio.tags['covr'] = [MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)]
                audio.save()
                return True
                
            # WAV, DSF, and OGG have much stricter or non-standard embedding protocols.
            # For this MVP, we will only rewrite the major 3 formats.
            else:
                logger.warning(f"Embedding not supported for {ext}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to embed art into {file_path.name}: {e}")
            return False
