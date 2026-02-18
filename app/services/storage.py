"""
Storage service for DigitalOcean Spaces (S3-compatible).

BOL Storage Structure:
    Raw BOLs:     greencandle/dispatch/raw/bol/{mc_number}_{load_id}_BOL_signed.{ext}
    Processed:    greencandle/dispatch/processed/bol/{mc_number}_{load_id}_processed{_suffix}.pdf

Workflow:
    1. Driver uploads → upload_bol() → dispatch/raw/bol/
    2. OCR processes → get_object() reads from raw → save_processed_bol() → dispatch/processed/bol/
    3. Factoring packet → uses processed BOL from dispatch/processed/bol/
"""
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
    Uploads raw BOL to Spaces (private) at dispatch/raw/bol/.
    Converts images (JPG/PNG) to PDF automatically for professionalism.
    Returns (bucket, key) only. Store these in DB; generate URLs dynamically via get_document_url() or get_object().
    
    Path: greencandle/dispatch/raw/bol/{mc_number}_{load_id}_BOL_signed.pdf
    """
    prefix = settings.STORAGE_BUCKET_PREFIX.rstrip("/")
    
    # Always save as PDF (images will be converted)
    file_path = f"{prefix}/raw/bol/{mc_number}_{load_id}_BOL_signed.pdf"

    if not DO_SPACES_KEY or not DO_SPACES_SECRET:
        print("⚠️  WARNING: No DigitalOcean Keys found. Returning MOCK bucket/key.")
        return (DO_SPACES_BUCKET or "greencandle", file_path)

    s3 = get_s3_client()
    try:
        await file.seek(0)
        file_content = await file.read()
        if not file_content:
            raise ValueError("File content is empty")
        
        # Check if it's an image and convert to PDF
        ext = (file.filename or "").split(".")[-1].lower() if "." in (file.filename or "") else "jpg"
        content_type = (file.content_type or "").lower()
        is_image = ext in ("jpg", "jpeg", "png", "gif", "webp") or "image/" in content_type
        
        if is_image:
            # Convert image to PDF
            print(f"🖼️  Converting image to PDF...")
            file_content = _image_to_pdf(file_content, content_type)
            content_type = "application/pdf"
        elif ext == "pdf" or "pdf" in content_type:
            # Already PDF, use as-is
            content_type = "application/pdf"
        else:
            # Unknown format, try to convert if it looks like an image
            print(f"⚠️  Unknown file type '{ext}', attempting PDF conversion...")
            file_content = _image_to_pdf(file_content, content_type)
            content_type = "application/pdf"
        
        print(f"📤 Uploading RAW BOL (as PDF) to bucket '{DO_SPACES_BUCKET}' key '{file_path}' (private)")
        s3.put_object(
            Bucket=DO_SPACES_BUCKET,
            Key=file_path,
            Body=file_content,
            ContentType=content_type,
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


def save_processed_bol(content: bytes, mc_number: str, load_id: str, filename_suffix: Optional[str] = None) -> Tuple[str, str]:
    """
    Save processed BOL (after OCR) to Spaces (private) at dispatch/processed/bol/.
    Returns (bucket, key) only.
    
    Path: greencandle/dispatch/processed/bol/{mc_number}_{load_id}_processed{_suffix}.pdf
    
    Args:
        content: PDF bytes (processed BOL)
        mc_number: MC number
        load_id: Load ID
        filename_suffix: Optional suffix (e.g., "_ocr", "_invoice") to add before .pdf
    """
    prefix = settings.STORAGE_BUCKET_PREFIX.rstrip("/")
    suffix = f"_{filename_suffix}" if filename_suffix else ""
    file_path = f"{prefix}/processed/bol/{mc_number}_{load_id}_processed{suffix}.pdf"

    if not DO_SPACES_KEY or not DO_SPACES_SECRET:
        print("⚠️  WARNING: No DigitalOcean Keys found. Returning MOCK bucket/key.")
        return (DO_SPACES_BUCKET or "greencandle", file_path)

    s3 = get_s3_client()
    try:
        if not content:
            raise ValueError("Content is empty")
        print(f"💾 Saving PROCESSED BOL to bucket '{DO_SPACES_BUCKET}' key '{file_path}' (private)")
        s3.put_object(
            Bucket=DO_SPACES_BUCKET,
            Key=file_path,
            Body=content,
            ContentType="application/pdf",
            # No ACL = private; backend generates URLs when needed
        )
        return (DO_SPACES_BUCKET, file_path)
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"❌ Save Processed BOL Error ({error_type}): {error_msg}")
        import traceback
        traceback.print_exc()
        raise ValueError(f"Failed to save processed BOL: {error_msg}") from e


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


def convert_bol_image_to_pdf(bucket: str, jpg_key: str) -> Tuple[str, str]:
    """
    Convert an existing JPG/PNG BOL in Spaces to PDF format.
    Downloads the image, converts to PDF, uploads as .pdf, returns new (bucket, pdf_key).
    
    Args:
        bucket: Spaces bucket name
        jpg_key: Key to the JPG/PNG file (e.g., "dispatch/raw/bol/TEST125_TEST-LOAD-125_BOL_signed.jpg")
    
    Returns:
        (bucket, pdf_key) tuple where pdf_key is the new PDF path
    """
    s3 = get_s3_client()
    
    # Download the image
    image_content = get_object(bucket, jpg_key)
    
    # Determine content type from key
    ext = jpg_key.split(".")[-1].lower() if "." in jpg_key else "jpg"
    content_type = f"image/{ext}" if ext in ("jpg", "jpeg", "png", "gif", "webp") else "image/jpeg"
    
    # Convert to PDF
    pdf_content = _image_to_pdf(image_content, content_type)
    
    # Generate PDF key (replace extension with .pdf)
    pdf_key = jpg_key.rsplit(".", 1)[0] + ".pdf"
    
    # Upload PDF
    s3.put_object(
        Bucket=bucket,
        Key=pdf_key,
        Body=pdf_content,
        ContentType="application/pdf",
    )
    
    print(f"✅ Converted {jpg_key} → {pdf_key}")
    return (bucket, pdf_key)


def get_processed_bol_key(raw_key: str, filename_suffix: Optional[str] = None) -> str:
    """
    Convert raw BOL key to processed BOL key.
    
    Example:
        raw: dispatch/raw/bol/MC123_LOAD001_BOL_signed.pdf
        processed: dispatch/processed/bol/MC123_LOAD001_processed.pdf
    
    Args:
        raw_key: Raw BOL key (e.g., "dispatch/raw/bol/MC123_LOAD001_BOL_signed.pdf")
        filename_suffix: Optional suffix (e.g., "_ocr", "_invoice") to add before .pdf
    
    Returns:
        Processed BOL key path
    """
    if "/raw/bol/" not in raw_key:
        raise ValueError(f"Invalid raw BOL key format: {raw_key}")
    
    # Extract filename part (everything after /raw/bol/)
    filename_part = raw_key.split("/raw/bol/")[-1]
    # Remove _BOL_signed.{ext} and replace with _processed{suffix}.pdf
    base_name = filename_part.rsplit("_BOL_signed", 1)[0]
    suffix = f"_{filename_suffix}" if filename_suffix else ""
    processed_key = raw_key.replace("/raw/bol/", "/processed/bol/").replace(
        filename_part, f"{base_name}_processed{suffix}.pdf"
    )
    return processed_key


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