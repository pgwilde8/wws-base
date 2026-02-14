"""
Scrape emails from broker websites (when website IS NOT NULL).

For brokers that already have a website URL, fetch the page and extract emails.
Much more reliable than searching for websites - you already know the site exists.

Usage:
  PYTHONPATH=. python3 app/scripts/scrape_emails_from_websites.py
  PYTHONPATH=. python3 app/scripts/scrape_emails_from_websites.py --limit 100
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

import requests
from sqlalchemy import text
from app.core.deps import SessionLocal
from scripts.attach_packet_emails import score_email, promote_best

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")


def extract_emails_from_html(html: str, domain: str) -> list[str]:
    """Extract unique emails from HTML, filtering out common non-dispatch addresses."""
    emails = set()
    for match in EMAIL_RE.finditer(html):
        email = match.group(0).lower().strip()
        # Skip image URLs, data URIs, etc.
        if email.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
            continue
        # Skip common non-dispatch emails
        skip_patterns = [
            "noreply", "no-reply", "donotreply", "privacy", "legal",
            "abuse", "postmaster", "webmaster", "hostmaster"
        ]
        if any(pattern in email for pattern in skip_patterns):
            continue
        emails.add(email)
    return sorted(emails)


def scrape_broker_website(mc: str, website: str, debug: bool = False) -> list[tuple[str, float]]:
    """
    Scrape emails from a broker's website.
    Returns list of (email, confidence_score) tuples.
    """
    if not website or not website.startswith(("http://", "https://")):
        website = f"https://{website}"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(website, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        
        html = response.text
        domain = website.replace("http://", "").replace("https://", "").split("/")[0]
        
        emails = extract_emails_from_html(html, domain)
        if debug:
            print(f"      Found {len(emails)} emails: {emails[:5]}")
        
        # Score each email
        scored = []
        for email in emails:
            # Use website source, nearby text is empty (we're scraping HTML)
            score = score_email(email, "website", "", domain)
            scored.append((email, score))
        
        return scored
        
    except Exception as e:
        if debug:
            print(f"      ⚠️  Scrape error: {e}")
        return []


def scrape_brokers(limit: int | None = None, dry_run: bool = False, debug: bool = False):
    """Scrape emails from broker websites."""
    db = SessionLocal()
    try:
        # Get brokers WITH websites but WITHOUT primary_email
        query = text("""
            SELECT mc_number, company_name, website
            FROM webwise.brokers
            WHERE website IS NOT NULL
              AND (primary_email IS NULL OR primary_email = '')
            ORDER BY mc_number
            LIMIT :limit
        """)
        result = db.execute(query, {"limit": limit or 999999})
        brokers = result.fetchall()

        if not brokers:
            print("✅ No brokers need email scraping (all have websites with emails or no websites).")
            return

        print(f"🔍 Found {len(brokers)} brokers with websites but no primary_email. Starting scrape...")
        if dry_run:
            print("   [DRY RUN MODE - No updates will be made]")

        updated = 0
        found_emails = 0
        failed = 0

        for idx, (mc, name, website) in enumerate(brokers, 1):
            print(f"\n[{idx}/{len(brokers)}] MC {mc}: {name}")
            print(f"   Website: {website}")
            
            if dry_run:
                emails_scored = scrape_broker_website(mc, website, debug=debug)
                if emails_scored:
                    print(f"   → Would add {len(emails_scored)} emails:")
                    for email, score in sorted(emails_scored, key=lambda x: x[1], reverse=True)[:3]:
                        print(f"      {email} (confidence: {score:.2f})")
                else:
                    print(f"   → No emails found")
                time.sleep(2)  # Rate limit
                continue

            emails_scored = scrape_broker_website(mc, website, debug=debug)
            if emails_scored:
                # Insert into broker_emails
                for email, score in emails_scored:
                    insert_query = text("""
                        INSERT INTO webwise.broker_emails (mc_number, email, source, confidence)
                        VALUES (:mc, :email, 'website', :score)
                        ON CONFLICT (mc_number, email) DO UPDATE SET confidence = GREATEST(confidence, :score)
                    """)
                    db.execute(insert_query, {"mc": mc, "email": email, "score": score})
                    found_emails += 1
                
                # Promote best email to primary_email
                raw_conn = db.connection().connection
                promoted = promote_best(raw_conn, mc)
                db.commit()
                
                if promoted:
                    updated += 1
                    print(f"   ✅ Added {len(emails_scored)} emails, promoted best to primary_email")
                else:
                    print(f"   ✅ Added {len(emails_scored)} emails")
            else:
                failed += 1
                print(f"   ❌ No emails found")

            # Rate limiting
            if idx < len(brokers):
                time.sleep(2)  # 2 second delay between scrapes

        print(f"\n📊 Summary:")
        print(f"   ✅ Brokers updated: {updated}")
        print(f"   📧 Total emails found: {found_emails}")
        print(f"   ❌ No emails found: {failed}")

    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape emails from broker websites")
    parser.add_argument("--limit", type=int, help="Limit number of brokers to process")
    parser.add_argument("--dry-run", action="store_true", help="Scrape but don't update database")
    parser.add_argument("--debug", action="store_true", help="Show detailed debugging")
    args = parser.parse_args()
    scrape_brokers(limit=args.limit, dry_run=args.dry_run, debug=args.debug)
