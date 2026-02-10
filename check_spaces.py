#!/usr/bin/env python3
"""Quick script to verify DigitalOcean Spaces credentials and list buckets."""
import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

DO_SPACES_KEY = os.getenv("DO_SPACES_KEY")
DO_SPACES_SECRET = os.getenv("DO_SPACES_SECRET")
DO_SPACES_REGION = os.getenv("DO_SPACES_REGION", "nyc3")
DO_SPACES_ENDPOINT = os.getenv("DO_SPACES_ENDPOINT") or f"https://{DO_SPACES_REGION}.digitaloceanspaces.com"

print("🔍 Checking DigitalOcean Spaces...")
print(f"Region: {DO_SPACES_REGION}")
print(f"Endpoint: {DO_SPACES_ENDPOINT}")
print(f"Key: {DO_SPACES_KEY[:10]}..." if DO_SPACES_KEY else "Key: NOT SET")
print()

if not DO_SPACES_KEY or not DO_SPACES_SECRET:
    print("❌ DO_SPACES_KEY or DO_SPACES_SECRET not set in .env")
    exit(1)

try:
    s3 = boto3.client(
        "s3",
        region_name=DO_SPACES_REGION,
        endpoint_url=DO_SPACES_ENDPOINT,
        aws_access_key_id=DO_SPACES_KEY,
        aws_secret_access_key=DO_SPACES_SECRET,
    )
    
    print("✅ Credentials accepted.")
    
    # Try to list buckets (may fail if key doesn't have list permission)
    try:
        response = s3.list_buckets()
        buckets = response.get("Buckets", [])
        if buckets:
            print(f"\n📦 Found {len(buckets)} bucket(s):")
            for b in buckets:
                print(f"   - {b['Name']} (created: {b.get('CreationDate', 'unknown')})")
        else:
            print("⚠️  No buckets found.")
    except Exception as e:
        print(f"⚠️  Cannot list buckets (key may not have list permission): {e}")
        print("   This is OK - trying direct bucket access instead...")
        buckets = []
    
    # Check if target bucket exists by trying to access it directly
    target_bucket = os.getenv("DO_SPACES_BUCKET", "our-cloud-storage")
    print(f"\n🔍 Testing access to bucket '{target_bucket}'...")
    
    try:
        # Try to get bucket location (tests if bucket exists and we have access)
        s3.head_bucket(Bucket=target_bucket)
        print(f"✅ Bucket '{target_bucket}' exists and is accessible!")
        
        # Try listing objects (to verify write access)
        try:
            objects = s3.list_objects_v2(Bucket=target_bucket, MaxKeys=1)
            print(f"✅ Can read from bucket (found {objects.get('KeyCount', 0)} object(s))")
        except:
            print("⚠️  Can access bucket but may not have read permission")
            
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "404" or "NoSuchBucket" in str(e):
            print(f"❌ Bucket '{target_bucket}' does NOT exist in region '{DO_SPACES_REGION}'")
            print(f"\n💡 Create it in DigitalOcean → Spaces → Create Bucket")
            print(f"   Name: {target_bucket}")
            print(f"   Region: {DO_SPACES_REGION}")
        else:
            print(f"❌ Cannot access bucket: {error_code}: {e}")
            print(f"\n💡 Possible issues:")
            print(f"   1. Bucket doesn't exist")
            print(f"   2. Bucket is in a different region (check DO_SPACES_REGION)")
            print(f"   3. Key doesn't have permission for this bucket")
    except Exception as e:
        print(f"❌ Cannot access bucket: {type(e).__name__}: {e}")
        print(f"\n💡 Possible issues:")
        print(f"   1. Bucket doesn't exist")
        print(f"   2. Bucket is in a different region (check DO_SPACES_REGION)")
        print(f"   3. Key doesn't have permission for this bucket")
        
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
