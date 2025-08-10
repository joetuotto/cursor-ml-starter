#!/usr/bin/env python3
"""Paranoid model v5 training pipeline with multitask learning."""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yaml
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    roc_auc_score, average_precision_score, brier_score_loss,
    mean_squared_error, r2_score
)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
import joblib


def load_config(config_path: str) -> Dict:
    """Load YAML configuration."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_data(data_path: str, fallback_path: str = None) -> pd.DataFrame:
    """Load training data with fallback."""
    if os.path.exists(data_path):
        print(f"📊 Loading data from {data_path}")
        return pd.read_csv(data_path)
    elif fallback_path and os.path.exists(fallback_path):
        print(f"⚠️  Main data not found, using fallback: {fallback_path}")
        return pd.read_csv(fallback_path)
    else:
        raise FileNotFoundError(f"Neither {data_path} nor {fallback_path} found")


def create_feature_groups(config: Dict) -> Dict[str, List[str]]:
    """Create feature groups from config."""
    return {
        'base': config['features']['base'],
        'soc': config['features']['soc'], 
        'shl': config['features']['shl'],
        'ops': config['features']['ops'],
        'externals': config['features']['externals']
    }


def create_interactions(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    """Create interaction features."""
    df_inter = df.copy()
    
    for interaction in config['features']['interactions']:
        feat1, feat2 = interaction
        
        if feat2 == 'SOC':
            # Interact feat1 with all SOC features
            for soc_feat in config['features']['soc']:
                if feat1 in df_inter.columns and soc_feat in df_inter.columns:
                    col_name = f"{feat1}_x_{soc_feat}"
                    df_inter[col_name] = df_inter[feat1] * df_inter[soc_feat]
        elif feat2 == 'PIO':
            # PIO = ops + framing subset
            pio_features = [f for f in config['features']['ops'] if 'framing' in f or 'propaganda' in f]
            for pio_feat in pio_features:
                if feat1 in df_inter.columns and pio_feat in df_inter.columns:
                    col_name = f"{feat1}_x_{pio_feat}"
                    df_inter[col_name] = df_inter[feat1] * df_inter[pio_feat]
        else:
            # Direct interaction
            if feat1 in df_inter.columns and feat2 in df_inter.columns:
                col_name = f"{feat1}_x_{feat2}"
                df_inter[col_name] = df_inter[feat1] * df_inter[feat2]
    
    return df_inter


def create_preprocessor(feature_cols: List[str], config: Dict) -> ColumnTransformer:
    """Create preprocessing pipeline."""
    
    # Identify feature types based on names
    count_features = [f for f in feature_cols if any(x in f for x in ['events', 'incidents', 'TAB', 'NEK'])]
    index_features = [f for f in feature_cols if 'index' in f or f in ['HSK', 'HMNI', 'RSR']]
    other_features = [f for f in feature_cols if f not in count_features + index_features]
    
    transformers = []
    
    if count_features:
        # log1p + minmax for counts
        transformers.append(('counts', Pipeline([
            ('log1p', None),  # Will handle in custom step
            ('minmax', MinMaxScaler())
        ]), count_features))
    
    if index_features:
        # z-score for indices
        transformers.append(('indices', StandardScaler(), index_features))
    
    if other_features:
        # clip + minmax for other features
        transformers.append(('features', MinMaxScaler(), other_features))
    
    return ColumnTransformer(transformers, remainder='passthrough')


def calculate_expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Calculate Expected Calibration Error (ECE)."""
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]
    
    ece = 0
    for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
        in_bin = (y_prob > bin_lower) & (y_prob <= bin_upper)
        prop_in_bin = in_bin.mean()
        
        if prop_in_bin > 0:
            accuracy_in_bin = y_true[in_bin].mean()
            avg_confidence_in_bin = y_prob[in_bin].mean()
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
    
    return ece


