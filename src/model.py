from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

import joblib
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split, KFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RANDOM_STATE: int = 42
FEATURES = ["EMF", "Income", "Urbanization"]
TARGET = "TFR"


@dataclass
class TrainResult:
    model_path: str
    metrics_path: str
    feature_plot_path: Optional[str]
    rmse: float
    r2: float


def build_model(
    model_type: str = "rf",
    n_estimators: int = 200,
    max_depth: Optional[int] = None,
) -> Pipeline:
    if model_type == "linear":
        pre = ColumnTransformer(
            transformers=[("num", StandardScaler(), FEATURES)],
            remainder="drop",
        )
        reg = LinearRegression()
        return Pipeline([("pre", pre), ("reg", reg)])
    else:
        reg = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
        return Pipeline([("reg", reg)])


def _holdout_metrics(pipeline: Pipeline, X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, float]:
    preds = pipeline.predict(X_val)
    rmse = float(np.sqrt(mean_squared_error(y_val, preds)))
    r2 = float(r2_score(y_val, preds))
    return {"rmse": rmse, "r2": r2}


def _cv_metrics(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series, cv: int) -> Dict[str, float]:
    kf = KFold(n_splits=cv, shuffle=True, random_state=RANDOM_STATE)
    neg_rmse = cross_val_score(
        pipeline, X, y, scoring="neg_root_mean_squared_error", cv=kf, n_jobs=-1
    )
    r2_scores = cross_val_score(
        pipeline, X, y, scoring="r2", cv=kf, n_jobs=-1
    )
    return {
        "rmse": float(-neg_rmse.mean()),
        "r2": float(r2_scores.mean()),
        "cv": cv,
    }


def train(
    data: pd.DataFrame,
    test_size: float = 0.2,
    n_estimators: int = 200,
    max_depth: Optional[int] = None,
    model_type: str = "rf",
    cv: Optional[int] = None,
) -> Tuple[Pipeline, Dict[str, float]]:
    X = data[FEATURES]
    y = data[TARGET]

    pipeline = build_model(model_type=model_type, n_estimators=n_estimators, max_depth=max_depth)

    if cv and cv >= 2:
        metrics = _cv_metrics(pipeline, X, y, cv=cv)
        pipeline.fit(X, y)
        metrics["mode"] = f"cv-{cv}"
    else:
        X_tr, X_val, y_tr, y_val = train_test_split(
            X, y, test_size=test_size, random_state=RANDOM_STATE
        )
        pipeline.fit(X_tr, y_tr)
        metrics = _holdout_metrics(pipeline, X_val, y_val)
        metrics["mode"] = "holdout"

    metrics["model_type"] = model_type
    return pipeline, metrics


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def evaluate_and_save(
    pipeline: Pipeline,
    data: pd.DataFrame,
    metrics: Dict[str, float],
    model_path: str = "./artifacts/model.joblib",
    metrics_path: str = "./artifacts/metrics.json",
    feature_plot_path: str = "./artifacts/feature_importance.png",
) -> TrainResult:
    _ensure_dir(model_path)
    _ensure_dir(metrics_path)
    _ensure_dir(feature_plot_path)

    joblib.dump(pipeline, model_path)
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    feature_plot = None
    reg = pipeline.named_steps.get("reg")
    if hasattr(reg, "feature_importances_"):
        importances = reg.feature_importances_
        labels = FEATURES
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(labels, importances)
        ax.set_title("Feature importances")
        ax.set_ylabel("Importance")
        fig.tight_layout()
        plt.savefig(feature_plot_path)
        plt.close(fig)
        feature_plot = feature_plot_path

    return TrainResult(
        model_path=model_path,
        metrics_path=metrics_path,
        feature_plot_path=feature_plot,
        rmse=float(metrics["rmse"]),
        r2=float(metrics["r2"]),
    )
