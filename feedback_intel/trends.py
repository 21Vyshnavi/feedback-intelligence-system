from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TrendSummary:
    weekly: pd.DataFrame
    latest_week: str | None
    wow_delta: float | None


def compute_weekly_trends(df: pd.DataFrame) -> TrendSummary:
    if df.empty or "created_at" not in df.columns or "sentiment_compound" not in df.columns:
        return TrendSummary(weekly=pd.DataFrame(), latest_week=None, wow_delta=None)

    tmp = df.copy()
    tmp["created_at"] = pd.to_datetime(tmp["created_at"], utc=True, errors="coerce")
    tmp = tmp.dropna(subset=["created_at"])
    if tmp.empty:
        return TrendSummary(weekly=pd.DataFrame(), latest_week=None, wow_delta=None)

    tmp = tmp.set_index("created_at").sort_index()
    weekly = tmp.resample("W")["sentiment_compound"].mean().to_frame("avg_sentiment")
    weekly["wow_delta"] = weekly["avg_sentiment"].diff()

    latest_week = None if weekly.empty else str(weekly.index.max().date())
    wow_delta = None
    if len(weekly) >= 2:
        wow_delta = float(weekly["wow_delta"].iloc[-1])
    return TrendSummary(weekly=weekly.reset_index(names=["week"]), latest_week=latest_week, wow_delta=wow_delta)

