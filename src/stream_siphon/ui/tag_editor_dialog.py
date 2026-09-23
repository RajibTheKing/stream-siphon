"""Dialog for manually editing every ID3 tag on a downloaded MP3, saved directly back to disk."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ..core.metadata import EditableTags, read_editable_tags, write_editable_tags

_COVER_MIME_BY_SUFFIX = {".png": "image/png", ".webp": "image/webp"}


class TagEditorDialog(QDialog):
    """Loads the MP3's current ID3 tags into an editable form and overwrites the file on save."""

    def __init__(self, mp3_path: str, parent=None):
        super().__init__(parent)
        self.mp3_path = Path(mp3_path)
        self.updated_tags: Optional[EditableTags] = None
        self.setWindowTitle("Edit MP3 Tags")
        self.setMinimumWidth(440)

        self._cover_bytes: Optional[bytes] = None
        self._cover_mime = ""
        self._cover_removed = False
        self._cover_changed = False

        tags, cover_bytes, cover_mime = read_editable_tags(self.mp3_path)
        self._cover_bytes = cover_bytes
        self._cover_mime = cover_mime

        self._build_ui(tags)

    def _build_ui(self, tags: EditableTags) -> None:
        layout = QVBoxLayout(self)

        cover_row = QHBoxLayout()
        self.cover_label = QLabel()
        self.cover_label.setObjectName("CoverPreview")
        self.cover_label.setFixedSize(96, 96)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_row.addWidget(self.cover_label)

        cover_buttons = QVBoxLayout()
        change_cover_button = QPushButton("Change Cover...")
        change_cover_button.clicked.connect(self._on_change_cover)
        remove_cover_button = QPushButton("Remove Cover")
        remove_cover_button.clicked.connect(self._on_remove_cover)
        cover_buttons.addWidget(change_cover_button)
        cover_buttons.addWidget(remove_cover_button)
        cover_buttons.addStretch(1)
        cover_row.addLayout(cover_buttons)
        cover_row.addStretch(1)
        layout.addLayout(cover_row)

        self._refresh_cover_preview()

        form = QFormLayout()
        self.title_edit = QLineEdit(tags.title)
        self.artist_edit = QLineEdit(tags.artist)
        self.album_artist_edit = QLineEdit(tags.album_artist)
        self.composer_edit = QLineEdit(tags.composer)
        self.album_edit = QLineEdit(tags.album)
        self.genre_edit = QLineEdit(tags.genre)
        self.year_edit = QLineEdit(tags.year)
        self.track_number_edit = QLineEdit(tags.track_number)
        self.publisher_edit = QLineEdit(tags.publisher)
        self.comment_edit = QLineEdit(tags.comment)

        form.addRow("Title", self.title_edit)
        form.addRow("Artist", self.artist_edit)
        form.addRow("Album Artist", self.album_artist_edit)
        form.addRow("Composer", self.composer_edit)
        form.addRow("Album", self.album_edit)
        form.addRow("Genre", self.genre_edit)
        form.addRow("Year", self.year_edit)
        form.addRow("Track Number", self.track_number_edit)
        form.addRow("Publisher", self.publisher_edit)
        form.addRow("Comment", self.comment_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _refresh_cover_preview(self) -> None:
        if self._cover_bytes and not self._cover_removed:
            pixmap = QPixmap()
            pixmap.loadFromData(self._cover_bytes)
            self.cover_label.setText("")
            self.cover_label.setPixmap(
                pixmap.scaled(
                    96,
                    96,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.cover_label.setPixmap(QPixmap())
            self.cover_label.setText("No Cover")

    def _on_change_cover(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Choose Cover Image", "", "Images (*.jpg *.jpeg *.png *.webp)"
        )
        if not file_path:
            return
        path = Path(file_path)
        self._cover_bytes = path.read_bytes()
        self._cover_mime = _COVER_MIME_BY_SUFFIX.get(path.suffix.lower(), "image/jpeg")
        self._cover_removed = False
        self._cover_changed = True
        self._refresh_cover_preview()

    def _on_remove_cover(self) -> None:
        self._cover_bytes = None
        self._cover_removed = True
        self._cover_changed = True
        self._refresh_cover_preview()

    def _on_save(self) -> None:
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Edit MP3 Tags", "Title cannot be empty.")
            return

        tags = EditableTags(
            title=self.title_edit.text().strip(),
            artist=self.artist_edit.text().strip(),
            album_artist=self.album_artist_edit.text().strip(),
            composer=self.composer_edit.text().strip(),
            album=self.album_edit.text().strip(),
            genre=self.genre_edit.text().strip(),
            year=self.year_edit.text().strip(),
            track_number=self.track_number_edit.text().strip(),
            publisher=self.publisher_edit.text().strip(),
            comment=self.comment_edit.text().strip(),
        )

        try:
            write_editable_tags(
                self.mp3_path,
                tags,
                cover_bytes=self._cover_bytes if (self._cover_changed and not self._cover_removed) else None,
                cover_mime=self._cover_mime,
                remove_cover=self._cover_removed,
            )
        except OSError as exc:
            QMessageBox.critical(self, "Edit MP3 Tags", f"Failed to save tags:\n{exc}")
            return

        self.updated_tags = tags
        self.accept()
