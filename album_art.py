import os
import requests
import time
import logging
from pathlib import Path
from mutagen import File
from normalization import ArtistNormalizer, AlbumNormalizer

logger = logging.getLogger("ArtworkHealer")

# API Keys & Identity
USER_AGENT = "AudiophileServer/1.0 ( your@email.com )"

# Fanart
FANART_API_KEY = os.getenv("FANART_TV_PROJECT_API_KEY")
FANART_CLIENT_API_KEY = os.getenv("FANART_TV_CLIENT_API_KEY")

# Discogs
DISCOGS_TOKEN = os.getenv("DISCOGS_TOKEN")
DISCOGS_SECRET = os.getenv("DISCOGS_SECRET")


class ArtworkHealer:
    @staticmethod
    def fetch_cover_art(mb_release_group_id, mb_release_id, artist, album):
        """
        Attempts to find artwork cascading through:
        1. Exact Edition (Cover Art Archive)
        2. High-Res Master (Fanart.tv)
        3. Master Fallback (Cover Art Archive)
        4. Database Search (Discogs)
        5. Text Search (iTunes)
        """
        mb_headers = {"User-Agent": USER_AGENT}
        image_data = None

        # Priority 1: Specific Edition (Cover Art Archive Release MBID)
        if mb_release_id:
            try:
                url = f"https://coverartarchive.org/release/{mb_release_id}/front"
                res = requests.get(
                    url, headers=mb_headers, allow_redirects=True, timeout=10
                )
                if res.status_code == 200:
                    image_data = res.content
            except Exception:
                pass
            time.sleep(1.1)  # Respect MB rate limit

        # Priority 2: High-Resolution Master Album Artwork (Fanart.tv)
        if not image_data and mb_release_group_id and FANART_API_KEY:
            try:
                url = f"https://webservice.fanart.tv/v3/music/albums/{mb_release_group_id}"
                fanart_headers = {"api-key": FANART_API_KEY}
                if FANART_CLIENT_API_KEY:
                    fanart_headers["client-key"] = FANART_CLIENT_API_KEY

                res = requests.get(url, headers=fanart_headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()

                    albums = data.get("albums", {})
                    album_data = albums.get(mb_release_group_id, {})
                    covers = album_data.get("albumcover", [])

                    if covers:
                        covers.sort(key=lambda x: int(x.get("likes", 0)), reverse=True)
                        art_url = covers[0].get("url")

                        if art_url:
                            img_res = requests.get(art_url, timeout=15)
                            if img_res.status_code == 200:
                                image_data = img_res.content
            except Exception as e:
                logger.warning(f"Fanart fetch failed for {album}: {e}")

        # Priority 3: Master Album Fallback (Cover Art Archive Release Group MBID)
        if not image_data and mb_release_group_id:
            try:
                url = f"https://coverartarchive.org/release-group/{mb_release_group_id}/front"
                res = requests.get(
                    url, headers=mb_headers, allow_redirects=True, timeout=10
                )
                if res.status_code == 200:
                    image_data = res.content
            except Exception:
                pass
            time.sleep(1.1)

        # Priority 4: Database Search (Discogs)
        if not image_data and artist and album and DISCOGS_TOKEN and DISCOGS_SECRET:
            try:
                artist_name_normalized, artist_key = ArtistNormalizer.normalize(artist)
                album_name_normalized = AlbumNormalizer.normalize(album)
                url = "https://api.discogs.com/database/search"
                params = {
                    "artist": artist_name_normalized,
                    "release_title": album_name_normalized,
                    "type": "release",
                    "per_page": 1,
                }
                discogs_headers = {
                    "User-Agent": USER_AGENT,
                    "Authorization": f"Discogs key={DISCOGS_TOKEN}, secret={DISCOGS_SECRET}",
                }

                res = requests.get(
                    url, params=params, headers=discogs_headers, timeout=10
                )
                if res.status_code == 200:
                    data = res.json()
                    results = data.get("results", [])
                    if results:
                        # Grab the full-size cover image (not the thumbnail)
                        art_url = results[0].get("cover_image")
                        if art_url and not art_url.endswith("spacer.gif"):
                            img_res = requests.get(
                                art_url, headers=mb_headers, timeout=10
                            )
                            if img_res.status_code == 200:
                                image_data = img_res.content
            except Exception as e:
                logger.warning(f"Discogs fetch failed for {album}: {e}")
            time.sleep(1.1)  # Respect Discogs 60req/min rate limit

        # Priority 5: Fallback to iTunes Search API
        if not image_data and artist and album:
            try:
                artist_name_normalized, artist_key = ArtistNormalizer.normalize(artist)
                album_name_normalized = AlbumNormalizer.normalize(album)
                url = "https://itunes.apple.com/search"
                params = {
                    "term": f"{artist_name_normalized} {album_name_normalized}",
                    "entity": "album",
                    "limit": 1,
                }
                res = requests.get(url, params=params, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("resultCount", 0) > 0:
                        art_url = data["results"][0]["artworkUrl100"].replace(
                            "100x100bb", "600x600bb"
                        )
                        img_res = requests.get(art_url, timeout=10)
                        if img_res.status_code == 200:
                            image_data = img_res.content
            except Exception:
                pass

        return image_data

    @staticmethod
    def embed_artwork(file_path, image_data):
        """Safely writes binary image data directly into the audio file metadata."""
        try:
            audio = File(file_path)
            if audio is None:
                return False

            ext = file_path.suffix.lower()
            mime_type = "image/jpeg"

            # 1. FLAC Embedding
            if ext == ".flac":
                from mutagen.flac import Picture

                pic = Picture()
                pic.type = 3
                pic.mime = mime_type
                pic.desc = "Front Cover"
                pic.data = image_data
                audio.clear_pictures()
                audio.add_picture(pic)
                audio.save()
                return True

            # 2. MP3 / ID3 Embedding
            elif ext == ".mp3":
                from mutagen.id3 import ID3, APIC

                if audio.tags is None:
                    audio.add_tags()
                audio.tags.add(
                    APIC(
                        encoding=3,
                        mime=mime_type,
                        type=3,
                        desc="Cover",
                        data=image_data,
                    )
                )
                audio.save()
                return True

            # 3. M4A / ALAC / MP4 Embedding
            elif ext in [".m4a", ".mp4", ".alac"]:
                from mutagen.mp4 import MP4Cover

                if audio.tags is None:
                    audio.add_tags()
                audio.tags["covr"] = [
                    MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)
                ]
                audio.save()
                return True

            else:
                return False

        except Exception as e:
            logger.error(f"Failed to embed art into {file_path.name}: {e}")
            return False
