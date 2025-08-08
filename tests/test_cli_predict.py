from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def test_cli_train_and_predict(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    venv_python = project_root / ".venv/bin/python"
    assert venv_python.exists(), "Virtualenv not found; create it before running tests"

    # Prepare minimal CSV in temp directory
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    csv_path = data_dir / "data.csv"
    csv_path.write_text(
        """EMF,Income,Urbanization,TFR
1.0,1000,0.30,1.80
2.0,2000,0.70,2.10
1.5,1500,0.50,1.90
1.2,1200,0.40,1.70
1.8,1800,0.60,2.00
2.2,2200,0.80,2.20
0.9,900,0.20,1.60
1.1,1100,0.35,1.75
""",
        encoding="utf-8",
    )

    # Train (linear + small CV)
    train_cmd = [
        str(venv_python),
        "-m",
        "src.cli",
        "train",
        "--csv",
        str(csv_path),
        "--model",
        "linear",
        "--cv",
        "4",
    ]
    proc_train = subprocess.run(train_cmd, cwd=project_root, capture_output=True, text=True)
    assert proc_train.returncode == 0, proc_train.stderr

    # Predict
    pred_cmd = [
        str(venv_python),
        "-m",
        "src.cli",
        "predict",
        "--csv",
        str(csv_path),
    ]
    proc_pred = subprocess.run(pred_cmd, cwd=project_root, capture_output=True, text=True)
    assert proc_pred.returncode == 0, proc_pred.stderr
    out = json.loads(proc_pred.stdout)
    assert "predictions" in out and len(out["predictions"]) == 8