def calculate_fairness_metrics(y_true: np.ndarray, y_prob: np.ndarray, 
                             groups: np.ndarray) -> Dict[str, float]:
    """Calculate fairness metrics across groups."""
    group_aucs = {}
    for group in np.unique(groups):
        mask = groups == group
        if mask.sum() > 10:  # Minimum samples
            try:
                auc = roc_auc_score(y_true[mask], y_prob[mask])
                group_aucs[str(group)] = auc
            except:
                pass
    
    if len(group_aucs) > 1:
        aucs = list(group_aucs.values())
        delta_auc = max(aucs) - min(aucs)
    else:
        delta_auc = 0.0
    
    return {'group_aucs': group_aucs, 'delta_auc': delta_auc}


def train_multitask_model(df: pd.DataFrame, config: Dict) -> Dict[str, Any]:
    """Train multitask paranoid model."""
    print("🎯 Starting multitask training...")
    
    # Create features with interactions
    df_feat = create_interactions(df, config)
    
    # Get all feature columns (exclude metadata and targets)
    exclude_cols = ['topic_id', 'ts_start', 'ts_end', 'region', 'actor_group', 'political_load']
    exclude_cols += [col for col in df_feat.columns if col.startswith('target_')]
    feature_cols = [col for col in df_feat.columns if col not in exclude_cols]
    
    X = df_feat[feature_cols]
    
    # Handle missing values
    X = X.fillna(X.median())
    
    # Apply log1p to count features manually
    count_features = [f for f in feature_cols if any(x in f for x in ['events', 'incidents', 'TAB', 'NEK'])]
    for feat in count_features:
        if feat in X.columns:
            X[feat] = np.log1p(X[feat])
    
    # Create preprocessor
    preprocessor = create_preprocessor(feature_cols, config)
    
    # Set up temporal CV
    tss = TimeSeriesSplit(n_splits=config['cv_folds'])
    
    # Convert ts_end to datetime for splitting
    df_feat['ts_end_dt'] = pd.to_datetime(df_feat['ts_end'])
    sort_idx = df_feat['ts_end_dt'].argsort()
    
    X_sorted = X.iloc[sort_idx]
    df_sorted = df_feat.iloc[sort_idx]
    
    results = {}
    models = {}
    
    for target in config['targets']:
        print(f"\n🎯 Training {target}...")
        
        y = df_sorted[f'target_{target}'].values
        
        if target == 'conflict_intensity':
            # Continuous target - Ridge regression
            model = Pipeline([
                ('preprocessor', preprocessor),
                ('regressor', Ridge(alpha=1.0, random_state=config['seed']))
            ])
            
            cv_scores = []
            for train_idx, val_idx in tss.split(X_sorted):
                X_train, X_val = X_sorted.iloc[train_idx], X_sorted.iloc[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]
                
                model.fit(X_train, y_train)
                y_pred = model.predict(X_val)
                
                mse = mean_squared_error(y_val, y_pred)
                r2 = r2_score(y_val, y_pred)
                cv_scores.append({'mse': mse, 'r2': r2})
            
            # Train final model
            model.fit(X_sorted, y)
            models[target] = model
            
            avg_mse = np.mean([s['mse'] for s in cv_scores])
            avg_r2 = np.mean([s['r2'] for s in cv_scores])
            
            results[target] = {
                'type': 'continuous',
                'cv_mse': avg_mse,
                'cv_r2': avg_r2,
                'cv_rmse': np.sqrt(avg_mse)
            }
            
        else:
            # Binary target - Logistic regression with calibration
            base_model = LogisticRegression(
                random_state=config['seed'],
                max_iter=1000,
                penalty='l2'
            )
            
            if config['calibration'] == 'isotonic':
                model = Pipeline([
                    ('preprocessor', preprocessor),
                    ('classifier', CalibratedClassifierCV(
                        base_model, method='isotonic', cv=3
                    ))
                ])
            else:
                model = Pipeline([
                    ('preprocessor', preprocessor),
                    ('classifier', base_model)
                ])
            
            cv_scores = []
            for train_idx, val_idx in tss.split(X_sorted):
                X_train, X_val = X_sorted.iloc[train_idx], X_sorted.iloc[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]
                
                model.fit(X_train, y_train)
                y_prob = model.predict_proba(X_val)[:, 1]
                
                auc = roc_auc_score(y_val, y_prob)
                pr_auc = average_precision_score(y_val, y_prob)
                brier = brier_score_loss(y_val, y_prob)
                ece = calculate_expected_calibration_error(y_val, y_prob)
                
                cv_scores.append({
                    'auc': auc, 'pr_auc': pr_auc, 
                    'brier': brier, 'ece': ece
                })
            
            # Train final model
            model.fit(X_sorted, y)
            models[target] = model
            
            # Calculate fairness metrics on full dataset
            y_prob_full = model.predict_proba(X_sorted)[:, 1]
            groups = df_sorted['region'].values.astype(str)  # Ensure string type
            fairness = calculate_fairness_metrics(y, y_prob_full, groups)
            
            results[target] = {
                'type': 'binary',
                'cv_auc': np.mean([s['auc'] for s in cv_scores]),
                'cv_pr_auc': np.mean([s['pr_auc'] for s in cv_scores]),
                'cv_brier': np.mean([s['brier'] for s in cv_scores]),
                'cv_ece': np.mean([s['ece'] for s in cv_scores]),
                'fairness': fairness
            }
    
    return {'results': results, 'models': models, 'feature_names': feature_cols}


