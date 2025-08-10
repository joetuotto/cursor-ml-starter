#!/usr/bin/env python3
"""
🚨 ALERT TESTING SCRIPT - Fire Test Alerts

Tests Prometheus + Grafana alert configurations by pushing
test metrics and validating alert firing and recovery.
"""

import os
import time
import requests
import argparse
from typing import Dict, List, Tuple
import json
from datetime import datetime


class AlertTester:
    """Test alert configurations by firing synthetic alerts."""
    
    def __init__(self, pushgateway_url: str = None, slack_webhook: str = None):
        self.pushgateway_url = pushgateway_url or os.getenv('PROMETHEUS_PUSHGATEWAY_URL', 'http://localhost:9091')
        self.slack_webhook = slack_webhook or os.getenv('SLACK_WEBHOOK_URL')
        self.job_name = 'paranoid_test'
        self.instance = 'test-runner'
        
    def push_metrics(self, metrics: Dict[str, float], labels: Dict[str, str] = None) -> bool:
        """Push test metrics to Prometheus Pushgateway."""
        labels = labels or {}
        default_labels = {
            'job': self.job_name,
            'instance': self.instance,
            'environment': 'test'
        }
        labels.update(default_labels)
        
        # Format metrics for Prometheus
        prometheus_data = []
        for metric_name, value in metrics.items():
            label_str = ','.join([f'{k}="{v}"' for k, v in labels.items()])
            prometheus_data.append(f'{metric_name}{{{label_str}}} {value}')
        
        metrics_text = '\n'.join(prometheus_data) + '\n'
        
        try:
            url = f"{self.pushgateway_url}/metrics/job/{self.job_name}/instance/{self.instance}"
            response = requests.post(
                url,
                data=metrics_text,
                headers={'Content-Type': 'text/plain; version=0.0.4'},
                timeout=10
            )
            response.raise_for_status()
            print(f"✅ Pushed metrics to {url}")
            return True
        except Exception as e:
            print(f"❌ Failed to push metrics: {e}")
            return False
    
    def clear_test_metrics(self) -> bool:
        """Clear test metrics from Pushgateway."""
        try:
            url = f"{self.pushgateway_url}/metrics/job/{self.job_name}/instance/{self.instance}"
            response = requests.delete(url, timeout=10)
            response.raise_for_status()
            print(f"🧹 Cleared test metrics from {url}")
            return True
        except Exception as e:
            print(f"❌ Failed to clear metrics: {e}")
            return False
    
    def send_slack_notification(self, message: str, emoji: str = "🧪") -> bool:
        """Send test notification to Slack."""
        if not self.slack_webhook:
            print("⚠️ No Slack webhook configured")
            return True
        
        try:
            payload = {
                "text": f"{emoji} Alert Test Notification",
                "username": "Alert Tester",
                "attachments": [{
                    "color": "good",
                    "fields": [{
                        "title": "Test Message",
                        "value": message,
                        "short": False
                    }, {
                        "title": "Timestamp",
                        "value": datetime.now().isoformat(),
                        "short": True
                    }]
                }]
            }
            
            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            response.raise_for_status()
            print("✅ Slack notification sent")
            return True
        except Exception as e:
            print(f"❌ Slack notification failed: {e}")
            return False
    
    def test_auc_drop_alert(self, auc_value: float = 0.75, duration: int = 60) -> bool:
        """Test AUC drop critical alert."""
        print(f"\n🚨 Testing AUC Drop Alert (AUC: {auc_value})")
        
        # Push bad metrics
        bad_metrics = {
            'paranoid_auc': auc_value,
            'paranoid_quality_gates_passed': 0
        }
        
        labels = {'target': 'sensitive_class'}
        
        if not self.push_metrics(bad_metrics, labels):
            return False
        
        self.send_slack_notification(
            f"🧪 Testing AUC drop alert with AUC={auc_value}. "
            f"Alert should fire within 5 minutes if configured correctly."
        )
        
        print(f"⏰ Waiting {duration}s for alert to fire...")
        time.sleep(duration)
        
        # Restore good metrics
        good_metrics = {
            'paranoid_auc': 0.96,
            'paranoid_quality_gates_passed': 1
        }
        
        if not self.push_metrics(good_metrics, labels):
            return False
        
        self.send_slack_notification(
            f"✅ AUC restored to 0.96. Alert should resolve."
        )
        
        return True
    
    def test_bias_violation_alert(self, delta_auc: float = 0.15, duration: int = 60) -> bool:
        """Test bias violation alert."""
        print(f"\n⚖️ Testing Bias Violation Alert (Δ-AUC: {delta_auc})")
        
        # Push biased metrics
        bias_metrics = {
            'paranoid_fairness_max_delta_auc': delta_auc,
            'paranoid_group_auc': 0.90  # One group
        }
        
        if not self.push_metrics(bias_metrics):
            return False
        
        # Push another group with lower AUC
        bias_metrics_low = {
            'paranoid_group_auc': 0.75  # Another group
        }
        labels = {'group': 'demographic_b'}
        
        if not self.push_metrics(bias_metrics_low, labels):
            return False
        
        self.send_slack_notification(
            f"🧪 Testing bias violation alert with Δ-AUC={delta_auc}. "
            f"Critical ethics alert should fire."
        )
        
        print(f"⏰ Waiting {duration}s for bias alert to fire...")
        time.sleep(duration)
        
        # Restore fair metrics
        fair_metrics = {
            'paranoid_fairness_max_delta_auc': 0.05,
            'paranoid_group_auc': 0.87
        }
        
        if not self.push_metrics(fair_metrics):
            return False
        
        self.send_slack_notification(
            f"✅ Bias resolved: Δ-AUC now 0.05. Alert should resolve."
        )
        
        return True
    
    def test_quality_gates_alert(self, duration: int = 60) -> bool:
        """Test quality gates failure alert."""
        print(f"\n🚦 Testing Quality Gates Failure Alert")
        
        # Push failed gates
        failed_metrics = {
            'paranoid_quality_gates_passed': 0,
            'paranoid_quality_gate_auc_minimum': 0,
            'paranoid_quality_gate_fairness_check': 0,
            'paranoid_quality_gate_calibration_check': 0
        }
        
        if not self.push_metrics(failed_metrics):
            return False
        
        self.send_slack_notification(
            f"🧪 Testing quality gates failure. All gates marked as failed."
        )
        
        print(f"⏰ Waiting {duration}s for quality gates alert...")
        time.sleep(duration)
        
        # Restore passing gates
        passed_metrics = {
            'paranoid_quality_gates_passed': 1,
            'paranoid_quality_gate_auc_minimum': 1,
            'paranoid_quality_gate_fairness_check': 1,
            'paranoid_quality_gate_calibration_check': 1
        }
        
        if not self.push_metrics(passed_metrics):
            return False
        
        self.send_slack_notification(
            f"✅ Quality gates restored. All gates now passing."
        )
        
        return True
    
    def test_concept_drift_alert(self, critical_alerts: int = 3, duration: int = 60) -> bool:
        """Test concept drift alert."""
        print(f"\n🌊 Testing Concept Drift Alert ({critical_alerts} critical alerts)")
        
        # Push drift metrics
        drift_metrics = {
            'paranoid_drift_alerts_critical': critical_alerts,
            'paranoid_drift_alerts_total': critical_alerts + 2,
            'paranoid_drift_status_stable': 0
        }
        
        if not self.push_metrics(drift_metrics):
            return False
        
        self.send_slack_notification(
            f"🧪 Testing concept drift alert with {critical_alerts} critical alerts."
        )
        
        print(f"⏰ Waiting {duration}s for drift alert...")
        time.sleep(duration)
        
        # Restore stable metrics
        stable_metrics = {
            'paranoid_drift_alerts_critical': 0,
            'paranoid_drift_alerts_total': 0,
            'paranoid_drift_status_stable': 1
        }
        
        if not self.push_metrics(stable_metrics):
            return False
        
        self.send_slack_notification(
            f"✅ Concept drift resolved. System now stable."
        )
        
        return True
    
    def test_calibration_drift_alert(self, ece_value: float = 0.08, duration: int = 60) -> bool:
        """Test calibration drift alert."""
        print(f"\n📊 Testing Calibration Drift Alert (ECE: {ece_value})")
        
        # Push poor calibration
        cal_metrics = {
            'paranoid_calibration_ece': ece_value,
            'paranoid_brier_score': 0.28
        }
        
        if not self.push_metrics(cal_metrics):
            return False
        
        self.send_slack_notification(
            f"🧪 Testing calibration drift with ECE={ece_value}."
        )
        
        print(f"⏰ Waiting {duration}s for calibration alert...")
        time.sleep(duration)
        
        # Restore good calibration
        good_cal_metrics = {
            'paranoid_calibration_ece': 0.019,
            'paranoid_brier_score': 0.142
        }
        
        if not self.push_metrics(good_cal_metrics):
            return False
        
        self.send_slack_notification(
            f"✅ Calibration restored: ECE now 0.019."
        )
        
        return True
    
    def run_full_alert_test_suite(self, wait_time: int = 30) -> Dict[str, bool]:
        """Run complete alert test suite."""
        print("🚨 PARANOID ALERT TEST SUITE")
        print("=" * 50)
        
        self.send_slack_notification(
            "🧪 Starting comprehensive alert test suite. "
            "Expect multiple test alerts over the next few minutes."
        )
        
        results = {}
        
        # Test each alert type
        test_functions = [
            ('AUC Drop Critical', lambda: self.test_auc_drop_alert(duration=wait_time)),
            ('Bias Violation', lambda: self.test_bias_violation_alert(duration=wait_time)),
            ('Quality Gates Failure', lambda: self.test_quality_gates_alert(duration=wait_time)),
            ('Concept Drift', lambda: self.test_concept_drift_alert(duration=wait_time)),
            ('Calibration Drift', lambda: self.test_calibration_drift_alert(duration=wait_time))
        ]
        
        for test_name, test_func in test_functions:
            try:
                print(f"\n{'='*20} {test_name} {'='*20}")
                results[test_name] = test_func()
                
                if results[test_name]:
                    print(f"✅ {test_name} test completed")
                else:
                    print(f"❌ {test_name} test failed")
                
                # Wait between tests
                if test_name != test_functions[-1][0]:  # Not last test
                    print(f"⏱️ Waiting {wait_time//2}s before next test...")
                    time.sleep(wait_time // 2)
                    
            except Exception as e:
                print(f"💥 {test_name} test error: {e}")
                results[test_name] = False
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 ALERT TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(results.values())
        total = len(results)
        
        for test_name, passed_test in results.items():
            status = "✅ PASSED" if passed_test else "❌ FAILED"
            print(f"{test_name:25} {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        # Clean up
        print("\n🧹 Cleaning up test metrics...")
        self.clear_test_metrics()
        
        self.send_slack_notification(
            f"🧪 Alert test suite completed: {passed}/{total} tests passed. "
            f"Check Prometheus and Grafana for alert firing history."
        )
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Test Paranoid Alert Configurations")
    parser.add_argument('--pushgateway_url', help='Prometheus Pushgateway URL')
    parser.add_argument('--slack_webhook', help='Slack webhook URL for notifications')
    parser.add_argument('--test', choices=['auc', 'bias', 'gates', 'drift', 'calibration', 'all'],
                       default='all', help='Specific test to run')
    parser.add_argument('--wait_time', type=int, default=30, 
                       help='Wait time between alert fire and resolve (seconds)')
    parser.add_argument('--auc_value', type=float, default=0.75, 
                       help='AUC value for drop test')
    parser.add_argument('--delta_auc', type=float, default=0.15,
                       help='Delta-AUC value for bias test')
    
    args = parser.parse_args()
    
    tester = AlertTester(args.pushgateway_url, args.slack_webhook)
    
    if args.test == 'all':
        results = tester.run_full_alert_test_suite(args.wait_time)
        success = all(results.values())
    elif args.test == 'auc':
        success = tester.test_auc_drop_alert(args.auc_value, args.wait_time)
    elif args.test == 'bias':
        success = tester.test_bias_violation_alert(args.delta_auc, args.wait_time)
    elif args.test == 'gates':
        success = tester.test_quality_gates_alert(args.wait_time)
    elif args.test == 'drift':
        success = tester.test_concept_drift_alert(duration=args.wait_time)
    elif args.test == 'calibration':
        success = tester.test_calibration_drift_alert(duration=args.wait_time)
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
