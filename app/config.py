"""全局配置。"""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
UPLOADS_DIR = BASE_DIR / "uploads"

MAX_UPLOAD_MB = 100
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".webm", ".aiff", ".aif"}

DEFAULT_ENGINE = "auto"  # auto | dsp | basicpitch
