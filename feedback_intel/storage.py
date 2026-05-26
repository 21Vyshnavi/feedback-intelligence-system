from __future__ import annotations

from pathlib import Path

import pandas as pd


def dataset_path(data_dir: Path) -> Path:
    return data_dir / "feedback.parquet"


def load_dataset(data_dir: Path) -> pd.DataFrame:
    path = dataset_path(data_dir)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def upsert_dataset(data_dir: Path, incoming: pd.DataFrame) -> pd.DataFrame:
    if incoming.empty:
        return load_dataset(data_dir)

    path = dataset_path(data_dir)
    if not path.exists():
        incoming.to_parquet(path, index=False)
        return incoming

    existing = pd.read_parquet(path)
    combined = pd.concat([existing, incoming], ignore_index=True)
    if "source" in combined.columns and "source_id" in combined.columns:
        combined = combined.drop_duplicates(subset=["source", "source_id"], keep="last")
    combined.to_parquet(path, index=False)
    return combined

