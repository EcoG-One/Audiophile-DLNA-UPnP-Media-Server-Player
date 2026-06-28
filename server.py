import sqlite3
import hashlib
import os
import json
import ipaddress
from io import BytesIO
from mutagen import File
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
import re
import urllib.parse
import html
import asyncio
import sqlite3
import logging
import socket
import struct
import uuid
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
from aiohttp import web
from mutagen import File as MutagenFile
from transcoder import AudioTranscoder
from capabilities import BrowserCapabilities
from artist_art import MUSIC_LIBRARY_BASE, get_artist_assets
from normalization import ArtistNormalizer

logger = logging.getLogger("AudiophileServer")


def load_config(config_path=os.path.expanduser("~/.audiophile_server/server_config.json")):
    """
    Loads configuration from disk. If the file is missing or corrupted,
    it returns safe default values.
    """
    # 1. Define base defaults
    config = {
        "BIND_IP": "192.168.178.143",  # Replace with your actual local IP
        "PORT": 8080,
        "MEDIA_DIRS": [],
        # "UUID": str(uuid.uuid4()),  # Generate a persistent UUID if none exists
    }

    # 2. Check if file exists
    if not os.path.exists(config_path):
        logger.info(f"Configuration file '{config_path}' not found. Using defaults.")
        return config

    # 3. Read and parse the file
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            saved_config = json.load(f)

            # Merge loaded settings into the defaults (ensures missing keys don't break the app)
            config.update(saved_config)
            logger.info("Configuration loaded successfully from disk.")

    except json.JSONDecodeError:
        logger.error(
            f"Configuration file '{config_path}' is corrupted! Falling back to defaults."
        )
    except Exception as e:
        logger.error(f"Failed to read configuration file: {e}")

    return config


