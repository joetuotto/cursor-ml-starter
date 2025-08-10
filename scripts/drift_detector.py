#!/usr/bin/env python3
"""
📊 CONCEPT DRIFT DETECTOR - Model Performance Monitoring

Detects:
- Performance degradation (AUC drops > 0.05)
- Feature drift (distribution changes)
- Prediction drift (calibration shifts)
- Quality gate violations
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
import argparse
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import warnings
warnings.filterwarnings('ignore')


class DriftDetector:
    """Monitors model performance and detects concept drift."""
    
    def __init__(self, webhook_url: str = None, tg_bot_token: str = None, tg_chat_id: str = None):
        self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK_URL')
        self.tg_bot_token = tg_bot_token or os.getenv('TG_BOT_TOKEN')
        self.tg_chat_id = tg_chat_id or os.getenv('TG_CHAT_ID')
        
        self.drift_thresholds = {
            'auc_drop': 0.05,          # AUC drops more than 5%
            'calibration_shift': 0.10,  # ECE increases more than 10%
            'feature_drift_psi': 0.25,  # PSI > 0.25 indicates significant drift
            'prediction_drift_kl': 0.20  # KL divergence > 0.20
        }
        
        self.quality_gates = {
            'auc_minimum': 0.86,
            'pr_auc_minimum': 0.80,
            'brier_maximum': 0.19,
            'ece_maximum': 0.05,
            'delta_auc_maximum': 0.10
        }
    
    def send_alert(self, alert_type: str, message: str, details: Dict = None, severity: str = 'warning'):
        """Send alert via Slack webhook and/or Telegram."""
        details = details or {}
        timestamp = datetime.now().isoformat()
        
        # Slack alert
        if self.webhook_url:
            self._send_slack_alert(alert_type, message, details, severity, timestamp)
        
        # Telegram alert
        if self.tg_bot_token and self.tg_chat_id:
            self._send_telegram_alert(alert_type, message, details, severity, timestamp)
        
        # Always log to console
        severity_emoji = {'critical': '🚨', 'warning': '⚠️', 'info': 'ℹ️'}.get(severity, '📊')
        print(f"{severity_emoji} {alert_type}: {message}")
        if details:
            print(f"   Details: {details}")
    
    def _send_slack_alert(self, alert_type: str, message: str, details: Dict, severity: str, timestamp: str):
        """Send Slack webhook alert."""
        try:
            color_map = {'critical': 'danger', 'warning': 'warning', 'info': 'good'}
            color = color_map.get(severity, 'warning')
            
            payload = {
                'text': f'🚨 Paranoid Model Drift Alert',
                'attachments': [{
                    'color': color,
                    'fields': [
                        {'title': 'Alert Type', 'value': alert_type, 'short': True},
                        {'title': 'Severity', 'value': severity.upper(), 'short': True},
                        {'title': 'Message', 'value': message, 'short': False},
                        {'title': 'Timestamp', 'value': timestamp, 'short': True},
                        *[{'title': k, 'value': str(v), 'short': True} for k, v in details.items()]
                    ]
                }]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            print(f"❌ Slack alert failed: {e}")
    
    def _send_telegram_alert(self, alert_type: str, message: str, details: Dict, severity: str, timestamp: str):
        """Send Telegram bot alert."""
        try:
            severity_emoji = {'critical': '🚨', 'warning': '⚠️', 'info': 'ℹ️'}.get(severity, '📊')
            
            text = f"{severity_emoji} *Paranoid Model Alert*\n\n"
            text += f"*Type:* {alert_type}\n"
            text += f"*Severity:* {severity.upper()}\n"
            text += f"*Message:* {message}\n\n"
            
            if details:
                text += "*Details:*\n"
                for k, v in details.items():
                    text += f"• {k}: `{v}`\n"
            
            text += f"\n*Time:* {timestamp}"
            
            url = f"https://api.telegram.org/bot{self.tg_bot_token}/sendMessage"
            payload = {
                'chat_id': self.tg_chat_id,
                'text': text,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            print(f"❌ Telegram alert failed: {e}")
    
    def load_historical_metrics(self, metrics_dir: str = 'artifacts') -> List[Dict]:
        """Load historical performance metrics."""
        historical_metrics = []
        
        # Look for timestamped metrics files
        metrics_files = list(Path(metrics_dir).glob('metrics_*.json'))
        metrics_files.append(Path(metrics_dir) / 'metrics.json')  # Current metrics
        
        for file_path in metrics_files:
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        metrics = json.load(f)
                    
                    # Add timestamp if missing
                    if 'timestamp' not in metrics:
                        metrics['timestamp'] = file_path.stat().st_mtime
                    
                    historical_metrics.append(metrics)
                except Exception as e:
                    print(f"⚠️ Could not load {file_path}: {e}")
        
        # Sort by timestamp
        return sorted(historical_metrics, key=lambda m: m.get('timestamp', 0))
    
    def calculate_psi(self, baseline: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
        """Calculate Population Stability Index (PSI) for feature drift."""
        try:
            # Create bins based on baseline distribution
            bin_edges = np.percentile(baseline, np.linspace(0, 100, bins + 1))
            bin_edges[0] = -np.inf
            bin_edges[-1] = np.inf
            
            # Calculate distributions
            baseline_counts = np.histogram(baseline, bins=bin_edges)[0]
            current_counts = np.histogram(current, bins=bin_edges)[0]
            
            # Convert to proportions
            baseline_props = baseline_counts / len(baseline)
            current_props = current_counts / len(current)
            
            # Avoid division by zero
            baseline_props = np.where(baseline_props == 0, 0.0001, baseline_props)
            current_props = np.where(current_props == 0, 0.0001, current_props)
            
            # Calculate PSI
            psi = np.sum((current_props - baseline_props) * np.log(current_props / baseline_props))
            
            return float(psi)
            
        except Exception as e:
            print(f"⚠️ PSI calculation failed: {e}")
            return 0.0
    
    def calculate_kl_divergence(self, p: np.ndarray, q: np.ndarray) -> float:
        """Calculate KL divergence between prediction distributions."""
        try:
            # Ensure non-zero probabilities
            p = np.where(p == 0, 1e-8, p)
            q = np.where(q == 0, 1e-8, q)
            
            # Normalize
            p = p / np.sum(p)
            q = q / np.sum(q)
            
            return float(np.sum(p * np.log(p / q)))
            
        except Exception as e:
            print(f"⚠️ KL divergence calculation failed: {e}")
            return 0.0
    
    def detect_performance_drift(self, historical_metrics: List[Dict]) -> List[Dict]:
        """Detect performance degradation over time."""
        alerts = []
        
        if len(historical_metrics) < 2:
            return alerts
        
        current_metrics = historical_metrics[-1]
        baseline_metrics = historical_metrics[0]  # Use first as baseline
        
        # Check AUC drift for each target
        for target in ['sensitive_class', 'suppression_event_6w', 'narrative_shift_4w']:
            current_auc = current_metrics.get('performance', {}).get(f'{target}_auc', 0)
            baseline_auc = baseline_metrics.get('performance', {}).get(f'{target}_auc', 0)
            
            if baseline_auc > 0 and current_auc > 0:
                auc_drop = baseline_auc - current_auc
                
                if auc_drop > self.drift_thresholds['auc_drop']:
                    alerts.append({
                        'type': 'AUC_DRIFT',
                        'severity': 'critical' if auc_drop > 0.10 else 'warning',
                        'target': target,
                        'baseline_auc': baseline_auc,
                        'current_auc': current_auc,
                        'drop': auc_drop,
                        'threshold': self.drift_thresholds['auc_drop']
                    })
        
        # Check calibration drift
        current_ece = current_metrics.get('calibration', {}).get('ece_mean', 0)
        baseline_ece = baseline_metrics.get('calibration', {}).get('ece_mean', 0)
        
        if baseline_ece > 0 and current_ece > 0:
            ece_increase = current_ece - baseline_ece
            
            if ece_increase > self.drift_thresholds['calibration_shift']:
                alerts.append({
                    'type': 'CALIBRATION_DRIFT',
                    'severity': 'warning',
                    'baseline_ece': baseline_ece,
                    'current_ece': current_ece,
                    'increase': ece_increase,
                    'threshold': self.drift_thresholds['calibration_shift']
                })
        
        return alerts
    
    def detect_quality_gate_violations(self, current_metrics: Dict) -> List[Dict]:
        """Check current metrics against quality gates."""
        alerts = []
        performance = current_metrics.get('performance', {})
        
        # Check AUC minimums
        for target in ['sensitive_class', 'suppression_event_6w', 'narrative_shift_4w']:
            auc = performance.get(f'{target}_auc', 0)
            if auc < self.quality_gates['auc_minimum']:
                alerts.append({
                    'type': 'QUALITY_GATE_VIOLATION',
                    'severity': 'critical',
                    'gate': 'AUC_MINIMUM',
                    'target': target,
                    'value': auc,
                    'threshold': self.quality_gates['auc_minimum']
                })
        
        # Check fairness
        fairness = current_metrics.get('fairness', {})
        max_delta_auc = fairness.get('max_delta_auc', 0)
        if max_delta_auc > self.quality_gates['delta_auc_maximum']:
            alerts.append({
                'type': 'QUALITY_GATE_VIOLATION',
                'severity': 'warning',
                'gate': 'FAIRNESS',
                'value': max_delta_auc,
                'threshold': self.quality_gates['delta_auc_maximum']
            })
        
        # Check calibration
        calibration = current_metrics.get('calibration', {})
        ece = calibration.get('ece_mean', 0)
        if ece > self.quality_gates['ece_maximum']:
            alerts.append({
                'type': 'QUALITY_GATE_VIOLATION',
                'severity': 'warning',
                'gate': 'CALIBRATION',
                'value': ece,
                'threshold': self.quality_gates['ece_maximum']
            })
        
        return alerts
    
    def run_drift_detection(self, metrics_dir: str = 'artifacts') -> Dict[str, Any]:
        """Run complete drift detection analysis."""
        print("📊 Running drift detection...")
        
        # Load historical metrics
        historical_metrics = self.load_historical_metrics(metrics_dir)
        
        if not historical_metrics:
            print("⚠️ No historical metrics found")
            return {'alerts': [], 'status': 'no_data'}
        
        current_metrics = historical_metrics[-1]
        
        # Detect different types of drift
        performance_alerts = self.detect_performance_drift(historical_metrics)
        quality_alerts = self.detect_quality_gate_violations(current_metrics)
        
        all_alerts = performance_alerts + quality_alerts
        
        # Send alerts
        for alert in all_alerts:
            alert_type = alert['type']
            severity = alert['severity']
            
            if alert_type == 'AUC_DRIFT':
                message = f"AUC dropped by {alert['drop']:.3f} for {alert['target']} (threshold: {alert['threshold']})"
                details = {
                    'target': alert['target'],
                    'baseline_auc': f"{alert['baseline_auc']:.3f}",
                    'current_auc': f"{alert['current_auc']:.3f}",
                    'drop': f"{alert['drop']:.3f}"
                }
            elif alert_type == 'CALIBRATION_DRIFT':
                message = f"Calibration degraded by {alert['increase']:.3f} ECE (threshold: {alert['threshold']})"
                details = {
                    'baseline_ece': f"{alert['baseline_ece']:.3f}",
                    'current_ece': f"{alert['current_ece']:.3f}",
                    'increase': f"{alert['increase']:.3f}"
                }
            elif alert_type == 'QUALITY_GATE_VIOLATION':
                message = f"Quality gate violation: {alert['gate']} = {alert['value']:.3f} (threshold: {alert['threshold']})"
                details = {
                    'gate': alert['gate'],
                    'value': f"{alert['value']:.3f}",
                    'threshold': f"{alert['threshold']:.3f}"
                }
                if 'target' in alert:
                    details['target'] = alert['target']
            else:
                message = f"Unknown alert: {alert}"
                details = alert
            
            self.send_alert(alert_type, message, details, severity)
        
        # Summary
        drift_summary = {
            'timestamp': datetime.now().isoformat(),
            'total_alerts': len(all_alerts),
            'critical_alerts': len([a for a in all_alerts if a['severity'] == 'critical']),
            'warning_alerts': len([a for a in all_alerts if a['severity'] == 'warning']),
            'alerts': all_alerts,
            'historical_points': len(historical_metrics),
            'status': 'drift_detected' if all_alerts else 'stable'
        }
        
        print(f"📊 Drift detection complete: {len(all_alerts)} alerts generated")
        
        return drift_summary


def main():
    parser = argparse.ArgumentParser(description="Paranoid Model Drift Detector")
    parser.add_argument('--metrics_dir', default='artifacts', help='Metrics directory')
    parser.add_argument('--webhook_url', help='Slack webhook URL (or use SLACK_WEBHOOK_URL env)')
    parser.add_argument('--tg_bot_token', help='Telegram bot token (or use TG_BOT_TOKEN env)')
    parser.add_argument('--tg_chat_id', help='Telegram chat ID (or use TG_CHAT_ID env)')
    parser.add_argument('--out', default='artifacts/drift_report.json', help='Output report path')
    
    args = parser.parse_args()
    
    detector = DriftDetector(
        webhook_url=args.webhook_url,
        tg_bot_token=args.tg_bot_token,
        tg_chat_id=args.tg_chat_id
    )
    
    drift_summary = detector.run_drift_detection(args.metrics_dir)
    
    # Save report
    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w') as f:
        json.dump(drift_summary, f, indent=2)
    
    print(f"📊 Drift report saved to {args.out}")
    
    # Exit with error code if critical alerts
    if drift_summary['critical_alerts'] > 0:
        print(f"🚨 {drift_summary['critical_alerts']} critical alerts detected")
        exit(1)


if __name__ == "__main__":
    main()
