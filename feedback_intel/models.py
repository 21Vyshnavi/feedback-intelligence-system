from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class FeedbackEntry:
    source: str
    source_id: str

    app_id: str | None
    region: str | None
    language: str | None

    created_at: datetime
    fetched_at: datetime

    author: str | None
    rating: float | None
    title: str | None
    text: str
    url: str | None

    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        d["fetched_at"] = self.fetched_at.isoformat()
        return d

