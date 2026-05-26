from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .fetchers.app_store import fetch_app_store_reviews
from .fetchers.csv_surveys import ingest_survey_csv
from .fetchers.google_play import fetch_google_play_reviews
from .sentiment import analyze_sentiment


def _safe_json(val) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return json.dumps(val, ensure_ascii=False, default=str)
    except Exception:
        return json.dumps(str(val), ensure_ascii=False)


def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    tmp = df.copy()

    if "raw" in tmp.columns:
        tmp["raw"] = tmp["raw"].map(_safe_json)

    tmp["text"] = tmp["text"].fillna("").astype(str)

    sentiments = tmp["text"].map(analyze_sentiment)
    tmp["sentiment_label"] = sentiments.map(lambda s: s.label)
    tmp["sentiment_compound"] = sentiments.map(lambda s: s.compound)
    tmp["sentiment_confidence"] = sentiments.map(lambda s: s.confidence)

    tmp["created_at"] = pd.to_datetime(tmp["created_at"], utc=True, errors="coerce").dt.tz_convert("UTC")
    tmp["fetched_at"] = pd.to_datetime(tmp["fetched_at"], utc=True, errors="coerce").dt.tz_convert("UTC")
    tmp["created_date"] = tmp["created_at"].dt.date.astype(str)
    tmp["week"] = tmp["created_at"].dt.to_period("W").astype(str)

    return tmp


def build_dataset(
    *,
    google_play_app_id: str | None = None,
    apple_app_id: str | None = None,
    apple_country: str = "us",
    google_play_country: str = "us",
    google_play_lang: str = "en",
    google_play_max_reviews: int = 500,
    apple_max_pages: int = 10,
    survey_csv_paths: list[Path] | None = None,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    if google_play_app_id:
        frames.append(
            fetch_google_play_reviews(
                app_id=google_play_app_id,
                lang=google_play_lang,
                country=google_play_country,
                max_reviews=google_play_max_reviews,
            )
        )

    if apple_app_id:
        frames.append(fetch_app_store_reviews(app_id=apple_app_id, country=apple_country, max_pages=apple_max_pages))

    if survey_csv_paths:
        for p in survey_csv_paths:
            frames.append(ingest_survey_csv(path=p))

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    if "fetched_at" not in out.columns:
        out["fetched_at"] = datetime.now(timezone.utc).isoformat()

    return _enrich(out)
