import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger("Transcoder")

class AudioTranscoder:
    def __init__(self, cache_dir: str = "transcode_cache", max_cache_mb: int = 2000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_cache_mb = max_cache_mb
        self._active_transcodes = {}

        # Run an initial cleanup on server boot just in case it was left full
        asyncio.create_task(self.cleanup_cache())

    async def get_transcoded_file(self, input_path: str, media_id: str) -> Path:
        """
        Returns the path to the transcoded FLAC file. 
        If not cached, transcodes it on the fly.
        """
        cache_path = self.cache_dir / f"{media_id}.flac"

        # 1. Cache Hit (Instant Playback)
        if cache_path.exists() and cache_path.stat().st_size > 0:
            # "Touch" the file to update its modified time.
            # This is critical for the LRU algorithm to know this file was just used.
            try:
                cache_path.touch(exist_ok=True)
            except OSError:
                pass 
            return cache_path

        # 2. Prevent race conditions
        if media_id in self._active_transcodes:
            await self._active_transcodes[media_id]
            return cache_path

        # 3. Transcode Miss - Execute FFmpeg
        future = asyncio.get_running_loop().create_future()
        self._active_transcodes[media_id] = future

        try:
            input_ext = Path(input_path).suffix.lower().lstrip(".")
            logger.info(
                f"Starting on-the-fly {input_ext.upper()}->FLAC transcode for {media_id}"
            )

            process = await asyncio.create_subprocess_exec(
                'ffmpeg', '-i', str(input_path),
                '-c:a', 'flac',
                '-compression_level', '5',
                '-map_metadata', '0',
                '-y', str(cache_path),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )

            _, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                logger.error(f"FFmpeg Transcode failed: {error_msg}")
                if cache_path.exists():
                    cache_path.unlink()
                raise RuntimeError("Audio transcoding failed")

            logger.info(f"Transcode complete for {media_id}")
            future.set_result(True)

            # --- NEW: Trigger LRU Cleanup in the background ---
            # We fire this off without 'await' so the audio stream starts immediately!
            asyncio.create_task(self.cleanup_cache())

            return cache_path

        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            self._active_transcodes.pop(media_id, None)

    async def cleanup_cache(self):
        """
        Enforces an LRU cache limit on the transcode directory.
        Offloads blocking file I/O to a background thread.
        """
        loop = asyncio.get_running_loop()

        def _sync_cleanup():
            max_bytes = self.max_cache_mb * 1024 * 1024
            files = []
            total_size = 0

            # Gather all cached files and their stats
            for p in self.cache_dir.glob('*.flac'):
                # Crucial: Do not delete files that are currently being created!
                if p.stem in self._active_transcodes:
                    continue

                try:
                    stat = p.stat()
                    # We use st_mtime because .touch() updates it reliably
                    files.append((p, stat.st_size, stat.st_mtime))
                    total_size += stat.st_size
                except FileNotFoundError:
                    pass # File was already deleted by another process

            # If we are under the limit, do nothing
            if total_size <= max_bytes:
                return 0

            # Sort files by modified time (oldest first)
            files.sort(key=lambda x: x[2])

            bytes_deleted = 0
            for p, size, _ in files:
                # Stop deleting once we are back under the maximum size
                if total_size <= max_bytes:
                    break

                try:
                    p.unlink()
                    total_size -= size
                    bytes_deleted += size
                    logger.debug(f"LRU Cache Cleanup: Deleted {p.name} ({size / 1024 / 1024:.2f} MB)")
                except OSError as e:
                    logger.warning(f"Failed to delete cached file {p.name}: {e}")

            if bytes_deleted > 0:
                logger.info(f"LRU Cache Cleanup freed {bytes_deleted / 1024 / 1024:.2f} MB.")

            return bytes_deleted

        # Run the synchronous cleanup logic in the executor
        await loop.run_in_executor(None, _sync_cleanup)
