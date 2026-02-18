"""
Invoice Generation Service - Creates professional invoices from driver to broker.
"""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from datetime import datetime
from typing import Dict, Optional


def generate_invoice_pdf(
    driver_name: str,
    driver_mc: str,
    driver_address: Optional[str],
    broker_name: str,
    broker_mc: str,
    broker_address: Optional[str],
    load_id: str,
    origin: str,
    destination: str,
    rate: float,
    invoice_date: Optional[str] = None,
    payment_terms: str = "Net 30",
) -> bytes:
    """
    Generate professional invoice PDF from driver to broker.
    
    Returns PDF bytes ready to save or attach.
    """
    if not invoice_date:
        invoice_date = datetime.now().strftime("%B %d, %Y")
    
    # Create PDF in memory
    from io import BytesIO
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 24)
    c.setFillColorRGB(0.2, 0.8, 0.4)  # Green
    c.drawString(1*inch, height - 1*inch, "INVOICE")
    
    # Invoice details (top right)
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.7, 0.7, 0.7)
    c.drawRightString(width - 1*inch, height - 1*inch, f"Invoice Date: {invoice_date}")
    c.drawRightString(width - 1*inch, height - 1.2*inch, f"Invoice #: {load_id}")
    
    # From (Driver) - Left side
    y_pos = height - 2*inch
    c.setFont("Helvetica-Bold", 12)
    c.setFillColorRGB(1, 1, 1)
    c.drawString(1*inch, y_pos, "FROM:")
    y_pos -= 0.3*inch
    c.setFont("Helvetica", 11)
    c.drawString(1*inch, y_pos, driver_name)
    y_pos -= 0.2*inch
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, y_pos, f"MC#: {driver_mc}")
    if driver_address:
        y_pos -= 0.2*inch
        c.drawString(1*inch, y_pos, driver_address)
    
    # To (Broker) - Right side
    y_pos = height - 2*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - 1*inch, y_pos, "TO:")
    y_pos -= 0.3*inch
    c.setFont("Helvetica", 11)
    c.drawRightString(width - 1*inch, y_pos, broker_name)
    y_pos -= 0.2*inch
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 1*inch, y_pos, f"MC#: {broker_mc}")
    if broker_address:
        y_pos -= 0.2*inch
        c.drawRightString(width - 1*inch, y_pos, broker_address)
    
    # Line separator
    y_pos = height - 3.5*inch
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.line(1*inch, y_pos, width - 1*inch, y_pos)
    
    # Load details table
    y_pos -= 0.5*inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1*inch, y_pos, "Description")
    c.drawRightString(width - 1*inch, y_pos, "Amount")
    
    y_pos -= 0.3*inch
    c.setStrokeColorRGB(0.5, 0.5, 0.5)
    c.line(1*inch, y_pos, width - 1*inch, y_pos)
    
    y_pos -= 0.3*inch
    c.setFont("Helvetica", 10)
    description = f"Freight services - {origin} to {destination}"
    c.drawString(1*inch, y_pos, description)
    c.drawRightString(width - 1*inch, y_pos, f"${rate:,.2f}")
    
    # Total
    y_pos -= 0.5*inch
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.line(1*inch, y_pos, width - 1*inch, y_pos)
    y_pos -= 0.3*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y_pos, "Total Due:")
    c.drawRightString(width - 1*inch, y_pos, f"${rate:,.2f}")
    
    # Payment terms
    y_pos -= 0.8*inch
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawString(1*inch, y_pos, f"Payment Terms: {payment_terms}")
    y_pos -= 0.2*inch
    c.drawString(1*inch, y_pos, f"Load ID: {load_id}")
    
    # Footer
    y_pos = 0.5*inch
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(1*inch, y_pos, "Thank you for your business!")
    c.drawRightString(width - 1*inch, y_pos, "Green Candle Dispatch")
    
    c.save()
    buffer.seek(0)
    return buffer.read()
