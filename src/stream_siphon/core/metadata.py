"""Build ID3 tags from yt-dlp info (optionally enriched by a local Ollama LLM) and embed them into an MP3."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from mutagen.id3 import APIC, COMM, ID3, TALB, TCOM, TDRC, TIT2, TPE1, TPUB
from mutagen.mp3 import MP3

OLLAMA_URL = os.environ.get("STREAM_SIPHON_OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("STREAM_SIPHON_OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT = 60  # seconds - generous enough to cover a cold model load on first call
_THUMBNAIL_TIMEOUT = 8


@dataclass
class TrackTags:
    title: str
    singer: str
    composer: str
    album: str
    year: str
    publisher: str
    comment: str
    thumbnail_url: str


def _truncate_title(title: str) -> str:
    """Keep only the portion before the first '|' or fullwidth '｜' separator many uploaders use for extra tags."""
    for sep in ("｜", "|"):
        if sep in title:
            return title.split(sep, 1)[0].strip()
    return title.strip()


def _guess_singer_from_title(title: str, uploader: str) -> tuple[str, str]:
    """Best-effort split of an 'Artist - Song' style title; returns (singer, clean_title)."""
    match = re.match(r"^\s*(.+?)\s*[-\u2013\u2014]\s*(.+?)\s*$", title)
    if match:
        return match.group(1), match.group(2)
    return uploader, title


def _query_ollama(
    title: str,
    uploader: str,
    description: str,
    status_callback: Optional[Callable[[str], None]] = None,
) -> Optional[dict]:
    """Ask a local Ollama model to infer singer/composer/album from video context; returns None if unreachable."""
    if status_callback:
        status_callback(f"Asking local LLM ({OLLAMA_MODEL}) for metadata...")
    prompt = (
        "You are a music metadata assistant. Given a YouTube video's title, channel name, "
        "and description, infer the song's metadata. Respond with ONLY strict JSON, no prose, "
        'matching this schema: {"singer": string, "composer": string, "album": string}. '
        "If a field is unknown, use an empty string.\n\n"
        f"Title: {title}\nChannel: {uploader}\nDescription: {description[:500]}"
    )
    payload = json.dumps(
        {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json"}
    ).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT) as response:
            body = json.loads(response.read().decode("utf-8"))
        result = json.loads(body.get("response", "{}"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        if status_callback:
            status_callback("LLM unreachable, skipping enrichment.")
        return None
    if status_callback:
        status_callback("LLM response received.")
    return result


def build_tags(
    info: dict,
    use_llm: bool = False,
    status_callback: Optional[Callable[[str], None]] = None,
) -> TrackTags:
    """Assemble ID3 tag values from yt-dlp's info dict, optionally enriched by a local LLM."""
    raw_title = info.get("title") or "Unknown title"
    title = _truncate_title(raw_title)
    uploader = info.get("uploader") or info.get("channel") or "Unknown"
    upload_date = info.get("upload_date") or ""
    year = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}" if len(upload_date) == 8 else ""

    # YouTube Music uploads sometimes carry these directly; regular videos rarely do.
    singer = info.get("artist") or ""
    composer = info.get("composer") or ""
    album = info.get("album") or info.get("track") or ""

    singer_confident = bool(singer)
    if not singer:
        singer, title = _guess_singer_from_title(title, uploader)
        singer_confident = singer != uploader

    if use_llm and (not singer_confident or not composer or not album):
        # Pass the untruncated title so segments after '|' (e.g. the real artist) stay visible to the model.
        enriched = _query_ollama(raw_title, uploader, info.get("description") or "", status_callback)
        if enriched:
            if not singer_confident and enriched.get("singer"):
                singer = enriched["singer"]
            composer = composer or enriched.get("composer") or ""
            album = album or enriched.get("album") or ""

    return TrackTags(
        title=title,
        singer=singer or uploader,
        composer=composer,
        album=album,
        year=year,
        publisher=uploader,
        comment=info.get("webpage_url") or "",
        thumbnail_url=info.get("thumbnail") or "",
    )


_THUMBNAIL_HEADERS = {
    # YouTube's image CDN returns 403 for the default urllib User-Agent.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _fetch_thumbnail(url: str) -> Optional[bytes]:
    if not url:
        return None
    request = urllib.request.Request(url, headers=_THUMBNAIL_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=_THUMBNAIL_TIMEOUT) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def _thumbnail_mime(data: bytes) -> str:
    """Sniff the image format since yt-dlp's best thumbnail is often webp, not jpeg."""
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _fetch_cover_art_fallback(
    tags: TrackTags, status_callback: Optional[Callable[[str], None]] = None
) -> Optional[bytes]:
    """Look up real cover art on iTunes using the (possibly LLM-enriched) singer/album/title."""
    query = " ".join(part for part in (tags.singer, tags.album or tags.title) if part).strip()
    if not query:
        return None
    if status_callback:
        status_callback("Thumbnail unavailable, searching iTunes for cover art...")
    search_url = "https://itunes.apple.com/search?" + urllib.parse.urlencode(
        {"term": query, "media": "music", "limit": 1}
    )
    request = urllib.request.Request(search_url, headers=_THUMBNAIL_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=_THUMBNAIL_TIMEOUT) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    results = body.get("results") or []
    if not results:
        return None
    artwork_url = results[0].get("artworkUrl100") or ""
    if not artwork_url:
        return None
    # iTunes serves a low-res thumbnail by default; ask for a larger crop.
    artwork_url = artwork_url.replace("100x100bb", "600x600bb")
    return _fetch_thumbnail(artwork_url)


def embed_tags(
    mp3_path: Path,
    tags: TrackTags,
    use_llm: bool = False,
    status_callback: Optional[Callable[[str], None]] = None,
) -> None:
    """Write ID3v2 tags (title, singer, composer, album, date, publisher, cover art) into the MP3 file."""
    audio = MP3(mp3_path, ID3=ID3)
    if audio.tags is None:
        audio.add_tags()
    id3 = audio.tags

    id3.setall("TIT2", [TIT2(encoding=3, text=tags.title)])
    id3.setall("TPE1", [TPE1(encoding=3, text=tags.singer)])
    if tags.composer:
        id3.setall("TCOM", [TCOM(encoding=3, text=tags.composer)])
    if tags.album:
        id3.setall("TALB", [TALB(encoding=3, text=tags.album)])
    if tags.year:
        id3.setall("TDRC", [TDRC(encoding=3, text=tags.year)])
    if tags.publisher:
        id3.setall("TPUB", [TPUB(encoding=3, text=tags.publisher)])
    if tags.comment:
        id3.setall("COMM", [COMM(encoding=3, lang="eng", desc="", text=tags.comment)])

    thumbnail_bytes = _fetch_thumbnail(tags.thumbnail_url)
    if not thumbnail_bytes and use_llm:
        thumbnail_bytes = _fetch_cover_art_fallback(tags, status_callback)
    if thumbnail_bytes:
        id3.delall("APIC")
        id3.add(
            APIC(
                encoding=3,
                mime=_thumbnail_mime(thumbnail_bytes),
                type=3,
                desc="Cover",
                data=thumbnail_bytes,
            )
        )

    audio.save(v2_version=3)
