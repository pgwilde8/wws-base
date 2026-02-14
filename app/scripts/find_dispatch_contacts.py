"""
Find dispatch emails and phone numbers for brokers using company name, MC, and DOT.

Uses multiple strategies:
1. Search DuckDuckGo for "{company name} dispatch email" and "{company name} dispatch phone"
2. Search for "{company name} MC {mc_number} contact"
3. If website exists, scrape it for contact info
4. Extract emails and phone numbers from search results

Usage:
  PYTHONPATH=. python3 app/scripts/find_dispatch_contacts.py
  PYTHONPATH=. python3 app/scripts/find_dispatch_contacts.py --limit 100
  PYTHONPATH=. python3 app/scripts/find_dispatch_contacts.py --mc 567093
"""
import argparse
import re
import time
from pathlib import Path

# Load .env before app imports
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        HAS_DDGS = True
    except ImportError:
        HAS_DDGS = False
        print("⚠️  'ddgs' not installed. Install with: pip install ddgs")
        print("   Falling back to HTML scraping (less reliable)")

import requests
from sqlalchemy import text
from app.core.deps import SessionLocal
from scripts.attach_packet_emails import score_email, promote_best

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})')


def clean_email_base(email: str) -> str:
    """Strip plus-addressing from email (e.g. loads+trucksmarter@example.com -> loads@example.com)."""
    e = email.strip().lower()
    if "@" not in e:
        return e
    local, domain = e.rsplit("@", 1)
    if "+" in local:
        local = local.split("+", 1)[0]
    return f"{local}@{domain}"


def clean_phone(phone: str) -> str | None:
    """Clean and normalize phone number."""
    if not phone:
        return None
    # Extract digits and + sign
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    # Add +1 if it's a 10-digit number without country code
    if len(cleaned) == 10:
        cleaned = f"+1{cleaned}"
    elif not cleaned.startswith("+") and len(cleaned) == 11 and cleaned.startswith("1"):
        cleaned = f"+{cleaned}"
    return cleaned if cleaned else None


def extract_emails_from_text(text: str) -> set[str]:
    """Extract unique emails from text, filtering out common non-dispatch addresses."""
    emails = set()
    for match in EMAIL_RE.finditer(text):
        email = match.group(0).lower().strip()
        # Skip image URLs, data URIs, etc.
        if email.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
            continue
        # Skip common non-dispatch emails
        skip_patterns = [
            "noreply", "no-reply", "donotreply", "privacy", "legal",
            "abuse", "postmaster", "webmaster", "hostmaster", "example.com"
        ]
        if any(pattern in email for pattern in skip_patterns):
            continue
        emails.add(clean_email_base(email))
    return emails


def extract_phones_from_text(text: str) -> set[str]:
    """Extract phone numbers from text."""
    phones = set()
    for match in PHONE_RE.finditer(text):
        # Reconstruct phone number
        parts = match.groups()
        if parts[1] and parts[2] and parts[3]:  # area code, exchange, number
            country = parts[0] if parts[0] else "+1"
            if not country.startswith("+"):
                country = "+1"
            phone = f"{country}{parts[1]}{parts[2]}{parts[3]}"
            cleaned = clean_phone(phone)
            if cleaned:
                phones.add(cleaned)
    return phones


def search_dispatch_contacts(company_name: str, mc_number: str | None = None, debug: bool = False) -> tuple[set[str], set[str]]:
    """
    Search for dispatch emails and phone numbers.
    Returns (emails_set, phones_set).
    """
    emails = set()
    phones = set()
    
    # Build search queries
    queries = [
        f'"{company_name}" dispatch email',
        f'"{company_name}" dispatch phone',
        f'"{company_name}" carrier email',
        f'"{company_name}" carrier phone',
    ]
    
    if mc_number:
        queries.extend([
            f'"{company_name}" MC {mc_number} contact',
            f'"{company_name}" MC {mc_number} email',
            f'"{company_name}" MC {mc_number} phone',
        ])
    
    if not HAS_DDGS:
        if debug:
            print("      ⚠️  ddgs library not available, skipping search")
        return emails, phones
    
    try:
        with DDGS() as ddgs:
            for query in queries:
                if debug:
                    print(f"      Searching: {query}")
                
                try:
                    results = list(ddgs.text(query, max_results=5))
                    if debug:
                        print(f"         Found {len(results)} results")
                    
                    for result in results:
                        # Extract from title and snippet
                        text_content = f"{result.get('title', '')} {result.get('body', '')}"
                        
                        found_emails = extract_emails_from_text(text_content)
                        found_phones = extract_phones_from_text(text_content)
                        
                        emails.update(found_emails)
                        phones.update(found_phones)
                        
                        if debug and (found_emails or found_phones):
                            print(f"         Found: {list(found_emails)[:2]} {list(found_phones)[:2]}")
                        
                        # Also try fetching the URL to scrape more content
                        url = result.get("href", "")
                        if url and (len(emails) < 3 or len(phones) < 2):  # Only if we need more
                            try:
                                headers = {
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                                }
                                response = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
                                if response.status_code == 200:
                                    page_emails = extract_emails_from_text(response.text)
                                    page_phones = extract_phones_from_text(response.text)
                                    emails.update(page_emails)
                                    phones.update(page_phones)
                                    if debug and (page_emails or page_phones):
                                        print(f"         Scraped from {url[:50]}: {list(page_emails)[:2]} {list(page_phones)[:2]}")
                            except Exception as e:
                                if debug:
                                    print(f"         ⚠️  Could not fetch {url[:50]}: {e}")
                    
                    # Rate limit between queries
                    time.sleep(1)
                    
                except Exception as e:
                    if debug:
                        print(f"      ⚠️  Search error for '{query}': {e}")
                    continue
                    
    except Exception as e:
        if debug:
            print(f"      ⚠️  DDGS error: {e}")
    
    return emails, phones


