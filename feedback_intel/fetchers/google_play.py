from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

try:
    from google_play_scraper import Sort, reviews  # type: ignore
except Exception:  # pragma: no cover
    Sort = None
    reviews = None


def fetch_google_play_reviews(
    *,
    app_id: str,
    lang: str = "en",
    country: str = "us",
    max_reviews: int = 500,
) -> pd.DataFrame:
    if reviews is None or Sort is None:
        raise RuntimeError(
            "google-play-scraper is not available. Install requirements.txt dependencies."
        )

    fetched_at = datetime.now(timezone.utc)

    all_rows: list[dict[str, Any]] = []
    continuation_token = None
    remaining = max_reviews

    while remaining > 0:
        count = min(200, remaining)
        result, continuation_token = reviews(
            app_id,
            lang=lang,
            country=country,
            sort=Sort.NEWEST,
            count=count,
            continuation_token=continuation_token,
        )
        if not result:
            break

        for item in result:
            created_at = item.get("at")
            if created_at is None:
                created_at = fetched_at
            if getattr(created_at, "tzinfo", None) is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            text = (item.get("content") or "").strip()
            title = (item.get("title") or "").strip() or None
            author = (item.get("userName") or "").strip() or None
            score = item.get("score")
            source_id = str(item.get("reviewId") or f"gp:{hash((author, title, text, created_at))}")

            all_rows.append(
                {
                    "source": "google_play",
                    "source_id": source_id,
                    "app_id": app_id,
                    "region": country,
                    "language": lang,
                    "created_at": created_at.isoformat(),
                    "fetched_at": fetched_at.isoformat(),
                    "author": author,
                    "rating": float(score) if score is not None else None,
                    "title": title,
                    "text": text,
                    "url": None,
                    "raw": item,
                }
            )

        remaining -= len(result)
        if continuation_token is None:
            break

    return pd.DataFrame(all_rows)

