#!/usr/bin/env python3
"""
Quick test: verify SECRET_KEY and SMTP credentials are loaded and working.
Run from project root: python3 app/scripts/test_email_connection.py
"""
import os
import smtplib
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(env_path, override=True)
except ImportError:
    pass


def main():
    print("=== GCD Config & SMTP Test ===\n")

    # 1. SECRET_KEY
    sk = os.getenv("SECRET_KEY", "")
    if not sk or sk in ("dev-secret-change-me", "your_super_secret_random_hex_string", "change-me-please"):
        print("❌ SECRET_KEY: not set or still default. Sessions/Stripe signing may be insecure.")
    else:
        print(f"✅ SECRET_KEY: set ({len(sk)} chars)")

    # 2. SMTP credentials (EMAIL_* or MXROUTE_*)
    user = os.getenv("MXROUTE_SMTP_USER") or os.getenv("EMAIL_USER")
    password = os.getenv("MXROUTE_SMTP_PASSWORD") or os.getenv("EMAIL_PASS")
    host = os.getenv("MXROUTE_SMTP_HOST") or os.getenv("EMAIL_HOST", "fusion.mxrouting.net")
    port = int(os.getenv("MXROUTE_SMTP_PORT") or os.getenv("EMAIL_PORT", "465"))

    if not user or not password:
        print("❌ SMTP: EMAIL_USER/EMAIL_PASS or MXROUTE_SMTP_USER/MXROUTE_SMTP_PASSWORD missing")
        return

    print(f"   SMTP: {host}:{port} as {user}")

    # 3. Handshake
    try:
        with smtplib.SMTP_SSL(host, port) as server:
            server.login(user, password)
        print("✅ SMTP: connection and login OK")
    except Exception as e:
        print(f"❌ SMTP: {e}")

    print("\nDone. Restart uvicorn if you changed .env.")


if __name__ == "__main__":
    main()