# Configuration
# MEDIA_DIRS = [r"C:\Users\EcoG\Desktop\AppleMusicDecrypt-Windows\downloads"]
# BIND_IP = "192.168.178.143"  # Replace with your actual local IP
# PORT = 8080
UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "ecog-audiophile-dlna"))
SERVER_NAME = "EcoG Audiophile Server"
ART_CACHE_DIR = os.path.expanduser("~/.audiophile_server/art_cache")
os.makedirs(ART_CACHE_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DLNAServer")

# ==========================================
# 1. Database & Metadata Scanner
# ==========================================
class MediaLibrary:
    def __init__(self, db_path=os.path.expanduser("~/.audiophile_server/media.db")):
        self.art_cache_dir = Path(ART_CACHE_DIR)
        self.art_cache_dir.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()

        # 1. Artists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS artists (
                id TEXT PRIMARY KEY,
                normalized_key TEXT,
                mbid TEXT,
                name TEXT NOT NULL
            )
        """)

        # 2. Release Groups (The conceptual album, e.g., "The Wall")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS release_groups (
                id TEXT PRIMARY KEY,
                mbid TEXT,
                artist_id TEXT,
                title TEXT NOT NULL,
                FOREIGN KEY(artist_id) REFERENCES artists(id)
            )
        """)

        # 3. Releases (Specific editions, e.g., "The Wall (1994 Remaster)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS releases (
                id TEXT PRIMARY KEY,
                release_group_id TEXT,
                mbid TEXT,
                title TEXT,
                year TEXT,
                label TEXT,
                catalog_num TEXT,
                barcode TEXT,
                folder_path TEXT,
                art_hash TEXT,
                FOREIGN KEY(release_group_id) REFERENCES release_groups(id)
            )
        """)

        # 4. Tracks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id TEXT PRIMARY KEY,
                release_id TEXT,
                artist_id TEXT, 
                mbid TEXT,
                title TEXT NOT NULL,
                track_number INTEGER,
                disc_number INTEGER,
                duration REAL,
                path TEXT NOT NULL,
                mime_type TEXT,
                size INTEGER,
                FOREIGN KEY(release_id) REFERENCES releases(id),
                FOREIGN KEY(artist_id) REFERENCES artists(id)
            )
        """)

        # 5. Playlists (The container)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                file_path TEXT UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 6. Playlist Tracks (The ordered contents)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                playlist_id TEXT,
                track_id TEXT,
                position INTEGER,
                FOREIGN KEY(playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY(track_id) REFERENCES tracks(id) ON DELETE CASCADE,
                PRIMARY KEY (playlist_id, track_id, position)
            )
        """)

        # Safely inject the new Audiophile metrics into the releases table
        try:
            cursor.execute("ALTER TABLE releases ADD COLUMN quality_text TEXT")
            cursor.execute("ALTER TABLE releases ADD COLUMN quality_rank INTEGER DEFAULT 0")
            cursor.execute("ALTER TABLE releases ADD COLUMN codec TEXT")
            cursor.execute("ALTER TABLE releases ADD COLUMN sample_rate INTEGER")
            cursor.execute("ALTER TABLE releases ADD COLUMN bit_depth INTEGER")
            cursor.execute("ALTER TABLE tracks ADD COLUMN start_time REAL")
            cursor.execute("ALTER TABLE tracks ADD COLUMN end_time REAL")
            cursor.execute("ALTER TABLE tracks ADD COLUMN cue_path TEXT")
        except sqlite3.OperationalError:
            pass # Columns already exist

        # Create indexes for fast UI lookups
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_rg_artist ON release_groups(artist_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_rel_rg ON releases(release_group_id)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trk_rel ON tracks(release_id)")

        self.conn.commit()

        # Run the Deduplication Migration!
        self._migrate_and_deduplicate_artists()

    def _migrate_and_deduplicate_artists(self):
        """Safely merges duplicate artists based on their normalized keys."""
        cursor = self.conn.cursor()

        # Safely add the column if it's an older database
        try:
            cursor.execute("ALTER TABLE artists ADD COLUMN normalized_key TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        cursor.execute("SELECT id, name FROM artists")
        all_artists = cursor.fetchall()

        canonical_map = {}

        for artist_id, raw_name in all_artists:
            display_name, norm_key = ArtistNormalizer.normalize(raw_name)

            if norm_key not in canonical_map:
                # First time seeing this key: Promote it to Canonical
                canonical_map[norm_key] = artist_id
                cursor.execute(
                    "UPDATE artists SET normalized_key=?, name=? WHERE id=?",
                    (norm_key, display_name, artist_id),
                )
            else:
                # Duplicate detected!
                canonical_id = canonical_map[norm_key]
                if canonical_id != artist_id:
                    # 1. Reassign Albums (Release Groups)
                    cursor.execute(
                        "UPDATE release_groups SET artist_id=? WHERE artist_id=?",
                        (canonical_id, artist_id),
                    )
                    # 2. Reassign Tracks
                    cursor.execute(
                        "UPDATE tracks SET artist_id=? WHERE artist_id=?",
                        (canonical_id, artist_id),
                    )
                    # 3. Delete the Duplicate
                    cursor.execute("DELETE FROM artists WHERE id=?", (artist_id,))

        # Ensure fast, unique lookups going forward
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_artists_norm_key ON artists(normalized_key)"
        )
        self.conn.commit()

    def _purge_missing_files(self):
        """
        Scans the database for file paths that no longer exist on disk.
        Deletes the missing tracks and cascades to clean up orphaned albums and artists.
        """
        from pathlib import Path
        import logging

        logger = logging.getLogger("MediaLibrary")

        cursor = self.conn.cursor()

        # Grab all known file paths from the database
        cursor.execute("SELECT id, path FROM tracks")
        all_tracks = cursor.fetchall()

        missing_track_ids = []
        for track_id, path_str in all_tracks:
            if not path_str or not Path(path_str).exists():
                missing_track_ids.append(track_id)

        if missing_track_ids:
            print(
                f"🧹 Purging {len(missing_track_ids)} missing tracks from the database..."
            )

            # 1. Delete the missing tracks
            # Using executemany safely bypasses SQLite's 999-variable limit for massive purges
            cursor.executemany(
                "DELETE FROM tracks WHERE id=?", [(tid,) for tid in missing_track_ids]
            )

            # 2. Clean up orphaned Releases (Albums that have 0 tracks left)
            cursor.execute("""
                DELETE FROM releases 
                WHERE id NOT IN (SELECT DISTINCT release_id FROM tracks)
            """)

            # 3. Clean up orphaned Release Groups (Master albums with 0 editions left)
            cursor.execute("""
                DELETE FROM release_groups 
                WHERE id NOT IN (SELECT DISTINCT release_group_id FROM releases)
            """)

            # 4. Clean up orphaned Artists (Artists with no tracks AND no albums left)
            cursor.execute("""
                DELETE FROM artists 
                WHERE id NOT IN (
                    SELECT DISTINCT artist_id FROM tracks 
                    UNION 
                    SELECT DISTINCT artist_id FROM release_groups
                )
            """)

            self.conn.commit()
            print("✨ Database purge complete. Orphaned metadata removed.")

    def scan_directories(self, directories):
        from pathlib import Path
        import logging

        logger = logging.getLogger("MediaLibrary")

        logger.info(f"{'\033[93m'}Starting media scan...{'\033[0m'}")
        self._purge_missing_files()

        supported_exts = {
            ".flac",
            ".wav",
            ".mp3",
            ".dsf",
            ".m4a",
            ".mp4",
            ".ogg",
            ".aiff",
            ".aif",
            ".alac",
            ".wma",
            ".ape",
            ".wv",
            ".m3u",
            ".m3u8"
        }
        cue_target_files = set()

        # PHASE 1: CUE SHEET INJECTION
        for directory in directories:
            path = Path(directory)
            for file_path in path.rglob("*.cue"):
                # Run the custom CUE indexer
                target_audio_file = self._index_cue_file(file_path)
                if target_audio_file:
                    # Blacklist the large target file from being scanned normally!
                    cue_target_files.add(str(target_audio_file.resolve()))

        # PHASE 2: STANDARD FILE SCAN
        for directory in directories:
            path = Path(directory)
            for file_path in path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in supported_exts:
                    # Skip the file if it was already sliced up by a CUE sheet
                    if str(file_path.resolve()) not in cue_target_files:
                        self._index_file(file_path)

        # PHASE 3: PLAYLIST SYNC
        for directory in directories:
            path = Path(directory)
            for file_path in path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in {
                    ".m3u",
                    ".m3u8",
                }:
                    self._index_m3u(file_path)

        self.conn.commit()
        self._fetch_missing_artist_art()
        self.heal_missing_album_art()
        logger.info(f"{'\033[93m'}Scan complete.{'\033[0m'}")

    def _index_m3u(self, file_path):
        import hashlib
        from playlist_manager import PlaylistManager

        cursor = self.conn.cursor()

        playlist_name = file_path.stem
        # Generate a deterministic ID based on the file location
        playlist_id = hashlib.md5(f"playlist_{file_path}".encode()).hexdigest()

        # 1. Upsert the Playlist Container
        cursor.execute(
            """
            INSERT OR IGNORE INTO playlists (id, name, file_path) 
            VALUES (?, ?, ?)
        """,
            (playlist_id, playlist_name, str(file_path)),
        )

        # 2. Extract paths from the physical file
        physical_paths = PlaylistManager.parse_m3u(file_path)

        # 3. Wipe and rebuild the relational links (ensures DB exactly matches the file)
        cursor.execute(
            "DELETE FROM playlist_tracks WHERE playlist_id=?", (playlist_id,)
        )

        position = 1
        for track_path in physical_paths:
            # We must find the internal database ID for this physical path
            # (Note: For CUE sheets, this grabs the first virtual track slice pointing to the FLAC)
            cursor.execute("SELECT id FROM tracks WHERE path=? LIMIT 1", (track_path,))
            row = cursor.fetchone()

            if row:
                track_id = row[0]
                cursor.execute(
                    """
                    INSERT INTO playlist_tracks (playlist_id, track_id, position)
                    VALUES (?, ?, ?)
                """,
                    (playlist_id, track_id, position),
                )
                position += 1


    def _index_cue_file(self, cue_path):
        import hashlib
        import traceback
        from mutagen import File
        from cue_parser import CueParser
        from audio_quality import AudioAnalyzer
        from normalization import ArtistNormalizer, AlbumNormalizer

        try:
            # 1. Parse CUE Data
            cue_data = CueParser.parse(cue_path)
            if not cue_data or not cue_data.get("file") or not cue_data.get("tracks"):
                return None

            # 2. Resolve Target Audio File
            target_path = cue_path.parent / cue_data['file']
            if not target_path.exists():
                if not cue_data['file'].lower().endswith(('.flac', '.ape', '.mp3', '.m4a', '.mp4', '.wv', '.alac')):
                    # Attempt to find a matching audio file with the same base name
                    base_name = cue_data['file'].rsplit('.', 1)[0]
                    for ext in ['.flac', '.ape', '.mp3', '.m4a', '.mp4', '.wv', '.alac']:
                        potential_file = cue_path.parent / f"{base_name}{ext}"
                        if potential_file.exists():
                            target_path = potential_file
                            break
            if not target_path.exists():
                print(f"⚠️ [CUE] Target audio file missing: {target_path}")
                return None

            # 3. Analyze Audio (We do this ONCE for the whole massive file)
            audio = File(target_path, easy=True)
            if audio is None:
                return None

            metrics = AudioAnalyzer.analyze(target_path, audio)
            total_duration = getattr(audio.info, "length", 0)

            # 4. Global Metadata Normalization
            album_name_raw = cue_data['title']
            album_name_normalized = AlbumNormalizer.normalize(album_name_raw)
            album_artist_display, album_artist_norm = ArtistNormalizer.normalize(cue_data['artist'])

            cursor = self.conn.cursor()

            def get_or_create_artist(norm_key, display_name):
                cursor.execute("SELECT id FROM artists WHERE normalized_key=?", (norm_key,))
                row = cursor.fetchone()
                if row: return row[0]
                new_id = hashlib.md5(norm_key.encode()).hexdigest()
                cursor.execute("INSERT INTO artists (id, normalized_key, name) VALUES (?, ?, ?)", (new_id, norm_key, display_name))
                return new_id

            album_artist_id = get_or_create_artist(album_artist_norm, album_artist_display)

            # 5. Strict Deterministic Hashing
            rg_id = hashlib.md5(f"{album_artist_id}_{album_name_normalized.lower()}".encode()).hexdigest()
            base_folder_path = str(cue_path.parent)
            release_id = hashlib.md5(f"{rg_id}_{base_folder_path}_{metrics['quality_rank']}_CUE".encode()).hexdigest()

            # Upsert Master and Release Group
            cursor.execute(
                "INSERT OR IGNORE INTO release_groups (id, artist_id, title) VALUES (?, ?, ?)",
                (rg_id, album_artist_id, album_name_normalized)
            )

            art_hash = self._extract_and_cache_art(target_path)

            cursor.execute('''
                INSERT OR IGNORE INTO releases 
                (id, release_group_id, title, folder_path, art_hash, quality_text, quality_rank, codec, sample_rate, bit_depth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (release_id, rg_id, album_name_raw, base_folder_path, art_hash, metrics["quality_text"], metrics["quality_rank"], metrics["codec"], metrics["sample_rate"], metrics["bit_depth"]))

            # 6. Inject Virtual Tracks!
            tracks = cue_data['tracks']
            for i, track in enumerate(tracks):
                track_display, track_norm = ArtistNormalizer.normalize(track['artist'])
                track_artist_id = get_or_create_artist(track_norm, track_display)

                # Calculate End Time: The start time of the NEXT track, or the total file length if it's the last track.
                start_time = track['start_time']
                end_time = tracks[i+1]['start_time'] if i + 1 < len(tracks) else total_duration
                duration = end_time - start_time

                track_id = hashlib.md5(f"{release_id}_cue_{track['track_number']}_{start_time}".encode()).hexdigest()

                cursor.execute('''
                    INSERT OR REPLACE INTO tracks 
                    (id, release_id, artist_id, title, track_number, duration, path, mime_type, size, start_time, end_time, cue_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (track_id, release_id, track_artist_id, track['title'], track['track_number'], duration, 
                      str(target_path), f"audio/{target_path.suffix.lower().strip('.')}", target_path.stat().st_size, start_time, end_time, str(cue_path)))

            return target_path

        except Exception as e:
            print(f"❌ Failed to parse CUE {cue_path}: {e}")
            traceback.print_exc()
            return None

    def heal_missing_album_art(self):
        """
        Background task: Finds albums missing cover art, fetches high-res images,
        embeds them into the physical files, and updates the UI cache.
        """
        import logging
        from album_art import ArtworkHealer
        from pathlib import Path
        import hashlib

        logger = logging.getLogger("MediaLibrary")
        cursor = self.conn.cursor()

        # Find all releases (editions) that have NO artwork
        cursor.execute('''
            SELECT r.id, r.mbid, rg.mbid, r.title, a.name 
            FROM releases r
            JOIN release_groups rg ON r.release_group_id = rg.id
            JOIN artists a ON rg.artist_id = a.id
            WHERE r.art_hash IS NULL
        ''')
        missing_releases = cursor.fetchall()

        if not missing_releases:
            return

        logger.info(f"🩺 Healing Engine: Found {len(missing_releases)} albums missing artwork.")

        for rel_id, rel_mbid, rg_mbid, album_title, artist_name in missing_releases:
            logger.info(f"Fetching art for: {artist_name} - {album_title}")

            # 1. Fetch the image data
            image_data = ArtworkHealer.fetch_cover_art(rg_mbid, rel_mbid, artist_name, album_title)

            if image_data:
                # 2. Hash and cache for the Web UI
                art_hash = hashlib.md5(image_data).hexdigest()
                art_path = self.art_cache_dir / art_hash

                if not art_path.exists():
                    with open(art_path, "wb") as f:
                        f.write(image_data)

                # 3. Find all tracks belonging to this edition
                cursor.execute("SELECT path FROM tracks WHERE release_id=?", (rel_id,))
                tracks = cursor.fetchall()

                success_count = 0
                for (track_path,) in tracks:
                    # 4. Embed into the physical audio file!
                    if ArtworkHealer.embed_artwork(Path(track_path), image_data):
                        success_count += 1

                # 5. Update the database so the UI displays the new art instantly
                if success_count > 0:
                    cursor.execute("UPDATE releases SET art_hash=? WHERE id=?", (art_hash, rel_id))
                    self.conn.commit()
                    logger.info(f"✅ Successfully embedded art into {success_count} files for '{album_title}'.")
            else:
                logger.warning(f"❌ Could not find artwork for '{album_title}'. Will retry next scan.")

    def _index_file(self, file_path):
        import hashlib
        import re
        import traceback
        from normalization import ArtistNormalizer, AlbumNormalizer
        from audio_quality import AudioAnalyzer

        try:
            from mutagen import File
            from mutagen import MutagenError

            # 1. OPEN THE AUDIO FILE
            audio = File(file_path, easy=True)
            if audio is None:
                return

            cursor = self.conn.cursor()

            # --- 2. HELPER: Safely extract tags ---
            def get_tag(key, default=None):
                val = audio.get(key)
                return val[0] if val else default

            # --- 3. BASIC METADATA EXTRACTION & NORMALIZATION ---
            title = get_tag("title", file_path.stem)

            raw_track_artist = get_tag("artist", "Unknown Artist")
            raw_album_artist = get_tag("albumartist", raw_track_artist)

            track_display, track_norm = ArtistNormalizer.normalize(raw_track_artist)
            album_display, album_norm = ArtistNormalizer.normalize(raw_album_artist)

            album_name_raw = get_tag("album", "Unknown Album")
            album_name_normalized = AlbumNormalizer.normalize(album_name_raw)

            # --- 4. ADVANCED METADATA / IDENTIFIERS ---
            mb_track_artist_id = get_tag("musicbrainz_artistid")
            mb_album_artist_id = get_tag(
                "musicbrainz_albumartistid", mb_track_artist_id
            )
            mb_release_group_id = get_tag("musicbrainz_releasegroupid")
            mb_release_id = get_tag("musicbrainz_albumid")
            mb_track_id = get_tag("musicbrainz_trackid")

            year_raw = get_tag("date") or get_tag("originaldate") or ""
            year = str(year_raw)[:4]

            label = get_tag("organization") or get_tag("label") or ""
            cat_num = get_tag("catalognumber", "")
            barcode = get_tag("barcode", "")

            def parse_num(val):
                match = re.search(r"\d+", str(val))
                return int(match.group()) if match else 1

            track_num = parse_num(get_tag("tracknumber", 0))
            disc_num = parse_num(get_tag("discnumber", 1))

            # --- 5. AUDIO QUALITY ANALYSIS ---
            metrics = AudioAnalyzer.analyze(file_path, audio)

            # --- 6. STRICT DETERMINISTIC HASHING ---
            def get_or_create_artist(norm_key, display_name, mbid):
                cursor.execute(
                    "SELECT id FROM artists WHERE normalized_key=?", (norm_key,)
                )
                row = cursor.fetchone()
                if row:
                    return row[0]
                new_id = hashlib.md5(norm_key.encode()).hexdigest()
                cursor.execute(
                    "INSERT INTO artists (id, normalized_key, mbid, name) VALUES (?, ?, ?, ?)",
                    (new_id, norm_key, mbid, display_name),
                )
                return new_id

            track_artist_id = get_or_create_artist(
                track_norm, track_display, mb_track_artist_id
            )
            album_artist_id = get_or_create_artist(
                album_norm, album_display, mb_album_artist_id
            )

            # MASTER ALBUM HASH
            rg_id = hashlib.md5(
                f"{album_artist_id}_{album_name_normalized.lower()}".encode()
            ).hexdigest()

            # --- MULTI-DISC FOLDER COLLAPSING ---
            parent_dir = file_path.parent
            dir_name = parent_dir.name

            # Detect folders like "CD1", "CD 1", "Disc 2", "Disk 01", "Part 1"
            is_disc_folder = re.match(r"(?i)^(cd|disc|disk|part)[\s\-_]*\d+$", dir_name)

            if is_disc_folder:
                # Step UP one directory to use the main album folder as the Edition identity
                base_folder_path = str(parent_dir.parent)
            else:
                # Use the current folder
                base_folder_path = str(parent_dir)

            # SPECIFIC EDITION HASH: Use the collapsed base folder path!
            sig = f"{rg_id}_{base_folder_path}_{metrics['quality_rank']}"
            release_id = hashlib.md5(sig.encode()).hexdigest()

            # Clean edition title for UI display
            clean_title = re.sub(
                r"(?i)\s*[\(\[]?(disc|cd)\s*\d+[\)\]]?", "", album_name_raw
            ).strip()
            edition_hints = [year, label, cat_num]
            hints = [h for h in edition_hints if h]
            release_title = (
                f"{clean_title} [{' | '.join(hints)}]" if hints else clean_title
            )

            # TRACK HASH
            track_id = hashlib.md5(
                f"{release_id}_{disc_num}_{track_num}_{title}".encode()
            ).hexdigest()

            # --- 7. DATABASE UPSERTS ---
            cursor.execute(
                "INSERT OR IGNORE INTO release_groups (id, mbid, artist_id, title) VALUES (?, ?, ?, ?)",
                (rg_id, mb_release_group_id, album_artist_id, album_name_normalized),
            )

            art_hash = self._extract_and_cache_art(file_path)

            cursor.execute(
                """
                INSERT OR IGNORE INTO releases 
                (id, release_group_id, mbid, title, year, label, catalog_num, barcode, folder_path, art_hash, 
                 quality_text, quality_rank, codec, sample_rate, bit_depth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    release_id,
                    rg_id,
                    mb_release_id,
                    release_title,
                    year,
                    label,
                    cat_num,
                    barcode,
                    str(file_path.parent),
                    art_hash,
                    metrics["quality_text"],
                    metrics["quality_rank"],
                    metrics["codec"],
                    metrics["sample_rate"],
                    metrics["bit_depth"],
                ),
            )

            cursor.execute(
                """
                INSERT OR REPLACE INTO tracks 
                (id, release_id, artist_id, mbid, title, track_number, disc_number, duration, path, mime_type, size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    track_id,
                    release_id,
                    track_artist_id,
                    mb_track_id,
                    title,
                    track_num,
                    disc_num,
                    getattr(audio.info, "length", 0),
                    str(file_path),
                    f"audio/{file_path.suffix.lower().strip('.')}",
                    file_path.stat().st_size,
                ),
            )

        except MutagenError as e:
            print(f"⚠️ [SKIP] Corrupt or unreadable audio file '{file_path.name}': {e}")
            return
        except Exception as e:
            print(f"❌ Failed to index {file_path} due to unexpected error: {e}")
            traceback.print_exc()

    def _extract_and_cache_art(self, file_path):
        import hashlib

        try:
            from mutagen import File

            audio = File(file_path)

            # 1. Total Failure Check
            if audio is None:
                return None

            art_data = None

            # 2. FLAC Handling
            if hasattr(audio, "pictures") and audio.pictures:
                art_data = audio.pictures[0].data

            # 3. M4A / MP3 Handling (Crucial: ensure tags is not None!)
            elif hasattr(audio, "tags") and audio.tags is not None:

                # Apple M4A
                if "covr" in audio.tags and audio.tags["covr"]:
                    art_data = bytes(audio.tags["covr"][0])

                # Standard MP3 (ID3)
                else:
                    for key in audio.tags.keys():
                        if key.startswith("APIC:"):
                            art_data = audio.tags[key].data
                            break

            # 4. If no art was found, exit cleanly
            if not art_data:
                return None

            # 5. Hash and Cache the Image
            art_hash = hashlib.md5(art_data).hexdigest()
            art_path = self.art_cache_dir / art_hash

            if not art_path.exists():
                with open(art_path, "wb") as f:
                    f.write(art_data)

            return art_hash

        except Exception as e:
            # We fail silently instead of throwing terminal errors for missing art
            import logging

            logger = logging.getLogger("DLNAServer")
            logger.warning(f"Could not extract art from {file_path}: {e}")
            return None

    def _fetch_missing_artist_art(self):
        """
        Background task: Iterates over all known artists and triggers artwork
        downloads for any missing assets.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM artists WHERE name IS NOT NULL")
        artists = cursor.fetchall()

        from artist_art import get_artist_assets
        import logging

        logger = logging.getLogger("MediaLibrary")
        logger.info(f"Scanning {len(artists)} artists for missing artwork...")

        for (artist_name,) in artists:
            try:
                # get_artist_assets() automatically checks the disk first and
                # skips downloading if the assets already exist.
                get_artist_assets(artist_name)
            except Exception as e:
                logger.error(
                    f"Background artwork fetch failed for '{artist_name}': {e}"
                )

        logger.info("Background artist artwork acquisition complete.")


import email.utils
import time


# ==========================================
# 2. SSDP Discovery
# ==========================================
class SSDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, ip, port, uuid):
        self.ip = ip
        self.port = port
        self.uuid = uuid
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        sock = transport.get_extra_info("socket")

        # 1. Allow multiple apps to use port 1900
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # 2. Bind multicast EXPLICITLY to our specific network interface (BIND_IP)
        # This prevents the OS from sending SSDP packets to Docker/VPN adapters
        mreq = socket.inet_aton("239.255.255.250") + socket.inet_aton(self.ip)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # 3. Force outbound multicast traffic to use the correct interface
        sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(self.ip)
        )

        # 4. Set Time-To-Live so packets don't drop at the first switch
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)

        logger.info(f"SSDP Bound explicitly to interface {self.ip}")

        # Start passive NOTIFY broadcasts
        asyncio.create_task(self.broadcast_notify())

    def datagram_received(self, data, addr):
        msg = data.decode("utf-8", errors="ignore")
        if msg.startswith("M-SEARCH"):
            # Generate RFC 1123 format date (required by strict DLNA clients)
            date_str = email.utils.formatdate(
                timeval=None, localtime=False, usegmt=True
            )

            response = (
                "HTTP/1.1 200 OK\r\n"
                "CACHE-CONTROL: max-age=1800\r\n"
                f"DATE: {date_str}\r\n"
                "EXT:\r\n"
                f"LOCATION: http://{self.ip}:{self.port}/description.xml\r\n"
                f"SERVER: Linux/5.0 UPnP/1.0 {SERVER_NAME}/1.0\r\n"
                "ST: upnp:rootdevice\r\n"
                f"USN: uuid:{self.uuid}::upnp:rootdevice\r\n"
                "\r\n"
            )
            # Send unicast reply directly back to the device that asked
            self.transport.sendto(response.encode("utf-8"), addr)

    async def broadcast_notify(self):
        """Periodically announce the server's existence to the network."""
        while True:
            if self.transport:
                notify_msg = (
                    "NOTIFY * HTTP/1.1\r\n"
                    "HOST: 239.255.255.250:1900\r\n"
                    "CACHE-CONTROL: max-age=1800\r\n"
                    f"LOCATION: http://{self.ip}:{self.port}/description.xml\r\n"
                    f"SERVER: Linux/5.0 UPnP/1.0 {SERVER_NAME}/1.0\r\n"
                    "NT: upnp:rootdevice\r\n"
                    "NTS: ssdp:alive\r\n"
                    f"USN: uuid:{self.uuid}::upnp:rootdevice\r\n"
                    "\r\n"
                )
                # Multicast the notification
                self.transport.sendto(
                    notify_msg.encode("utf-8"), ("239.255.255.250", 1900)
                )
            await asyncio.sleep(30)  # Broadcast every 30 seconds


