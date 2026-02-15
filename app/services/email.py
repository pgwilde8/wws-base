import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# One source of truth for all email variables
MX_HOST = os.getenv("MXROUTE_SMTP_HOST", "fusion.mxrouting.net")
MX_PORT = int(os.getenv("MXROUTE_SMTP_PORT", "465"))
MX_USER = os.getenv("MXROUTE_SMTP_USER")
MX_PASS = os.getenv("MXROUTE_SMTP_PASSWORD")
EMAIL_DOMAIN = os.getenv("EMAIL_DOMAIN", "gcdloads.com")

# Alias the variables if you need the older names for compatibility
MXROUTE_SMTP_HOST = MX_HOST
MXROUTE_SMTP_PORT = MX_PORT
MXROUTE_SMTP_USER = MX_USER
MXROUTE_SMTP_PASSWORD = MX_PASS

def send_negotiation_email(
    to_email: str,
    subject: str,
    body: str,
    load_id: str,
    negotiation_id: int,
    driver_name: str, # Added to identify the sender
    load_source: Optional[str] = None
) -> Dict[str, any]:
    """
    Sends email from [driver]+[load_id]@gcdloads.com via Fusion SMTP.
    """
    if not MXROUTE_SMTP_USER or not MXROUTE_SMTP_PASSWORD:
        return {"status": "error", "message": "SMTP credentials missing in .env"}

    try:
        # 1. Create the Dynamic Sender (e.g., seth+L123@gcdloads.com)
        # This is the "Magic" that makes replies route to your DB correctly
        sender_email = f"{driver_name.lower()}+{load_id}@{EMAIL_DOMAIN}"
        
        # 2. Add load board tag to broker email (e.g., broker+trucksmarter@domain.com)
        tagged_broker_email = add_load_board_tag(to_email, load_source)

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = tagged_broker_email
        msg['Subject'] = subject
        # Critical: Reply-To ensures even if they hit "Reply", it goes to the tagged address
        msg['Reply-To'] = sender_email 

        # Body with context for the broker
        full_body = f"{body}\n\n---\nRef: {load_id}"
        msg.attach(MIMEText(full_body, 'plain'))

        # 3. Connect via SSL to Fusion
        with smtplib.SMTP_SSL(MXROUTE_SMTP_HOST, MXROUTE_SMTP_PORT) as server:
            server.login(MXROUTE_SMTP_USER, MXROUTE_SMTP_PASSWORD)
            server.send_message(msg)

        return {
            "status": "success",
            "sent_from": sender_email,
            "sent_to": tagged_broker_email,
            "sent_at": datetime.now().isoformat()
        }

    except Exception as e:
        return {"status": "error", "message": f"SMTP Error: {str(e)}"}


def add_load_board_tag(email: str, load_source: Optional[str] = None) -> str:
    """Add plus-addressing tag to broker email (e.g. broker+trucksmarter@domain.com)."""
    if not load_source:
        if "+" in email and "@" in email:
            local, domain = email.rsplit("@", 1)
            base_local = local.split("+", 1)[0]
            return f"{base_local}@{domain}"
        return email
    tag = re.sub(r"[^a-z0-9]", "", load_source.lower())
    if "+" in email and "@" in email:
        local, domain = email.rsplit("@", 1)
        base_local = local.split("+", 1)[0]
    elif "@" in email:
        base_local, domain = email.rsplit("@", 1)
    else:
        return email
    return f"{base_local}+{tag}@{domain}"


def parse_broker_reply(email_body: str, email_subject: str = "") -> Dict:
    """
    Parse broker reply to determine status hint (replied/won/lost) and optional extracted rate.
    """
    text = (email_body or "").lower() + " " + (email_subject or "").lower()
    status_hint = "replied"
    extracted_rate = None

    # Look for won/yes/accept indicators
    if any(phrase in text for phrase in ["accepted", "yes we can", "book it", "confirmed", "you got it", "$"]):
        status_hint = "won"
        # Try to extract rate: $1,234 or $1234.56
        rate_match = re.search(r'\$\s*([\d,]+(?:\.\d{2})?)', text)
        if rate_match:
            try:
                extracted_rate = float(rate_match.group(1).replace(",", ""))
            except (ValueError, TypeError):
                pass

    # Look for lost/no indicators
    if any(phrase in text for phrase in ["no thanks", "already covered", "filled", "sorry we", "passed", "can't", "cannot"]):
        status_hint = "lost"

    return {"status_hint": status_hint, "extracted_rate": extracted_rate}