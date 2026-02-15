import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration from .env
MXROUTE_SMTP_HOST = os.getenv("MXROUTE_SMTP_HOST", "fusion.mxrouting.net")
MXROUTE_SMTP_PORT = int(os.getenv("MXROUTE_SMTP_PORT", "465"))
MXROUTE_SMTP_USER = os.getenv("MXROUTE_SMTP_USER")
MXROUTE_SMTP_PASSWORD = os.getenv("MXROUTE_SMTP_PASSWORD")
EMAIL_DOMAIN = os.getenv("EMAIL_DOMAIN", "gcdloads.com")

def add_load_board_tag(email: str, load_source: Optional[str] = None) -> str:
    """Adds plus-addressing tag to broker email (e.g., broker+trucksmarter@domain.com)"""
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

def send_negotiation_email(
    to_email: str,
    subject: str,
    body: str,
    load_id: str,
    negotiation_id: int,
    driver_name: str,
    load_source: Optional[str] = None
) -> Dict[str, any]:
    """Sends tagged email from [driver]+[load_id]@gcdloads.com"""
    if not MXROUTE_SMTP_USER or not MXROUTE_SMTP_PASSWORD:
        return {"status": "error", "message": "SMTP credentials missing in .env"}

    try:
        sender_email = f"{driver_name.lower()}+{load_id}@{EMAIL_DOMAIN}"
        tagged_broker_email = add_load_board_tag(to_email, load_source)

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = tagged_broker_email
        msg['Subject'] = subject
        msg['Reply-To'] = sender_email 

        full_body = f"{body}\n\n---\nRef Load: {load_id}\nNeg ID: {negotiation_id}"
        msg.attach(MIMEText(full_body, 'plain'))

        # Use SSL for Fusion on Port 465
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