# ==========================================
# 3. HTTP Server & UPnP SOAP Endpoints
# ==========================================
class UPnPServer:

    def __init__(
        self,
        library,
        ip,
        port,
        uuid,
        config_path=os.path.expanduser("~/.audiophile_server/server_config.json"),
    ):
        self.library = library
        self.uuid = uuid
        self.config_path = config_path
        self.ip = ip
        self.port = port

        # In-memory configuration state
        self.config = load_config(self.config_path)

        # Concurrency & Task Management
        self._config_lock = asyncio.Lock()
        self._rescan_task = None
        # Initialize the transcoder for on-the-fly conversions of ALAC to FLAC if needed
        self.transcoder = AudioTranscoder()  
        self.app = web.Application(middlewares=[self.dlna_headers_middleware])
        self.setup_routes()

    @web.middleware
    async def dlna_headers_middleware(self, request, handler):
        # Critical for Pioneer N-50AE compatibility
        response = await handler(request)
        response.headers['transferMode.dlna.org'] = 'Streaming'
        response.headers['contentFeatures.dlna.org'] = 'DLNA.ORG_OP=01;DLNA.ORG_CI=0;DLNA.ORG_FLAGS=01700000000000000000000000000000'
        return response

    def setup_routes(self):
        self.app.router.add_get("/description.xml", self.handle_description)
        self.app.router.add_post("/ContentDirectory/control", self.handle_soap)
        self.app.router.add_get("/media/{id}", self.handle_media)
        # Art Route
        self.app.router.add_get("/art/{hash}", self.handle_art)
        # API Routes for Configuration and Search
        self.app.router.add_get("/api/config", self.api_get_config)
        self.app.router.add_post("/api/config", self.api_set_config)
        self.app.router.add_get("/api/search", self.api_search)
        self.app.router.add_get("/api/albums", self.api_get_all_albums)
        self.app.router.add_get("/api/artists", self.api_get_all_artists)
        self.app.router.add_get('/api/albums/{album_id}', self.api_get_album)
        self.app.router.add_get("/api/artists/{artist_name}", self.api_get_artist)
        self.app.router.add_static("/artist-art", str(MUSIC_LIBRARY_BASE))
        # Playlist API Routes
        self.app.router.add_get("/api/playlists", self.api_get_playlists)
        self.app.router.add_post("/api/playlists", self.api_create_playlist)
        self.app.router.add_get(
            "/api/playlists/{playlist_id}", self.api_get_playlist_tracks
        )
        self.app.router.add_post(
            "/api/playlists/{playlist_id}/tracks", self.api_add_to_playlist
        )

    async def handle_description(self, request):
        # UPnP Device Architecture XML
        xml = f"""<?xml version="1.0"?>
        <root xmlns="urn:schemas-upnp-org:device-1-0">
            <specVersion><major>1</major><minor>0</minor></specVersion>
            <device>
                <deviceType>urn:schemas-upnp-org:device:MediaServer:1</deviceType>
                <friendlyName>{SERVER_NAME}</friendlyName>
                <manufacturer>Custom Python Server</manufacturer>
                <modelName>Audiophile DLNA</modelName>
                <UDN>uuid:{self.uuid}</UDN>
                <serviceList>
                    <service>
                        <serviceType>urn:schemas-upnp-org:service:ContentDirectory:1</serviceType>
                        <serviceId>urn:upnp-org:serviceId:ContentDirectory</serviceId>
                        <controlURL>/ContentDirectory/control</controlURL>
                        <eventSubURL>/ContentDirectory/event</eventSubURL>
                        <SCPDURL>/ContentDirectory.xml</SCPDURL>
                    </service>
                </serviceList>
            </device>
        </root>"""
        return web.Response(text=xml, content_type='text/xml')

    async def handle_soap(self, request):
        import traceback

        try:
            body = await request.text()

            # 1. Parse Strict SOAP Variables
            object_id_match = re.search(r"<ObjectID[^>]*>(.*?)</ObjectID>", body)
            object_id = object_id_match.group(1) if object_id_match else "0"

            browse_flag_match = re.search(r"<BrowseFlag[^>]*>(.*?)</BrowseFlag>", body)
            browse_flag = (
                browse_flag_match.group(1)
                if browse_flag_match
                else "BrowseDirectChildren"
            )

            start_idx_match = re.search(
                r"<StartingIndex[^>]*>(\d+)</StartingIndex>", body
            )
            starting_index = int(start_idx_match.group(1)) if start_idx_match else 0

            req_count_match = re.search(
                r"<RequestedCount[^>]*>(\d+)</RequestedCount>", body
            )
            requested_count = int(req_count_match.group(1)) if req_count_match else 0

            cursor = self.library.conn.cursor()
            import html
            import urllib.parse

            items_xml = ""
            item_count = 0
            total_matches = 0

            # ==========================================
            # HANDLE BROWSE METADATA
            # ==========================================
            if browse_flag == "BrowseMetadata":
                items_xml = f"""
                <container id="{object_id}" parentID="-1" restricted="1" searchable="0">
                    <dc:title>Folder Info</dc:title>
                    <upnp:class>object.container</upnp:class>
                </container>"""
                item_count = 1
                total_matches = 1

            # ==========================================
            # HANDLE BROWSE DIRECT CHILDREN
            # ==========================================
            elif browse_flag == "BrowseDirectChildren":

                # --- ROOT VIEW: List Artists ---
                if object_id == "0":
                    cursor.execute("SELECT id, name FROM artists ORDER BY name")
                    all_artists = cursor.fetchall()
                    total_matches = len(all_artists)

                    end_index = (
                        starting_index + requested_count
                        if requested_count > 0
                        else total_matches
                    )
                    artists = all_artists[starting_index:end_index]

                    for artist_id, name in artists:
                        if not name:
                            continue
                        # Using the clean MD5 hash instead of the raw name
                        v_id = f"artist_{artist_id}"

                        items_xml += f"""
                        <container id="{v_id}" parentID="0" restricted="1" childCount="1" searchable="0">
                            <dc:title>{html.escape(name)}</dc:title>
                            <upnp:class>object.container.person.musicArtist</upnp:class>
                        </container>"""
                        item_count += 1

                # --- ARTIST VIEW: List Albums (Releases) ---
                elif object_id.startswith("artist_"):
                    artist_id = object_id.replace("artist_", "")

                    # Fetch specific releases (editions) for this artist
                    cursor.execute(
                        """
                        SELECT r.id, r.title, MIN(r.art_hash) 
                        FROM releases r
                        JOIN release_groups rg ON r.release_group_id = rg.id
                        WHERE rg.artist_id=? 
                        GROUP BY r.id 
                        ORDER BY r.year, r.title
                    """,
                        (artist_id,),
                    )

                    all_albums = cursor.fetchall()
                    total_matches = len(all_albums)

                    end_index = (
                        starting_index + requested_count
                        if requested_count > 0
                        else total_matches
                    )
                    albums = all_albums[starting_index:end_index]

                    for rel_id, title, art_hash in albums:
                        if not title:
                            continue
                        v_id = f"release_{rel_id}"

                        items_xml += f"""
                        <container id="{v_id}" parentID="{object_id}" restricted="1" childCount="1" searchable="0">
                            <dc:title>{html.escape(title)}</dc:title>
                            <upnp:class>object.container.album.musicAlbum</upnp:class>
                        </container>"""
                        item_count += 1

                # --- ALBUM VIEW: List Tracks ---
                elif object_id.startswith("release_"):
                    release_id = object_id.replace("release_", "")

                    # Fetch tracks with their specific track artist and release info
                    cursor.execute(
                        """
                        SELECT t.id, t.title, t.mime_type, t.size, t.duration, r.art_hash, ta.name, r.title
                        FROM tracks t
                        JOIN releases r ON t.release_id = r.id
                        JOIN artists ta ON t.artist_id = ta.id
                        WHERE t.release_id=? 
                        ORDER BY t.disc_number, t.track_number
                    """,
                        (release_id,),
                    )

                    all_tracks = cursor.fetchall()
                    total_matches = len(all_tracks)

                    end_index = (
                        starting_index + requested_count
                        if requested_count > 0
                        else total_matches
                    )
                    tracks = all_tracks[starting_index:end_index]

                    for track in tracks:
                        (
                            t_id,
                            title,
                            mime_type,
                            size,
                            duration,
                            art_hash,
                            track_artist,
                            album_title,
                        ) = track

                        # Handle potential null duration safely
                        safe_duration = int(duration or 0)
                        m, s = divmod(safe_duration, 60)
                        h, m = divmod(m, 60)
                        dur_str = f"{h}:{m:02d}:{s:02d}.000"

                        art_tag = ""
                        if art_hash:
                            art_url = f"http://{self.ip}:{self.port}/art/{art_hash}"
                            art_tag = f"""
                            <upnp:albumArtURI dlna:profileID="JPEG_TN">{art_url}</upnp:albumArtURI>
                            <upnp:icon>{art_url}</upnp:icon>
                            """

                        items_xml += f"""
                        <item id="{t_id}" parentID="{object_id}" restricted="1">
                            <dc:title>{html.escape(title)}</dc:title>
                            <upnp:class>object.item.audioItem.musicTrack</upnp:class>
                            <upnp:artist>{html.escape(track_artist)}</upnp:artist>
                            <upnp:album>{html.escape(album_title)}</upnp:album>
                            {art_tag}
                            <res protocolInfo="http-get:*:{mime_type}:DLNA.ORG_OP=01;DLNA.ORG_CI=0;DLNA.ORG_FLAGS=01700000000000000000000000000000" 
                                 size="{size or 0}" duration="{dur_str}">http://{self.ip}:{self.port}/media/{t_id}</res>
                        </item>"""
                        item_count += 1

            # ==========================================
            # WRAP AND RETURN STRICT DIDL-LITE XML
            # ==========================================
            didl = f"""<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" 
                                  xmlns:dc="http://purl.org/dc/elements/1.1/" 
                                  xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
                                  xmlns:dlna="urn:schemas-dlna-org:metadata-1-0/">
                {items_xml}
            </DIDL-Lite>"""

            soap_response = f"""<?xml version="1.0" encoding="utf-8"?>
            <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
                <s:Body>
                    <u:BrowseResponse xmlns:u="urn:schemas-upnp-org:service:ContentDirectory:1">
                        <Result>{html.escape(didl)}</Result>
                        <NumberReturned>{item_count}</NumberReturned>
                        <TotalMatches>{total_matches}</TotalMatches>
                        <UpdateID>1</UpdateID>
                    </u:BrowseResponse>
                </s:Body>
            </s:Envelope>"""

            from aiohttp import web

            return web.Response(
                text=soap_response, content_type="text/xml", charset="utf-8"
            )

        except Exception as e:
            print(f"\n--- CRITICAL ERROR IN DLNA BROWSE (handle_soap) ---")
            traceback.print_exc()
            print(f"---------------------------------------------------\n")
            from aiohttp import web

            return web.Response(status=500, text=f"DLNA Error: {str(e)}")

    async def handle_media(self, request):
        import traceback
        from pathlib import Path

        media_id = request.match_info["id"]
        cursor = self.library.conn.cursor()

        # 1. Query the new 'tracks' table instead of 'media'
        cursor.execute("SELECT path, mime_type FROM tracks WHERE id=?", (media_id,))
        row = cursor.fetchone()

        if not row or not Path(row[0]).exists():
            return web.Response(status=404, text="Media not found")

        original_path, original_mime = row

        # 2. Derive the codec dynamically for the Transcoder
        codec = "unknown"
        lower_path = original_path.lower()
        if lower_path.endswith(".m4a") or lower_path.endswith(".mp4"):
            codec = "alac"
        elif lower_path.endswith(".flac"):
            codec = "flac"
        elif lower_path.endswith(".ape"):
            codec = "ape"
        elif lower_path.endswith(".wv"):
            codec = "wv"

        # 3. Transcoding & Delivery Logic
        try:
            user_agent = request.headers.get("User-Agent", "")
            from capabilities import BrowserCapabilities

            # Always transcode APE and WV. For ALAC, defer to the browser capabilities.
            needs_transcode = False
            if codec in ["ape", "wv"]:
                needs_transcode = True
            elif BrowserCapabilities.needs_alac_transcoding(user_agent, codec):
                needs_transcode = True

            if needs_transcode:
                serve_path = await self.transcoder.get_transcoded_file(
                    original_path, media_id
                )
                mime_type = "audio/flac"
            else:
                serve_path = Path(original_path)
                mime_type = original_mime

            response = web.FileResponse(serve_path)
            response.content_type = mime_type
            return response

        except Exception as e:
            print(f"\n--- STREAMING ERROR ---")
            traceback.print_exc()
            return web.Response(status=500, text=f"Streaming error: {str(e)}")

    async def handle_art(self, request):
        art_hash = request.match_info["hash"]

        # Check the new extension-less format first
        art_path = Path(ART_CACHE_DIR) / art_hash

        # Fallback for older scans that might have .jpg
        if not art_path.exists():
            art_path = Path(ART_CACHE_DIR) / f"{art_hash}.jpg"

        if art_path.exists():
            return web.FileResponse(art_path, headers={"Content-Type": "image/jpeg"})
        return web.Response(status=404)

    async def _persist_config(self, config_data):
        """
        Saves the configuration to disk using an atomic write pattern.
        This ensures power failures during a write don't corrupt the JSON file.
        """
        loop = asyncio.get_running_loop()

        def _atomic_write():
            dir_name = os.path.dirname(os.path.abspath(self.config_path)) or "."
            # 1. Write to a temporary file first
            fd, tmp_path = tempfile.mkstemp(
                dir=dir_name, prefix="config_tmp_", suffix=".json"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(config_data, f, indent=4)

                # 2. Atomically replace the old config file with the new one
                os.replace(tmp_path, self.config_path)
            except Exception as e:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise e

        # Offload file I/O to a thread pool so it doesn't block the async event loop
        await loop.run_in_executor(None, _atomic_write)

    def _trigger_background_rescan(self, directories):
        """
        Safely triggers a media library rescan. If a rescan is already running,
        it cancels the ongoing rescan and starts a fresh one with the new paths.
        """
        if self._rescan_task and not self._rescan_task.done():
            logger.info("Configuration updated. Cancelling active media rescan...")
            self._rescan_task.cancel()

        self._rescan_task = asyncio.create_task(self._async_rescan_worker(directories))

    async def _async_rescan_worker(self, directories):
        """The actual background worker task."""
        logger.info(f"Starting background media rescan for directories: {directories}")
        try:
            # We offload the blocking SQLite/Mutagen scan to a thread so
            # the web server remains 100% responsive during the scan.
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.library.scan_directories, directories)

            # Note: In a true production app, you would also increment the UPnP
            # SystemUpdateID here so renderers know the library changed!
            logger.info("Background media rescan completed successfully.")

        except asyncio.CancelledError:
            logger.warning(
                "Media rescan was cancelled by a newer configuration update."
            )
        except Exception as e:
            logger.error(f"Critical error during background media rescan: {e}")

    async def api_get_config(self, request):
        return web.json_response(
            {"BIND_IP": self.config["BIND_IP"], "PORT": self.config["PORT"], "MEDIA_DIRS": self.config["MEDIA_DIRS"]}
        )

    async def api_set_config(self, request):
        try:
            payload = await request.json()
        except Exception:
            return web.json_response(
                {
                    "success": False,
                    "errors": ["Invalid JSON payload."],
                    "rescan_triggered": False,
                },
                status=400,
            )

        errors = []
        validated_config = {}

        # ==========================================
        # 1. VALIDATION PHASE
        # ==========================================

        # Validate BIND_IP
        raw_ip = payload.get("BIND_IP")
        if raw_ip is not None:
            try:
                # Validates both IPv4 and IPv6 format
                parsed_ip = ipaddress.ip_address(raw_ip)
                validated_config["BIND_IP"] = str(parsed_ip)
            except ValueError:
                errors.append(f"Invalid IP address format: '{raw_ip}'")

        # Validate PORT
        raw_port = payload.get("PORT")
        if raw_port is not None:
            try:
                port_num = int(raw_port)
                if not (1024 <= port_num <= 65535):
                    errors.append(
                        f"Port must be between 1024 and 65535. Received: {port_num}"
                    )
                else:
                    validated_config["PORT"] = port_num
            except (ValueError, TypeError):
                errors.append(f"Port must be a valid integer. Received: '{raw_port}'")

        # Validate MEDIA_DIRS
        raw_dirs = payload.get("MEDIA_DIRS")
        if raw_dirs is not None:
            if not isinstance(raw_dirs, list):
                errors.append("MEDIA_DIRS must be a list of directory paths.")
            else:
                valid_dirs = []
                for d in raw_dirs:
                    path = Path(d).resolve()  # Resolves symlinks and normalizes path
                    if not path.exists():
                        errors.append(f"Directory does not exist: {d}")
                    elif not path.is_dir():
                        errors.append(f"Path is not a directory: {d}")
                    elif not os.access(path, os.R_OK | os.X_OK):
                        errors.append(f"Directory lacks read/execute permissions: {d}")
                    else:
                        valid_dirs.append(str(path))

                # Remove duplicates while preserving order
                validated_config["MEDIA_DIRS"] = list(dict.fromkeys(valid_dirs))

        # Reject if any validation checks failed
        if errors:
            return web.json_response(
                {"success": False, "errors": errors, "rescan_triggered": False},
                status=400,
            )

        # ==========================================
        # 2. ATOMIC APPLICATION & PERSISTENCE
        # ==========================================
        rescan_triggered = False

        # Lock to prevent race conditions from rapid successive API calls
        async with self._config_lock:
            # Detect if media directories have changed (requires a rescan)
            current_dirs = set(self.config.get("MEDIA_DIRS", []))
            new_dirs = set(validated_config.get("MEDIA_DIRS", current_dirs))
            dirs_changed = current_dirs != new_dirs

            # Update active in-memory state
            self.config.update(validated_config)

            # Persist to disk safely
            try:
                await self._persist_config(self.config)
            except IOError as e:
                logger.error(f"Failed to persist configuration: {e}")
                return web.json_response(
                    {
                        "success": False,
                        "errors": [
                            f"Configuration applied in-memory, but failed to save to disk: {str(e)}"
                        ],
                        "rescan_triggered": False,
                    },
                    status=500,
                )

            # ==========================================
            # 3. BACKGROUND RESCAN (Side-Effect)
            # ==========================================
            if dirs_changed:
                self._trigger_background_rescan(self.config["MEDIA_DIRS"])
                rescan_triggered = True

        # ==========================================
        # 4. COMPREHENSIVE RESPONSE
        # ==========================================
        return web.json_response(
            {
                "success": True,
                "errors": [],
                "rescan_triggered": rescan_triggered,
                "active_config": self.config,
            }
        )

    async def api_search(self, request):
        import traceback

        try:
            query = request.query.get("q", "")
            if not query:
                return web.json_response({"artists": [], "albums": [], "tracks": []})

            cursor = self.library.conn.cursor()

            # 1. Standard raw search for Albums and Tracks
            standard_search = f"%{query.lower()}%"

            # 2. Normalized search for Artists
            from normalization import ArtistNormalizer

            _, norm_key = ArtistNormalizer.normalize(query)
            artist_search = f"%{norm_key}%"

            # Fetch Tracks (using standard_search)
            cursor.execute(
                """
                SELECT t.id, t.title, ta.name, rg.title, t.duration, r.art_hash, rg.id
                FROM tracks t
                JOIN artists ta ON t.artist_id = ta.id
                JOIN releases r ON t.release_id = r.id
                JOIN release_groups rg ON r.release_group_id = rg.id
                WHERE t.title LIKE ? COLLATE NOCASE
                ORDER BY t.title LIMIT 10
            """,
                (standard_search,),
            )
            tracks = [
                {
                    "id": row[0],
                    "title": row[1],
                    "artist": row[2],
                    "album": row[3],
                    "duration": row[4],
                    "art": row[5],
                    "album_id": row[6],
                }
                for row in cursor.fetchall()
            ]

            # Fetch Albums (using standard_search)
            cursor.execute(
                """
                SELECT rg.id, rg.title, a.name, MIN(r.art_hash)
                FROM release_groups rg
                JOIN artists a ON rg.artist_id = a.id
                LEFT JOIN releases r ON rg.id = r.release_group_id
                WHERE rg.title LIKE ? COLLATE NOCASE
                GROUP BY rg.id 
                ORDER BY rg.title LIMIT 5
            """,
                (standard_search,),
            )
            albums = [
                {"id": row[0], "title": row[1], "artist": row[2], "art_hash": row[3]}
                for row in cursor.fetchall()
            ]

            # Fetch Artists (using the highly accurate normalized artist_search!)
            cursor.execute(
                """
                SELECT a.name, COUNT(DISTINCT rg.id)
                FROM artists a
                LEFT JOIN release_groups rg ON a.id = rg.artist_id
                WHERE a.normalized_key LIKE ? 
                GROUP BY a.id 
                ORDER BY a.name LIMIT 5
            """,
                (artist_search,),
            )
            artists = [
                {"name": row[0], "album_count": row[1]} for row in cursor.fetchall()
            ]

            return web.json_response(
                {"tracks": tracks, "albums": albums, "artists": artists}
            )

        except Exception as e:
            print(f"\n--- CRITICAL ERROR IN api_search ---")
            traceback.print_exc()
            print(f"------------------------------------\n")
            return web.json_response({"error": str(e)}, status=500)

    async def api_get_all_albums(self, request):
        import traceback

        try:
            cursor = self.library.conn.cursor()

            # CRITICAL FIX: We now query the Master Albums (release_groups)
            # instead of individual editions, and grab the first available art_hash.
            cursor.execute("""
                SELECT rg.id, rg.title, a.name, MIN(r.art_hash)
                FROM release_groups rg
                JOIN artists a ON rg.artist_id = a.id
                LEFT JOIN releases r ON rg.id = r.release_group_id
                GROUP BY rg.id
                ORDER BY rg.title COLLATE NOCASE
            """)

            albums = []
            for row in cursor.fetchall():
                albums.append(
                    {
                        "id": row[0],  # This is now safely the Master 'rg_...' ID!
                        "title": row[1],
                        "artist": row[2],
                        "art_hash": row[3],
                    }
                )

            return web.json_response(albums)

        except Exception as e:
            print(f"\n--- CRITICAL ERROR IN api_get_all_albums ---")
            traceback.print_exc()
            print(f"--------------------------------------------\n")
            return web.json_response({"error": str(e)}, status=500)

    async def api_get_album(self, request):
        import traceback
        import urllib.parse

        try:
            # Safely extract the ID from the URL
            album_id = urllib.parse.unquote(request.match_info.get("album_id", ""))
            print(f"--> Requested Album ID: '{album_id}'")

            if not album_id:
                return web.json_response({"error": "Missing ID in URL"}, status=400)
            cursor = self.library.conn.cursor()

            # 1. Fetch Master Album Info
            cursor.execute(
                """
                SELECT rg.title, a.name 
                FROM release_groups rg 
                JOIN artists a ON rg.artist_id = a.id 
                WHERE rg.id=?
            """,
                (album_id,),
            )
            master_row = cursor.fetchone()

            if not master_row:
                return web.json_response({"error": "Album not found"}, status=404)

            album_title, artist_name = master_row

            # 2. Fetch Editions (Releases) with Audio Metrics AND Folder Path
            cursor.execute(
                """
                SELECT id, title, year, label, catalog_num, art_hash, 
                       quality_text, quality_rank, codec, sample_rate, bit_depth, folder_path
                FROM releases 
                WHERE release_group_id=? 
                ORDER BY quality_rank DESC, year ASC
            """,
                (album_id,),
            )

            editions = []
            for r_row in cursor.fetchall():
                rel_id = r_row[0]

                # 3. Fetch Tracks for this specific Edition
                cursor.execute(
                    """
                    SELECT t.id, t.title, t.track_number, t.disc_number, t.duration, t.path, t.mime_type, t.size, a.name, t.start_time, t.end_time
                    FROM tracks t
                    JOIN artists a ON t.artist_id = a.id
                    WHERE t.release_id=? 
                    ORDER BY t.disc_number, t.track_number
                """,
                    (rel_id,),
                )

                tracks = []
                for t_row in cursor.fetchall():
                    tracks.append(
                        {
                            "id": t_row[0],
                            "title": t_row[1],
                            "track_number": t_row[2],
                            "disc_number": t_row[3],
                            "duration": t_row[4],
                            "path": t_row[5],
                            "mime_type": t_row[6],
                            "size": t_row[7],
                            "artist": t_row[8],
                            # Slice Data for CUE Support
                            "start_time": t_row[9],
                            "end_time": t_row[10],
                        }
                    )

                editions.append(
                    {
                        "release_id": rel_id,
                        "edition_title": r_row[1],
                        "year": r_row[2],
                        "label": r_row[3],
                        "catalog": r_row[4],
                        "art_hash": r_row[5],
                        "quality_text": r_row[6],
                        "quality_rank": r_row[7],
                        "codec": r_row[8],
                        "sample_rate": r_row[9],
                        "bit_depth": r_row[10],
                        "folder_path": r_row[11],
                        "tracks": tracks,
                    }
                )

            return web.json_response(
                {
                    "id": album_id,
                    "title": album_title,
                    "artist": artist_name,
                    "editions": editions,
                }
            )

        except Exception as e:
            print(f"\n--- CRITICAL ERROR IN api_get_album ---")
            traceback.print_exc()
            print(f"---------------------------------------\n")
            return web.json_response({"error": str(e)}, status=500)

    async def api_get_all_artists(self, request):
        import traceback

        try:
            cursor = self.library.conn.cursor()

            # Count how many unique conceptual albums (release groups) each artist has
            # Change JOIN to LEFT JOIN to include artists from compilations.
            cursor.execute("""
                SELECT a.name, COUNT(DISTINCT rg.id) 
                FROM artists a
                JOIN release_groups rg ON a.id = rg.artist_id  
                GROUP BY a.id
                ORDER BY a.name
            """)
            rows = cursor.fetchall()

            # Fetch the rich assets from our caching system
            from artist_art import get_cached_artist_assets

            artists = []
            for row in rows:
                name = row[0]
                if not name:
                    continue

                assets = get_cached_artist_assets(name)

                artists.append(
                    {
                        "name": name,
                        "album_count": row[1],
                        "thumbnail": assets.get("thumbnail", ""),
                        "background": assets.get("background", ""),
                        "logo": assets.get("logo", ""),
                    }
                )

            return web.json_response(artists)

        except Exception as e:
            print(f"\n--- CRITICAL ERROR IN api_get_all_artists ---")
            traceback.print_exc()
            print(f"---------------------------------------------\n")
            return web.json_response({"error": str(e)}, status=500)

    async def api_get_artist(self, request):
        import traceback

        try:
            import urllib.parse

            artist_name = urllib.parse.unquote(request.match_info["artist_name"])
            cursor = self.library.conn.cursor()

            # 1. Look up the new Relational Artist ID
            cursor.execute("SELECT id FROM artists WHERE name=?", (artist_name,))
            artist_row = cursor.fetchone()

            if not artist_row:
                return web.json_response(
                    {"error": "Artist not found in database."}, status=404
                )

            artist_id = artist_row[0]

            # 2. Get all conceptual albums (Release Groups) for this specific artist
            # We grab the art_hash from the FIRST edition to use as the cover thumbnail
            cursor.execute(
                """
                SELECT rg.id, rg.title, MIN(r.art_hash)
                FROM release_groups rg
                LEFT JOIN releases r ON rg.id = r.release_group_id
                WHERE rg.artist_id = ?
                GROUP BY rg.id
                ORDER BY rg.title
            """,
                (artist_id,),
            )

            albums = []
            for row in cursor.fetchall():
                albums.append(
                    {
                        "id": row[
                            0
                        ],  # This uses the new rg_ ID so clicking it works perfectly!
                        "title": row[1],
                        "artist": artist_name,
                        "art_hash": row[2],
                    }
                )

            # 3. Fetch the rich assets from our new caching system!
            from artist_art import get_cached_artist_assets

            assets = get_cached_artist_assets(artist_name)

            return web.json_response(
                {
                    "name": artist_name,
                    "albums": albums,
                    "thumbnail": assets.get("thumbnail", ""),
                    "background": assets.get("background", ""),
                    "logo": assets.get("logo", ""),
                }
            )

        except Exception as e:
            print(f"\n--- CRITICAL ERROR IN api_get_artist ---")
            traceback.print_exc()
            print(f"----------------------------------------\n")
            return web.json_response({"error": str(e)}, status=500)

    async def api_get_playlists(self, request):
        cursor = self.library.conn.cursor()
        cursor.execute("SELECT id, name, file_path FROM playlists ORDER BY name")
        playlists = [
            {"id": r[0], "name": r[1], "file_path": r[2]} for r in cursor.fetchall()
        ]
        return web.json_response(playlists)

    async def api_create_playlist(self, request):
        import uuid
        from pathlib import Path

        data = await request.json()
        name = data.get("name", "New Playlist")

        # Determine where to save new playlists (Uses the first configured media directory)
        base_dir = self.config.get("MEDIA_DIRS", ["."])[0]
        playlist_dir = Path(base_dir) / "Playlists"
        playlist_dir.mkdir(exist_ok=True)

        file_path = playlist_dir / f"{name}.m3u"
        playlist_id = str(uuid.uuid4())

        cursor = self.library.conn.cursor()
        cursor.execute(
            "INSERT INTO playlists (id, name, file_path) VALUES (?, ?, ?)",
            (playlist_id, name, str(file_path)),
        )
        self.library.conn.commit()

        # Write an empty M3U file to disk immediately
        from playlist_manager import PlaylistManager

        PlaylistManager.write_m3u(file_path, name, [])

        return web.json_response({"success": True, "id": playlist_id, "name": name})
    
    async def api_get_playlist_tracks(self, request):
        import traceback
        import urllib.parse
        
        try:
            playlist_id = urllib.parse.unquote(request.match_info.get("playlist_id", ""))
            cursor = self.library.conn.cursor()
            
            # 1. Get Playlist Metadata
            cursor.execute("SELECT name, file_path FROM playlists WHERE id=?", (playlist_id,))
            row = cursor.fetchone()
            
            if not row:
                return web.json_response({"error": "Playlist not found"}, status=404)
                
            playlist_name, file_path = row
            
            # 2. Get Ordered Tracks with full UI Metadata
            # We join across 5 tables to ensure the React UI gets the album art and artist names!
            cursor.execute('''
                SELECT t.id, t.title, t.duration, t.path, t.mime_type, a.name, r.art_hash, rg.title
                FROM playlist_tracks pt
                JOIN tracks t ON pt.track_id = t.id
                JOIN artists a ON t.artist_id = a.id
                LEFT JOIN releases r ON t.release_id = r.id
                LEFT JOIN release_groups rg ON r.release_group_id = rg.id
                WHERE pt.playlist_id=?
                ORDER BY pt.position
            ''', (playlist_id,))
            
            tracks = []
            for t_row in cursor.fetchall():
                tracks.append({
                    "id": t_row[0],
                    "title": t_row[1],
                    "duration": t_row[2],
                    "path": t_row[3],
                    "mime_type": t_row[4],
                    "artist": t_row[5],
                    "art_hash": t_row[6],
                    "album": t_row[7]
                })
                
            return web.json_response({
                "id": playlist_id,
                "name": playlist_name,
                "file_path": file_path,
                "tracks": tracks
            })
            
        except Exception as e:
            print(f"\n--- CRITICAL ERROR IN api_get_playlist_tracks ---")
            traceback.print_exc()
            return web.json_response({"error": str(e)}, status=500)
        

    async def api_add_to_playlist(self, request):
        playlist_id = request.match_info["playlist_id"]
        data = await request.json()
        track_id = data.get("track_id")

        cursor = self.library.conn.cursor()

        # 1. Get the target playlist file path
        cursor.execute(
            "SELECT file_path, name FROM playlists WHERE id=?", (playlist_id,)
        )
        row = cursor.fetchone()
        if not row:
            return web.json_response({"error": "Playlist not found"}, status=404)
        file_path, playlist_name = row

        # 2. Get the next position index
        cursor.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM playlist_tracks WHERE playlist_id=?",
            (playlist_id,),
        )
        next_pos = cursor.fetchone()[0]

        # 3. Insert into the database
        cursor.execute(
            "INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (?, ?, ?)",
            (playlist_id, track_id, next_pos),
        )
        self.library.conn.commit()

        # 4. Fetch the full, updated tracklist to write to disk
        cursor.execute(
            """
            SELECT t.path, t.duration, t.title, a.name 
            FROM playlist_tracks pt
            JOIN tracks t ON pt.track_id = t.id
            JOIN artists a ON t.artist_id = a.id
            WHERE pt.playlist_id=?
            ORDER BY pt.position
        """,
            (playlist_id,),
        )

        tracks_data = []
        for r in cursor.fetchall():
            tracks_data.append(
                {"path": r[0], "duration": r[1], "title": r[2], "artist": r[3]}
            )

        # 5. Overwrite the physical M3U file to sync the changes!
        from playlist_manager import PlaylistManager

        PlaylistManager.write_m3u(file_path, playlist_name, tracks_data)

        return web.json_response({"success": True})


