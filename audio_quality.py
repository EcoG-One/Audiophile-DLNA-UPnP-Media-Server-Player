class AudioAnalyzer:
    @staticmethod
    def analyze(file_path, audio_obj):
        """
        Interrogates audio file headers safely, handling missing or corrupted metadata,
        and assigns a standardized Audiophile Quality Rank.
        """
        # Safely handle file_path whether it's a string or a pathlib.Path
        ext = file_path.suffix.lower() if hasattr(file_path, "suffix") else ""
        info = getattr(audio_obj, "info", None)

        if not info:
            return {
                "codec": "Unknown",
                "sample_rate": 0,
                "bit_depth": 0,
                "bitrate": 0,
                "quality_text": "Unknown",
                "quality_rank": 0,
            }

        # --- CRITICAL FIX: Safe Integer Casting ---
        # Mutagen will frequently return None or strings for missing headers.
        # This forces them to safely become 0 so our logic doesn't crash.
        def safe_int(val):
            try:
                return int(val) if val is not None else 0
            except (TypeError, ValueError):
                return 0

        sample_rate = safe_int(getattr(info, "sample_rate", 0))
        bitrate = safe_int(getattr(info, "bitrate", 0))
        bit_depth = safe_int(getattr(info, "bits_per_sample", 0))
        # ------------------------------------------

        # 1. Codec Detection
        codec = "Unknown"
        if ext == ".flac":
            codec = "FLAC"
        elif ext == ".mp3":
            codec = "MP3"
        elif ext in [".m4a", ".mp4"]:
            # Apple containers can hold Lossless (ALAC) or Lossy (AAC)
            codec = "ALAC" if bit_depth > 0 or bitrate > 400000 else "AAC"
        elif ext == ".wav":
            codec = "WAV"
        elif ext in [".aiff", ".aif"]:
            codec = "AIFF"
        elif ext == ".ogg":
            codec = "OGG"
        elif ext in [".dsf", ".dff"]:
            codec = "DSD"

        # 2. Fix Missing Bit Depths for known lossless formats
        if codec in ["FLAC", "ALAC", "WAV", "AIFF"] and bit_depth == 0:
            bit_depth = 16

        # 3. MQA Detection Placeholder
        is_mqa = False

        # 4. Classification & Ranking
        if is_mqa:
            quality_text = "Master Quality Authenticated"
            quality_rank = 40
        elif codec in ["FLAC", "ALAC", "WAV", "AIFF", "DSD"]:
            if sample_rate > 48000 or bit_depth > 16 or codec == "DSD":
                quality_text = "High-Resolution Lossless"
                quality_rank = 30
            else:
                quality_text = "CD-Quality Lossless"
                quality_rank = 20
        else:
            quality_text = "Lossy"
            quality_rank = 10

        return {
            "codec": codec,
            "sample_rate": sample_rate,
            "bit_depth": bit_depth,
            "bitrate": bitrate,
            "quality_text": quality_text,
            "quality_rank": quality_rank,
        }
