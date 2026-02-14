import sys
import argparse
import re
from pathlib import Path

# Load .env before app imports so DATABASE_URL is set
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

from sqlalchemy import text
from app.core.deps import SessionLocal
from scripts.attach_packet_emails import promote_best


def clean_email_base(email: str) -> str:
    """
    Strip plus-addressing from the local part so we store the canonical "base" address.
    e.g. availableloads+trucksmarter@triplettransport.com -> availableloads@triplettransport.com
    Brokers deliver to the same inbox; the +tag is only for their sorting. We keep primary_email
    clean so dispatch can add the right tag (e.g. +dat, +trucksmarter) based on load source.
    """
    e = email.strip().lower()
    if "@" not in e:
        return e
    local, domain = e.rsplit("@", 1)
    if "+" in local:
        local = local.split("+", 1)[0]
    return f"{local}@{domain}"


def clean_phone(phone: str | None) -> str | None:
    """Clean phone number: remove spaces, dashes, parentheses, keep + and digits."""
    if not phone:
        return None
    import re
    # Keep digits, +, and spaces (for formatting)
    cleaned = re.sub(r'[^\d\+\s\(\)\-]', '', phone.strip())
    return cleaned if cleaned else None


def add_contact(mc, email=None, phone=None, website=None, dot=None, call_to_book=False):
    """
    Add broker contact info: email, phone, website, DOT (all optional, but at least one required).
    Email is cleaned (removes +tags) and stored in broker_emails + promoted to primary_email.
    Phone, website, DOT are updated on the broker record.
    If call_to_book=True, sets preferred_contact_method='call_to_book' (broker prefers phone calls).
    """
    if not any([email, phone, website, dot]):
        raise ValueError("At least one of --email, --phone, --website, or --dot must be provided")
    
    # Store the clean base (no +tag) so primary_email works for any board; dispatch can add +dat/+trucksmarter by load source
    canonical = None
    if email:
        canonical = clean_email_base(email)
    
    cleaned_phone = clean_phone(phone)
    cleaned_website = website.strip() if website else None
    # Remove http:// or https:// prefix if present (store clean domain)
    if cleaned_website:
        cleaned_website = cleaned_website.replace("http://", "").replace("https://", "").replace("www.", "").strip()
    
    db = SessionLocal()
    try:
        # 0. Ensure broker row exists (broker_emails has FK to brokers)
        db.execute(
            text(
                "INSERT INTO webwise.brokers (mc_number, source) VALUES (:mc, 'manual') "
                "ON CONFLICT (mc_number) DO NOTHING"
            ),
            {"mc": mc},
        )
        
        # 1. Insert email into the "Memory" table if provided
        if canonical:
            db.execute(
                text(
                    "INSERT INTO webwise.broker_emails (mc_number, email, source, confidence) "
                    "VALUES (:mc, :email, 'manual', :score) "
                    "ON CONFLICT (mc_number, email) DO UPDATE SET confidence = :score"
                ),
                {"mc": mc, "email": canonical, "score": 0.90}  # Manual entries get high confidence
            )
        
        # 2. Update broker record with phone, website, DOT (if provided)
        update_fields = []
        update_params = {"mc": mc}
        
        phone_field_used = None  # Track which field we're updating
        if cleaned_phone:
            # Check if broker already has a primary_phone
            existing_check = db.execute(
                text("SELECT primary_phone, secondary_phone FROM webwise.brokers WHERE mc_number = :mc"),
                {"mc": mc}
            ).fetchone()
            
            existing_primary = existing_check[0] if existing_check else None
            existing_secondary = existing_check[1] if existing_check and len(existing_check) > 1 else None
            
            # Normalize for comparison (remove formatting)
            normalize_phone = lambda p: re.sub(r'[^\d]', '', p) if p else ""
            new_phone_normalized = normalize_phone(cleaned_phone)
            existing_primary_normalized = normalize_phone(existing_primary) if existing_primary else ""
            existing_secondary_normalized = normalize_phone(existing_secondary) if existing_secondary else ""
            
            # If primary_phone exists and is different, store new phone as secondary_phone
            if existing_primary and new_phone_normalized != existing_primary_normalized:
                if not existing_secondary or new_phone_normalized != existing_secondary_normalized:
                    update_fields.append("secondary_phone = :phone")
                    update_params["phone"] = cleaned_phone
                    phone_field_used = "secondary_phone"
                    print(f"   Storing as secondary_phone (primary_phone already set: {existing_primary})")
                else:
                    print(f"   Phone already exists as secondary_phone, skipping")
            else:
                # No primary_phone or same phone - update primary_phone
                update_fields.append("primary_phone = :phone")
                update_params["phone"] = cleaned_phone
                phone_field_used = "primary_phone"
        
        if cleaned_website:
            update_fields.append("website = :website")
            update_params["website"] = cleaned_website
        
        if dot:
            update_fields.append("dot_number = :dot")
            update_params["dot"] = str(dot).strip()
        
        # Set preferred contact method
        if call_to_book:
            # Explicitly marked as "call to book" - always use phone
            update_fields.append("preferred_contact_method = 'call_to_book'")
        elif cleaned_phone and not canonical:
            # Phone but no email - auto-set to call_to_book
            update_fields.append("preferred_contact_method = 'call_to_book'")
        elif canonical and not call_to_book:
            # Has email and not explicitly call_to_book - prefer email
            update_fields.append("preferred_contact_method = 'email'")
        
        if update_fields:
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            result = db.execute(
                text(f"UPDATE webwise.brokers SET {', '.join(update_fields)} WHERE mc_number = :mc"),
                update_params
            )
            rows_updated = result.rowcount
            if rows_updated == 0:
                print(f"⚠️  Warning: No rows updated for MC {mc}. Broker may not exist.")
            else:
                print(f"   Updated {rows_updated} row(s) in brokers table")
        
        # 3. Trigger the "Promotion" logic to update the main brokers table (only if email was provided)
        if canonical:
            raw_conn = db.connection().connection
            promote_best(raw_conn, mc)
        
        db.commit()
        
        # Success message
        parts = []
        if canonical:
            if canonical != email.strip().lower():
                parts.append(f"email: {canonical} (from {email})")
            else:
                parts.append(f"email: {email}")
        if cleaned_phone and phone_field_used:
            parts.append(f"{phone_field_used}: {cleaned_phone}")
        if cleaned_website:
            parts.append(f"website: {cleaned_website}")
        if dot:
            parts.append(f"DOT: {dot}")
        
        print(f"✅ Successfully added for MC {mc}: {', '.join(parts)}")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Usage: 
    # python3 app/scripts/add_broker_contact.py --mc 567093 --email nematches@ntgfreight.com
    # python3 app/scripts/add_broker_contact.py --mc 567093 --phone "+1 (267) 930-1849" --website ntgfreight.com --dot 2236769
    # python3 app/scripts/add_broker_contact.py --mc 945637 --phone "+1 (602) 755-3668" --call-to-book
    parser = argparse.ArgumentParser(description="Add broker contact info (at least one of email/phone/website/DOT required)")
    parser.add_argument("--mc", required=True, help="MC number")
    parser.add_argument("--email", help="Broker email (tags like +trucksmarter will be stripped)")
    parser.add_argument("--phone", help="Phone number (will be cleaned)")
    parser.add_argument("--website", help="Website URL (http/https/www will be stripped)")
    parser.add_argument("--dot", help="DOT number")
    parser.add_argument("--call-to-book", action="store_true", help="Mark broker as preferring phone calls (call to book)")
    args = parser.parse_args()
    add_contact(args.mc, email=args.email, phone=args.phone, website=args.website, dot=args.dot, call_to_book=args.call_to_book)