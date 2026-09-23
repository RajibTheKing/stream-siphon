"""Background download of the best-quality audio for a YouTube URL, as MP3."""

from __future__ import annotations

import uuid
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from yt_dlp import YoutubeDL

from ..config import DEFAULT_DOWNLOAD_DIR
from .models import Track


class DownloadWorker(QThread):
    """Runs yt-dlp off the UI thread and reports progress/result via signals."""

    progress = Signal(float, str)  # percent (0-100), status text
    finished = Signal(Track)
    failed = Signal(str)

    def __init__(self, url: str, output_dir: Path = DEFAULT_DOWNLOAD_DIR, parent=None):
        super().__init__(parent)
        self._url = url.strip()
        self._output_dir = output_dir
        self._track_id = uuid.uuid4().hex[:12]

    def _on_progress_hook(self, status: dict) -> None:
        if status.get("status") == "downloading":
            total = status.get("total_bytes") or status.get("total_bytes_estimate")
            downloaded = status.get("downloaded_bytes", 0)
            pct = (downloaded / total * 100) if total else 0.0
            self.progress.emit(pct, "Downloading...")
        elif status.get("status") == "finished":
            self.progress.emit(100.0, "Converting to MP3...")

    def run(self) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)

        outtmpl = str(self._output_dir / f"{self._track_id}_%(title)s.%(ext)s")
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [self._on_progress_hook],
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "0",  # 0 = best available VBR quality
                }
            ],
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self._url, download=True)
                # Filename before postprocessing swaps the extension to .mp3.
                original_path = Path(ydl.prepare_filename(info))
        except Exception as exc:  # noqa: BLE001 - surface any yt-dlp/ffmpeg error to the UI
            self.failed.emit(str(exc))
            return

        mp3_path = original_path.with_suffix(".mp3")
        if not mp3_path.exists():
            matches = list(self._output_dir.glob(f"{self._track_id}_*.mp3"))
            if not matches:
                self.failed.emit("Download finished but the MP3 file could not be located.")
                return
            mp3_path = matches[0]

        track = Track(
            id=self._track_id,
            title=info.get("title", "Unknown title"),
            artist=info.get("uploader", "Unknown"),
            duration=int(info.get("duration") or 0),
            file_path=str(mp3_path),
            thumbnail_url=info.get("thumbnail", "") or "",
            source_url=self._url,
        )
        self.finished.emit(track)
