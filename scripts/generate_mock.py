#!/usr/bin/env python3
"""Generate mock paranoid model training data."""

import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def generate_mock_data(n_samples: int = 50, seed: int = 1337) -> pd.DataFrame:
    """Generate mock paranoid model data according to specifications."""
    np.random.seed(seed)
    
    # Generate base features
    data = {}
    
    # Topic and time metadata
    data['topic_id'] = [f"topic_{i:04d}" for i in range(n_samples)]
    
    # Generate dates over last 2 years
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)
    dates = pd.date_range(start_date, end_date, periods=n_samples)
    random_days = np.random.randint(1, 30, n_samples)
    data['ts_start'] = [d - timedelta(days=int(rd)) for d, rd in zip(dates, random_days)]
    data['ts_end'] = dates
    
    # Categorical features
    regions = ['NA', 'EU', 'AS', 'AF', 'SA', 'OC']
    actors = ['gov', 'ngo', 'corp', 'media', 'acad', 'mil']
    data['region'] = np.random.choice(regions, n_samples)
    data['actor_group'] = np.random.choice(actors, n_samples)
    data['political_load'] = np.random.uniform(-1, 1, n_samples)
    
    # Base features (TAB, NEK, etc.)
    base_features = ['TAB', 'NEK', 'HSK', 'HMNI', 'RSR', 'ARDI', 'SRK', 'PKR']
    for feat in base_features:
        data[feat] = np.random.lognormal(0, 1, n_samples)
    
    # Social features (MAF, MSI, etc.)
    soc_features = ['MAF', 'MSI', 'EPP', 'CPB']
    for feat in soc_features:
        data[feat] = np.random.uniform(0, 1, n_samples)
    
    # SHL features
    shl_features = ['OPK', 'ALGO', 'UL', 'IPO', 'HAN', 'AV', 'TKI']
    for feat in shl_features:
        data[feat] = np.random.exponential(1, n_samples)
    
    # Operational indices
    ops_features = [
        'propaganda_index', 'framing_intensity', 'coordination_index', 
        'suppression_pressure_index', 'secret_history_index', 'hist_visibility_gap',
        'hist_missing_docs_score', 'hist_treatment_asymmetry', 'hist_meta_ref_ratio',
        'hist_echo_signal', 'finance_pressure_index', 'network_density', 
        'geospatial_risk', 'precursor_score'
    ]
    for feat in ops_features:
        data[feat] = np.random.normal(0, 1, n_samples)
    
    # External features
    external_features = [
        'external_sanction_index', 'media_censorship_score', 
        'incidents_sanction_events_24m', 'censorship_events_24m'
    ]
    for feat in external_features:
        data[feat] = np.random.poisson(2, n_samples)
    
    # Generate correlated targets
    base_signal = (
        0.3 * data['propaganda_index'] +
        0.2 * data['coordination_index'] +
        0.4 * data['suppression_pressure_index'] +
        0.1 * np.random.normal(0, 1, n_samples)
    )
    
    # Binary targets
    data['target_sensitive_class'] = (base_signal > np.percentile(base_signal, 70)).astype(int)
    data['target_suppression_event_6w'] = (
        (base_signal + 0.3 * data['media_censorship_score']) > np.percentile(base_signal, 75)
    ).astype(int)
    data['target_narrative_shift_4w'] = (
        (data['framing_intensity'] + 0.2 * base_signal) > np.percentile(data['framing_intensity'], 80)
    ).astype(int)
    
    # Continuous target
    data['target_conflict_intensity'] = np.clip(
        0.6 * base_signal + 0.4 * data['geospatial_risk'] + 0.1 * np.random.normal(0, 0.5, n_samples),
        0, 1
    )
    
    df = pd.DataFrame(data)
    
    # Convert timestamps to ISO format
    df['ts_start'] = df['ts_start'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    df['ts_end'] = df['ts_end'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    return df


def main():
    parser = argparse.ArgumentParser(description="Generate mock paranoid model data")
    parser.add_argument('--out', default='data/paranoid_mock.csv', help='Output CSV path')
    parser.add_argument('--n', type=int, default=50, help='Number of samples')
    parser.add_argument('--seed', type=int, default=1337, help='Random seed')
    
    args = parser.parse_args()
    
    # Create output directory
    import os
    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    
    # Generate data
    df = generate_mock_data(args.n, args.seed)
    
    # Save
    df.to_csv(args.out, index=False)
    print(f"✅ Generated {len(df)} samples → {args.out}")
    print(f"📊 Columns: {list(df.columns)}")
    print(f"🎯 Targets: sensitive_class={df['target_sensitive_class'].mean():.2f}, "
          f"suppression_6w={df['target_suppression_event_6w'].mean():.2f}, "
          f"narrative_4w={df['target_narrative_shift_4w'].mean():.2f}, "
          f"conflict={df['target_conflict_intensity'].mean():.2f}")


if __name__ == "__main__":
    main()
