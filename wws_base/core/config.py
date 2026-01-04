import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_ENV = os.getenv("APP_ENV", "template")

settings = Settings()
