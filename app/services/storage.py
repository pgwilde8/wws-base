import io
import os
from datetime import datetime
from typing import Optional, Tuple

import boto3
from fastapi import UploadFile

from app.core.config import settings

# Presigned URL expiry (seconds) when sending to factor or showing in UI
PRESIGNED_EXPIRES = 3600

# Load from .env
DO_SPACES_KEY = os.getenv("DO_SPACES_KEY")
DO_SPACES_SECRET = os.getenv("DO_SPACES_SECRET")
DO_SPACES_REGION = os.getenv("DO_SPACES_REGION", "nyc3")
DO_SPACES_BUCKET = os.getenv("DO_SPACES_BUCKET", "greencandle")
DO_SPACES_ENDPOINT = os.getenv("DO_SPACES_ENDPOINT") or f"https://{DO_SPACES_REGION}.digitaloceanspaces.com"


def get_s3_client():
    """Get boto3 S3 client configured for DigitalOcean Spaces."""
    if not DO_SPACES_KEY or not DO_SPACES_SECRET:
        raise ValueError("DO_SPACES_KEY and DO_SPACES_SECRET must be set in environment")
    return boto3.client(
        "s3",
        region_name=DO_SPACES_REGION,
        endpoint_url=DO_SPACES_ENDPOINT,
        aws_access_key_id=DO_SPACES_KEY,
        aws_secret_access_key=DO_SPACES_SECRET,
    )


def list_buckets():
    """Helper to verify Spaces access and list available buckets."""
    try:
        s3 = get_s3_client()
        response = s3.list_buckets()
        return [b["Name"] for b in response.get("Buckets", [])]
    except Exception as e:
        # Key may not have list_buckets permission - that's OK, try direct access
        return []


async def upload_bol(file: UploadFile, mc_number: str, load_id: str) -> Tuple[str, str]:
    """
    Uploads BOL to Spaces (private). Returns (bucket, key) only.
    Store these in DB; generate URLs dynamically via get_document_url() or get_object().
    """
    prefix = settings.STORAGE_BUCKET_PREFIX.rstrip("/")
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    file_path = f"{prefix}/raw/bol/{mc_number}_{load_id}_BOL_signed.{file_extension}"

    if not DO_SPACES_KEY or not DO_SPACES_SECRET:
        print("⚠️  WARNING: No DigitalOcean Keys found. Returning MOCK bucket/key.")
        return (DO_SPACES_BUCKET or "greencandle", file_path)

    s3 = get_s3_client()
    try:
        await file.seek(0)
        file_content = await file.read()
        if not file_content:
            raise ValueError("File content is empty")
        print(f"📤 Uploading to bucket '{DO_SPACES_BUCKET}' key '{file_path}' (private)")
        s3.put_object(
            Bucket=DO_SPACES_BUCKET,
            Key=file_path,
            Body=file_content,
            ContentType=file.content_type or "image/jpeg",
            # No ACL = private; backend generates URLs when needed
        )
        return (DO_SPACES_BUCKET, file_path)
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Enhanced error message for NoSuchBucket
        if "NoSuchBucket" in error_type or "does not exist" in error_msg:
            available_buckets = list_buckets()
            bucket_info = f"Trying bucket: '{DO_SPACES_BUCKET}' in region '{DO_SPACES_REGION}'"
            if available_buckets:
                bucket_info += f"\nAvailable buckets: {', '.join(available_buckets)}"
            else:
                bucket_info += "\n(Cannot list buckets - key may not have list permission, but bucket might still exist)"
            error_msg = f"{error_msg}\n{bucket_info}\n💡 Create '{DO_SPACES_BUCKET}' in DigitalOcean → Spaces → Create Bucket (region: {DO_SPACES_REGION})"
        
        print(f"❌ Upload Error ({error_type}): {error_msg}")
        import traceback
        traceback.print_exc()
        # Re-raise so route can catch and return detailed error
        raise ValueError(error_msg) from e


def get_object(bucket: str, key: str) -> bytes:
    """
    Retrieve file from Spaces (private). Use for OCR, factoring packet, or streaming.
    Raises if bucket/key missing or access fails.
    """
    s3 = get_s3_client()
    resp = s3.get_object(Bucket=bucket, Key=key)
    return resp["Body"].read()


def get_presigned_url(bucket: str, key: str, expires_in: int = PRESIGNED_EXPIRES) -> str:
    """Generate a temporary URL for download/view. Backend never stores public URLs."""
    s3 = get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def _image_to_pdf(content: bytes, content_type: str) -> bytes:
    """Convert JPG/PNG image bytes to single-page PDF. Returns PDF bytes."""
    import img2pdf
    pdf_bytes = img2pdf.convert(io.BytesIO(content))
    return pdf_bytes


async def upload_load_document(
    file: UploadFile,
    trucker_id: int,
    load_id: str,
    doc_type: str = "BOL",
) -> Tuple[str, str]:
    """
    Upload load document (BOL, RateCon, Lumper) to Spaces (private).
    Converts images to PDF. Returns (bucket, key) only — store these in DB;
    generate URLs via get_presigned_url() or get_object() when needed.
    """
    prefix = settings.STORAGE_BUCKET_PREFIX.rstrip("/")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    ext = (file.filename or "").split(".")[-1].lower() if "." in (file.filename or "") else "jpg"
    content_type = (file.content_type or "").lower()

    await file.seek(0)
    content = await file.read()
    if not content:
        raise ValueError("File content is empty")

    is_image = ext in ("jpg", "jpeg", "png", "gif", "webp") or "image/" in content_type
    target_ext = "pdf"
    target_content_type = "application/pdf"

    if is_image:
        content = _image_to_pdf(content, content_type)
        target_ext = "pdf"
        target_content_type = "application/pdf"

    file_path = f"{prefix}/trucker_{trucker_id}/load_{load_id}/{doc_type}_{timestamp}.{target_ext}"

    if not DO_SPACES_KEY or not DO_SPACES_SECRET:
        print("⚠️  WARNING: No DigitalOcean Keys. Returning MOCK bucket/key.")
        return (DO_SPACES_BUCKET or "greencandle", file_path)

    s3 = get_s3_client()
    s3.put_object(
        Bucket=DO_SPACES_BUCKET,
        Key=file_path,
        Body=content,
        ContentType=target_content_type,
        # No ACL = private; backend generates URLs when needed
    )
    return (DO_SPACES_BUCKET, file_path)