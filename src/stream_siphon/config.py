"""App-wide paths and constants."""

from pathlib import Path

APP_NAME = "Stream Siphon"
ORG_NAME = "StreamSiphon"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DOWNLOAD_DIR = PROJECT_ROOT / "downloads"
LIBRARY_FILE = DEFAULT_DOWNLOAD_DIR / "library.json"


def ensure_dirs() -> None:
    DEFAULT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
