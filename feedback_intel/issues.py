from __future__ import annotations

from dataclasses import dataclass

import re
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


@dataclass(frozen=True)
class IssueRow:
    phrase: str
    negative_mentions: int
    avg_compound: float
    priority: float


def extract_top_issues(
    df: pd.DataFrame,
    *,
    top_k: int = 15,
    min_df: int = 2,
) -> pd.DataFrame:
    if df.empty or "text" not in df.columns or "sentiment_label" not in df.columns:
        return pd.DataFrame(columns=["phrase", "negative_mentions", "avg_compound", "priority"])

    neg = df[df["sentiment_label"] == "negative"].copy()
    if neg.empty:
        return pd.DataFrame(columns=["phrase", "negative_mentions", "avg_compound", "priority"])

    texts = neg["text"].fillna("").astype(str).tolist()
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 3),
        min_df=min_df,
        max_features=5000,
    )

    try:
        mat = vectorizer.fit_transform(texts)
    except ValueError:
        return pd.DataFrame(columns=["phrase", "negative_mentions", "avg_compound", "priority"])

    terms = np.array(vectorizer.get_feature_names_out())
    # Use TF-IDF sum as a proxy for "salience" among negative feedback.
    salience = mat.sum(axis=0).A1
    if salience.size == 0:
        return pd.DataFrame(columns=["phrase", "negative_mentions", "avg_compound", "priority"])

    top_idx = np.argsort(-salience)[: max(1, top_k)]
    top_terms = terms[top_idx].tolist()

    rows: list[IssueRow] = []
    neg_compound = neg["sentiment_compound"].astype(float)
    for phrase in top_terms:
        safe = re.escape(phrase)
        mask = neg["text"].str.contains(rf"\\b{safe}\\b", case=False, na=False, regex=True)
        mentions = int(mask.sum())
        if mentions <= 0:
            continue
        avg = float(neg_compound[mask].mean())
        # Higher is more urgent: more mentions, more negative sentiment.
        priority = mentions * abs(min(0.0, avg))
        rows.append(IssueRow(phrase=phrase, negative_mentions=mentions, avg_compound=avg, priority=priority))

    out = pd.DataFrame([r.__dict__ for r in rows])
    if out.empty:
        return pd.DataFrame(columns=["phrase", "negative_mentions", "avg_compound", "priority"])
    return out.sort_values(["priority", "negative_mentions"], ascending=[False, False]).reset_index(drop=True)
