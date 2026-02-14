"""
Enrich broker websites by searching DuckDuckGo for company name + location.

Searches for brokers WHERE website IS NULL using:
  "{company_name} {city} {state} freight transportation"

Updates webwise.brokers.website with the first search result URL.

Usage:
  PYTHONPATH=. python3 app/scripts/enrich_broker_websites.py
  PYTHONPATH=. python3 app/scripts/enrich_broker_websites.py --limit 100
  PYTHONPATH=. python3 app/scripts/enrich_broker_websites.py --dry-run
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

# DuckDuckGo HTML search (no API key needed) - fallback if library not available
DDG_SEARCH_URL = "https://html.duckduckgo.com/html/"


def clean_url(url: str) -> str | None:
    """Extract and clean a domain from a DuckDuckGo result URL."""
    if not url:
        return None
    # DuckDuckGo wraps URLs like: /l/?kh=-1&uddg=https://example.com
    match = re.search(r"uddg=([^&]+)", url)
    if match:
        url = match.group(1)
    # Decode URL encoding
    try:
        import urllib.parse
        url = urllib.parse.unquote(url)
    except Exception:
        pass
    # Extract domain (remove path, query, fragment)
    match = re.match(r"https?://([^/?#]+)", url)
    if match:
        domain = match.group(1).lower().strip()
        # Basic validation: must have a dot and look like a domain
        if "." in domain and len(domain) > 3:
            return domain
    return None


def search_website(company_name: str, city: str | None, state: str | None, debug: bool = False) -> str | None:
    """
    Search DuckDuckGo for broker website.
    Returns cleaned domain (e.g. 'triplettransport.com') or None.
    """
    # Build search query: Try simpler first, then add keywords if needed
    # Start with: "Company Name City State" (broader, catches more)
    query_parts = [company_name]
    if city:
        query_parts.append(city)
    if state:
        query_parts.append(state)
    # Don't add "freight transportation" initially - too restrictive for small companies
    query = " ".join(filter(None, query_parts))

    if debug:
        print(f"      Query: {query}")

    # Use duckduckgo-search library if available (more reliable)
    if HAS_DDGS:
        try:
            # Try multiple search strategies
            search_queries = [
                query,  # Original: "Company City State"
                f'"{company_name}" website',  # Try: "Company Name" website
                f'{company_name} official site',  # Try: Company Name official site
            ]
            
            best_domain = None
            for search_q in search_queries:
                if debug:
                    print(f"      Trying query: {search_q}")
                with DDGS() as ddgs:
                    results = list(ddgs.text(search_q, max_results=10))
                    if debug:
                        print(f"      Found {len(results)} results")
                    
                    for result in results:
                        url = result.get("href", "")
                        if debug:
                            print(f"      Checking: {url}")
                        domain = clean_url(url)
                        if domain:
                            # Aggressively filter out directory/review sites
                            skip_domains = [
                                "duckduckgo.com", "wikipedia.org", "linkedin.com", 
                                "facebook.com", "yellowpages.com", "manta.com",
                                "truckingdatabase.com", "transportreviews.com",
                                "seakexperts.com", "safer.fmcsa.dot.gov",
                                "carrierlists.com", "freightquote.com",
                                "truckinginfo.com", "truckersreport.com",
                                "indeed.com", "glassdoor.com", "zoominfo.com",
                                "crunchbase.com", "bloomberg.com", "youtube.com",
                                "google.com", "bing.com", "yahoo.com"
                            ]
                            if any(skip in domain for skip in skip_domains):
                                continue
                            
                            # Extract root domain (remove www. and subdomains)
                            domain_parts = domain.lower().replace("www.", "").split(".")
                            if len(domain_parts) >= 2:
                                root_domain = ".".join(domain_parts[-2:])  # e.g. "embarktrucks.com"
                                domain_name = domain_parts[-2]  # e.g. "embarktrucks"
                            else:
                                root_domain = domain.lower()
                                domain_name = domain_parts[0] if domain_parts else ""
                            
                            # Extract meaningful words from company name (skip common words)
                            skip_words = {"inc", "llc", "corp", "ltd", "transportation", "transport", "logistics", "trucking", "freight"}
                            company_words = [
                                w.lower().strip(".,&") 
                                for w in company_name.split() 
                                if len(w) > 2 and w.lower() not in skip_words
                            ]
                            
                            # Strong match: root domain name contains a significant company word
                            # e.g. "armen" in "armentransportation.com" or "mawson" in "mawsonandmawson2290.com"
                            strong_match = any(word in domain_name for word in company_words if len(word) > 3)
                            
                            if strong_match:
                                # Prefer root domain over subdomains (embarktrucks.com > investors.embarktrucks.com)
                                if "." not in domain_name and domain.count(".") <= 2:
                                    if debug:
                                        print(f"      ✅ Selected (strong name match): {root_domain}")
                                    return root_domain
                                else:
                                    # Subdomain match - save but keep looking for root
                                    if not best_domain or "investors" not in domain.lower():
                                        best_domain = root_domain
                                        if debug:
                                            print(f"      💾 Saved subdomain match: {root_domain}")
                            
                            # Weak match: save as fallback but keep looking
                            elif not best_domain:
                                best_domain = root_domain
                                if debug:
                                    print(f"      💾 Saved as fallback: {root_domain}")
                    
                    # If we found a strong root domain match, stop searching
                    if best_domain:
                        # Check if best_domain has a strong name match
                        best_parts = best_domain.lower().replace("www.", "").split(".")
                        best_name = best_parts[-2] if len(best_parts) >= 2 else best_parts[0]
                        if any(word in best_name for word in company_words if len(word) > 3):
                            if debug:
                                print(f"      ✅ Stopping search, found strong match: {best_domain}")
                            break
            
            # Return best match found, but only if it has some name match
            if best_domain:
                best_parts = best_domain.lower().replace("www.", "").split(".")
                best_name = best_parts[-2] if len(best_parts) >= 2 else best_parts[0]
                # Only return if there's at least a partial name match (avoid false positives)
                if any(word in best_name for word in company_words if len(word) > 3):
                    if debug:
                        print(f"      ✅ Using best match with name match: {best_domain}")
                    return best_domain
                elif debug:
                    print(f"      ❌ Best match has no name match, rejecting: {best_domain}")
                
        except Exception as e:
            if debug:
                print(f"      ⚠️  Library search error: {e}")
            # Fall through to HTML scraping fallback

    # Fallback: HTML scraping
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        params = {"q": query}
        response = requests.get(DDG_SEARCH_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        html = response.text
        if debug:
            print(f"      HTML length: {len(html)}")
            # Save a sample for inspection
            if len(html) < 50000:
                print(f"      HTML sample (first 500 chars): {html[:500]}")

        # DuckDuckGo HTML results use /l/?uddg= URLs that redirect
        # Pattern: href="/l/?kh=-1&uddg=https://example.com&..."
        uddg_pattern = r'href="/l/\?[^"]*uddg=([^"&]+)'
        uddg_matches = re.findall(uddg_pattern, html)
        if debug and uddg_matches:
            print(f"      Found {len(uddg_matches)} uddg URLs")
        
        for url in uddg_matches[:5]:
            domain = clean_url(url)
            if domain and not any(skip in domain for skip in [
                "duckduckgo.com", "wikipedia.org", "linkedin.com",
                "facebook.com", "yellowpages.com", "manta.com", "youtube.com"
            ]):
                if debug:
                    print(f"      ✅ Found via HTML uddg: {domain}")
                return domain

        # Fallback: look for direct https?:// URLs in href attributes
        direct_pattern = r'href="(https?://[^"]+)"'
        direct_matches = re.findall(direct_pattern, html)
        if debug and direct_matches:
            print(f"      Found {len(direct_matches)} direct URLs")
        
        for url in direct_matches[:10]:  # Check more since we filter
            domain = clean_url(url)
            if domain and not any(skip in domain for skip in [
                "duckduckgo.com", "wikipedia.org", "linkedin.com",
                "facebook.com", "yellowpages.com", "manta.com", "youtube.com",
                "google.com", "bing.com"
            ]):
                if debug:
                    print(f"      ✅ Found via HTML direct: {domain}")
                return domain

    except Exception as e:
        if debug:
            print(f"      ⚠️  HTML search error: {e}")
    return None


def enrich_brokers(limit: int | None = None, dry_run: bool = False, debug: bool = False):
    """Enrich broker websites from DuckDuckGo search."""
    db = SessionLocal()
    try:
        # Get brokers without websites
        query = text("""
            SELECT mc_number, company_name, phy_city, phy_state
            FROM webwise.brokers
            WHERE website IS NULL
              AND company_name IS NOT NULL
              AND company_name != 'Unknown'
            ORDER BY mc_number
            LIMIT :limit
        """)
        result = db.execute(query, {"limit": limit or 999999})
        brokers = result.fetchall()

        if not brokers:
            print("✅ No brokers need website enrichment.")
            return

        print(f"🔍 Found {len(brokers)} brokers without websites. Starting enrichment...")
        if dry_run:
            print("   [DRY RUN MODE - No updates will be made]")

        updated = 0
        failed = 0
        skipped = 0

        for idx, (mc, name, city, state) in enumerate(brokers, 1):
            print(f"\n[{idx}/{len(brokers)}] MC {mc}: {name} ({city}, {state})")
            if dry_run:
                domain = search_website(name, city, state, debug=debug)
                if domain:
                    print(f"   → Would set website = {domain}")
                else:
                    print(f"   → No website found")
                time.sleep(1.5)  # Rate limit even in dry-run
                continue

            domain = search_website(name, city, state, debug=debug)
            if domain:
                update_query = text("""
                    UPDATE webwise.brokers
                    SET website = :domain, updated_at = CURRENT_TIMESTAMP
                    WHERE mc_number = :mc
                """)
                db.execute(update_query, {"domain": domain, "mc": mc})
                db.commit()
                updated += 1
                print(f"   ✅ Set website = {domain}")
            else:
                failed += 1
                print(f"   ❌ No website found")

            # Rate limiting: be respectful to DuckDuckGo
            if idx < len(brokers):
                time.sleep(1.5)  # 1.5 second delay between searches

        print(f"\n📊 Summary:")
        print(f"   ✅ Updated: {updated}")
        print(f"   ❌ Not found: {failed}")
        print(f"   ⏭️  Skipped: {skipped}")

    except Exception as e:
        print(f"❌ Enrichment failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich broker websites via DuckDuckGo search")
    parser.add_argument("--limit", type=int, help="Limit number of brokers to process (for testing)")
    parser.add_argument("--dry-run", action="store_true", help="Search but don't update database")
    parser.add_argument("--debug", action="store_true", help="Show detailed search debugging")
    args = parser.parse_args()
    enrich_brokers(limit=args.limit, dry_run=args.dry_run, debug=args.debug)
