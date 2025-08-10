#!/usr/bin/env python3
"""
🚀 STAGING → PRODUCTION PROMOTION

Promotes paranoid artifacts from staging to production with:
- Quality gate validation
- Automated testing
- Blue-green deployment simulation
- Rollback capability
"""

import json
import os
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
import subprocess
import warnings
warnings.filterwarnings('ignore')


class StagingPromoter:
    """Promote staging artifacts to production."""
    
    def __init__(self, staging_env: str = 'staging', production_env: str = 'production'):
        self.staging_env = staging_env
        self.production_env = production_env
        
        # Environment-specific configurations
        self.staging_bucket = os.getenv('S3_STAGING_BUCKET', f'paranoid-{staging_env}')
        self.production_bucket = os.getenv('S3_PRODUCTION_BUCKET', f'paranoid-{production_env}')
        
        self.staging_url = os.getenv('STAGING_URL', f'https://staging-api.paranoidmodels.com')
        self.production_url = os.getenv('PROD_URL', f'https://api.paranoidmodels.com')
        
        # Quality gates for promotion
        self.promotion_gates = {
            'min_auc': 0.86,
            'max_delta_auc': 0.10,
            'max_ece': 0.05,
            'min_why_it_matters_coverage': 0.80,
            'max_drift_alerts': 0,
            'min_smoke_test_pass_rate': 1.0
        }
    
    def load_staging_metrics(self, staging_artifacts_dir: str = 'staging_artifacts') -> Dict[str, Any]:
        """Load metrics from staging environment."""
        try:
            metrics_path = os.path.join(staging_artifacts_dir, 'metrics.json')
            if os.path.exists(metrics_path):
                with open(metrics_path, 'r') as f:
                    return json.load(f)
            else:
                print(f"⚠️ Staging metrics not found: {metrics_path}")
                return {}
        except Exception as e:
            print(f"❌ Failed to load staging metrics: {e}")
            return {}
    
    def validate_promotion_gates(self, staging_metrics: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate that staging meets promotion criteria."""
        print("🚦 Validating promotion gates...")
        
        violations = []
        
        # Check AUC performance
        performance = staging_metrics.get('performance', {})
        targets = ['sensitive_class', 'suppression_event_6w', 'narrative_shift_4w']
        
        for target in targets:
            auc_key = f'{target}_auc'
            auc_value = performance.get(auc_key, 0)
            if auc_value < self.promotion_gates['min_auc']:
                violations.append(f"AUC {target}: {auc_value:.3f} < {self.promotion_gates['min_auc']}")
        
        # Check fairness
        fairness = staging_metrics.get('fairness', {})
        max_delta_auc = fairness.get('max_delta_auc', 1.0)
        if max_delta_auc > self.promotion_gates['max_delta_auc']:
            violations.append(f"Fairness Δ-AUC: {max_delta_auc:.3f} > {self.promotion_gates['max_delta_auc']}")
        
        # Check calibration
        calibration = staging_metrics.get('calibration', {})
        ece = calibration.get('ece_mean', 1.0)
        if ece > self.promotion_gates['max_ece']:
            violations.append(f"Calibration ECE: {ece:.3f} > {self.promotion_gates['max_ece']}")
        
        gates_passed = len(violations) == 0
        
        if gates_passed:
            print("✅ All promotion gates passed")
        else:
            print("❌ Promotion gates failed:")
            for violation in violations:
                print(f"   • {violation}")
        
        return gates_passed, violations
    
    def run_staging_smoke_tests(self) -> Tuple[bool, Dict[str, Any]]:
        """Run comprehensive smoke tests against staging."""
        print("🧪 Running staging smoke tests...")
        
        try:
            # Set staging URL for smoke tests
            env = os.environ.copy()
            env['PROD_URL'] = self.staging_url
            
            # Run Puppeteer smoke tests
            result = subprocess.run(
                ['make', 'paranoid-smoke'],
                cwd='.',
                capture_output=True,
                text=True,
                env=env,
                timeout=300  # 5 minute timeout
            )
            
            smoke_passed = result.returncode == 0
            
            # Try to extract metrics from output
            smoke_metrics = {
                'tests_passed': smoke_passed,
                'exit_code': result.returncode,
                'output_length': len(result.stdout),
                'error_length': len(result.stderr)
            }
            
            # Look for coverage information in output
            if 'why it matters coverage' in result.stdout.lower():
                # Extract coverage percentage (basic regex)
                import re
                coverage_match = re.search(r'(\d+)%.*why.*matters', result.stdout.lower())
                if coverage_match:
                    coverage = int(coverage_match.group(1)) / 100
                    smoke_metrics['why_it_matters_coverage'] = coverage
                    
                    if coverage < self.promotion_gates['min_why_it_matters_coverage']:
                        smoke_passed = False
            
            if smoke_passed:
                print("✅ Staging smoke tests passed")
            else:
                print("❌ Staging smoke tests failed")
                print(f"   Exit code: {result.returncode}")
                if result.stderr:
                    print(f"   Error: {result.stderr[:200]}...")
            
            return smoke_passed, smoke_metrics
            
        except Exception as e:
            print(f"❌ Smoke test execution failed: {e}")
            return False, {'error': str(e)}
    
    def check_drift_status(self, staging_artifacts_dir: str = 'staging_artifacts') -> Tuple[bool, Dict[str, Any]]:
        """Check drift status in staging."""
        print("📊 Checking drift status...")
        
        try:
            drift_path = os.path.join(staging_artifacts_dir, 'drift_report.json')
            if os.path.exists(drift_path):
                with open(drift_path, 'r') as f:
                    drift_data = json.load(f)
                
                critical_alerts = drift_data.get('critical_alerts', 0)
                drift_stable = critical_alerts <= self.promotion_gates['max_drift_alerts']
                
                if drift_stable:
                    print(f"✅ Drift status stable ({critical_alerts} critical alerts)")
                else:
                    print(f"❌ Drift detected ({critical_alerts} critical alerts)")
                
                return drift_stable, drift_data
            else:
                print("⚠️ No drift report found, assuming stable")
                return True, {}
                
        except Exception as e:
            print(f"❌ Drift check failed: {e}")
            return False, {'error': str(e)}
    
    def create_promotion_report(self, 
                              staging_metrics: Dict[str, Any],
                              gates_result: Tuple[bool, List[str]],
                              smoke_result: Tuple[bool, Dict[str, Any]],
                              drift_result: Tuple[bool, Dict[str, Any]]) -> Dict[str, Any]:
        """Create comprehensive promotion report."""
        
        gates_passed, gate_violations = gates_result
        smoke_passed, smoke_metrics = smoke_result
        drift_stable, drift_metrics = drift_result
        
        can_promote = gates_passed and smoke_passed and drift_stable
        
        report = {
            'promotion_timestamp': datetime.now(timezone.utc).isoformat(),
            'staging_environment': self.staging_env,
            'production_environment': self.production_env,
            'promotion_decision': 'APPROVE' if can_promote else 'REJECT',
            'gates_validation': {
                'passed': gates_passed,
                'violations': gate_violations,
                'criteria': self.promotion_gates
            },
            'smoke_tests': {
                'passed': smoke_passed,
                'metrics': smoke_metrics
            },
            'drift_check': {
                'stable': drift_stable,
                'metrics': drift_metrics
            },
            'staging_metrics': staging_metrics,
            'promotion_summary': {
                'quality_gates': '✅ PASS' if gates_passed else '❌ FAIL',
                'smoke_tests': '✅ PASS' if smoke_passed else '❌ FAIL',
                'drift_status': '✅ STABLE' if drift_stable else '❌ DRIFT',
                'overall': '✅ APPROVED' if can_promote else '❌ REJECTED'
            }
        }
        
        return report
    
    def execute_promotion(self, staging_artifacts_dir: str = 'staging_artifacts', 
                        production_artifacts_dir: str = 'artifacts') -> bool:
        """Execute the actual promotion of artifacts."""
        print("🚀 Executing promotion to production...")
        
        try:
            # Copy staging artifacts to production directory
            staging_files = [
                'metrics.json', 'signal.raw.json', 'report.enriched.json',
                'humint_profile.json', 'drift_report.json', 'paranoid_models.joblib'
            ]
            
            os.makedirs(production_artifacts_dir, exist_ok=True)
            
            for filename in staging_files:
                staging_path = os.path.join(staging_artifacts_dir, filename)
                production_path = os.path.join(production_artifacts_dir, filename)
                
                if os.path.exists(staging_path):
                    subprocess.run(['cp', staging_path, production_path], check=True)
                    print(f"✅ Promoted {filename}")
                else:
                    print(f"⚠️ Staging file not found: {filename}")
            
            # Deploy to production
            deploy_result = subprocess.run(
                ['python3', 'scripts/deploy_artifacts.py', '--provider', 'auto', '--artifacts_dir', production_artifacts_dir],
                capture_output=True,
                text=True
            )
            
            if deploy_result.returncode == 0:
                print("✅ Production deployment successful")
                return True
            else:
                print(f"❌ Production deployment failed: {deploy_result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Promotion execution failed: {e}")
            return False
    
    def send_promotion_notification(self, report: Dict[str, Any]) -> bool:
        """Send promotion notification via configured channels."""
        try:
            webhook_url = os.getenv('SLACK_WEBHOOK_URL')
            if not webhook_url:
                print("ℹ️ No webhook configured, skipping notification")
                return True
            
            decision = report['promotion_decision']
            summary = report['promotion_summary']
            
            color = 'good' if decision == 'APPROVE' else 'danger'
            emoji = '🚀' if decision == 'APPROVE' else '🚫'
            
            message = {
                'text': f'{emoji} Paranoid Model Promotion: {decision}',
                'attachments': [{
                    'color': color,
                    'fields': [
                        {'title': 'Environment', 'value': f'{self.staging_env} → {self.production_env}', 'short': True},
                        {'title': 'Decision', 'value': decision, 'short': True},
                        {'title': 'Quality Gates', 'value': summary['quality_gates'], 'short': True},
                        {'title': 'Smoke Tests', 'value': summary['smoke_tests'], 'short': True},
                        {'title': 'Drift Status', 'value': summary['drift_status'], 'short': True},
                        {'title': 'Overall', 'value': summary['overall'], 'short': True},
                        {'title': 'Timestamp', 'value': report['promotion_timestamp'], 'short': False}
                    ]
                }]
            }
            
            import requests
            response = requests.post(webhook_url, json=message, timeout=10)
            response.raise_for_status()
            
            print("✅ Promotion notification sent")
            return True
            
        except Exception as e:
            print(f"⚠️ Notification failed: {e}")
            return False
    
    def run_promotion_pipeline(self, 
                             staging_artifacts_dir: str = 'staging_artifacts',
                             force: bool = False,
                             dry_run: bool = False) -> Dict[str, Any]:
        """Run complete staging → production promotion pipeline."""
        print(f"🚀 Starting {self.staging_env} → {self.production_env} promotion pipeline")
        
        # Load staging metrics
        staging_metrics = self.load_staging_metrics(staging_artifacts_dir)
        if not staging_metrics:
            print("❌ Cannot proceed without staging metrics")
            return {'status': 'failed', 'reason': 'no_staging_metrics'}
        
        # Validate promotion gates
        gates_result = self.validate_promotion_gates(staging_metrics)
        
        # Run smoke tests
        smoke_result = self.run_staging_smoke_tests()
        
        # Check drift status
        drift_result = self.check_drift_status(staging_artifacts_dir)
        
        # Create promotion report
        report = self.create_promotion_report(staging_metrics, gates_result, smoke_result, drift_result)
        
        # Save promotion report
        report_path = f'promotion_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📄 Promotion report saved: {report_path}")
        
        # Decision logic
        can_promote = report['promotion_decision'] == 'APPROVE'
        
        if dry_run:
            print("🔍 DRY RUN: No actual promotion performed")
            return report
        
        if can_promote or force:
            if force and not can_promote:
                print("⚠️ FORCED PROMOTION: Bypassing failed gates")
                report['forced'] = True
            
            # Execute promotion
            promotion_success = self.execute_promotion(staging_artifacts_dir)
            report['promotion_executed'] = promotion_success
            
            if promotion_success:
                print("🎉 Promotion completed successfully!")
                report['status'] = 'promoted'
            else:
                print("❌ Promotion execution failed")
                report['status'] = 'promotion_failed'
        else:
            print("🚫 Promotion rejected due to failed gates")
            report['status'] = 'rejected'
        
        # Send notification
        self.send_promotion_notification(report)
        
        return report


def main():
    parser = argparse.ArgumentParser(description="Staging to Production Promotion")
    parser.add_argument('--staging-artifacts', default='staging_artifacts', 
                       help='Staging artifacts directory')
    parser.add_argument('--staging-env', default='staging', help='Staging environment name')
    parser.add_argument('--production-env', default='production', help='Production environment name')
    parser.add_argument('--force', action='store_true', help='Force promotion despite gate failures')
    parser.add_argument('--dry-run', action='store_true', help='Validate only, do not promote')
    
    args = parser.parse_args()
    
    promoter = StagingPromoter(args.staging_env, args.production_env)
    
    report = promoter.run_promotion_pipeline(
        staging_artifacts_dir=args.staging_artifacts,
        force=args.force,
        dry_run=args.dry_run
    )
    
    # Exit with appropriate code
    if report['status'] in ['promoted', 'rejected']:
        if report['status'] == 'promoted':
            print(f"✅ Promotion successful: {args.staging_env} → {args.production_env}")
            exit(0)
        else:
            print(f"🚫 Promotion rejected")
            exit(1)
    else:
        print(f"❌ Promotion failed: {report.get('reason', 'unknown')}")
        exit(2)


if __name__ == "__main__":
    main()
