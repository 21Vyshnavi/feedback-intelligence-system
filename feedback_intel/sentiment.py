from __future__ import annotations

from dataclasses import dataclass

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


@dataclass(frozen=True)
class SentimentResult:
    label: str  # negative|neutral|positive
    compound: float  # [-1, 1]
    confidence: float  # [0, 1] (heuristic)


_analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(text: str) -> SentimentResult:
    s = _analyzer.polarity_scores(text or "")
    compound = float(s.get("compound", 0.0))

    if compound <= -0.05:
        label = "negative"
    elif compound >= 0.05:
        label = "positive"
    else:
        label = "neutral"

    confidence = min(1.0, max(0.0, abs(compound)))
    return SentimentResult(label=label, compound=compound, confidence=confidence)

