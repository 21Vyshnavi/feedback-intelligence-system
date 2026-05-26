from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path

    google_play_app_id: str | None
    google_play_lang: str
    google_play_country: str
    google_play_max_reviews: int

    apple_app_id: str | None
    apple_country: str
    apple_max_pages: int

    default_timezone: str


def load_settings() -> Settings:
    data_dir = Path(os.getenv("FEEDBACK_INTEL_DATA_DIR", "data")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    def _int(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None or raw.strip() == "":
            return default
        return int(raw)

    return Settings(
        data_dir=data_dir,
        google_play_app_id=os.getenv("GOOGLE_PLAY_APP_ID"),
        google_play_lang=os.getenv("GOOGLE_PLAY_LANG", "en"),
        google_play_country=os.getenv("GOOGLE_PLAY_COUNTRY", "us"),
        google_play_max_reviews=_int("GOOGLE_PLAY_MAX_REVIEWS", 500),
        apple_app_id=os.getenv("APPLE_APP_ID"),
        apple_country=os.getenv("APPLE_COUNTRY", "us"),
        apple_max_pages=_int("APPLE_MAX_PAGES", 10),
        default_timezone=os.getenv("FEEDBACK_INTEL_TZ", "UTC"),
    )

