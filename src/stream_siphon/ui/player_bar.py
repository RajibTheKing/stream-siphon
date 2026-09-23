"""Bottom mini-player: now-playing info, seek bar, transport controls and speed."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStyle,
    QVBoxLayout,
)

from .track_item import format_duration

SPEED_OPTIONS = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
SKIP_MS = 10_000


class SeekSlider(QSlider):
    """Horizontal slider that jumps straight to the clicked position instead of paging."""

    def _value_from_x(self, x: int) -> int:
        return QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), x, max(self.width(), 1))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSliderDown(True)
            self.setSliderPosition(self._value_from_x(int(event.position().x())))
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.setSliderPosition(self._value_from_x(int(event.position().x())))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSliderDown(False)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class PlayerBar(QFrame):
    play_pause_clicked = Signal()
    seek_moved = Signal(int)
    skip_requested = Signal(int)
    rate_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PlayerBar")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        info_row = QHBoxLayout()
        self.art_label = QLabel("♪")
        self.art_label.setObjectName("PlayerArt")
        self.art_label.setFixedSize(40, 40)
        self.art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_row.addWidget(self.art_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        self.title_label = QLabel("Nothing playing")
        self.title_label.setObjectName("NowPlayingTitle")
        self.artist_label = QLabel("Pick a track from your library")
        self.artist_label.setObjectName("NowPlayingArtist")
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.artist_label)
        info_row.addLayout(text_layout, 1)

        speed_label = QLabel("Speed")
        speed_label.setObjectName("NowPlayingArtist")
        info_row.addWidget(speed_label)
        self.speed_combo = QComboBox()
        self.speed_combo.setObjectName("SpeedCombo")
        for speed in SPEED_OPTIONS:
            self.speed_combo.addItem(f"{speed:g}x", speed)
        self.speed_combo.setCurrentIndex(SPEED_OPTIONS.index(1.0))
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        info_row.addWidget(self.speed_combo)
        layout.addLayout(info_row)

        seek_row = QHBoxLayout()
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setObjectName("TimeLabel")
        self.seek_slider = SeekSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setObjectName("SeekSlider")
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderMoved.connect(self._on_seek_moved)
        self.total_time_label = QLabel("0:00")
        self.total_time_label.setObjectName("TimeLabel")
        seek_row.addWidget(self.current_time_label)
        seek_row.addWidget(self.seek_slider, 1)
        seek_row.addWidget(self.total_time_label)
        layout.addLayout(seek_row)

        transport_row = QHBoxLayout()
        transport_row.addStretch(1)
        self.rewind_button = QPushButton("⏪")
        self.rewind_button.setObjectName("SkipButton")
        self.rewind_button.setFixedSize(34, 34)
        self.rewind_button.clicked.connect(lambda: self.skip_requested.emit(-SKIP_MS))
        self.play_pause_button = QPushButton("▶")
        self.play_pause_button.setObjectName("PlayPauseButton")
        self.play_pause_button.setFixedSize(48, 48)
        self.play_pause_button.clicked.connect(self.play_pause_clicked)
        self.forward_button = QPushButton("⏩")
        self.forward_button.setObjectName("SkipButton")
        self.forward_button.setFixedSize(34, 34)
        self.forward_button.clicked.connect(lambda: self.skip_requested.emit(SKIP_MS))
        transport_row.addWidget(self.rewind_button)
        transport_row.addWidget(self.play_pause_button)
        transport_row.addWidget(self.forward_button)
        transport_row.addStretch(1)
        layout.addLayout(transport_row)

    def _on_seek_moved(self, value: int) -> None:
        self.current_time_label.setText(format_duration(value // 1000))
        self.seek_moved.emit(value)

    def _on_speed_changed(self, index: int) -> None:
        self.rate_changed.emit(SPEED_OPTIONS[index])

    def is_seeking(self) -> bool:
        return self.seek_slider.isSliderDown()

    def set_track(self, title: str, artist: str) -> None:
        self.title_label.setText(title)
        self.artist_label.setText(artist or "Unknown artist")

    def clear_track(self) -> None:
        self.title_label.setText("Nothing playing")
        self.artist_label.setText("Pick a track from your library")
        self.seek_slider.setRange(0, 0)
        self.current_time_label.setText("0:00")
        self.total_time_label.setText("0:00")
        self.set_playing(False)

    def set_duration(self, duration_ms: int) -> None:
        self.seek_slider.setRange(0, duration_ms)
        self.total_time_label.setText(format_duration(duration_ms // 1000))

    def set_position(self, position_ms: int) -> None:
        if not self.is_seeking():
            self.seek_slider.setValue(position_ms)
        self.current_time_label.setText(format_duration(position_ms // 1000))

    def set_playing(self, playing: bool) -> None:
        self.play_pause_button.setText("⏸" if playing else "▶")