# ==========================================
# 4. Main Event Loop
# ==========================================
async def main():
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_running_loop()

    # --- THE WINDOWS 10054 SILENCER ---
    def silence_winerror(loop, context):
        exc = context.get("exception")
        # If it's the exact Windows socket disconnect error, ignore it completely
        if (
            isinstance(exc, ConnectionResetError)
            and getattr(exc, "winerror", None) == 10054
        ):
            return
        # Otherwise, process exceptions normally
        loop.default_exception_handler(context)

    loop.set_exception_handler(silence_winerror)

    # 1. Load the persistent configuration
    config_file = os.path.expanduser(
        "~/.audiophile_server/server_config.json"
    )
    app_config = load_config(config_file)

    # Extract settings
    host_ip = app_config["BIND_IP"]
    host_port = app_config["PORT"]
    media_directories = app_config["MEDIA_DIRS"]
    # server_uuid = app_config["UUID"]

    # 2. Initialize the Database/Library Scanner
    library = MediaLibrary(db_path=os.path.expanduser("~/.audiophile_server/media.db"))
    # If there are directories configured, do an initial background check
    if media_directories:
        logger.info(f"Loaded {len(media_directories)} media directories from config.")
        # Optional: Start a background thread to verify/index them on boot
        import threading

        threading.Thread(
            target=library.scan_directories, args=(media_directories,), daemon=True
        ).start()

    loop = asyncio.get_running_loop()

    # Start SSDP
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: SSDPProtocol(host_ip, host_port, UUID),
        local_addr=("0.0.0.0", 1900),
        allow_broadcast=True,
    )

    # Start Web Server
    upnp_server = UPnPServer(library, host_ip, host_port, UUID, config_path=config_file)
    upnp_server.config = app_config
    runner = web.AppRunner(upnp_server.app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', host_port)
    await site.start()

    logger.info(f"Server started on http://{host_ip}:{host_port}")

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        transport.close()
        await runner.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
