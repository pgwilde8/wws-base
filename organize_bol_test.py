from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from PyPDF2 import PdfMerger  # pip install PyPDF2
import os
import sys

# Config (fake for test)
load_id = "TEST-LOAD-001"
driver_name = "Test Driver"
mc_number = "TEST123"
date = "2026-02-17"

# Input raw PDF (can be passed as command-line arg)
raw_pdf = sys.argv[1] if len(sys.argv) > 1 else "raw_bol_test.pdf"
cover_pdf = "cover_page.pdf"
final_pdf = "organized_bol_test.pdf"

# Check if raw PDF exists
if not os.path.exists(raw_pdf):
    print(f"❌ Error: Raw BOL file '{raw_pdf}' not found.")
    print(f"   Usage: python organize_bol_test.py [path/to/raw_bol.pdf]")
    print(f"   Or place 'raw_bol_test.pdf' in the current directory.")
    sys.exit(1)

# Step 1: Create cover page PDF
print(f"📄 Creating cover page...")
c = canvas.Canvas(cover_pdf, pagesize=letter)
c.setFont("Helvetica-Bold", 16)
c.drawString(1*inch, 10*inch, "Green Candle Dispatch – Bill of Lading")
c.setFont("Helvetica", 12)
c.drawString(1*inch, 9.5*inch, f"Load ID: {load_id}")
c.drawString(1*inch, 9*inch, f"Driver: {driver_name}")
c.drawString(1*inch, 8.5*inch, f"MC Number: {mc_number}")
c.drawString(1*inch, 8*inch, f"Date: {date}")
c.drawString(1*inch, 7*inch, "Submitted to Century Finance for Funding")
c.save()

# Step 2: Merge cover + raw BOL
print(f"🔗 Merging cover page with '{raw_pdf}'...")
merger = PdfMerger()
merger.append(cover_pdf)
merger.append(raw_pdf)
merger.write(final_pdf)
merger.close()

# Cleanup temp
os.remove(cover_pdf)

print(f"✅ Success! Created: {final_pdf}")
print(f"   Size: {os.path.getsize(final_pdf) / 1024:.1f} KB")