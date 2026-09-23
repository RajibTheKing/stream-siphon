# Stream Siphon

A small desktop app (PySide6 / Qt) that downloads the highest-quality MP3 audio
from a YouTube URL and keeps a local, browsable library.

## Features

- Paste a YouTube URL and download the best available audio as MP3 (VBR ~best quality via `yt-dlp` + ffmpeg).
- Dashboard lists every downloaded track (title, artist, duration).
- Built-in mini player to play/pause tracks straight from the library.
- Delete tracks (removes both the library entry and the MP3 file).

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) available on your `PATH` (required by `yt-dlp` to extract MP3 audio).

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python run.py
```

Downloaded MP3s and the library index (`library.json`) are stored in the
`downloads/` folder at the project root.

## Project structure

```
stream-siphon/
├── run.py                     # Convenience entry point
├── src/stream_siphon/
│   ├── main.py                # QApplication bootstrap
│   ├── config.py              # Paths & app constants
│   ├── core/
│   │   ├── models.py          # Track data model
│   │   ├── library.py         # JSON-backed track store
│   │   └── downloader.py      # yt-dlp download worker (QThread)
│   └── ui/
│       ├── main_window.py     # Dashboard window
│       ├── track_item.py      # Track list row widget
│       └── styles.qss         # App stylesheet
└── downloads/                  # Local MP3 storage + library.json
```
