import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_ENV = os.getenv("APP_ENV", "template")
    # URL path prefix for cloud storage (Spaces/S3). This app uses one folder: our-cloud-storage/dispatch
    STORAGE_BUCKET_PREFIX = os.getenv("STORAGE_BUCKET_PREFIX", "our-cloud-storage/dispatch").rstrip("/")


settings = Settings()
