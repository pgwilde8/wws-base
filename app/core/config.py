import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_ENV = os.getenv("APP_ENV", "template")
    # Path prefix (folder) inside the bucket. Bucket name comes from DO_SPACES_BUCKET env var.
    # Example: bucket="our-cloud-storage", prefix="dispatch" → files go to our-cloud-storage/dispatch/...
    STORAGE_BUCKET_PREFIX = os.getenv("STORAGE_BUCKET_PREFIX", "dispatch").rstrip("/")


settings = Settings()
