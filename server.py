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
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()

        # 1. Artists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS artists (
                id TEXT PRIMARY KEY,
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
                path TEXT UNIQUE NOT NULL,
                mime_type TEXT,
                size INTEGER,
                FOREIGN KEY(release_id) REFERENCES releases(id),
                FOREIGN KEY(artist_id) REFERENCES artists(id)
            )
        """)

        # Create indexes for fast UI lookups
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_rg_artist ON release_groups(artist_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_rel_rg ON releases(release_group_id)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trk_rel ON tracks(release_id)")

        self.conn.commit()

    def scan_directories(self, directories):
        logger.info("Starting media scan...")
        cursor = self.conn.cursor()
        supported_exts = {'.flac', '.wav', '.mp3', '.dsf', '.m4a'}

        for directory in directories:
            path = Path(directory)
            for file_path in path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in supported_exts:
                    self._index_file(file_path, cursor)
        self.conn.commit()
        self._fetch_missing_artist_art()
        logger.info("Scan complete.")

    def _index_file(self, file_path: Path, cursor):
        try:          
            audio = File(file_path, easy=True)
            if audio is None:
                return

            # --- 1. Basic Metadata Extraction ---
            title = audio.get("title", [file_path.stem])[0]

            # Extract both Track Artist and Album Artist
            track_artist_name = audio.get("artist", ["Unknown Artist"])[0]
            # Fallback: If Album Artist is missing, use Track Artist
            album_artist_name = audio.get("albumartist", [track_artist_name])[0]

            album_name = audio.get("album", ["Unknown Album"])[0]

            # --- 2. Advanced Metadata / Identifiers ---
            mb_track_artist_id = audio.get("musicbrainz_artistid", [None])[0]
            mb_album_artist_id = audio.get(
                "musicbrainz_albumartistid", [mb_track_artist_id]
            )[0]

            mb_release_group_id = audio.get("musicbrainz_releasegroupid", [None])[0]
            mb_release_id = audio.get("musicbrainz_albumid", [None])[0]
            mb_track_id = audio.get("musicbrainz_trackid", [None])[0]

            year = audio.get("date", audio.get("originaldate", [""]))[0][:4]
            label = audio.get("organization", audio.get("label", [""]))[0]
            cat_num = audio.get("catalognumber", [""])[0]
            barcode = audio.get("barcode", [""])[0]

            import re

            def parse_num(val):
                match = re.search(r"\d+", str(val))
                return int(match.group()) if match else 1

            track_num = parse_num(audio.get("tracknumber", [0])[0])
            disc_num = parse_num(audio.get("discnumber", [1])[0])

            # --- 3. WATERFALL ID GENERATION ---

            track_artist_id = (
                mb_track_artist_id
                if mb_track_artist_id
                else hashlib.md5(track_artist_name.encode()).hexdigest()
            )
            album_artist_id = (
                mb_album_artist_id
                if mb_album_artist_id
                else hashlib.md5(album_artist_name.encode()).hexdigest()
            )

            if mb_release_group_id:
                rg_id = f"rg_{mb_release_group_id}"
            else:
                # Group by ALBUM ARTIST instead of Track Artist
                rg_id = hashlib.md5(
                    f"{album_artist_id}_{album_name}".encode()
                ).hexdigest()

            if mb_release_id:
                release_id = f"rel_{mb_release_id}"
                release_title = album_name
            else:
                folder_path = str(file_path.parent)
                sig = f"{rg_id}_{year}_{label}_{cat_num}_{barcode}_{folder_path}"
                release_id = hashlib.md5(sig.encode()).hexdigest()

                edition_hints = [year, label, cat_num]
                hints = [h for h in edition_hints if h]
                release_title = (
                    f"{album_name} [{' | '.join(hints)}]" if hints else album_name
                )

            track_id = (
                mb_track_id
                if mb_track_id
                else hashlib.md5(
                    f"{release_id}_{disc_num}_{track_num}_{title}".encode()
                ).hexdigest()
            )

            # --- 4. DATABASE UPSERTS ---

            # Insert BOTH artists (SQLite IGNORE ensures no duplicates)
            cursor.execute(
                "INSERT OR IGNORE INTO artists (id, mbid, name) VALUES (?, ?, ?)",
                (track_artist_id, mb_track_artist_id, track_artist_name),
            )
            cursor.execute(
                "INSERT OR IGNORE INTO artists (id, mbid, name) VALUES (?, ?, ?)",
                (album_artist_id, mb_album_artist_id, album_artist_name),
            )

            # Release Group is owned by the ALBUM ARTIST
            cursor.execute(
                "INSERT OR IGNORE INTO release_groups (id, mbid, artist_id, title) VALUES (?, ?, ?, ?)",
                (rg_id, mb_release_group_id, album_artist_id, album_name),
            )

            # (Insert Release logic remains exactly the same...)
            art_hash = self._extract_and_cache_art(file_path, release_id)
            cursor.execute(
                """
                INSERT OR IGNORE INTO releases 
                (id, release_group_id, mbid, title, year, label, catalog_num, barcode, folder_path, art_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )

            # Track is owned by the TRACK ARTIST
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

        except Exception as e:
            print(f"Failed to index {file_path}: {e}")

    def _extract_and_cache_art(self, file_path, album_name):
        """Extracts embedded artwork and saves it using a hash of the album name."""
        if album_name == "Unknown Album":
            return None

        # Create a safe, unique filename for the album art
        album_hash = hashlib.md5(album_name.encode("utf-8")).hexdigest()
        cache_path = Path(ART_CACHE_DIR) / f"{album_hash}.jpg"

        # Skip extraction if we already cached art for this album
        if cache_path.exists():
            return album_hash

        try:
            art_data = None
            extension = file_path.suffix.lower()

            # FLAC
            if extension == ".flac":
                audio = FLAC(file_path)
                if audio.pictures:
                    art_data = audio.pictures[0].data

            # MP3 (ID3)
            elif extension == ".mp3":
                audio = MP3(file_path)
                for tag in audio.tags.values():
                    if tag.FrameID == "APIC":
                        art_data = tag.data
                        break

            # M4A / ALAC / MP4
            elif extension in [".m4a", ".mp4"]:
                audio = MP4(file_path)
                if "covr" in audio.tags and audio.tags["covr"]:
                    art_data = audio.tags["covr"][0]

            # Save to disk if found
            if art_data:
                with open(cache_path, "wb") as f:
                    f.write(art_data)
                return album_hash

        except Exception as e:
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
            # We assume ALAC for m4a containers to trigger the transcoder check
            codec = "alac"
        elif lower_path.endswith(".flac"):
            codec = "flac"

        # 3. Transcoding & Delivery Logic
        try:
            user_agent = request.headers.get("User-Agent", "")

            # If you placed your BrowserCapabilities class in capabilities.py, import it:
            from capabilities import BrowserCapabilities

            if BrowserCapabilities.needs_alac_transcoding(user_agent, codec):
                # We assume you attached transcoder to self. If it's a global, just use `transcoder`
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
            query = request.query.get("q", "").lower()
            if not query:
                return web.json_response({"artists": [], "albums": [], "tracks": []})

            cursor = self.library.conn.cursor()
            search_term = f"%{query}%"

            # 1. Fetch Tracks (Updated JOIN for Track Artist)
            cursor.execute(
                """
                SELECT t.id, t.title, ta.name, rg.title, t.duration, r.art_hash
                FROM tracks t
                JOIN artists ta ON t.artist_id = ta.id
                JOIN releases r ON t.release_id = r.id
                JOIN release_groups rg ON r.release_group_id = rg.id
                WHERE t.title LIKE ? 
                ORDER BY t.title LIMIT 10
            """,
                (search_term,),
            )
            tracks = [
                {
                    "id": row[0],
                    "title": row[1],
                    "artist": row[2],
                    "album": row[3],
                    "duration": row[4],
                    "art": row[5],
                }
                for row in cursor.fetchall()
            ]

            # 2. Fetch Conceptual Albums / Release Groups (Limit 5)
            cursor.execute(
                """
                SELECT rg.id, rg.title, a.name, MIN(r.art_hash)
                FROM release_groups rg
                JOIN artists a ON rg.artist_id = a.id
                LEFT JOIN releases r ON rg.id = r.release_group_id
                WHERE rg.title LIKE ? 
                GROUP BY rg.id 
                ORDER BY rg.title LIMIT 5
            """,
                (search_term,),
            )
            # We return the rg_id so the React Router knows exactly where to navigate
            albums = [
                {"id": row[0], "title": row[1], "artist": row[2], "art_hash": row[3]}
                for row in cursor.fetchall()
            ]

            # 3. Fetch Artists (Limit 5)
            cursor.execute(
                """
                SELECT a.name, COUNT(DISTINCT rg.id)
                FROM artists a
                LEFT JOIN release_groups rg ON a.id = rg.artist_id
                WHERE a.name LIKE ? 
                GROUP BY a.id 
                ORDER BY a.name LIMIT 5
            """,
                (search_term,),
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

            # We grab the art_hash from the FIRST release in the group to use as the cover
            cursor.execute("""
                SELECT rg.id, rg.title, a.name, MIN(r.art_hash) 
                FROM release_groups rg
                JOIN artists a ON rg.artist_id = a.id
                JOIN releases r ON rg.id = r.release_group_id
                GROUP BY rg.id
                ORDER BY a.name, rg.title
            """)

            albums = [
                {"id": row[0], "title": row[1], "artist": row[2], "art_hash": row[3]}
                for row in cursor.fetchall()
            ]
            return web.json_response(albums)

        except Exception as e:
            print(f"\n--- CRITICAL ERROR IN api_get_all_albums ---")
            traceback.print_exc()
            print(f"--------------------------------------------\n")
            return web.json_response({"error": str(e)}, status=500)

    async def api_get_album(self, request):
        import traceback

        try:
            rg_id = request.match_info["album_id"]
            cursor = self.library.conn.cursor()

            # Get Group Meta (Album Title and Artist Name)
            cursor.execute(
                "SELECT title, (SELECT name FROM artists WHERE id=artist_id) FROM release_groups WHERE id=?",
                (rg_id,),
            )
            meta = cursor.fetchone()

            if not meta:
                return web.json_response(
                    {"error": "Album not found in database"}, status=404
                )

            album_title = meta[0]
            album_artist = meta[1]

            # Get all Releases (Editions) for this group
            cursor.execute(
                "SELECT id, title, year, label, catalog_num, art_hash FROM releases WHERE release_group_id=? ORDER BY year",
                (rg_id,),
            )
            release_rows = cursor.fetchall()

            editions = []
            for r_row in release_rows:
                rel_id = r_row[0]

                # Fetch tracks AND their specific Track Artist
                cursor.execute(
                    """
                    SELECT t.id, t.title, t.duration, t.track_number, t.disc_number, a.name 
                    FROM tracks t
                    JOIN artists a ON t.artist_id = a.id
                    WHERE t.release_id=? 
                    ORDER BY t.disc_number, t.track_number
                """,
                    (rel_id,),
                )

                tracks = [
                    {
                        "id": t[0],
                        "title": t[1],
                        "duration": t[2],
                        "track_number": t[3],
                        "disc_number": t[4],
                        "artist": t[5],  # This is the specific Track Artist!
                    }
                    for t in cursor.fetchall()
                ]

                editions.append(
                    {
                        "id": rel_id,
                        "edition_title": r_row[1],
                        "year": r_row[2],
                        "label": r_row[3],
                        "catalog": r_row[4],
                        "art_hash": r_row[5],
                        "tracks": tracks,
                    }
                )

            return web.json_response(
                {"title": album_title, "artist": album_artist, "editions": editions}
            )

        except Exception as e:
            print(f"\n--- CRITICAL ERROR IN api_get_album ---")
            traceback.print_exc()
            print(f"----------------------------------------\n")
            # Always return valid JSON, even on a total crash, so React doesn't break
            return web.json_response({"error": str(e)}, status=500)

    async def api_get_all_artists(self, request):
        import traceback

        try:
            cursor = self.library.conn.cursor()

            # Count how many unique conceptual albums (release groups) each artist has
            cursor.execute("""
                SELECT a.name, COUNT(DISTINCT rg.id) 
                FROM artists a
                LEFT JOIN release_groups rg ON a.id = rg.artist_id
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


# ==========================================
# 4. Main Event Loop
# ==========================================
async def main():
    logging.basicConfig(level=logging.INFO)

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
