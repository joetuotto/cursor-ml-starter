#!/usr/bin/env python3
"""Generate paranoid signals from trained model."""

import argparse
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def load_models(models_path: str):
    """Load trained paranoid models."""
    return joblib.load(models_path)


def generate_signal_data(n_samples: int = 50, seed: int = 1337) -> pd.DataFrame:
    """Generate new data for signal detection."""
    np.random.seed(seed)
    
    data = {}
    
    # Base monitoring data (simplified for demo)
    data['TAB'] = np.random.lognormal(0, 1, n_samples)
    data['NEK'] = np.random.lognormal(0, 1, n_samples) 
    data['HSK'] = np.random.uniform(0, 1, n_samples)
    data['HMNI'] = np.random.uniform(0, 1, n_samples)
    data['RSR'] = np.random.exponential(1, n_samples)
    data['ARDI'] = np.random.exponential(1, n_samples)
    data['SRK'] = np.random.exponential(1, n_samples)
    data['PKR'] = np.random.exponential(1, n_samples)
    
    # Social indicators
    data['MAF'] = np.random.uniform(0, 1, n_samples)
    data['MSI'] = np.random.uniform(0, 1, n_samples)
    data['EPP'] = np.random.uniform(0, 1, n_samples)
    data['CPB'] = np.random.uniform(0, 1, n_samples)
    
    # SHL features
    data['OPK'] = np.random.exponential(1, n_samples)
    data['ALGO'] = np.random.exponential(1, n_samples)
    data['UL'] = np.random.exponential(1, n_samples)
    data['IPO'] = np.random.exponential(1, n_samples)
    data['HAN'] = np.random.exponential(1, n_samples)
    data['AV'] = np.random.exponential(1, n_samples)
    data['TKI'] = np.random.exponential(1, n_samples)
    
    # Paranoid indices with some anomalous spikes
    anomaly_mask = np.random.random(n_samples) < 0.1  # 10% anomalies
    
    data['propaganda_index'] = np.random.normal(0, 1, n_samples)
    data['propaganda_index'][anomaly_mask] += np.random.normal(3, 1, anomaly_mask.sum())
    
    data['framing_intensity'] = np.random.normal(0, 1, n_samples)
    data['coordination_index'] = np.random.normal(0, 1, n_samples)
    data['suppression_pressure_index'] = np.random.normal(0, 1, n_samples)
    
    # Secret history signals
    data['secret_history_index'] = np.random.normal(0, 1, n_samples)
    data['hist_visibility_gap'] = np.random.normal(0, 1, n_samples)
    data['hist_missing_docs_score'] = np.random.normal(0, 1, n_samples)
    data['hist_treatment_asymmetry'] = np.random.normal(0, 1, n_samples)
    data['hist_meta_ref_ratio'] = np.random.normal(0, 1, n_samples)
    data['hist_echo_signal'] = np.random.normal(0, 1, n_samples)
    
    # Network and geospatial
    data['finance_pressure_index'] = np.random.normal(0, 1, n_samples)
    data['network_density'] = np.random.normal(0, 1, n_samples)
    data['geospatial_risk'] = np.random.normal(0, 1, n_samples)
    data['precursor_score'] = np.random.normal(0, 1, n_samples)
    
    # External pressure
    data['external_sanction_index'] = np.random.poisson(2, n_samples)
    data['media_censorship_score'] = np.random.poisson(2, n_samples)
    data['incidents_sanction_events_24m'] = np.random.poisson(2, n_samples)
    data['censorship_events_24m'] = np.random.poisson(2, n_samples)
    
    return pd.DataFrame(data)


