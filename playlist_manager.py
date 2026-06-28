import os
from pathlib import Path
import logging

logger = logging.getLogger("PlaylistManager")

class PlaylistManager:
    @staticmethod
    def parse_m3u(m3u_path):
        """Reads an M3U file and extracts absolute paths for all tracks."""
        tracks = []
        try:
            with open(m3u_path, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    # Resolve relative paths relative to the M3U file's location
                    target_path = Path(line)
                    if not target_path.is_absolute():
                        target_path = (Path(m3u_path).parent / target_path).resolve()
                        
                    if target_path.exists():
                        tracks.append(str(target_path))
                        
        except Exception as e:
            logger.error(f"Failed to parse {m3u_path}: {e}")
        return tracks

    @staticmethod
    def write_m3u(m3u_path, playlist_name, tracks_data):
        """Writes database track metadata back out to a physical M3U file."""
        try:
            # Ensure the directory exists
            Path(m3u_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(m3u_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                for t in tracks_data:
                    duration = int(t.get('duration', 0))
                    artist = t.get('artist', 'Unknown')
                    title = t.get('title', 'Unknown')
                    path = t.get('path', '')
                    
                    # Write the Extended Info and the absolute path
                    f.write(f"#EXTINF:{duration},{artist} - {title}\n")
                    f.write(f"{path}\n")
            return True
        except Exception as e:
            logger.error(f"Failed to write M3U {m3u_path}: {e}")
            return False