def scrape_website_for_contacts(website: str, debug: bool = False) -> tuple[set[str], set[str]]:
    """Scrape a website for emails and phone numbers."""
    emails = set()
    phones = set()
    
    if not website:
        return emails, phones
    
    if not website.startswith(("http://", "https://")):
        website = f"https://{website}"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(website, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        html = response.text
        emails = extract_emails_from_text(html)
        phones = extract_phones_from_text(html)
        
        if debug:
            print(f"      Scraped website: {len(emails)} emails, {len(phones)} phones")
        
    except Exception as e:
        if debug:
            print(f"      ⚠️  Website scrape error: {e}")
    
    return emails, phones


def find_contacts_for_broker(mc: str, company_name: str, website: str | None, mc_number: str | None = None, debug: bool = False) -> tuple[list[tuple[str, float]], list[str]]:
    """
    Find dispatch contacts for a broker using all available methods.
    Returns ([(email, confidence_score), ...], [phone, ...]).
    """
    all_emails = set()
    all_phones = set()
    
    # Strategy 1: Search DuckDuckGo
    if debug:
        print(f"   🔍 Searching DuckDuckGo...")
    search_emails, search_phones = search_dispatch_contacts(company_name, mc_number, debug=debug)
    all_emails.update(search_emails)
    all_phones.update(search_phones)
    
    # Strategy 2: Scrape website if available
    if website:
        if debug:
            print(f"   🌐 Scraping website {website}...")
        site_emails, site_phones = scrape_website_for_contacts(website, debug=debug)
        all_emails.update(site_emails)
        all_phones.update(site_phones)
    
    # Score emails
    domain = website.replace("http://", "").replace("https://", "").split("/")[0] if website else ""
    scored_emails = []
    for email in all_emails:
        score = score_email(email, "search", "", domain)
        scored_emails.append((email, score))
    
    # Sort by confidence
    scored_emails.sort(key=lambda x: x[1], reverse=True)
    
    return scored_emails, list(all_phones)


def enrich_brokers(limit: int | None = None, mc_filter: str | None = None, dry_run: bool = False, debug: bool = False):
    """Find dispatch contacts for brokers."""
    db = SessionLocal()
    try:
        # Build query
        if mc_filter:
            query = text("""
                SELECT mc_number, company_name, website, dot_number
                FROM webwise.brokers
                WHERE mc_number = :mc
            """)
            result = db.execute(query, {"mc": mc_filter})
        else:
            # Get brokers missing email or phone
            query = text("""
                SELECT mc_number, company_name, website, dot_number
                FROM webwise.brokers
                WHERE (primary_email IS NULL OR primary_email = '')
                   OR (primary_phone IS NULL OR primary_phone = '')
                ORDER BY mc_number
                LIMIT :limit
            """)
            result = db.execute(query, {"limit": limit or 999999})
        
        brokers = result.fetchall()
        
        if not brokers:
            print("✅ No brokers need contact enrichment.")
            return
        
        print(f"🔍 Found {len(brokers)} brokers needing contacts. Starting search...")
        if dry_run:
            print("   [DRY RUN MODE - No updates will be made]")
        
        updated_emails = 0
        updated_phones = 0
        found_emails_count = 0
        found_phones_count = 0
        failed = 0
        
        for idx, (mc, name, website, dot) in enumerate(brokers, 1):
            print(f"\n[{idx}/{len(brokers)}] MC {mc}: {name}")
            if website:
                print(f"   Website: {website}")
            
            if dry_run:
                emails_scored, phones = find_contacts_for_broker(mc, name, website, mc, debug=debug)
                if emails_scored:
                    print(f"   → Would add {len(emails_scored)} emails:")
                    for email, score in emails_scored[:3]:
                        print(f"      {email} (confidence: {score:.2f})")
                if phones:
                    print(f"   → Would add {len(phones)} phones:")
                    for phone in phones[:3]:
                        print(f"      {phone}")
                if not emails_scored and not phones:
                    print(f"   → No contacts found")
                time.sleep(2)
                continue
            
            emails_scored, phones = find_contacts_for_broker(mc, name, website, mc, debug=debug)
            
            has_updates = False
            
            # Insert emails
            if emails_scored:
                for email, score in emails_scored:
                    insert_query = text("""
                        INSERT INTO webwise.broker_emails (mc_number, email, source, confidence)
                        VALUES (:mc, :email, 'search', :score)
                        ON CONFLICT (mc_number, email) DO UPDATE SET confidence = GREATEST(confidence, :score)
                    """)
                    db.execute(insert_query, {"mc": mc, "email": email, "score": score})
                    found_emails_count += 1
                
                # Promote best email
                raw_conn = db.connection().connection
                promoted = promote_best(raw_conn, mc)
                if promoted:
                    updated_emails += 1
                    has_updates = True
                    print(f"   ✅ Added {len(emails_scored)} emails, promoted best to primary_email")
                else:
                    print(f"   ✅ Added {len(emails_scored)} emails")
            
            # Insert phones
            if phones:
                # Check existing phones
                existing_check = db.execute(
                    text("SELECT primary_phone, secondary_phone FROM webwise.brokers WHERE mc_number = :mc"),
                    {"mc": mc}
                ).fetchone()
                
                existing_primary = existing_check[0] if existing_check else None
                existing_secondary = existing_check[1] if existing_check and len(existing_check) > 1 else None
                
                # Normalize for comparison
                normalize_phone = lambda p: re.sub(r'[^\d]', '', p) if p else ""
                
                for phone in phones:
                    cleaned = clean_phone(phone)
                    if not cleaned:
                        continue
                    
                    new_normalized = normalize_phone(cleaned)
                    primary_normalized = normalize_phone(existing_primary) if existing_primary else ""
                    secondary_normalized = normalize_phone(existing_secondary) if existing_secondary else ""
                    
                    if not existing_primary:
                        # No primary phone - set it
                        update_query = text("""
                            UPDATE webwise.brokers
                            SET primary_phone = :phone, updated_at = CURRENT_TIMESTAMP
                            WHERE mc_number = :mc
                        """)
                        db.execute(update_query, {"phone": cleaned, "mc": mc})
                        existing_primary = cleaned
                        updated_phones += 1
                        has_updates = True
                        print(f"   ✅ Set primary_phone: {cleaned}")
                    elif new_normalized != primary_normalized:
                        # Different from primary - set as secondary if not already there
                        if not existing_secondary or new_normalized != secondary_normalized:
                            update_query = text("""
                                UPDATE webwise.brokers
                                SET secondary_phone = :phone, updated_at = CURRENT_TIMESTAMP
                                WHERE mc_number = :mc
                            """)
                            db.execute(update_query, {"phone": cleaned, "mc": mc})
                            existing_secondary = cleaned
                            updated_phones += 1
                            has_updates = True
                            print(f"   ✅ Set secondary_phone: {cleaned}")
                        break  # Only add one phone per run
            
            if has_updates:
                db.commit()
            
            if not emails_scored and not phones:
                failed += 1
                print(f"   ❌ No contacts found")
            
            # Rate limiting
            if idx < len(brokers):
                time.sleep(2)
        
        print(f"\n📊 Summary:")
        print(f"   ✅ Brokers with new emails: {updated_emails}")
        print(f"   📞 Brokers with new phones: {updated_phones}")
        print(f"   📧 Total emails found: {found_emails_count}")
        print(f"   📞 Total phones found: {found_phones_count}")
        print(f"   ❌ No contacts found: {failed}")
    
    except Exception as e:
        print(f"❌ Enrichment failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find dispatch emails and phones for brokers")
    parser.add_argument("--limit", type=int, help="Limit number of brokers to process")
    parser.add_argument("--mc", help="Process specific MC number only")
    parser.add_argument("--dry-run", action="store_true", help="Search but don't update database")
    parser.add_argument("--debug", action="store_true", help="Show detailed debugging")
    args = parser.parse_args()
    enrich_brokers(limit=args.limit, mc_filter=args.mc, dry_run=args.dry_run, debug=args.debug)
