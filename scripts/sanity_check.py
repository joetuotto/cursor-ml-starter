#!/usr/bin/env python3
"""
✅ PARANOID V5 - SANITY CHECK SCRIPT

Quick 5-minute validation before production deployment.
Checks environment, connectivity, and basic functionality.
"""

import os
import json
import subprocess
import time
from typing import Dict, List, Tuple, Any
import requests
import warnings
warnings.filterwarnings('ignore')


class SanityChecker:
    """Quick pre-deployment sanity checks."""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = 0
        self.start_time = time.time()
        
    def check(self, name: str, check_func) -> bool:
        """Run a single check with error handling."""
        print(f"🔍 {name}...", end=" ")
        try:
            result, message = check_func()
            if result:
                print(f"✅ {message}")
                self.checks_passed += 1
                return True
            else:
                print(f"❌ {message}")
                self.checks_failed += 1
                return False
        except Exception as e:
            print(f"💥 ERROR: {e}")
            self.checks_failed += 1
            return False
    
    def warn(self, message: str):
        """Log a warning."""
        print(f"⚠️ WARNING: {message}")
        self.warnings += 1
    
    def check_environment_variables(self) -> Tuple[bool, str]:
        """Check required environment variables."""
        required_vars = {
            'CURSOR_API_KEY': 'Cursor API access',
            'S3_BUCKET': 'S3 bucket for artifacts',
            'AWS_REGION': 'AWS region',
        }
        
        optional_vars = {
            'AWS_ACCESS_KEY_ID': 'AWS credentials',
            'PROMETHEUS_PUSHGATEWAY_URL': 'Prometheus monitoring',
            'SLACK_WEBHOOK_URL': 'Slack notifications',
        }
        
        missing_required = []
        missing_optional = []
        
        for var, desc in required_vars.items():
            if not os.getenv(var):
                missing_required.append(f"{var} ({desc})")
        
        for var, desc in optional_vars.items():
            if not os.getenv(var):
                missing_optional.append(f"{var} ({desc})")
        
        if missing_required:
            return False, f"Missing required: {', '.join(missing_required)}"
        
        if missing_optional:
            self.warn(f"Missing optional: {', '.join(missing_optional)}")
        
        return True, f"Environment OK ({len(required_vars)} required vars set)"
    
    def check_aws_connectivity(self) -> Tuple[bool, str]:
        """Check AWS S3 connectivity."""
        bucket = os.getenv('S3_BUCKET')
        if not bucket:
            return False, "S3_BUCKET not set"
        
        try:
            # Try AWS CLI if available
            result = subprocess.run(
                ['aws', 's3', 'ls', f's3://{bucket}/'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, f"S3 bucket {bucket} accessible"
            else:
                # Try with boto3
                try:
                    import boto3
                    s3 = boto3.client('s3')
                    s3.head_bucket(Bucket=bucket)
                    return True, f"S3 bucket {bucket} accessible (boto3)"
                except ImportError:
                    return False, "AWS CLI failed and boto3 not available"
                except Exception as e:
                    return False, f"S3 access failed: {str(e)[:50]}"
        except subprocess.TimeoutExpired:
            return False, "AWS CLI timeout"
        except FileNotFoundError:
            return False, "AWS CLI not found"
    
    def check_prometheus_connectivity(self) -> Tuple[bool, str]:
        """Check Prometheus Pushgateway connectivity."""
        gateway_url = os.getenv('PROMETHEUS_PUSHGATEWAY_URL')
        if not gateway_url:
            self.warn("PROMETHEUS_PUSHGATEWAY_URL not set - monitoring disabled")
            return True, "Skipped (not configured)"
        
        try:
            response = requests.get(f"{gateway_url}/metrics", timeout=5)
            if response.status_code == 200:
                return True, f"Prometheus Gateway accessible"
            else:
                return False, f"Gateway returned {response.status_code}"
        except Exception as e:
            return False, f"Connection failed: {str(e)[:50]}"
    
    def check_slack_webhook(self) -> Tuple[bool, str]:
        """Check Slack webhook connectivity."""
        webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        if not webhook_url:
            self.warn("SLACK_WEBHOOK_URL not set - alerts disabled")
            return True, "Skipped (not configured)"
        
        try:
            test_payload = {
                "text": "🧪 Paranoid V5 sanity check - please ignore",
                "username": "SanityBot"
            }
            response = requests.post(webhook_url, json=test_payload, timeout=5)
            if response.status_code == 200:
                return True, "Slack webhook accessible"
            else:
                return False, f"Webhook returned {response.status_code}"
        except Exception as e:
            return False, f"Connection failed: {str(e)[:50]}"
    
    def check_required_files(self) -> Tuple[bool, str]:
        """Check required files exist."""
        required_files = [
            'scripts/train_paranoid.py',
            'scripts/generate_paranoid_signal.py',
            'scripts/prometheus_exporter.py',
            'scripts/deploy_artifacts.py',
            'monitoring/grafana-paranoid-dashboard.json',
            'monitoring/prometheus-alert-rules.yaml'
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            return False, f"Missing files: {', '.join(missing_files[:3])}{'...' if len(missing_files) > 3 else ''}"
        
        return True, f"All {len(required_files)} required files present"
    
    def check_dependencies(self) -> Tuple[bool, str]:
        """Check Python dependencies."""
        required_packages = [
            'pandas', 'numpy', 'scikit-learn', 'joblib', 'requests'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            return False, f"Missing packages: {', '.join(missing_packages)}"
        
        return True, f"All {len(required_packages)} packages available"
    
    def check_playwright_setup(self) -> Tuple[bool, str]:
        """Check Playwright browser setup."""
        try:
            # Check if we're in web directory structure
            if os.path.exists('web/package.json'):
                with open('web/package.json', 'r') as f:
                    package_data = json.load(f)
                
                if 'puppeteer' in package_data.get('dependencies', {}):
                    return True, "Puppeteer available for testing"
                elif 'playwright' in package_data.get('dependencies', {}):
                    return True, "Playwright available for testing"
                else:
                    return False, "No browser automation library found"
            else:
                self.warn("web/package.json not found - UI testing disabled")
                return True, "Skipped (no web directory)"
        except Exception as e:
            return False, f"Package check failed: {e}"
    
    def check_makefile_targets(self) -> Tuple[bool, str]:
        """Check Makefile targets exist."""
        required_targets = [
            'paranoid-ultimate', 'paranoid-complete', 'paranoid-deploy',
            'paranoid-prometheus', 'setup-s3-lifecycle'
        ]
        
        if not os.path.exists('Makefile'):
            return False, "Makefile not found"
        
        try:
            with open('Makefile', 'r') as f:
                makefile_content = f.read()
            
            missing_targets = []
            for target in required_targets:
                if f"{target}:" not in makefile_content:
                    missing_targets.append(target)
            
            if missing_targets:
                return False, f"Missing targets: {', '.join(missing_targets[:2])}{'...' if len(missing_targets) > 2 else ''}"
            
            return True, f"All {len(required_targets)} Makefile targets present"
        except Exception as e:
            return False, f"Makefile read failed: {e}"
    
    def check_artifacts_directory(self) -> Tuple[bool, str]:
        """Check artifacts directory setup."""
        if not os.path.exists('artifacts'):
            os.makedirs('artifacts')
            return True, "Created artifacts directory"
        
        # Check for existing artifacts
        artifact_files = os.listdir('artifacts')
        if artifact_files:
            return True, f"Artifacts directory exists ({len(artifact_files)} files)"
        else:
            return True, "Artifacts directory ready (empty)"
    
    def check_permissions(self) -> Tuple[bool, str]:
        """Check file permissions for scripts."""
        script_files = [
            'scripts/train_paranoid.py',
            'scripts/generate_paranoid_signal.py',
            'scripts/prometheus_exporter.py',
            'scripts/deploy_artifacts.py'
        ]
        
        non_executable = []
        for script in script_files:
            if os.path.exists(script):
                if not os.access(script, os.X_OK):
                    try:
                        os.chmod(script, 0o755)
                    except:
                        non_executable.append(script)
        
        if non_executable:
            return False, f"Cannot make executable: {', '.join(non_executable)}"
        
        return True, "Script permissions OK"
    
    def run_basic_functionality_test(self) -> Tuple[bool, str]:
        """Run a basic functionality test."""
        try:
            # Test mock data generation
            result = subprocess.run(
                ['python3', 'scripts/generate_mock.py', '--n', '10', '--out', 'artifacts/sanity_test.csv'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and os.path.exists('artifacts/sanity_test.csv'):
                # Clean up test file
                os.remove('artifacts/sanity_test.csv')
                return True, "Basic functionality test passed"
            else:
                return False, f"Mock generation failed: {result.stderr[:50] if result.stderr else 'unknown error'}"
        except subprocess.TimeoutExpired:
            return False, "Functionality test timeout"
        except Exception as e:
            return False, f"Test failed: {str(e)[:50]}"
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all sanity checks."""
        print("🚀 PARANOID V5 - SANITY CHECK")
        print("=" * 50)
        
        # Core checks
        self.check("Environment Variables", self.check_environment_variables)
        self.check("Required Files", self.check_required_files)
        self.check("Python Dependencies", self.check_dependencies)
        self.check("Makefile Targets", self.check_makefile_targets)
        self.check("Artifacts Directory", self.check_artifacts_directory)
        self.check("Script Permissions", self.check_permissions)
        
        # Connectivity checks
        self.check("AWS S3 Connectivity", self.check_aws_connectivity)
        self.check("Prometheus Gateway", self.check_prometheus_connectivity)
        self.check("Slack Webhook", self.check_slack_webhook)
        
        # Setup checks
        self.check("Browser Testing Setup", self.check_playwright_setup)
        
        # Functionality test
        self.check("Basic Functionality", self.run_basic_functionality_test)
        
        # Summary
        print("=" * 50)
        total_time = time.time() - self.start_time
        total_checks = self.checks_passed + self.checks_failed
        
        if self.checks_failed == 0:
            print(f"🎉 ALL CHECKS PASSED! ({self.checks_passed}/{total_checks})")
            status = "READY"
        elif self.checks_failed <= 2:
            print(f"⚠️ MOSTLY READY ({self.checks_passed}/{total_checks} passed)")
            status = "MOSTLY_READY"
        else:
            print(f"❌ NOT READY ({self.checks_failed}/{total_checks} failed)")
            status = "NOT_READY"
        
        if self.warnings > 0:
            print(f"⚠️ {self.warnings} warnings (optional features disabled)")
        
        print(f"⏱️ Completed in {total_time:.1f}s")
        
        result = {
            'status': status,
            'checks_passed': self.checks_passed,
            'checks_failed': self.checks_failed,
            'warnings': self.warnings,
            'total_time': total_time,
            'ready_for_production': (self.checks_failed == 0)
        }
        
        # Next steps
        if result['ready_for_production']:
            print("\n🚀 NEXT STEPS:")
            print("1. Run: make paranoid-ultimate")
            print("2. Validate: make paranoid-production-check")
            print("3. Deploy: make paranoid-deploy")
        else:
            print("\n🔧 FIX ISSUES BEFORE PROCEEDING:")
            print("- Review failed checks above")
            print("- Set missing environment variables") 
            print("- Install missing dependencies")
        
        return result


def main():
    checker = SanityChecker()
    result = checker.run_all_checks()
    exit(0 if result['ready_for_production'] else 1)


if __name__ == "__main__":
    main()
