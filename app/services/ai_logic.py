"""
AI logic for parsing broker replies and extracting bid details.
"""
import re
from typing import Any


def extract_bid_details(email_body: str) -> dict[str, Any]:
    """
    Parse broker email body to extract offer amount and readiness signals.
    Returns: {extracted_offer, broker_ready}
    """
    if not email_body or not isinstance(email_body, str):
        return {"extracted_offer": None, "broker_ready": False}

    body_lower = email_body.lower()

    # Look for dollar amounts: $1,200 or 1200 or $1200.00
    amounts = re.findall(r"\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", email_body)
    extracted_offer = None
    if amounts:
        try:
            nums = [float(a.replace(",", "")) for a in amounts if float(a.replace(",", "")) < 100000]
            extracted_offer = max(nums) if nums else None
        except (ValueError, TypeError):
            pass

    # Check for "ready to book" type phrases
    ready_phrases = [
        "ready", "book it", "rate con", "send mc", "confirm", "locked",
        "you got it", "accepted", "done deal", "let's go", "approved",
    ]
    broker_ready = any(phrase in body_lower for phrase in ready_phrases)

    return {"extracted_offer": extracted_offer, "broker_ready": broker_ready}


def parse_sender_email(raw_from: str) -> str:
    """
    Extract clean email from 'Name <email@domain.com>' or 'email@domain.com'.
    """
    if not raw_from or not isinstance(raw_from, str):
        return ""
    raw = raw_from.strip()
    # Match angle-bracket format
    match = re.search(r"<([^>]+@[^>]+)>", raw)
    if match:
        return match.group(1).strip().lower()
    # Plain email
    if "@" in raw:
        return raw.lower()
    return ""
