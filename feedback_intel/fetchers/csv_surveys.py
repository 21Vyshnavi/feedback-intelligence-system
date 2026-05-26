from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def ingest_survey_csv(
    *,
    path: Path,
    source_name: str = "survey_csv",
    text_col: str = "feedback",
    created_col: str | None = "created_at",
    rating_col: str | None = "rating",
) -> pd.DataFrame:
    df = pd.read_csv(path)
    fetched_at = datetime.now(timezone.utc).isoformat()

    def _get(row, col: str | None):
        if col is None or col not in df.columns:
            return None
        return row[col]

    rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        text = str(row.get(text_col, "")).strip()
        if not text:
            continue

        created = _get(row, created_col)
        created_at = None
        if created is not None and str(created).strip() != "":
            try:
                created_at = pd.to_datetime(created, utc=True).to_pydatetime()
            except Exception:
                created_at = None
        if created_at is None:
            created_at = datetime.now(timezone.utc)

        rating = _get(row, rating_col)
        rating_f = None
        if rating is not None and str(rating).strip() != "":
            try:
                rating_f = float(rating)
            except Exception:
                rating_f = None

        rows.append(
            {
                "source": source_name,
                "source_id": f"{path.name}:{idx}",
                "app_id": None,
                "region": None,
                "language": None,
                "created_at": created_at.isoformat(),
                "fetched_at": fetched_at,
                "author": None,
                "rating": rating_f,
                "title": None,
                "text": text,
                "url": None,
                "raw": row.to_dict(),
            }
        )

    return pd.DataFrame(rows)

