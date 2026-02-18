#!/usr/bin/env python3
"""
Convert an existing JPG BOL in Spaces to PDF.
Usage: python convert_existing_bol.py "dispatch/raw/bol/TEST125_TEST-LOAD-125_BOL_signed.jpg"
"""
import sys
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.storage import convert_bol_image_to_pdf

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_existing_bol.py 'dispatch/raw/bol/FILENAME.jpg'")
        print("\nExample:")
        print("  python convert_existing_bol.py 'dispatch/raw/bol/TEST125_TEST-LOAD-125_BOL_signed.jpg'")
        sys.exit(1)
    
    jpg_key = sys.argv[1]
    bucket = "greencandle"
    
    print(f"🔄 Converting {jpg_key} to PDF...")
    try:
        bucket, pdf_key = convert_bol_image_to_pdf(bucket, jpg_key)
        print(f"✅ Success! PDF created at: {pdf_key}")
        print(f"   Original JPG: {jpg_key}")
        print(f"   New PDF: {pdf_key}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
