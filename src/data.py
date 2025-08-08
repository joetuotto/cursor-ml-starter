from __future__ import annotations

import os
from typing import List

import pandas as pd

REQUIRED_COLUMNS: List[str] = ["EMF", "Income", "Urbanization", "TFR"]


def load_data(csv_path: str) -> pd.DataFrame:
    """Load dataset from CSV and validate required columns.

    Args:
        csv_path: Path to CSV file containing training data.

    Returns:
        A pandas DataFrame with validated schema.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If required columns are missing or target has NaNs.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File not found: {csv_path}")

    data = pd.read_csv(csv_path)

    missing = [c for c in REQUIRED_COLUMNS if c not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if data["TFR"].isna().any():
        raise ValueError('Target column "TFR" contains NaN values')

    return data
