from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import feedparser
import pandas as pd

from ..http import make_session


def _apple_reviews_rss_url(*, app_id: str, country: str, page: int) -> str:
    # Apple RSS generator for customer reviews.
    # Example: https://itunes.apple.com/us/rss/customerreviews/id=1234567890/page=1/sortby=mostrecent/xml
    return (
        f"https://itunes.apple.com/{country}/rss/customerreviews/"
        f"id={app_id}/page={page}/sortby=mostrecent/xml"
    )


def fetch_app_store_reviews(
    *,
    app_id: str,
    country: str = "us",
    max_pages: int = 10,
) -> pd.DataFrame:
    session = make_session()
    fetched_at = datetime.now(timezone.utc)

    rows: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        url = _apple_reviews_rss_url(app_id=app_id, country=country, page=page)
        resp = session.get(url, headers={"User-Agent": "feedback-intel/1.0"})
        if resp.status_code >= 400:
            break

        parsed = feedparser.parse(resp.content)
        entries = parsed.get("entries", [])
        if not entries:
            break

        for e in entries:
            # First entry is often app metadata; skip if no review text.
            content = ""
            if "content" in e and e["content"]:
                content = (e["content"][0].get("value") or "").strip()
            summary = (e.get("summary") or "").strip()
            text = content or summary
            if not text:
                continue

            created_at = e.get("updated_parsed") or e.get("published_parsed")
            if created_at is not None:
                created_at_dt = datetime(*created_at[:6], tzinfo=timezone.utc)
            else:
                created_at_dt = fetched_at

            rating = None
            for key in ("im_rating", "im:rating"):
                val = e.get(key)
                if val is not None:
                    try:
                        if isinstance(val, dict):
                            rating = float(val.get("value"))
                        else:
                            rating = float(val)
                    except Exception:
                        rating = None
                    break

            rows.append(
                {
                    "source": "app_store",
                    "source_id": str(e.get("id") or e.get("link") or f"as:{hash(text)}"),
                    "app_id": app_id,
                    "region": country,
                    "language": None,
                    "created_at": created_at_dt.isoformat(),
                    "fetched_at": fetched_at.isoformat(),
                    "author": (e.get("author") or "").strip() or None,
                    "rating": rating,
                    "title": (e.get("title") or "").strip() or None,
                    "text": text,
                    "url": e.get("link"),
                    "raw": dict(e),
                }
            )

    return pd.DataFrame(rows)
