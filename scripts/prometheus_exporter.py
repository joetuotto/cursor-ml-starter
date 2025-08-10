#!/usr/bin/env python3
"""
📊 PROMETHEUS METRICS EXPORTER - Production Monitoring

Exports paranoid model metrics to Prometheus format for Grafana dashboards,
alerting, and production monitoring.
"""

import json
import os
import argparse
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any
import requests
import warnings
warnings.filterwarnings('ignore')


class PrometheusExporter:
    """Export paranoid metrics to Prometheus."""
    
    def __init__(self, pushgateway_url: str = None, job_name: str = 'paranoid-model'):
        self.pushgateway_url = pushgateway_url or os.getenv('PROMETHEUS_PUSHGATEWAY_URL', 'http://localhost:9091')
        self.job_name = job_name
        self.instance = os.getenv('INSTANCE_ID', 'paranoid-v5')
        self.environment = os.getenv('DEPLOYMENT_ENV', 'production')
        
    def load_metrics(self, artifacts_dir: str = 'artifacts') -> Dict[str, Any]:
        """Load all paranoid metrics from artifacts."""
        metrics_data = {}
        
        # Load main metrics
        metrics_path = os.path.join(artifacts_dir, 'metrics.json')
        if os.path.exists(metrics_path):
            with open(metrics_path, 'r') as f:
                metrics_data['performance'] = json.load(f)
        
        # Load drift report
        drift_path = os.path.join(artifacts_dir, 'drift_report.json')
        if os.path.exists(drift_path):
            with open(drift_path, 'r') as f:
                metrics_data['drift'] = json.load(f)
        
        # Load HUMINT profile
        humint_path = os.path.join(artifacts_dir, 'humint_profile.json')
        if os.path.exists(humint_path):
            with open(humint_path, 'r') as f:
                metrics_data['humint'] = json.load(f)
        
        # Load signal data
        signal_path = os.path.join(artifacts_dir, 'signal.raw.json')
        if os.path.exists(signal_path):
            with open(signal_path, 'r') as f:
                metrics_data['signal'] = json.load(f)
        
        # Load run metadata
        meta_path = os.path.join(artifacts_dir, 'run_meta.json')
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                metrics_data['metadata'] = json.load(f)
        
        return metrics_data
    
    def format_prometheus_metric(self, name: str, value: float, labels: Dict[str, str] = None, help_text: str = None) -> str:
        """Format a single Prometheus metric."""
        labels = labels or {}
        
        # Add standard labels
        standard_labels = {
            'job': self.job_name,
            'instance': self.instance,
            'environment': self.environment
        }
        labels.update(standard_labels)
        
        # Format labels
        label_str = ','.join([f'{k}="{v}"' for k, v in labels.items()])
        
        # Build metric string
        lines = []
        if help_text:
            lines.append(f'# HELP {name} {help_text}')
            lines.append(f'# TYPE {name} gauge')
        
        lines.append(f'{name}{{{label_str}}} {value}')
        
        return '\n'.join(lines)
    
    def export_to_prometheus_format(self, metrics_data: Dict[str, Any]) -> str:
        """Convert metrics to Prometheus format."""
        prometheus_metrics = []
        timestamp = int(time.time() * 1000)  # Unix timestamp in milliseconds
        
        # ===== MODEL PERFORMANCE METRICS =====
        if 'performance' in metrics_data:
            perf = metrics_data['performance']
            
            # AUC metrics for each target
            targets = ['sensitive_class', 'suppression_event_6w', 'narrative_shift_4w']
            for target in targets:
                auc_key = f'{target}_auc'
                if auc_key in perf.get('performance', {}):
                    auc_value = perf['performance'][auc_key]
                    prometheus_metrics.append(
                        self.format_prometheus_metric(
                            'paranoid_auc',
                            auc_value,
                            {'target': target},
                            'Area Under ROC Curve for paranoid classification targets'
                        )
                    )
                
                # PR-AUC
                pr_auc_key = f'{target}_pr_auc'
                if pr_auc_key in perf.get('performance', {}):
                    pr_auc_value = perf['performance'][pr_auc_key]
                    prometheus_metrics.append(
                        self.format_prometheus_metric(
                            'paranoid_pr_auc',
                            pr_auc_value,
                            {'target': target},
                            'Precision-Recall Area Under Curve'
                        )
                    )
            
            # Fairness metrics
            if 'fairness' in perf:
                fairness = perf['fairness']
                
                if 'max_delta_auc' in fairness:
                    prometheus_metrics.append(
                        self.format_prometheus_metric(
                            'paranoid_fairness_max_delta_auc',
                            fairness['max_delta_auc'],
                            {},
                            'Maximum Delta-AUC across demographic groups'
                        )
                    )
                
                # Group-specific AUCs
                for group, auc in fairness.get('group_auc', {}).items():
                    prometheus_metrics.append(
                        self.format_prometheus_metric(
                            'paranoid_group_auc',
                            auc,
                            {'group': group},
                            'AUC score by demographic group'
                        )
                    )
            
            # Calibration metrics
            if 'calibration' in perf:
                cal = perf['calibration']
                
                if 'ece_mean' in cal:
                    prometheus_metrics.append(
                        self.format_prometheus_metric(
                            'paranoid_calibration_ece',
                            cal['ece_mean'],
                            {},
                            'Expected Calibration Error'
                        )
                    )
                
                if 'brier_mean' in cal:
                    prometheus_metrics.append(
                        self.format_prometheus_metric(
                            'paranoid_brier_score',
                            cal['brier_mean'],
                            {},
                            'Brier Score for probability calibration'
                        )
                    )
        
        # ===== QUALITY GATES =====
        if 'metadata' in metrics_data and 'quality_gates' in metrics_data['metadata']:
            gates = metrics_data['metadata']['quality_gates']
            
            # Overall status
            overall_status = 1 if gates.get('overall_status') == 'PASS' else 0
            prometheus_metrics.append(
                self.format_prometheus_metric(
                    'paranoid_quality_gates_passed',
                    overall_status,
                    {},
                    'Overall quality gates status (1=PASS, 0=FAIL)'
                )
            )
            
            # Individual gates
            gate_metrics = {
                'auc_minimum': 'AUC minimum threshold check',
                'fairness_check': 'Fairness validation check',
                'calibration_check': 'Calibration quality check'
            }
            
            for gate, help_text in gate_metrics.items():
                if gate in gates:
                    value = 1 if gates[gate] else 0
                    prometheus_metrics.append(
                        self.format_prometheus_metric(
                            f'paranoid_quality_gate_{gate}',
                            value,
                            {},
                            help_text
                        )
                    )
        
        # ===== DRIFT METRICS =====
        if 'drift' in metrics_data:
            drift = metrics_data['drift']
            
            # Alert counts
            prometheus_metrics.append(
                self.format_prometheus_metric(
                    'paranoid_drift_alerts_total',
                    drift.get('total_alerts', 0),
                    {},
                    'Total drift alerts generated'
                )
            )
            
            prometheus_metrics.append(
                self.format_prometheus_metric(
                    'paranoid_drift_alerts_critical',
                    drift.get('critical_alerts', 0),
                    {},
                    'Critical drift alerts'
                )
            )
            
            # Drift status
            drift_status = 1 if drift.get('status') == 'stable' else 0
            prometheus_metrics.append(
                self.format_prometheus_metric(
                    'paranoid_drift_status_stable',
                    drift_status,
                    {},
                    'Model drift status (1=stable, 0=drift detected)'
                )
            )
        
        # ===== SIGNAL DETECTION =====
        if 'signal' in metrics_data:
            signal = metrics_data['signal']
            
            # Signal severity
            severity_mapping = {'high': 3, 'medium': 2, 'low': 1}
            severity_value = severity_mapping.get(signal.get('severity', 'low'), 1)
            prometheus_metrics.append(
                self.format_prometheus_metric(
                    'paranoid_latest_signal_severity',
                    severity_value,
                    {'signal_type': signal.get('signal_type', 'unknown')},
                    'Latest signal severity level (1=low, 2=medium, 3=high)'
                )
            )
            
            # Signal confidence
            if 'confidence' in signal:
                prometheus_metrics.append(
                    self.format_prometheus_metric(
                        'paranoid_latest_signal_confidence',
                        signal['confidence'],
                        {'signal_type': signal.get('signal_type', 'unknown')},
                        'Latest signal confidence score'
                    )
                )
            
            # Target scores
            for target, score in signal.get('scores', {}).items():
                prometheus_metrics.append(
                    self.format_prometheus_metric(
                        'paranoid_signal_target_score',
                        score,
                        {'target': target},
                        'Signal score for specific target'
                    )
                )
        
        # ===== HUMINT METRICS =====
        if 'humint' in metrics_data:
            humint = metrics_data['humint']
            
            # Network and hypothesis counts
            if 'summary' in humint:
                summary = humint['summary']
                
                prometheus_metrics.append(
                    self.format_prometheus_metric(
                        'paranoid_humint_networks_detected',
                        summary.get('active_networks', 0),
                        {},
                        'Number of active actor networks detected'
                    )
                )
                
                prometheus_metrics.append(
                    self.format_prometheus_metric(
                        'paranoid_humint_hypotheses_generated',
                        summary.get('hypotheses_generated', 0),
                        {},
                        'Number of motive hypotheses generated'
                    )
                )
                
                prometheus_metrics.append(
                    self.format_prometheus_metric(
                        'paranoid_humint_highest_confidence',
                        summary.get('highest_confidence', 0),
                        {},
                        'Highest confidence score among hypotheses'
                    )
                )
        
        # ===== DATA PIPELINE METRICS =====
        if 'metadata' in metrics_data:
            meta = metrics_data['metadata']
            
            # Data source metrics
            if 'data_sources' in meta:
                data_sources = meta['data_sources']
                
                prometheus_metrics.append(
                    self.format_prometheus_metric(
                        'paranoid_gdelt_range_days',
                        data_sources.get('gdelt_range_days', 0),
                        {},
                        'Number of days in GDELT data range'
                    )
                )
                
                prometheus_metrics.append(
                    self.format_prometheus_metric(
                        'paranoid_gdelt_min_events',
                        data_sources.get('gdelt_min_events', 0),
                        {},
                        'Minimum GDELT events threshold'
                    )
                )
            
            # Deployment timestamp
            if 'deployment' in meta:
                deployment = meta['deployment']
                try:
                    # Handle various timestamp formats
                    ts_str = deployment['timestamp']
                    if 'Z' in ts_str:
                        ts_str = ts_str.replace('Z', '+00:00')
                    if '+00-00' in ts_str:
                        ts_str = ts_str.replace('+00-00', '+00:00')
                    deployment_ts = datetime.fromisoformat(ts_str)
                    deployment_unix = int(deployment_ts.timestamp())
                except (ValueError, KeyError):
                    # Fallback to current timestamp
                    deployment_unix = int(time.time())
                
                prometheus_metrics.append(
                    self.format_prometheus_metric(
                        'paranoid_deployment_timestamp',
                        deployment_unix,
                        {'version': deployment.get('version', 'latest')},
                        'Unix timestamp of latest deployment'
                    )
                )
        
        # ===== SYSTEM HEALTH =====
        prometheus_metrics.append(
            self.format_prometheus_metric(
                'paranoid_pipeline_last_run_timestamp',
                timestamp // 1000,  # Convert to seconds
                {},
                'Unix timestamp of last pipeline run'
            )
        )
        
        prometheus_metrics.append(
            self.format_prometheus_metric(
                'paranoid_pipeline_status',
                1,  # 1 = successful run
                {},
                'Pipeline execution status (1=success, 0=failure)'
            )
        )
        
        return '\n\n'.join(prometheus_metrics) + '\n'
    
    def push_to_gateway(self, metrics_text: str) -> bool:
        """Push metrics to Prometheus Pushgateway."""
        try:
            url = f"{self.pushgateway_url}/metrics/job/{self.job_name}/instance/{self.instance}"
            
            headers = {
                'Content-Type': 'text/plain; version=0.0.4'
            }
            
            response = requests.post(url, data=metrics_text, headers=headers, timeout=10)
            response.raise_for_status()
            
            print(f"✅ Metrics pushed to Prometheus: {url}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to push metrics to Prometheus: {e}")
            return False
    
    def save_metrics_file(self, metrics_text: str, output_path: str = 'artifacts/prometheus_metrics.txt') -> bool:
        """Save metrics to file for file-based collection."""
        try:
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            
            with open(output_path, 'w') as f:
                f.write(metrics_text)
            
            print(f"📁 Metrics saved to file: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save metrics file: {e}")
            return False
    
    def export_metrics(self, artifacts_dir: str = 'artifacts', output_file: str = None, push_gateway: bool = True) -> bool:
        """Export all paranoid metrics to Prometheus."""
        print("📊 Exporting paranoid metrics to Prometheus...")
        
        # Load metrics data
        metrics_data = self.load_metrics(artifacts_dir)
        
        if not metrics_data:
            print("⚠️ No metrics data found to export")
            return False
        
        # Convert to Prometheus format
        prometheus_text = self.export_to_prometheus_format(metrics_data)
        
        success = True
        
        # Save to file if requested
        if output_file:
            success &= self.save_metrics_file(prometheus_text, output_file)
        else:
            # Default file save
            success &= self.save_metrics_file(prometheus_text)
        
        # Push to gateway if enabled
        if push_gateway and self.pushgateway_url:
            success &= self.push_to_gateway(prometheus_text)
        
        # Print sample metrics
        lines = prometheus_text.split('\n')
        sample_lines = [line for line in lines if line and not line.startswith('#')][:5]
        print("📊 Sample exported metrics:")
        for line in sample_lines:
            print(f"   {line}")
        
        print(f"📈 Total metrics exported: {len([l for l in lines if l and not l.startswith('#')])}")
        
        return success


def main():
    parser = argparse.ArgumentParser(description="Export Paranoid Metrics to Prometheus")
    parser.add_argument('--artifacts_dir', default='artifacts', help='Artifacts directory')
    parser.add_argument('--pushgateway_url', help='Prometheus Pushgateway URL')
    parser.add_argument('--job_name', default='paranoid-model', help='Prometheus job name')
    parser.add_argument('--output_file', help='Output file for metrics (optional)')
    parser.add_argument('--no-push', action='store_true', help='Skip pushing to gateway')
    
    args = parser.parse_args()
    
    exporter = PrometheusExporter(
        pushgateway_url=args.pushgateway_url,
        job_name=args.job_name
    )
    
    success = exporter.export_metrics(
        artifacts_dir=args.artifacts_dir,
        output_file=args.output_file,
        push_gateway=not args.no_push
    )
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
