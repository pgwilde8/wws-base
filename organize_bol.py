from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from PyPDF2 import PdfMerger
import os

# Fake DB data (replace with real in app)
load_id = "TEST-LOAD-001"
driver_name = "Test Driver"
mc_number = "TEST123"
date = "2026-02-17"

raw_pdf = "raw_bol_test.pdf"  # downloaded file
cover_pdf = "cover_page.pdf"
final_pdf = "organized_bol_test.pdf"

# Create cover page
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

# Merge cover + raw BOL
merger = PdfMerger()
merger.append(cover_pdf)
merger.append(raw_pdf)
merger.write(final_pdf)
merger.close()

# Cleanup
os.remove(cover_pdf)

print(f"Success! Created: {final_pdf}")
print(f"Size: {os.path.getsize(final_pdf) / 1024:.1f} KB")