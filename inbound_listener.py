"""
Inbound email listener: syncs replies from dispatch@gcdloads.com to webwise.messages.
Uses Message-ID for deduplication - never saves the same email twice.
"""
import hashlib
import imaplib
import email
import time
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from sqlalchemy import create_engine, text

# Lazy import for Auto-Pilot (app must be on path when listener runs from project root)
def _autopilot_available():
    try:
        from app.services.autopilot import process_autopilot_logic
        from app.services.ai_logic import parse_sender_email
        return process_autopilot_logic, parse_sender_email
    except ImportError:
        return None, None

# Config from .env
HOST = os.getenv("EMAIL_HOST", "fusion.mxrouting.net")
USER = os.getenv("EMAIL_USER", "dispatch@gcdloads.com")
PASS = os.getenv("EMAIL_PASS")
DB_URL = os.getenv("DATABASE_URL", "postgresql://wws-admin:WwsAdmin2026%21@localhost/wws_dispatch_db")
engine = create_engine(DB_URL)


def check_for_rate_con(subject: str, body: str) -> bool:
    """Detect Rate Confirmation keywords in email subject or body."""
    keywords = ["rate confirmation", "ratecon", "rate con", "rc attached", "signed copy", "rate confirmation attached"]
    content = ((subject or "") + " " + (body or ""))[:2000].lower()
    return any(k in content for k in keywords)


def _message_id_or_fallback(msg, sender: str, subject: str, body: str) -> str:
    """Use Message-ID header, or generate fallback for deduplication."""
    msg_id = msg.get("Message-ID")
    if msg_id and msg_id.strip():
        return msg_id.strip()
    # Fallback: hash of sender+subject+body so same email = same id
    raw = f"{sender}|{subject}|{body[:500]}"
    return f"gen-{hashlib.sha256(raw.encode()).hexdigest()[:40]}"


def save_to_db(sender: str, recipient: str, subject: str, body: str, msg_id: str) -> tuple:
    """
    Save message to DB. Returns (rowcount, load_id, sender, body, recipient) for Auto-Pilot.
    """
    try:
        tag_part = recipient.split("@")[0] if recipient and "@" in recipient else ""
        load_id = tag_part.split("+")[1] if "+" in tag_part else "GENERAL"

        query = text("""
            INSERT INTO webwise.messages (sender_email, recipient_tagged, subject, body_text, load_id, message_id)
            VALUES (:sender, :recipient, :subject, :body, :load_id, :msg_id)
            ON CONFLICT (message_id) DO NOTHING
        """)

        with engine.begin() as conn:
            result = conn.execute(
                query,
                {
                    "sender": sender,
                    "recipient": recipient,
                    "subject": subject or "",
                    "body": body or "",
                    "load_id": load_id,
                    "msg_id": msg_id,
                },
            )
            rowcount = result.rowcount
            if rowcount > 0:
                print(f"✅ NEW: Saved Load {load_id} from {sender}")
            else:
                print(f"⏭️ SKIPPED: Already have message {msg_id[:50]}...")

        return (rowcount, load_id, sender, body or "", recipient)

    except Exception as e:
        print(f"❌ DB Save Error: {e}")
        return (0, "", sender, body or "", recipient)


def _extract_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(errors="ignore")
        except Exception:
            pass
    return body


def listen_for_replies() -> None:
    print("👂 Deduplicating Listener Active... (Ctrl+C to stop)")
    while True:
        try:
            if not PASS:
                print("❌ EMAIL_PASS not set in .env")
                time.sleep(30)
                continue

            mail = imaplib.IMAP4_SSL(HOST)
            mail.login(USER, PASS)
            mail.select("inbox")

            _, messages = mail.search(None, "ALL")
            if not messages[0]:
                mail.logout()
                time.sleep(15)
                continue

            for num in messages[0].split():
                try:
                    _, data = mail.fetch(num, "(RFC822)")
                    msg = email.message_from_bytes(data[0][1])
                    sender = msg.get("From") or ""
                    recipient = msg.get("To") or ""
                    subject = msg.get("Subject") or ""
                    body = _extract_body(msg)
                    msg_id = _message_id_or_fallback(msg, sender, subject, body)
                    rowcount, load_id, _s, _b, _r = save_to_db(sender, recipient, subject, body, msg_id)

                    # Auto-Pilot: if new message, check if this load has autopilot enabled
                    if rowcount > 0 and load_id and load_id != "GENERAL":
                        tag_part = recipient.split("@")[0] if recipient and "@" in recipient else ""
                        driver_name = (tag_part.split("+")[0] if "+" in tag_part else "").strip()

                        # Rate Con detector: deduct 3.0 $CANDLE on success (consumption-based)
                        if driver_name and check_for_rate_con(subject, body):
                            try:
                                from app.services.ledger import deduct_success_fee, AUTOPILOT_COST
                                with engine.begin() as conn:
                                    rc_row = conn.execute(
                                        text("""
                                            SELECT aps.trucker_id FROM webwise.autopilot_settings aps
                                            JOIN webwise.trucker_profiles tp ON aps.trucker_id = tp.id
                                            WHERE LOWER(TRIM(tp.display_name)) = :dn
                                              AND aps.load_id = :load_id
                                              AND aps.is_autopilot = true
                                        """),
                                        {"dn": driver_name.lower(), "load_id": load_id},
                                    ).first()
                                if rc_row:
                                    tid = rc_row[0]
                                    if deduct_success_fee(engine, tid, load_id):
                                        with engine.begin() as conn2:
                                            conn2.execute(
                                                text("""
                                                    INSERT INTO webwise.notifications (trucker_id, message, notif_type, is_read)
                                                    VALUES (:tid, :msg, 'AUTOPILOT_SUCCESS', false)
                                                """),
                                                {"tid": tid, "msg": f"🏆 LOAD BOOKED! Rate confirmation received for Load #{load_id}. {AUTOPILOT_COST} $CANDLE utilized for this mission."},
                                            )
                                        print(f"✅ Rate Con detected → deducted {AUTOPILOT_COST} $CANDLE for Load {load_id}")
                            except Exception as rc_err:
                                print(f"⚠️ Rate Con deduction error: {rc_err}")

                        # Auto-Pilot: process broker reply (negotiate/counter logic)
                        process_fn, parse_fn = _autopilot_available()
                        if process_fn and parse_fn:
                            try:
                                broker_email = parse_fn(sender)
                                if driver_name and broker_email:
                                    with engine.begin() as conn:
                                        row = conn.execute(
                                            text("""
                                                SELECT aps.floor_price, aps.target_price
                                                FROM webwise.autopilot_settings aps
                                                JOIN webwise.trucker_profiles tp ON aps.trucker_id = tp.id
                                                WHERE LOWER(TRIM(tp.display_name)) = :dn
                                                AND aps.load_id = :load_id
                                                AND aps.is_autopilot = true
                                            """),
                                            {"dn": driver_name.lower(), "load_id": load_id},
                                        ).first()
                                    if row:
                                        status = process_fn(
                                            engine, load_id, body, broker_email,
                                            driver_name, float(row[0]), float(row[1]),
                                        )
                                        print(f"🤖 Auto-Pilot Action: {status}")
                            except Exception as ap_err:
                                print(f"⚠️ Auto-Pilot Error: {ap_err}")
                except Exception as e:
                    print(f"❌ Error processing message: {e}")

            mail.logout()
        except Exception as e:
            print(f"Sync Error: {e}")
        time.sleep(15)


if __name__ == "__main__":
    listen_for_replies()
