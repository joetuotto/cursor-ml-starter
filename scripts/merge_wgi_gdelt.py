#!/usr/bin/env python3
"""Merge WGI and GDELT data for Paranoid Model v5."""

import argparse
import os
import requests
import zipfile
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')


def download_file(url: str, output_path: str) -> bool:
    """Download a file from URL."""
    try:
        print(f"📥 Downloading {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Downloaded to {output_path}")
        return True
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False


def extract_zip(zip_path: str, extract_dir: str) -> bool:
    """Extract ZIP file."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print(f"📂 Extracted {zip_path} to {extract_dir}")
        return True
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return False


def download_wgi_data(raw_dir: str) -> str:
    """Download and extract WGI data."""
    wgi_url = "https://databankfiles.worldbank.org/public/ddpext_download/WGI_csv.zip"
    wgi_zip = os.path.join(raw_dir, "wgi.zip")
    wgi_dir = os.path.join(raw_dir, "wgi")
    
    if download_file(wgi_url, wgi_zip):
        if extract_zip(wgi_zip, wgi_dir):
            # Find the actual WGI data CSV
            wgi_files = list(Path(wgi_dir).rglob("*WGI*.csv"))
            if wgi_files:
                return str(wgi_files[0])
    
    return None


def get_gdelt_recent_urls(days: int = 90) -> List[str]:
    """Get GDELT event URLs for the last N days."""
    urls = []
    base_url = "http://data.gdeltproject.org/gdeltv2"
    
    # Generate URLs for recent days
    end_date = datetime.now()
    for i in range(days):
        date = end_date - timedelta(days=i)
        date_str = date.strftime("%Y%m%d")
        
        # Try a few hour intervals per day (GDELT updates every 15 minutes)
        for hour in ["000000", "060000", "120000", "180000"]:
            url = f"{base_url}/{date_str}{hour}.export.CSV.zip"
            urls.append(url)
    
    return urls[:20]  # Limit to 20 files to avoid overwhelming


def download_gdelt_data(raw_dir: str, max_files: int = 10) -> List[str]:
    """Download recent GDELT event data."""
    gdelt_dir = os.path.join(raw_dir, "gdelt")
    os.makedirs(gdelt_dir, exist_ok=True)
    
    urls = get_gdelt_recent_urls()
    downloaded_files = []
    
    print(f"🌍 Attempting to download {min(max_files, len(urls))} GDELT files...")
    
    for i, url in enumerate(urls[:max_files]):
        filename = os.path.basename(url)
        local_path = os.path.join(gdelt_dir, filename)
        
        if download_file(url, local_path):
            # Extract the ZIP
            extract_dir = os.path.join(gdelt_dir, f"extract_{i}")
            if extract_zip(local_path, extract_dir):
                # Find CSV files
                csv_files = list(Path(extract_dir).glob("*.CSV"))
                if csv_files:
                    downloaded_files.extend([str(f) for f in csv_files])
    
    print(f"✅ Downloaded {len(downloaded_files)} GDELT CSV files")
    return downloaded_files


def process_wgi_data(wgi_file: str) -> pd.DataFrame:
    """Process WGI data into paranoid features."""
    print("🏛️ Processing WGI data...")
    
    try:
        wgi = pd.read_csv(wgi_file)
        
        # Clean column names
        wgi.columns = wgi.columns.str.strip()
        
        # Essential governance indicators
        keep_cols = ['Country Name', 'Country Code', 'Year']
        indicator_cols = []
        
        # Look for key WGI indicators
        for col in wgi.columns:
            if any(indicator in col.lower() for indicator in [
                'voice', 'accountability', 'political stability', 'rule of law', 
                'regulatory quality', 'government effectiveness', 'control of corruption'
            ]):
                indicator_cols.append(col)
        
        if not indicator_cols:
            # Fallback: use numeric columns
            indicator_cols = [col for col in wgi.columns if wgi[col].dtype in ['float64', 'int64']][:10]
        
        wgi_clean = wgi[keep_cols + indicator_cols].copy()
        
        # Rename to paranoid features
        rename_map = {}
        for i, col in enumerate(indicator_cols[:8]):
            paranoid_names = ['TAB', 'NEK', 'HSK', 'HMNI', 'RSR', 'ARDI', 'SRK', 'PKR']
            if i < len(paranoid_names):
                rename_map[col] = paranoid_names[i]
        
        wgi_clean = wgi_clean.rename(columns=rename_map)
        
        # Filter recent years
        if 'Year' in wgi_clean.columns:
            wgi_clean = wgi_clean[wgi_clean['Year'] >= 2020]
        
        return wgi_clean
        
    except Exception as e:
        print(f"❌ WGI processing failed: {e}")
        return pd.DataFrame()


def process_gdelt_data(gdelt_files: List[str]) -> pd.DataFrame:
    """Process GDELT data into paranoid features."""
    print("📰 Processing GDELT data...")
    
    if not gdelt_files:
        return pd.DataFrame()
    
    # GDELT 2.0 Event format (first few columns)
    gdelt_cols = [
        'GLOBALEVENTID', 'SQLDATE', 'MonthYear', 'Year', 'FractionDate',
        'Actor1Code', 'Actor1Name', 'Actor1CountryCode', 'Actor1KnownGroupCode',
        'Actor2Code', 'Actor2Name', 'Actor2CountryCode', 'Actor2KnownGroupCode',
        'IsRootEvent', 'EventCode', 'EventBaseCode', 'EventRootCode',
        'QuadClass', 'GoldsteinScale', 'NumMentions', 'NumSources', 'NumArticles',
        'AvgTone', 'Actor1Geo_Type', 'Actor1Geo_FullName', 'Actor1Geo_CountryCode',
        'Actor2Geo_Type', 'Actor2Geo_FullName', 'Actor2Geo_CountryCode',
        'ActionGeo_Type', 'ActionGeo_FullName', 'ActionGeo_CountryCode'
    ]
    
    all_data = []
    
    for file_path in gdelt_files[:5]:  # Limit to first 5 files
        try:
            # GDELT files are tab-separated and often very large
            df = pd.read_csv(file_path, sep='\t', header=None, 
                           names=gdelt_cols[:30], low_memory=False, nrows=10000)
            all_data.append(df)
        except Exception as e:
            print(f"⚠️ Skipping {file_path}: {e}")
            continue
    
    if not all_data:
        return pd.DataFrame()
    
    # Combine all data
    gdelt = pd.concat(all_data, ignore_index=True)
    
    # Create paranoid features from GDELT
    country_features = gdelt.groupby('ActionGeo_CountryCode').agg({
        'AvgTone': 'mean',
        'GoldsteinScale': 'mean', 
        'NumMentions': 'sum',
        'NumSources': 'sum',
        'NumArticles': 'sum',
        'QuadClass': lambda x: (x == 4).mean(),  # Verbal cooperation
        'EventCode': lambda x: len(x.unique())   # Event diversity
    }).reset_index()
    
    # Map to paranoid feature names
    country_features = country_features.rename(columns={
        'ActionGeo_CountryCode': 'Country Code',
        'AvgTone': 'framing_intensity',
        'GoldsteinScale': 'coordination_index', 
        'NumMentions': 'propaganda_index',
        'NumSources': 'suppression_pressure_index',
        'NumArticles': 'secret_history_index',
        'QuadClass': 'network_density',
        'EventCode': 'geospatial_risk'
    })
    
    return country_features


def merge_wgi_gdelt(wgi_df: pd.DataFrame, gdelt_df: pd.DataFrame) -> pd.DataFrame:
    """Merge WGI and GDELT data into paranoid format."""
    print("🔗 Merging WGI and GDELT data...")
    
    if wgi_df.empty:
        print("⚠️ WGI data is empty, using GDELT only")
        merged = gdelt_df.copy() if not gdelt_df.empty else pd.DataFrame()
    elif gdelt_df.empty:
        print("⚠️ GDELT data is empty, using WGI only")
        merged = wgi_df.copy()
    else:
        # Merge on country code
        merged = pd.merge(wgi_df, gdelt_df, on='Country Code', how='outer')
    
    if merged.empty:
        print("❌ No data after merging")
        return pd.DataFrame()
    
    # Add missing paranoid features with synthetic data
    paranoid_features = {
        # Base features
        'TAB': lambda: np.random.lognormal(0, 1, len(merged)),
        'NEK': lambda: np.random.lognormal(0, 1, len(merged)),
        'HSK': lambda: np.random.uniform(0, 1, len(merged)),
        'HMNI': lambda: np.random.uniform(0, 1, len(merged)),
        'RSR': lambda: np.random.exponential(1, len(merged)),
        'ARDI': lambda: np.random.exponential(1, len(merged)),
        'SRK': lambda: np.random.exponential(1, len(merged)),
        'PKR': lambda: np.random.exponential(1, len(merged)),
        
        # Social features
        'MAF': lambda: np.random.uniform(0, 1, len(merged)),
        'MSI': lambda: np.random.uniform(0, 1, len(merged)),
        'EPP': lambda: np.random.uniform(0, 1, len(merged)),
        'CPB': lambda: np.random.uniform(0, 1, len(merged)),
        
        # SHL features
        'OPK': lambda: np.random.exponential(1, len(merged)),
        'ALGO': lambda: np.random.exponential(1, len(merged)),
        'UL': lambda: np.random.exponential(1, len(merged)),
        'IPO': lambda: np.random.exponential(1, len(merged)),
        'HAN': lambda: np.random.exponential(1, len(merged)),
        'AV': lambda: np.random.exponential(1, len(merged)),
        'TKI': lambda: np.random.exponential(1, len(merged)),
        
        # Operational indices (some may exist from GDELT)
        'propaganda_index': lambda: np.random.normal(0, 1, len(merged)),
        'framing_intensity': lambda: np.random.normal(0, 1, len(merged)), 
        'coordination_index': lambda: np.random.normal(0, 1, len(merged)),
        'suppression_pressure_index': lambda: np.random.normal(0, 1, len(merged)),
        'secret_history_index': lambda: np.random.normal(0, 1, len(merged)),
        'hist_visibility_gap': lambda: np.random.normal(0, 1, len(merged)),
        'hist_missing_docs_score': lambda: np.random.normal(0, 1, len(merged)),
        'hist_treatment_asymmetry': lambda: np.random.normal(0, 1, len(merged)),
        'hist_meta_ref_ratio': lambda: np.random.normal(0, 1, len(merged)),
        'hist_echo_signal': lambda: np.random.normal(0, 1, len(merged)),
        'finance_pressure_index': lambda: np.random.normal(0, 1, len(merged)),
        'network_density': lambda: np.random.normal(0, 1, len(merged)),
        'geospatial_risk': lambda: np.random.normal(0, 1, len(merged)),
        'precursor_score': lambda: np.random.normal(0, 1, len(merged)),
        
        # External features
        'external_sanction_index': lambda: np.random.poisson(2, len(merged)),
        'media_censorship_score': lambda: np.random.poisson(2, len(merged)),
        'incidents_sanction_events_24m': lambda: np.random.poisson(2, len(merged)),
        'censorship_events_24m': lambda: np.random.poisson(2, len(merged))
    }
    
    # Add missing features
    for feature, generator in paranoid_features.items():
        if feature not in merged.columns:
            merged[feature] = generator()
    
    # Add metadata columns
    merged['topic_id'] = [f"topic_{i:04d}" for i in range(len(merged))]
    merged['ts_start'] = pd.date_range('2024-01-01', periods=len(merged), freq='D')
    merged['ts_end'] = merged['ts_start'] + pd.Timedelta(days=1)
    merged['region'] = np.random.choice(['NA', 'EU', 'AS', 'AF', 'SA', 'OC'], len(merged))
    merged['actor_group'] = np.random.choice(['gov', 'ngo', 'corp', 'media', 'acad', 'mil'], len(merged))
    merged['political_load'] = np.random.uniform(-1, 1, len(merged))
    
    # Generate correlated targets
    base_signal = (
        0.3 * merged['propaganda_index'] + 
        0.2 * merged['coordination_index'] +
        0.4 * merged['suppression_pressure_index'] +
        0.1 * np.random.normal(0, 1, len(merged))
    )
    
    merged['target_sensitive_class'] = (base_signal > np.percentile(base_signal, 70)).astype(int)
    merged['target_suppression_event_6w'] = (
        (base_signal + 0.3 * merged['media_censorship_score']) > np.percentile(base_signal, 75)
    ).astype(int)
    merged['target_narrative_shift_4w'] = (
        (merged['framing_intensity'] + 0.2 * base_signal) > np.percentile(merged['framing_intensity'], 80)
    ).astype(int)
    merged['target_conflict_intensity'] = np.clip(
        0.6 * base_signal + 0.4 * merged['geospatial_risk'] + 0.1 * np.random.normal(0, 0.5, len(merged)),
        0, 1
    )
    
    # Convert timestamps to ISO format
    merged['ts_start'] = merged['ts_start'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    merged['ts_end'] = merged['ts_end'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    return merged


def main():
    parser = argparse.ArgumentParser(description="Merge WGI and GDELT data for Paranoid Model v5")
    parser.add_argument('--wgi_dir', default='data/raw/wgi', help='WGI data directory')
    parser.add_argument('--gdelt_dir', default='data/raw/gdelt', help='GDELT data directory') 
    parser.add_argument('--out', default='data/paranoid.csv', help='Output CSV path')
    parser.add_argument('--download', action='store_true', help='Download fresh data')
    parser.add_argument('--max_gdelt_files', type=int, default=10, help='Max GDELT files to download')
    parser.add_argument('--days', type=int, help='Days to fetch (overrides PARANOID_RANGE_DAYS)')
    parser.add_argument('--min-events', type=int, help='Minimum events required (overrides PARANOID_MIN_EVENTS)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    # Environment variable support
    days = args.days or int(os.getenv('PARANOID_RANGE_DAYS', '90'))
    min_events = getattr(args, 'min_events') or int(os.getenv('PARANOID_MIN_EVENTS', '200000'))
    debug = args.debug or os.getenv('PARANOID_DEBUG', '').lower() == 'true'
    
    if debug:
        print(f"🔧 Debug mode: days={days}, min_events={min_events}")
    
    # Create output directory
    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    os.makedirs('data/raw', exist_ok=True)
    
    wgi_df = pd.DataFrame()
    gdelt_df = pd.DataFrame()
    
    if args.download:
        print("🌍 Downloading fresh data...")
        
        # Download WGI
        wgi_file = download_wgi_data('data/raw')
        if wgi_file:
            wgi_df = process_wgi_data(wgi_file)
        
        # Download GDELT
        gdelt_files = download_gdelt_data('data/raw', args.max_gdelt_files)
        if gdelt_files:
            gdelt_df = process_gdelt_data(gdelt_files)
            if debug:
                print(f"🔍 GDELT events loaded: {len(gdelt_df)}")
            
            # Check minimum events threshold
            if len(gdelt_df) < min_events:
                print(f"⚠️ Too few GDELT events: {len(gdelt_df)} < {min_events}")
                if not debug:  # Allow override in debug mode
                    print("❌ Exiting due to insufficient data quality")
                    exit(1)
    
    else:
        print("📁 Using existing data...")
        
        # Process existing WGI files
        wgi_files = list(Path(args.wgi_dir).rglob("*WGI*.csv")) if os.path.exists(args.wgi_dir) else []
        if wgi_files:
            wgi_df = process_wgi_data(str(wgi_files[0]))
        
        # Process existing GDELT files
        gdelt_files = list(Path(args.gdelt_dir).rglob("*.CSV")) if os.path.exists(args.gdelt_dir) else []
        if gdelt_files:
            gdelt_df = process_gdelt_data([str(f) for f in gdelt_files])
    
    # Merge data
    merged_df = merge_wgi_gdelt(wgi_df, gdelt_df)
    
    if merged_df.empty:
        print("⚠️ No real data available, generating synthetic dataset...")
        from generate_mock import generate_mock_data
        merged_df = generate_mock_data(n_samples=200, seed=1337)
    
    # Save result
    merged_df.to_csv(args.out, index=False)
    print(f"✅ Saved {len(merged_df)} samples to {args.out}")
    print(f"📊 Columns: {len(merged_df.columns)}")
    print(f"🎯 Target distribution:")
    for target in ['target_sensitive_class', 'target_suppression_event_6w', 'target_narrative_shift_4w']:
        if target in merged_df.columns:
            print(f"  {target}: {merged_df[target].mean():.3f}")


if __name__ == "__main__":
    main()
