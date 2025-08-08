from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data import load_data
from src.model import train


def test_load_data(tmp_path: Path) -> None:
    csv_path = tmp_path / "data.csv"
    pd.DataFrame(
        {
            "EMF": [1.0, 2.0],
            "Income": [1000, 2000],
            "Urbanization": [0.3, 0.7],
            "TFR": [1.8, 2.1],
        }
    ).to_csv(csv_path, index=False)

    df = load_data(str(csv_path))
    assert set(["EMF", "Income", "Urbanization", "TFR"]).issubset(df.columns)


def test_train_predict(tmp_path: Path) -> None:
    csv_path = tmp_path / "data.csv"
    pd.DataFrame(
        {
            "EMF": [1.0, 2.0, 1.5, 1.2, 1.8, 2.2, 0.9, 1.1],
            "Income": [1000, 2000, 1500, 1200, 1800, 2200, 900, 1100],
            "Urbanization": [0.3, 0.7, 0.5, 0.4, 0.6, 0.8, 0.2, 0.35],
            "TFR": [1.8, 2.1, 1.9, 1.7, 2.0, 2.2, 1.6, 1.75],
        }
    ).to_csv(csv_path, index=False)

    df = load_data(str(csv_path))
    pipeline, metrics = train(df)
    assert "rmse" in metrics and "r2" in metrics
    preds = pipeline.predict(df[["EMF", "Income", "Urbanization"]])
    assert preds.shape[0] == df.shape[0]
