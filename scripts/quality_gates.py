#!/usr/bin/env python3
"""Quality gates validation for paranoid model v5."""

import argparse
import json
import sys
import yaml
from typing import Dict, List, Tuple


def load_metrics(metrics_path: str) -> Dict:
    """Load metrics JSON."""
    with open(metrics_path, 'r') as f:
        return json.load(f)


def load_config(config_path: str) -> Dict:
    """Load config YAML."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def validate_quality_gates(metrics: Dict, gates: Dict) -> Tuple[bool, List[str]]:
    """Validate metrics against quality gates."""
    failures = []
    
    for target, target_metrics in metrics.items():
        if target_metrics['type'] == 'binary':
            # Binary classification gates
            auc = target_metrics.get('cv_auc', 0)
            pr_auc = target_metrics.get('cv_pr_auc', 0)
            brier = target_metrics.get('cv_brier', 1)
            ece = target_metrics.get('cv_ece', 1)
            delta_auc = target_metrics.get('fairness', {}).get('delta_auc', 1)
            
            if auc < gates['auc_min']:
                failures.append(f"{target}: AUC {auc:.3f} < {gates['auc_min']}")
            
            if pr_auc < gates['pr_auc_min']:
                failures.append(f"{target}: PR-AUC {pr_auc:.3f} < {gates['pr_auc_min']}")
            
            if brier > gates['brier_max']:
                failures.append(f"{target}: Brier {brier:.3f} > {gates['brier_max']}")
            
            if ece > gates['ece_max']:
                failures.append(f"{target}: ECE {ece:.3f} > {gates['ece_max']}")
            
            if delta_auc > gates['delta_auc_max']:
                failures.append(f"{target}: Δ-AUC {delta_auc:.3f} > {gates['delta_auc_max']}")
        
        elif target_metrics['type'] == 'continuous':
            # Continuous regression gates (could add RMSE thresholds)
            r2 = target_metrics.get('cv_r2', 0)
            if r2 < 0.1:  # Basic sanity check
                failures.append(f"{target}: R² {r2:.3f} too low (< 0.1)")
    
    return len(failures) == 0, failures


def print_quality_report(metrics: Dict, gates: Dict, passed: bool, failures: List[str]) -> None:
    """Print formatted quality report."""
    print("🔍 PARANOID MODEL V5 QUALITY GATES")
    print("=" * 50)
    
    print(f"\n📊 METRICS SUMMARY:")
    for target, target_metrics in metrics.items():
        print(f"\n{target.upper()}:")
        if target_metrics['type'] == 'binary':
            print(f"  AUC:     {target_metrics.get('cv_auc', 0):.3f} (≥ {gates['auc_min']})")
            print(f"  PR-AUC:  {target_metrics.get('cv_pr_auc', 0):.3f} (≥ {gates['pr_auc_min']})")
            print(f"  Brier:   {target_metrics.get('cv_brier', 1):.3f} (≤ {gates['brier_max']})")
            print(f"  ECE:     {target_metrics.get('cv_ece', 1):.3f} (≤ {gates['ece_max']})")
            print(f"  Δ-AUC:   {target_metrics.get('fairness', {}).get('delta_auc', 1):.3f} (≤ {gates['delta_auc_max']})")
        else:
            print(f"  RMSE:    {target_metrics.get('cv_rmse', 1):.3f}")
            print(f"  R²:      {target_metrics.get('cv_r2', 0):.3f}")
    
    print(f"\n🎯 QUALITY GATES:")
    if passed:
        print("✅ ALL GATES PASSED")
    else:
        print("❌ QUALITY GATES FAILED")
        for failure in failures:
            print(f"  ❌ {failure}")
    
    print(f"\n📋 GATE THRESHOLDS:")
    print(f"  AUC ≥ {gates['auc_min']}")
    print(f"  PR-AUC ≥ {gates['pr_auc_min']}")
    print(f"  Brier ≤ {gates['brier_max']}")
    print(f"  ECE ≤ {gates['ece_max']}")
    print(f"  Δ-AUC ≤ {gates['delta_auc_max']}")


def main():
    parser = argparse.ArgumentParser(description="Validate paranoid model quality gates")
    parser.add_argument('--metrics', required=True, help='Metrics JSON path')
    parser.add_argument('--config', required=True, help='Config YAML path')
    parser.add_argument('--strict', action='store_true', help='Exit with error if gates fail')
    
    args = parser.parse_args()
    
    # Load data
    metrics = load_metrics(args.metrics)
    config = load_config(args.config)
    gates = config['quality_gates']
    
    # Validate gates
    passed, failures = validate_quality_gates(metrics, gates)
    
    # Print report
    print_quality_report(metrics, gates, passed, failures)
    
    # Exit with appropriate code
    if args.strict and not passed:
        print(f"\n💥 STRICT MODE: Exiting with error code 1")
        sys.exit(1)
    elif passed:
        print(f"\n🎉 Quality gates validation completed successfully!")
        sys.exit(0)
    else:
        print(f"\n⚠️  Quality gates failed, but continuing (use --strict to fail)")
        sys.exit(0)


if __name__ == "__main__":
    main()
