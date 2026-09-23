"""Main dashboard window: URL input, download progress, track list, mini player."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..config import APP_NAME, DEFAULT_DOWNLOAD_DIR
from ..core.downloader import DownloadWorker
from ..core.library import Library
from ..core.models import Track
from .track_item import TrackItemWidget, format_duration


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(760, 640)

        self.library = Library()
        self.worker: Optional[DownloadWorker] = None
        self.now_playing_id: Optional[str] = None
        self.settings = QSettings()

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)

        self._build_ui()
        self._reload_list()

    # ---------------------------------------------------------------- UI ---

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(20, 20, 20, 16)
        root_layout.setSpacing(14)

        title = QLabel("Stream Siphon")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Paste a YouTube link to grab the highest-quality MP3.")
        subtitle.setObjectName("AppSubtitle")
        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)

        input_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_input.returnPressed.connect(self.start_download)
        self.download_button = QPushButton("Download")
        self.download_button.setObjectName("PrimaryButton")
        self.download_button.clicked.connect(self.start_download)
        input_row.addWidget(self.url_input, stretch=1)
        input_row.addWidget(self.download_button)
        root_layout.addLayout(input_row)

        self.llm_checkbox = QCheckBox("Enrich metadata with local LLM (Ollama)")
        self.llm_checkbox.setChecked(self.settings.value("use_llm_enrichment", False, type=bool))
        self.llm_checkbox.toggled.connect(self._on_llm_toggle)
        root_layout.addWidget(self.llm_checkbox)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        root_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLabel")
        root_layout.addWidget(self.status_label)

        list_header = QHBoxLayout()
        library_label = QLabel("Your Library")
        library_label.setObjectName("SectionTitle")
        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.clicked.connect(self._open_download_folder)
        list_header.addWidget(library_label)
        list_header.addStretch(1)
        list_header.addWidget(self.open_folder_button)
        root_layout.addLayout(list_header)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("TrackList")
        self.list_widget.setSpacing(6)
        root_layout.addWidget(self.list_widget, stretch=1)

        player_row = QHBoxLayout()
        self.now_playing_label = QLabel("Nothing playing")
        self.now_playing_label.setObjectName("NowPlaying")
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderMoved.connect(self.player.setPosition)
        self.time_label = QLabel("0:00 / 0:00")
        player_row.addWidget(self.now_playing_label, stretch=1)
        player_row.addWidget(self.seek_slider, stretch=2)
        player_row.addWidget(self.time_label)
        root_layout.addLayout(player_row)

        self.setCentralWidget(root)

    # ----------------------------------------------------------- Library ---

    def _reload_list(self) -> None:
        self.list_widget.clear()
        for track in sorted(self.library.all(), key=lambda t: t.added_at, reverse=True):
            self._add_item(track)

    def _add_item(self, track: Track) -> None:
        item = QListWidgetItem(self.list_widget)
        widget = TrackItemWidget(track)
        widget.play_requested.connect(self._toggle_play)
        widget.delete_requested.connect(self._delete_track)
        item.setSizeHint(widget.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)

    def _open_download_folder(self) -> None:
        QFileDialog.getExistingDirectory(self, "Downloads", str(DEFAULT_DOWNLOAD_DIR))

    # ---------------------------------------------------------- Download ---

    def start_download(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, APP_NAME, "Please paste a YouTube URL first.")
            return
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, APP_NAME, "A download is already in progress.")
            return

        self.download_button.setEnabled(False)
        self.url_input.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting download...")

        self.worker = DownloadWorker(url, use_llm=self.llm_checkbox.isChecked())
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_download_finished)
        self.worker.failed.connect(self._on_download_failed)
        self.worker.start()

    def _on_llm_toggle(self, checked: bool) -> None:
        self.settings.setValue("use_llm_enrichment", checked)

    def _on_progress(self, percent: float, status: str) -> None:
        self.progress_bar.setValue(int(percent))
        self.status_label.setText(status)

    def _on_download_finished(self, track: Track) -> None:
        self.library.add(track)
        self._reload_list()
        self.status_label.setText(f"Saved: {track.title}")
        self._reset_download_ui()

    def _on_download_failed(self, message: str) -> None:
        QMessageBox.critical(self, APP_NAME, f"Download failed:\n{message}")
        self.status_label.setText("Download failed.")
        self._reset_download_ui()

    def _reset_download_ui(self) -> None:
        self.download_button.setEnabled(True)
        self.url_input.setEnabled(True)
        self.url_input.clear()
        self.progress_bar.setVisible(False)

    # ---------------------------------------------------------- Playback ---

    def _toggle_play(self, track_id: str) -> None:
        track = self.library.find(track_id)
        if not track:
            return
        if self.now_playing_id == track_id and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            return
        if self.now_playing_id == track_id:
            self.player.play()
            return

        self.now_playing_id = track_id
        self.player.setSource(QUrl.fromLocalFile(track.file_path))
        self.player.play()
        self.now_playing_label.setText(f"{track.title} — {track.artist}")
        self._refresh_play_icons()

    def _on_playback_state_changed(self, _state) -> None:
        self._refresh_play_icons()

    def _refresh_play_icons(self) -> None:
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if isinstance(widget, TrackItemWidget):
                widget.set_playing(playing and widget.track.id == self.now_playing_id)

    def _on_position_changed(self, position: int) -> None:
        self.seek_slider.setValue(position)
        current = format_duration(position // 1000)
        total = format_duration(self.player.duration() // 1000)
        self.time_label.setText(f"{current} / {total}")

    def _on_duration_changed(self, duration: int) -> None:
        self.seek_slider.setRange(0, duration)

    # ------------------------------------------------------------ Delete ---

    def _delete_track(self, track_id: str) -> None:
        track = self.library.find(track_id)
        if not track:
            return
        confirm = QMessageBox.question(
            self,
            APP_NAME,
            f"Delete '{track.title}' and its MP3 file?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        if self.now_playing_id == track_id:
            self.player.stop()
            self.now_playing_id = None
            self.now_playing_label.setText("Nothing playing")
        self.library.remove(track_id)
        file_path = Path(track.file_path)
        if file_path.exists():
            file_path.unlink()
        self._reload_list()
