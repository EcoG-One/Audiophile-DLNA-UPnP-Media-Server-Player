import re
from pathlib import Path

class CueParser:
    @staticmethod
    def time_to_seconds(time_str):
        """Converts CUE timecode (MM:SS:FF) where FF is frames (1/75th of a sec) to raw seconds."""
        parts = time_str.split(':')
        if len(parts) == 3:
            m, s, f = int(parts[0]), int(parts[1]), int(parts[2])
            return (m * 60) + s + (f / 75.0)
        return 0.0

    @staticmethod
    def parse(cue_path):
        """Extracts Master Album info and Virtual Tracks from a .cue file."""
        # Try multiple encodings, as CUE files are notoriously inconsistent
        content = ""
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1']:
            try:
                with open(cue_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        album_info = {
            'title': 'Unknown Album',
            'artist': 'Unknown Artist',
            'file': None,
            'tracks': []
        }

        current_track = None
        file_count = 0

        for line in content.splitlines():
            line = line.strip()
            if not line: continue

            # Extract quoted strings or take the rest of the line
            def extract_val(l):
                match = re.findall(r'"([^"]+)"', l)
                return match[0] if match else l.split(' ', 1)[1]

            # Global Metadata
            if line.startswith('TITLE') and not current_track:
                album_info['title'] = extract_val(line)
            elif line.startswith('PERFORMER') and not current_track:
                album_info['artist'] = extract_val(line)
            elif line.startswith("FILE"):
                file_count += 1
                if file_count > 1:
                    print(f"⏭️ [SKIP] Multi-file CUE sheet ignored: {cue_path.name}")
                    return None  # Returning None safely aborts the injection in the main scanner
                album_info["file"] = extract_val(line)

            # Track Metadata
            elif line.startswith('TRACK'):
                if current_track:
                    album_info['tracks'].append(current_track)
                parts = line.split()
                track_num = int(parts[1])
                current_track = {
                    'track_number': track_num, 
                    'title': f'Track {track_num}', 
                    'artist': album_info['artist'], 
                    'start_time': 0.0
                }
            elif line.startswith('TITLE') and current_track:
                current_track['title'] = extract_val(line)
            elif line.startswith('PERFORMER') and current_track:
                current_track['artist'] = extract_val(line)
            elif line.startswith('INDEX 01') and current_track:
                time_str = line.split()[2]
                current_track['start_time'] = CueParser.time_to_seconds(time_str)

        # Append the final track
        if current_track:
            album_info['tracks'].append(current_track)

        return album_info
