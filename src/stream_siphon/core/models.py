"""Track data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Track:
    id: str
    title: str
    artist: str = "Unknown"
    composer: str = ""
    album: str = ""
    duration: int = 0  # seconds
    file_path: str = ""
    thumbnail_url: str = ""
    source_url: str = ""
    published_at: str = ""
    added_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "composer": self.composer,
            "album": self.album,
            "duration": self.duration,
            "file_path": self.file_path,
            "thumbnail_url": self.thumbnail_url,
            "source_url": self.source_url,
            "published_at": self.published_at,
            "added_at": self.added_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Track":
        return Track(
            id=data.get("id", ""),
            title=data.get("title", "Unknown"),
            artist=data.get("artist", "Unknown"),
            composer=data.get("composer", ""),
            album=data.get("album", ""),
            duration=data.get("duration", 0),
            file_path=data.get("file_path", ""),
            thumbnail_url=data.get("thumbnail_url", ""),
            source_url=data.get("source_url", ""),
            published_at=data.get("published_at", ""),
            added_at=data.get("added_at", ""),
        )