def create_inference_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create same interaction features as used in training."""
    df_feat = df.copy()
    
    # Hardcoded interactions (should match training exactly)
    soc_features = ['MAF', 'MSI', 'EPP', 'CPB']
    ops_framing = ['framing_intensity', 'propaganda_index']  # PIO subset
    
    # secret_history_index x SOC
    for soc_feat in soc_features:
        if 'secret_history_index' in df_feat.columns and soc_feat in df_feat.columns:
            col_name = f"secret_history_index_x_{soc_feat}"
            df_feat[col_name] = df_feat['secret_history_index'] * df_feat[soc_feat]
    
    # secret_history_index x PIO (framing subset)
    for pio_feat in ops_framing:
        if 'secret_history_index' in df_feat.columns and pio_feat in df_feat.columns:
            col_name = f"secret_history_index_x_{pio_feat}"
            df_feat[col_name] = df_feat['secret_history_index'] * df_feat[pio_feat]
    
    # coordination_index x suppression_pressure_index
    if 'coordination_index' in df_feat.columns and 'suppression_pressure_index' in df_feat.columns:
        df_feat['coordination_index_x_suppression_pressure_index'] = (
            df_feat['coordination_index'] * df_feat['suppression_pressure_index']
        )
    
    # finance_pressure_index x RSR
    if 'finance_pressure_index' in df_feat.columns and 'RSR' in df_feat.columns:
        df_feat['finance_pressure_index_x_RSR'] = (
            df_feat['finance_pressure_index'] * df_feat['RSR']
        )
    
    # framing_intensity x MAF
    if 'framing_intensity' in df_feat.columns and 'MAF' in df_feat.columns:
        df_feat['framing_intensity_x_MAF'] = (
            df_feat['framing_intensity'] * df_feat['MAF']
        )
    
    return df_feat


def detect_paranoid_signals(models, df: pd.DataFrame) -> list:
    """Use trained models to detect paranoid signals."""
    signals = []
    
    # Create same features as training
    df_feat = create_inference_features(df)
    
    # Get feature columns (same as training)
    exclude_cols = ['topic_id', 'ts_start', 'ts_end', 'region', 'actor_group', 'political_load']
    exclude_cols += [col for col in df_feat.columns if col.startswith('target_')]
    feature_cols = [col for col in df_feat.columns if col not in exclude_cols]
    
    X = df_feat[feature_cols]
    X = X.fillna(X.median())
    
    # Apply log1p to count features manually
    count_features = [f for f in feature_cols if any(x in f for x in ['events', 'incidents', 'TAB', 'NEK'])]
    for feat in count_features:
        if feat in X.columns:
            X[feat] = np.log1p(X[feat])
    
    # Get predictions for each target
    predictions = {}
    for target, model in models.items():
        if target == 'conflict_intensity':
            pred = model.predict(X)
            predictions[target] = pred
        else:
            pred_proba = model.predict_proba(X)[:, 1]
            predictions[target] = pred_proba
    
    # Detect high-risk samples
    for i in range(len(df)):
        risk_factors = []
        severity = "low"
        
        if predictions['sensitive_class'][i] > 0.7:
            risk_factors.append("high_sensitivity")
            severity = "high"
        
        if predictions['suppression_event_6w'][i] > 0.6:
            risk_factors.append("suppression_imminent")
            severity = "high"
        
        if predictions['narrative_shift_4w'][i] > 0.5:
            risk_factors.append("narrative_manipulation")
            if severity == "low":
                severity = "medium"
        
        if predictions['conflict_intensity'][i] > 0.6:
            risk_factors.append("conflict_escalation")
            severity = "high"
        
        # Generate signal if any risk factors detected
        if risk_factors:
            # Identify the most anomalous features
            evidence = []
            feature_values = X.iloc[i]
            
            # Check for anomalous propaganda
            if feature_values.get('propaganda_index', 0) > 2:
                evidence.append(f"propaganda_spike: {feature_values['propaganda_index']:.2f}")
            
            # Check coordination
            if feature_values.get('coordination_index', 0) > 1.5:
                evidence.append(f"coordination_detected: {feature_values['coordination_index']:.2f}")
            
            # Check suppression
            if feature_values.get('suppression_pressure_index', 0) > 1:
                evidence.append(f"suppression_pressure: {feature_values['suppression_pressure_index']:.2f}")
            
            # Check secret history signals
            if feature_values.get('secret_history_index', 0) > 1:
                evidence.append(f"secret_history_anomaly: {feature_values['secret_history_index']:.2f}")
            
            if not evidence:
                evidence = ["anomalous_pattern_detected"]
            
            signal = {
                "id": f"paranoid_{i:04d}",
                "timestamp": (datetime.now() - timedelta(hours=np.random.randint(0, 24))).isoformat() + "Z",
                "category": "paranoid_detection",
                "signal_type": "multitarget_anomaly",
                "risk_factors": risk_factors,
                "severity": severity,
                "evidence": evidence,
                "scores": {
                    "sensitive_class": float(predictions['sensitive_class'][i]),
                    "suppression_6w": float(predictions['suppression_event_6w'][i]),
                    "narrative_shift": float(predictions['narrative_shift_4w'][i]),
                    "conflict_intensity": float(predictions['conflict_intensity'][i])
                },
                "confidence": min(0.95, max(0.6, np.mean([
                    predictions['sensitive_class'][i],
                    predictions['suppression_event_6w'][i],
                    predictions['narrative_shift_4w'][i]
                ])))
            }
            
            signals.append(signal)
    
    return signals


def main():
    parser = argparse.ArgumentParser(description="Generate paranoid signals")
    parser.add_argument('--models', default='artifacts/paranoid_models.joblib', help='Models path')
    parser.add_argument('--out', default='artifacts/signal.raw.json', help='Signal output path')
    parser.add_argument('--n', type=int, default=50, help='Number of samples to analyze')
    
    args = parser.parse_args()
    
    # Load models
    print(f"📊 Loading models from {args.models}")
    models = load_models(args.models)
    
    # Generate monitoring data
    print(f"🔍 Generating {args.n} monitoring samples...")
    df = generate_signal_data(args.n)
    
    # Detect signals
    print("🚨 Detecting paranoid signals...")
    signals = detect_paranoid_signals(models, df)
    
    # Save highest severity signal
    if signals:
        # Sort by severity and confidence
        severity_order = {"high": 3, "medium": 2, "low": 1}
        signals.sort(key=lambda x: (severity_order[x['severity']], x['confidence']), reverse=True)
        
        top_signal = signals[0]
        
        with open(args.out, 'w') as f:
            json.dump(top_signal, f, indent=2)
        
        print(f"✅ Generated signal: {top_signal['signal_type']} (severity: {top_signal['severity']})")
        print(f"🎯 Risk factors: {', '.join(top_signal['risk_factors'])}")
        print(f"📝 Evidence: {', '.join(top_signal['evidence'])}")
        print(f"💾 Saved to: {args.out}")
    else:
        # Generate a benign signal
        benign_signal = {
            "id": "paranoid_benign",
            "timestamp": datetime.now().isoformat() + "Z",
            "category": "paranoid_detection",
            "signal_type": "routine_monitoring",
            "risk_factors": [],
            "severity": "low",
            "evidence": ["normal_patterns"],
            "scores": {"all_clear": 0.95},
            "confidence": 0.85
        }
        
        with open(args.out, 'w') as f:
            json.dump(benign_signal, f, indent=2)
        
        print("✅ No high-risk signals detected - generated benign signal")
        print(f"💾 Saved to: {args.out}")


if __name__ == "__main__":
    main()
