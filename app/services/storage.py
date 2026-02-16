import io
import os
from datetime import datetime

import boto3
from fastapi import UploadFile

from app.core.config import settings

# Load from .env
DO_SPACES_KEY = os.getenv("DO_SPACES_KEY")
DO_SPACES_SECRET = os.getenv("DO_SPACES_SECRET")
DO_SPACES_REGION = os.getenv("DO_SPACES_REGION", "nyc3")
DO_SPACES_BUCKET = os.getenv("DO_SPACES_BUCKET", "our-cloud-storage")
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


async def upload_bol(file: UploadFile, mc_number: str, load_id: str) -> str:
    """Uploads BOL to Spaces and returns the public URL. Uses STORAGE_BUCKET_PREFIX (dispatch/) inside bucket."""
    
    # --- FAIL-SAFE FOR TESTING ---
    # If no keys are found, return a fake URL so we can test the MATH.
    if not DO_SPACES_KEY or not DO_SPACES_SECRET:
        print("⚠️  WARNING: No DigitalOcean Keys found. Returning MOCK URL.")
        prefix = settings.STORAGE_BUCKET_PREFIX
        return f"http://localhost:8990/mock-storage/{prefix}/{mc_number}/{load_id}/{file.filename}"
    # -----------------------------

    s3 = get_s3_client()
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    # Path format: dispatch/MC123456/LOAD_999/BOL_signed.jpg (prefix from config)
    prefix = settings.STORAGE_BUCKET_PREFIX.rstrip("/")
    file_path = f"{prefix}/{mc_number}/{load_id}/BOL_signed.{file_extension}"
    
    try:
        # Reset file pointer to start (FastAPI UploadFile may have been read already)
        await file.seek(0)
        # Read file content into memory for boto3
        file_content = await file.read()
        
        if not file_content:
            raise ValueError("File content is empty")
        
        print(f"📤 Uploading to bucket '{DO_SPACES_BUCKET}' in region '{DO_SPACES_REGION}' at path '{file_path}'")
        
        # Upload using put_object (works better with bytes than upload_fileobj for FastAPI UploadFile)
        s3.put_object(
            Bucket=DO_SPACES_BUCKET,
            Key=file_path,
            Body=file_content,
            ACL="public-read",
            ContentType=file.content_type or "image/jpeg"
        )
        # Public URL: https://nyc3.digitaloceanspaces.com/our-cloud-storage/dispatch/MC123/LOAD_999/BOL_signed.jpg
        return f"{DO_SPACES_ENDPOINT}/{DO_SPACES_BUCKET}/{file_path}"
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
) -> str:
    """
    Upload load document (BOL, RateCon, Lumper). Converts images to PDF for professionalism.
    Path: {prefix}/trucker_{id}/load_{id}/{doc_type}_{timestamp}.pdf
    Returns public file_url.
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
        print("⚠️  WARNING: No DigitalOcean Keys. Returning MOCK URL.")
        return f"http://localhost:8990/mock-storage/{file_path}"

    s3 = get_s3_client()
    s3.put_object(
        Bucket=DO_SPACES_BUCKET,
        Key=file_path,
        Body=content,
        ACL="public-read",
        ContentType=target_content_type,
    )
    return f"{DO_SPACES_ENDPOINT}/{DO_SPACES_BUCKET}/{file_path}"