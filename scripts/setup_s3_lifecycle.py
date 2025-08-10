#!/usr/bin/env python3
"""
🗂️ S3 LIFECYCLE MANAGEMENT - Automated Archival & Cleanup

Sets up S3 lifecycle policies for paranoid artifacts:
- Transition to IA after 30 days
- Archive to Glacier after 90 days
- Delete after 365 days (configurable retention)
- Backup retention with different rules
"""

import json
import os
import argparse
from typing import Dict, List, Any
import warnings
warnings.filterwarnings('ignore')


class S3LifecycleManager:
    """Manage S3 lifecycle policies for paranoid artifacts."""
    
    def __init__(self, bucket: str, region: str = None):
        self.bucket = bucket
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        
        # Import boto3 with fallback
        try:
            import boto3
            self.s3_client = boto3.client('s3', region_name=self.region)
        except ImportError:
            print("❌ boto3 not installed. Install with: pip install boto3")
            exit(1)
    
    def create_lifecycle_policy(self, 
                              production_retention_days: int = 365,
                              backup_retention_days: int = 90,
                              archive_transition_days: int = 90,
                              ia_transition_days: int = 30) -> Dict[str, Any]:
        """Create lifecycle policy configuration."""
        
        lifecycle_config = {
            "Rules": [
                {
                    "ID": "ParanoidProductionArtifacts",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "artifacts/production/"},
                    "Transitions": [
                        {
                            "Days": ia_transition_days,
                            "StorageClass": "STANDARD_IA"
                        },
                        {
                            "Days": archive_transition_days,
                            "StorageClass": "GLACIER"
                        }
                    ],
                    "Expiration": {
                        "Days": production_retention_days
                    },
                    "NoncurrentVersionTransitions": [
                        {
                            "NoncurrentDays": 7,
                            "StorageClass": "STANDARD_IA"
                        },
                        {
                            "NoncurrentDays": 30,
                            "StorageClass": "GLACIER"
                        }
                    ],
                    "NoncurrentVersionExpiration": {
                        "NoncurrentDays": 90
                    }
                },
                {
                    "ID": "ParanoidBackupArtifacts",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "artifacts/backup/"},
                    "Transitions": [
                        {
                            "Days": 7,
                            "StorageClass": "STANDARD_IA"
                        },
                        {
                            "Days": 30,
                            "StorageClass": "GLACIER"
                        }
                    ],
                    "Expiration": {
                        "Days": backup_retention_days
                    }
                },
                {
                    "ID": "ParanoidHistoryArtifacts",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "artifacts/history/"},
                    "Transitions": [
                        {
                            "Days": 1,
                            "StorageClass": "STANDARD_IA"
                        },
                        {
                            "Days": 7,
                            "StorageClass": "GLACIER"
                        }
                    ],
                    "Expiration": {
                        "Days": 180  # Keep history for 6 months
                    }
                },
                {
                    "ID": "ParanoidReportsCleanup",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "reports/"},
                    "Transitions": [
                        {
                            "Days": 14,
                            "StorageClass": "STANDARD_IA"
                        },
                        {
                            "Days": 60,
                            "StorageClass": "GLACIER"
                        }
                    ],
                    "Expiration": {
                        "Days": 365
                    }
                },
                {
                    "ID": "ParanoidTempCleanup",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "temp/"},
                    "Expiration": {
                        "Days": 7  # Clean up temp files quickly
                    }
                }
            ]
        }
        
        return lifecycle_config
    
    def create_bucket_notification_config(self) -> Dict[str, Any]:
        """Create bucket notification configuration for monitoring."""
        return {
            "CloudWatchConfigurations": [
                {
                    "Id": "ParanoidArtifactUploads",
                    "CloudWatchConfiguration": {
                        "LogGroupName": "paranoid-s3-access-logs"
                    },
                    "Events": ["s3:ObjectCreated:*"],
                    "Filter": {
                        "Key": {
                            "FilterRules": [
                                {
                                    "Name": "prefix",
                                    "Value": "artifacts/production/"
                                }
                            ]
                        }
                    }
                }
            ]
        }
    
    def setup_bucket_encryption(self) -> bool:
        """Set up bucket encryption for security."""
        try:
            encryption_config = {
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        },
                        'BucketKeyEnabled': True
                    }
                ]
            }
            
            self.s3_client.put_bucket_encryption(
                Bucket=self.bucket,
                ServerSideEncryptionConfiguration=encryption_config
            )
            
            print(f"✅ Encryption enabled for bucket: {self.bucket}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to set bucket encryption: {e}")
            return False
    
    def setup_bucket_versioning(self) -> bool:
        """Enable bucket versioning for rollback capability."""
        try:
            self.s3_client.put_bucket_versioning(
                Bucket=self.bucket,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            print(f"✅ Versioning enabled for bucket: {self.bucket}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to enable versioning: {e}")
            return False
    
    def setup_bucket_cors(self) -> bool:
        """Set up CORS for web access if needed."""
        try:
            cors_config = {
                'CORSRules': [
                    {
                        'AllowedMethods': ['GET'],
                        'AllowedOrigins': ['*'],
                        'AllowedHeaders': ['*'],
                        'MaxAgeSeconds': 3600,
                        'ExposeHeaders': ['ETag']
                    }
                ]
            }
            
            self.s3_client.put_bucket_cors(
                Bucket=self.bucket,
                CORSConfiguration=cors_config
            )
            
            print(f"✅ CORS configured for bucket: {self.bucket}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to set CORS: {e}")
            return False
    
    def apply_lifecycle_policy(self, policy_config: Dict[str, Any]) -> bool:
        """Apply lifecycle policy to bucket."""
        try:
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket,
                LifecycleConfiguration=policy_config
            )
            
            print(f"✅ Lifecycle policy applied to bucket: {self.bucket}")
            
            # Print policy summary
            print("📋 Lifecycle rules summary:")
            for rule in policy_config['Rules']:
                print(f"   • {rule['ID']}: {rule['Filter']['Prefix']}")
                if 'Expiration' in rule:
                    print(f"     - Expires after {rule['Expiration']['Days']} days")
                for transition in rule.get('Transitions', []):
                    print(f"     - Transition to {transition['StorageClass']} after {transition['Days']} days")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to apply lifecycle policy: {e}")
            return False
    
    def create_iam_policy(self) -> Dict[str, Any]:
        """Generate minimal IAM policy for paranoid CI/CD."""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "ParanoidArtifactAccess",
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:GetObject",
                        "s3:DeleteObject",
                        "s3:PutObjectAcl"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{self.bucket}/artifacts/*",
                        f"arn:aws:s3:::{self.bucket}/reports/*",
                        f"arn:aws:s3:::{self.bucket}/temp/*"
                    ]
                },
                {
                    "Sid": "ParanoidBucketList",
                    "Effect": "Allow",
                    "Action": [
                        "s3:ListBucket",
                        "s3:GetBucketLocation"
                    ],
                    "Resource": f"arn:aws:s3:::{self.bucket}",
                    "Condition": {
                        "StringLike": {
                            "s3:prefix": [
                                "artifacts/*",
                                "reports/*",
                                "temp/*"
                            ]
                        }
                    }
                }
            ]
        }
    
    def setup_complete_bucket(self, 
                            production_retention_days: int = 365,
                            backup_retention_days: int = 90,
                            enable_cors: bool = False) -> bool:
        """Set up complete S3 bucket configuration."""
        print(f"🪣 Setting up S3 bucket: {self.bucket}")
        
        success = True
        
        # Create bucket if it doesn't exist
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
            print(f"✅ Bucket {self.bucket} already exists")
        except:
            try:
                if self.region == 'us-east-1':
                    self.s3_client.create_bucket(Bucket=self.bucket)
                else:
                    self.s3_client.create_bucket(
                        Bucket=self.bucket,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
                print(f"✅ Created bucket: {self.bucket}")
            except Exception as e:
                print(f"❌ Failed to create bucket: {e}")
                return False
        
        # Set up bucket features
        success &= self.setup_bucket_encryption()
        success &= self.setup_bucket_versioning()
        
        if enable_cors:
            success &= self.setup_bucket_cors()
        
        # Apply lifecycle policy
        lifecycle_config = self.create_lifecycle_policy(
            production_retention_days=production_retention_days,
            backup_retention_days=backup_retention_days
        )
        success &= self.apply_lifecycle_policy(lifecycle_config)
        
        # Generate IAM policy
        iam_policy = self.create_iam_policy()
        iam_file = f"{self.bucket}-iam-policy.json"
        with open(iam_file, 'w') as f:
            json.dump(iam_policy, f, indent=2)
        print(f"📄 IAM policy saved to: {iam_file}")
        
        if success:
            print(f"🎉 S3 bucket {self.bucket} fully configured!")
            print("📋 Configuration summary:")
            print(f"   • Encryption: AES256")
            print(f"   • Versioning: Enabled")
            print(f"   • Production retention: {production_retention_days} days")
            print(f"   • Backup retention: {backup_retention_days} days")
            print(f"   • CORS: {'Enabled' if enable_cors else 'Disabled'}")
            print(f"   • IAM policy: {iam_file}")
        
        return success
    
    def get_lifecycle_status(self) -> Dict[str, Any]:
        """Get current lifecycle configuration status."""
        try:
            response = self.s3_client.get_bucket_lifecycle_configuration(Bucket=self.bucket)
            return response['Rules']
        except Exception as e:
            print(f"⚠️ No lifecycle configuration found: {e}")
            return {}
    
    def estimate_storage_costs(self, 
                             artifacts_per_day: int = 10,
                             avg_artifact_size_mb: float = 5.0,
                             days_to_project: int = 365) -> Dict[str, Any]:
        """Estimate storage costs with lifecycle policies."""
        
        # AWS S3 pricing (approximate, varies by region)
        pricing = {
            'standard': 0.023,      # per GB/month
            'standard_ia': 0.0125,  # per GB/month
            'glacier': 0.004,       # per GB/month
        }
        
        total_data_gb = (artifacts_per_day * avg_artifact_size_mb * days_to_project) / 1024
        
        # Estimate distribution based on lifecycle rules
        standard_gb = total_data_gb * 0.1      # First 30 days
        standard_ia_gb = total_data_gb * 0.2   # 30-90 days
        glacier_gb = total_data_gb * 0.7       # 90+ days
        
        monthly_costs = {
            'standard': standard_gb * pricing['standard'],
            'standard_ia': standard_ia_gb * pricing['standard_ia'],
            'glacier': glacier_gb * pricing['glacier']
        }
        
        total_monthly = sum(monthly_costs.values())
        
        return {
            'total_data_gb': total_data_gb,
            'distribution': {
                'standard_gb': standard_gb,
                'standard_ia_gb': standard_ia_gb,
                'glacier_gb': glacier_gb
            },
            'monthly_costs_usd': monthly_costs,
            'total_monthly_usd': total_monthly,
            'annual_estimated_usd': total_monthly * 12
        }


def main():
    parser = argparse.ArgumentParser(description="Setup S3 Lifecycle Management for Paranoid")
    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--production-retention', type=int, default=365, 
                       help='Production artifacts retention in days')
    parser.add_argument('--backup-retention', type=int, default=90,
                       help='Backup artifacts retention in days')
    parser.add_argument('--enable-cors', action='store_true',
                       help='Enable CORS for web access')
    parser.add_argument('--estimate-costs', action='store_true',
                       help='Show storage cost estimates')
    
    args = parser.parse_args()
    
    manager = S3LifecycleManager(args.bucket, args.region)
    
    if args.estimate_costs:
        costs = manager.estimate_storage_costs()
        print("\n💰 Storage cost estimates:")
        print(f"   Total data (1 year): {costs['total_data_gb']:.1f} GB")
        print(f"   Monthly cost: ${costs['total_monthly_usd']:.2f}")
        print(f"   Annual cost: ${costs['annual_estimated_usd']:.2f}")
        print("\n📊 Storage distribution:")
        for storage_class, gb in costs['distribution'].items():
            print(f"   {storage_class}: {gb:.1f} GB")
    
    success = manager.setup_complete_bucket(
        production_retention_days=args.production_retention,
        backup_retention_days=args.backup_retention,
        enable_cors=args.enable_cors
    )
    
    if success:
        print(f"\n🚀 Next steps:")
        print(f"1. Set environment variable: export S3_BUCKET={args.bucket}")
        print(f"2. Configure AWS credentials for CI/CD")
        print(f"3. Apply IAM policy: {args.bucket}-iam-policy.json")
        print(f"4. Test deployment: make paranoid-deploy")
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
