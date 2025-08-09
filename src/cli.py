from __future__ import annotations

import argparse
import json
import os
from typing import Optional

import joblib
import pandas as pd
from dotenv import load_dotenv  # type: ignore

from .data import load_data
from .model import evaluate_and_save, train
from .paranoid_model.publisher_llm import enrich_signal, write_enriched_report


def main(argv: Optional[list[str]] = None) -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Train or predict with the regression model")
    sub = parser.add_subparsers(dest="command", required=True)

    p_train = sub.add_parser("train", help="Train a model from CSV")
    p_train.add_argument("--csv", required=True, help="Path to training CSV")
    p_train.add_argument("--test_size", type=float, default=0.2)
    p_train.add_argument("--n_estimators", type=int, default=200)
    p_train.add_argument("--max_depth", type=int, default=None)
    p_train.add_argument("--model", choices=["rf", "linear"], default="rf")
    p_train.add_argument("--cv", type=int, default=None, help="K-fold CV (>=2) replaces holdout")

    p_pred = sub.add_parser("predict", help="Predict using a saved model")
    p_pred.add_argument("--model_path", default="./artifacts/model.joblib")
    p_pred.add_argument("--csv", required=True, help="CSV with EMF,Income,Urbanization columns")
    p_pred.add_argument("--out", default=None, help="Optional path to write predictions CSV")

    p_enrich = sub.add_parser("enrich", help="Enrich paranoid-model signal via Cursor GPT-5")
    p_enrich.add_argument("--signal", required=True, help="Path to raw signal JSON file")
    p_enrich.add_argument("--schema", required=True, help="Path to FEED_ITEM_SCHEMA JSON")
    p_enrich.add_argument(
        "--out", default="./artifacts/report.enriched.json", help="Where to write enriched JSON"
    )

    args = parser.parse_args(argv)

    if args.command == "train":
        data = load_data(args.csv)
        pipeline, metrics = train(
            data,
            test_size=args.test_size,
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            model_type=args.model,
            cv=args.cv,
        )
        result = evaluate_and_save(pipeline, data, metrics)
        print(
            json.dumps(
                {
                    "rmse": result.rmse,
                    "r2": result.r2,
                    "model_path": result.model_path,
                    "metrics_path": result.metrics_path,
                    "feature_plot_path": result.feature_plot_path,
                    "mode": metrics.get("mode"),
                    "model_type": metrics.get("model_type"),
                },
                indent=2,
            )
        )

    elif args.command == "predict":
        model = joblib.load(args.model_path)
        df = pd.read_csv(args.csv)
        X = df[["EMF", "Income", "Urbanization"]]
        preds = model.predict(X)
        out_json = {"predictions": list(map(float, preds))}
        print(json.dumps(out_json, indent=2))

        if args.out:
            os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
            pd.DataFrame({"prediction": preds}).to_csv(args.out, index=False)

    elif args.command == "enrich":
        with open(args.signal, "r", encoding="utf-8") as f:
            raw_signal = json.load(f)
        with open(args.schema, "r", encoding="utf-8") as f:
            schema = json.load(f)

        enriched = enrich_signal(raw_signal, schema)
        out_path = write_enriched_report(enriched, args.out)
        print(json.dumps({"enriched_path": out_path}, indent=2))


if __name__ == "__main__":
    main()
