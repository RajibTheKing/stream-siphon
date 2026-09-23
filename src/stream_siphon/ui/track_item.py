"""Single row widget shown in the dashboard's audio list."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ..core.models import Track


def format_duration(seconds: int) -> str:
    minutes, secs = divmod(max(int(seconds), 0), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


class TrackItemWidget(QFrame):
    play_requested = Signal(str)
    edit_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, track: Track, parent=None):
        super().__init__(parent)
        self.track = track
        self.setObjectName("TrackItem")
        self._build_ui()
        self.setToolTip(self._build_tooltip())

    def _build_tooltip(self) -> str:
        lines = [f"Singer: {self.track.artist or 'Unknown'}"]
        if self.track.composer:
            lines.append(f"Composer: {self.track.composer}")
        if self.track.album:
            lines.append(f"Album: {self.track.album}")
        if self.track.published_at:
            lines.append(f"Published: {self.track.published_at}")
        return "\n".join(lines)

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        self.play_button = QPushButton("▶")
        self.play_button.setObjectName("PlayButton")
        self.play_button.setFixedSize(36, 36)
        self.play_button.clicked.connect(lambda: self.play_requested.emit(self.track.id))
        layout.addWidget(self.play_button)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self.title_label = QLabel(self.track.title)
        self.title_label.setObjectName("TrackTitle")
        self.title_label.setWordWrap(True)
        self.artist_label = QLabel(self.track.artist)
        self.artist_label.setObjectName("TrackArtist")
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.artist_label)
        layout.addLayout(text_layout, stretch=1)

        self.duration_label = QLabel(format_duration(self.track.duration))
        self.duration_label.setObjectName("TrackDuration")
        layout.addWidget(self.duration_label)

        self.edit_button = QPushButton("✎")
        self.edit_button.setObjectName("EditButton")
        self.edit_button.setFixedSize(32, 32)
        self.edit_button.setToolTip("Edit MP3 tags")
        self.edit_button.clicked.connect(lambda: self.edit_requested.emit(self.track.id))
        layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("🗑")
        self.delete_button.setObjectName("DeleteButton")
        self.delete_button.setFixedSize(32, 32)
        self.delete_button.clicked.connect(lambda: self.delete_requested.emit(self.track.id))
        layout.addWidget(self.delete_button)

    def set_playing(self, playing: bool) -> None:
        self.play_button.setText("⏸" if playing else "▶")
