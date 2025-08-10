#!/usr/bin/env python3
"""
☁️ ARTIFACT DEPLOYMENT - S3/Azure Blob/GCS Sync

Deploys paranoid pipeline artifacts to cloud storage with versioning,
backup management, and rollback capabilities.
"""

import os
import json
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import hashlib
import warnings
warnings.filterwarnings('ignore')


class ArtifactDeployer:
    """Deploy paranoid artifacts to cloud storage."""
    
    def __init__(self, provider: str = 'auto'):
        self.provider = self._detect_provider(provider)
        self.timestamp = datetime.now(timezone.utc).isoformat().replace(':', '-')
        
        if self.provider == 's3':
            try:
                import boto3
                self.s3_client = boto3.client('s3')
                self.bucket = os.getenv('S3_BUCKET', 'paranoid-newswire')
                self.prefix = os.getenv('S3_PREFIX', 'artifacts')
            except ImportError:
                print("⚠️ boto3 not installed, falling back to local deployment")
                self.provider = 'local'
        elif self.provider == 'azure':
            # Azure Blob setup would go here
            self.container = os.getenv('AZURE_CONTAINER', 'paranoid-artifacts')
        elif self.provider == 'gcs':
            # Google Cloud Storage setup would go here
            self.bucket = os.getenv('GCS_BUCKET', 'paranoid-newswire')
    
    def _detect_provider(self, provider: str) -> str:
        """Auto-detect cloud provider based on environment."""
        if provider != 'auto':
            return provider
        
        if os.getenv('AWS_ACCESS_KEY_ID') or os.getenv('AWS_PROFILE'):
            return 's3'
        elif os.getenv('AZURE_STORAGE_CONNECTION_STRING'):
            return 'azure'
        elif os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            return 'gcs'
        else:
            return 'local'  # Fallback to local backup
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def create_run_metadata(self, artifacts_dir: str = 'artifacts') -> Dict:
        """Create run metadata for governance and audit trail."""
        metadata = {
            'deployment': {
                'timestamp': self.timestamp,
                'deployer': os.getenv('USER', 'unknown'),
                'environment': os.getenv('DEPLOYMENT_ENV', 'production'),
                'version': os.getenv('BUILD_VERSION', 'latest'),
                'commit_hash': self._get_git_commit(),
                'provider': self.provider
            },
            'data_sources': {
                'wgi_snapshot_date': self._get_wgi_date(),
                'gdelt_range_days': int(os.getenv('PARANOID_RANGE_DAYS', '90')),
                'gdelt_min_events': int(os.getenv('PARANOID_MIN_EVENTS', '200000')),
                'data_version': self._get_data_version()
            },
            'artifacts': {},
            'quality_gates': {},
            'governance': {
                'pii_compliance': 'actor_fields_only',
                'bias_monitoring': 'enabled',
                'audit_trail': True,
                'retention_days': 90
            }
        }
        
        # Add artifact hashes and sizes
        artifact_files = [
            'metrics.json', 'signal.raw.json', 'report.enriched.json',
            'humint_profile.json', 'drift_report.json', 'paranoid_models.joblib'
        ]
        
        for artifact in artifact_files:
            file_path = os.path.join(artifacts_dir, artifact)
            if os.path.exists(file_path):
                metadata['artifacts'][artifact] = {
                    'size_bytes': os.path.getsize(file_path),
                    'sha256': self.calculate_file_hash(file_path),
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                }
        
        # Add quality gate results
        metrics_path = os.path.join(artifacts_dir, 'metrics.json')
        if os.path.exists(metrics_path):
            with open(metrics_path, 'r') as f:
                metrics = json.load(f)
            
            performance = metrics.get('performance', {})
            fairness = metrics.get('fairness', {})
            calibration = metrics.get('calibration', {})
            
            metadata['quality_gates'] = {
                'auc_minimum': all(performance.get(f'{t}_auc', 0) >= 0.86 
                                 for t in ['sensitive_class', 'suppression_event_6w', 'narrative_shift_4w']),
                'fairness_check': fairness.get('max_delta_auc', 1) <= 0.10,
                'calibration_check': calibration.get('ece_mean', 1) <= 0.05,
                'overall_status': 'PASS' if all([
                    all(performance.get(f'{t}_auc', 0) >= 0.86 
                        for t in ['sensitive_class', 'suppression_event_6w', 'narrative_shift_4w']),
                    fairness.get('max_delta_auc', 1) <= 0.10,
                    calibration.get('ece_mean', 1) <= 0.05
                ]) else 'FAIL'
            }
        
        return metadata
    
    def _get_git_commit(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                  capture_output=True, text=True, timeout=5)
            return result.stdout.strip() if result.returncode == 0 else 'unknown'
        except:
            return 'unknown'
    
    def _get_wgi_date(self) -> str:
        """Get WGI data snapshot date."""
        try:
            wgi_files = list(Path('data/raw/wgi').rglob('*.csv'))
            if wgi_files:
                return datetime.fromtimestamp(wgi_files[0].stat().st_mtime).isoformat()
        except:
            pass
        return 'unknown'
    
    def _get_data_version(self) -> str:
        """Generate data version identifier."""
        try:
            paranoid_csv = 'data/paranoid.csv'
            if os.path.exists(paranoid_csv):
                return self.calculate_file_hash(paranoid_csv)[:12]
        except:
            pass
        return 'unknown'
    
    def backup_current_artifacts(self) -> bool:
        """Create backup of current production artifacts."""
        if self.provider == 's3':
            return self._backup_s3()
        elif self.provider == 'local':
            return self._backup_local()
        return False
    
    def _backup_s3(self) -> bool:
        """Backup current S3 artifacts."""
        try:
            # List current production artifacts
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=f"{self.prefix}/production/"
            )
            
            if 'Contents' not in response:
                print("ℹ️ No existing production artifacts to backup")
                return True
            
            backup_prefix = f"{self.prefix}/backup/{self.timestamp}"
            
            for obj in response['Contents']:
                source_key = obj['Key']
                backup_key = source_key.replace(f"{self.prefix}/production/", f"{backup_prefix}/")
                
                self.s3_client.copy_object(
                    Bucket=self.bucket,
                    CopySource={'Bucket': self.bucket, 'Key': source_key},
                    Key=backup_key
                )
            
            print(f"✅ Backed up {len(response['Contents'])} artifacts to {backup_prefix}")
            return True
            
        except Exception as e:
            print(f"❌ S3 backup failed: {e}")
            return False
    
    def _backup_local(self) -> bool:
        """Backup artifacts locally."""
        try:
            backup_dir = f"backups/{self.timestamp}"
            os.makedirs(backup_dir, exist_ok=True)
            
            # Copy current artifacts
            for artifact in ['report.enriched.json', 'metrics.json', 'signal.raw.json']:
                src = f"artifacts/{artifact}"
                dst = f"{backup_dir}/{artifact}"
                if os.path.exists(src):
                    subprocess.run(['cp', src, dst], check=True)
            
            print(f"✅ Local backup created: {backup_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Local backup failed: {e}")
            return False
    
    def deploy_artifacts(self, artifacts_dir: str = 'artifacts', force: bool = False) -> bool:
        """Deploy artifacts to cloud storage."""
        print(f"☁️ Deploying artifacts via {self.provider}...")
        
        # Create run metadata
        metadata = self.create_run_metadata(artifacts_dir)
        
        # Save metadata locally
        metadata_path = os.path.join(artifacts_dir, 'run_meta.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Check quality gates unless forced
        if not force and metadata['quality_gates'].get('overall_status') == 'FAIL':
            print("❌ Quality gates FAILED - deployment blocked")
            print("   Use --force to override quality gates")
            return False
        
        # Backup current production
        if not self.backup_current_artifacts():
            if not force:
                print("❌ Backup failed - deployment blocked")
                return False
        
        # Deploy based on provider
        if self.provider == 's3':
            return self._deploy_s3(artifacts_dir)
        elif self.provider == 'local':
            return self._deploy_local(artifacts_dir)
        else:
            print(f"❌ Provider {self.provider} not implemented")
            return False
    
    def _deploy_s3(self, artifacts_dir: str) -> bool:
        """Deploy artifacts to S3."""
        try:
            deploy_files = [
                'report.enriched.json',  # Main newswire feed
                'metrics.json',          # Quality metrics
                'signal.raw.json',       # Raw signals
                'humint_profile.json',   # Intelligence analysis
                'drift_report.json',     # Model health
                'run_meta.json'          # Governance metadata
            ]
            
            deployed_count = 0
            
            for filename in deploy_files:
                local_path = os.path.join(artifacts_dir, filename)
                if not os.path.exists(local_path):
                    print(f"⚠️ Skipping missing file: {filename}")
                    continue
                
                # Deploy to production path
                s3_key = f"{self.prefix}/production/{filename}"
                
                self.s3_client.upload_file(
                    local_path, 
                    self.bucket, 
                    s3_key,
                    ExtraArgs={
                        'ContentType': 'application/json',
                        'CacheControl': 'max-age=60',  # 1 minute cache
                        'Metadata': {
                            'deployment-timestamp': self.timestamp,
                            'deployer': os.getenv('USER', 'unknown'),
                            'commit-hash': self._get_git_commit()
                        }
                    }
                )
                
                # Also deploy to timestamped path for history
                timestamped_key = f"{self.prefix}/history/{self.timestamp}/{filename}"
                self.s3_client.upload_file(local_path, self.bucket, timestamped_key)
                
                deployed_count += 1
                print(f"✅ Deployed {filename} -> s3://{self.bucket}/{s3_key}")
            
            print(f"🚀 Successfully deployed {deployed_count} artifacts to S3")
            print(f"📡 Production feed: s3://{self.bucket}/{self.prefix}/production/report.enriched.json")
            
            return True
            
        except Exception as e:
            print(f"❌ S3 deployment failed: {e}")
            return False
    
    def _deploy_local(self, artifacts_dir: str) -> bool:
        """Deploy artifacts locally (for development)."""
        try:
            deploy_dir = 'deploy/production'
            os.makedirs(deploy_dir, exist_ok=True)
            
            deploy_files = [
                'report.enriched.json', 'metrics.json', 'signal.raw.json',
                'humint_profile.json', 'drift_report.json', 'run_meta.json'
            ]
            
            for filename in deploy_files:
                src = os.path.join(artifacts_dir, filename)
                dst = os.path.join(deploy_dir, filename)
                if os.path.exists(src):
                    subprocess.run(['cp', src, dst], check=True)
                    print(f"✅ Deployed {filename} -> {dst}")
            
            print(f"🚀 Local deployment complete: {deploy_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Local deployment failed: {e}")
            return False
    
    def rollback_to_backup(self, backup_timestamp: str = None) -> bool:
        """Rollback to previous backup."""
        if self.provider == 's3':
            return self._rollback_s3(backup_timestamp)
        elif self.provider == 'local':
            return self._rollback_local(backup_timestamp)
        return False
    
    def _rollback_s3(self, backup_timestamp: str = None) -> bool:
        """Rollback S3 deployment."""
        try:
            if not backup_timestamp:
                # Find latest backup
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket,
                    Prefix=f"{self.prefix}/backup/",
                    Delimiter='/'
                )
                
                if 'CommonPrefixes' not in response:
                    print("❌ No backups found")
                    return False
                
                backup_dirs = [p['Prefix'].split('/')[-2] for p in response['CommonPrefixes']]
                backup_timestamp = sorted(backup_dirs)[-1]
                print(f"🔄 Using latest backup: {backup_timestamp}")
            
            backup_prefix = f"{self.prefix}/backup/{backup_timestamp}"
            
            # List backup files
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=backup_prefix
            )
            
            if 'Contents' not in response:
                print(f"❌ Backup {backup_timestamp} not found")
                return False
            
            # Restore each file
            for obj in response['Contents']:
                backup_key = obj['Key']
                filename = backup_key.split('/')[-1]
                production_key = f"{self.prefix}/production/{filename}"
                
                self.s3_client.copy_object(
                    Bucket=self.bucket,
                    CopySource={'Bucket': self.bucket, 'Key': backup_key},
                    Key=production_key
                )
            
            print(f"🔄 Rollback complete: restored {len(response['Contents'])} files")
            return True
            
        except Exception as e:
            print(f"❌ S3 rollback failed: {e}")
            return False
    
    def _rollback_local(self, backup_timestamp: str = None) -> bool:
        """Rollback local deployment."""
        try:
            if not backup_timestamp:
                backup_dirs = [d for d in os.listdir('backups') if os.path.isdir(f'backups/{d}')]
                if not backup_dirs:
                    print("❌ No backups found")
                    return False
                backup_timestamp = sorted(backup_dirs)[-1]
                print(f"🔄 Using latest backup: {backup_timestamp}")
            
            backup_dir = f"backups/{backup_timestamp}"
            production_dir = "deploy/production"
            
            if not os.path.exists(backup_dir):
                print(f"❌ Backup {backup_timestamp} not found")
                return False
            
            # Restore files
            for filename in os.listdir(backup_dir):
                src = os.path.join(backup_dir, filename)
                dst = os.path.join(production_dir, filename)
                subprocess.run(['cp', src, dst], check=True)
            
            print(f"🔄 Rollback complete: {backup_dir} -> {production_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Local rollback failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Deploy Paranoid Artifacts")
    parser.add_argument('--provider', choices=['s3', 'azure', 'gcs', 'local', 'auto'], 
                       default='auto', help='Cloud provider')
    parser.add_argument('--artifacts_dir', default='artifacts', help='Artifacts directory')
    parser.add_argument('--force', action='store_true', help='Force deploy despite quality gate failures')
    parser.add_argument('--rollback', help='Rollback to specific backup timestamp')
    parser.add_argument('--list-backups', action='store_true', help='List available backups')
    
    args = parser.parse_args()
    
    deployer = ArtifactDeployer(args.provider)
    
    if args.rollback:
        success = deployer.rollback_to_backup(args.rollback)
        exit(0 if success else 1)
    
    if args.list_backups:
        print("📋 Available backups:")
        # Implementation would list backups based on provider
        return
    
    success = deployer.deploy_artifacts(args.artifacts_dir, args.force)
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