def save_results(results: Dict, models: Dict, feature_names: List[str], 
                config: Dict, outdir: str) -> None:
    """Save training results and models."""
    os.makedirs(outdir, exist_ok=True)
    
    # Save metrics
    metrics_path = os.path.join(outdir, 'metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(results['results'], f, indent=2)
    
    # Save models
    models_path = os.path.join(outdir, 'paranoid_models.joblib')
    joblib.dump(models, models_path)
    
    # Save feature importance (for binary models)
    importance_data = {}
    for target, model in models.items():
        if results['results'][target]['type'] == 'binary':
            try:
                if hasattr(model.named_steps['classifier'], 'feature_importances_'):
                    importance = model.named_steps['classifier'].feature_importances_
                elif hasattr(model.named_steps['classifier'], 'coef_'):
                    importance = np.abs(model.named_steps['classifier'].coef_[0])
                else:
                    importance = np.ones(len(feature_names))  # fallback
                
                importance_data[target] = dict(zip(feature_names, importance.tolist()))
            except:
                importance_data[target] = {}
    
    importance_path = os.path.join(outdir, 'feature_importance.json')
    with open(importance_path, 'w') as f:
        json.dump(importance_data, f, indent=2)
    
    print(f"✅ Results saved to {outdir}")
    print(f"📊 Metrics: {metrics_path}")
    print(f"🤖 Models: {models_path}")
    print(f"📈 Importance: {importance_path}")


def main():
    parser = argparse.ArgumentParser(description="Train paranoid model v5")
    parser.add_argument('--config', required=True, help='Config YAML path')
    parser.add_argument('--data', required=True, help='Training data CSV path')
    parser.add_argument('--fallback', help='Fallback data CSV path')
    parser.add_argument('--outdir', default='artifacts', help='Output directory')
    
    args = parser.parse_args()
    
    # Load config and data
    config = load_config(args.config)
    df = load_data(args.data, args.fallback)
    
    print(f"📊 Loaded {len(df)} samples")
    print(f"🎯 Targets: {config['targets']}")
    print(f"⚙️  Config: {args.config}")
    
    # Train models
    training_results = train_multitask_model(df, config)
    
    # Save results
    save_results(
        training_results, 
        training_results['models'],
        training_results['feature_names'],
        config, 
        args.outdir
    )
    
    # Print summary
    print("\n🎯 TRAINING SUMMARY:")
    for target, metrics in training_results['results'].items():
        print(f"\n{target}:")
        if metrics['type'] == 'binary':
            print(f"  AUC: {metrics['cv_auc']:.3f}")
            print(f"  PR-AUC: {metrics['cv_pr_auc']:.3f}")
            print(f"  Brier: {metrics['cv_brier']:.3f}")
            print(f"  ECE: {metrics['cv_ece']:.3f}")
            print(f"  Δ-AUC: {metrics['fairness']['delta_auc']:.3f}")
        else:
            print(f"  RMSE: {metrics['cv_rmse']:.3f}")
            print(f"  R²: {metrics['cv_r2']:.3f}")


if __name__ == "__main__":
    main()
