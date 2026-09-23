"""JSON-backed store of downloaded tracks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from ..config import LIBRARY_FILE, ensure_dirs
from .models import Track


class Library:
    def __init__(self, library_file: Path = LIBRARY_FILE):
        self._file = library_file
        self._tracks: List[Track] = []
        ensure_dirs()
        self.load()

    def load(self) -> None:
        if self._file.exists():
            try:
                data = json.loads(self._file.read_text(encoding="utf-8"))
                self._tracks = [Track.from_dict(item) for item in data]
            except (json.JSONDecodeError, OSError):
                self._tracks = []
        else:
            self._tracks = []
        # Drop entries whose MP3 file was deleted/moved outside the app.
        self._tracks = [t for t in self._tracks if Path(t.file_path).exists()]

    def save(self) -> None:
        data = [t.to_dict() for t in self._tracks]
        self._file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def all(self) -> List[Track]:
        return list(self._tracks)

    def add(self, track: Track) -> None:
        self._tracks = [t for t in self._tracks if t.id != track.id]
        self._tracks.append(track)
        self.save()

    def remove(self, track_id: str) -> Optional[Track]:
        for t in self._tracks:
            if t.id == track_id:
                self._tracks.remove(t)
                self.save()
                return t
        return None

    def find(self, track_id: str) -> Optional[Track]:
        for t in self._tracks:
            if t.id == track_id:
                return t
        return None
