"""
Email service for sending negotiation emails and receiving broker replies.
Uses mxroute SMTP for sending, and can parse incoming replies to update negotiation status.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from typing import Optional, Dict
from datetime import datetime

# mxroute SMTP Configuration (load from .env)
MXROUTE_SMTP_HOST = os.getenv("MXROUTE_SMTP_HOST", "mail.mxroute.com")
MXROUTE_SMTP_PORT = int(os.getenv("MXROUTE_SMTP_PORT", "587"))
MXROUTE_SMTP_USER = os.getenv("MXROUTE_SMTP_USER")  # e.g., "noreply@greencandledispatch.com"
MXROUTE_SMTP_PASSWORD = os.getenv("MXROUTE_SMTP_PASSWORD")
MXROUTE_FROM_EMAIL = os.getenv("MXROUTE_FROM_EMAIL", MXROUTE_SMTP_USER or "noreply@greencandledispatch.com")


def send_negotiation_email(
    to_email: str,
    subject: str,
    body: str,
    load_id: str,
    negotiation_id: int
) -> Dict[str, any]:
    """
    Send a negotiation email to a broker via mxroute SMTP.
    Returns status dict with success/error info.
    """
    if not MXROUTE_SMTP_USER or not MXROUTE_SMTP_PASSWORD:
        return {
            "status": "error",
            "message": "mxroute SMTP not configured. Set MXROUTE_SMTP_USER and MXROUTE_SMTP_PASSWORD in .env"
        }
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = MXROUTE_FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg['Reply-To'] = MXROUTE_FROM_EMAIL  # Replies come back to your inbox
        
        # Add body with tracking headers (for reply parsing)
        body_with_tracking = f"""
{body}

---
Load ID: {load_id}
Negotiation ID: {negotiation_id}
"""
        msg.attach(MIMEText(body_with_tracking, 'plain'))
        
        # Add custom headers for tracking (some email providers support this)
        msg['X-Load-ID'] = load_id
        msg['X-Negotiation-ID'] = str(negotiation_id)
        
        # Send via mxroute SMTP
        with smtplib.SMTP(MXROUTE_SMTP_HOST, MXROUTE_SMTP_PORT) as server:
            server.starttls()
            server.login(MXROUTE_SMTP_USER, MXROUTE_SMTP_PASSWORD)
            server.send_message(msg)
        
        return {
            "status": "success",
            "message": f"Email sent to {to_email}",
            "sent_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to send email: {str(e)}"
        }


def parse_broker_reply(email_body: str, email_subject: str) -> Dict[str, any]:
    """
    Parse an incoming broker reply email to extract:
    - Is it a positive response? (keywords: "yes", "accepted", "confirmed", rate numbers)
    - Is it a rejection? (keywords: "no", "unavailable", "taken")
    - What rate did they offer? (extract dollar amounts)
    
    Returns dict with: status_hint, extracted_rate, confidence
    """
    body_lower = email_body.lower()
    subject_lower = email_subject.lower()
    combined = f"{subject_lower} {body_lower}"
    
    # Extract dollar amounts
    import re
    dollar_amounts = re.findall(r'\$[\d,]+\.?\d*', email_body)
    extracted_rate = None
    if dollar_amounts:
        # Take the largest amount (likely the rate)
        amounts = [float(a.replace('$', '').replace(',', '')) for a in dollar_amounts]
        extracted_rate = max(amounts) if amounts else None
    
    # Positive indicators
    positive_keywords = ['yes', 'accepted', 'confirmed', 'approved', 'booked', 'available', 'interested']
    is_positive = any(keyword in combined for keyword in positive_keywords)
    
    # Negative indicators
    negative_keywords = ['no', 'unavailable', 'taken', 'booked elsewhere', 'not available', 'declined']
    is_negative = any(keyword in combined for keyword in negative_keywords)
    
    # Determine status hint
    # SAFETY: Positive replies with rates go to PENDING_APPROVAL, not WON
    # Driver must confirm to avoid AI accepting bad loads
    if is_positive and extracted_rate:
        status_hint = "pending_approval"  # Driver needs to confirm
        confidence = "high"
    elif is_positive:
        status_hint = "replied"
        confidence = "medium"
    elif is_negative:
        status_hint = "lost"
        confidence = "high"
    else:
        status_hint = "replied"
        confidence = "low"
    
    return {
        "status_hint": status_hint,
        "extracted_rate": extracted_rate,
        "confidence": confidence,
        "has_rate": extracted_rate is not None,
        "is_positive": is_positive,
        "is_negative": is_negative
    }
