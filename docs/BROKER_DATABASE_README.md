# Broker Database Reference

Master reference for the `webwise` broker directory: schema, columns, lookup commands, and enrichment workflows.

---

## Database Connection

```bash
psql "postgresql://wws-admin:WwsAdmin2026%21@localhost/wws_dispatch_db"
```

---

## Schema Overview

| Table | Purpose |
|-------|---------|
| **webwise.brokers** | One row per MC# — primary contact info, address, source |
| **webwise.broker_emails** | Multiple emails per MC with source and confidence |

**Primary key:** `mc_number` (MC digits only, no "MC" prefix)

---

## webwise.brokers — Columns

| Column | Type | Description |
|--------|------|-------------|
| `mc_number` | VARCHAR(20) PK | Motor Carrier number (digits only, e.g. `322572`) |
| `dot_number` | VARCHAR(20) | USDOT number |
| `company_name` | VARCHAR(255) | Legal name from FMCSA |
| `dba_name` | VARCHAR(255) | Doing-Business-As name |
| `website` | VARCHAR(255) | Domain only (no http/https/www) |
| `primary_email` | VARCHAR(255) | Best email for dispatch (canonical, no +tags) |
| `primary_phone` | VARCHAR(50) | Main dispatch/contact phone |
| `secondary_phone` | VARCHAR(50) | Additional phone (e.g. regional, backup) |
| `fax` | VARCHAR(50) | Fax number |
| `phy_street` | VARCHAR(255) | Physical street address |
| `phy_city` | VARCHAR(100) | City |
| `phy_state` | VARCHAR(50) | State code |
| `phy_zip` | VARCHAR(20) | ZIP code |
| `rating` | DECIMAL(3,2) | Optional broker rating |
| `source` | VARCHAR(50) | `fmcsa_api` \| `FMCSA` \| `manual` \| `enriched` |
| `preferred_contact_method` | VARCHAR(20) | `email` \| `phone` \| `call_to_book` |
| `created_at` | TIMESTAMP | When record was created |
| `updated_at` | TIMESTAMP | Last update |

**Note:** `secondary_phone` and `preferred_contact_method` are added via migrations. Run `sql/add_secondary_phone.sql` and `sql/add_preferred_contact_method.sql` if missing.

---

## webwise.broker_emails — Columns

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGSERIAL PK | Auto-increment |
| `mc_number` | VARCHAR(20) FK | References brokers(mc_number) |
| `email` | TEXT | Email address (canonical, no +tags) |
| `source` | TEXT | `manual` \| `carrier_packet` \| `website` \| `search` \| `fmcsa` |
| `confidence` | NUMERIC(4,3) | 0.000–1.000 (e.g. 0.90 for manual) |
| `evidence` | TEXT | Optional context (filename, URL, snippet) |
| `created_at` | TIMESTAMPTZ | When added |

**Unique:** (mc_number, email)

---

## Lookup Commands

### By MC number (preferred — most reliable)

```sql
SELECT mc_number, company_name, primary_email, primary_phone, secondary_phone, website, dot_number
FROM webwise.brokers
WHERE mc_number = '322572';
```

### Expanded view (one field per line)

```sql
\x on
SELECT * FROM webwise.brokers WHERE mc_number = '322572';
\x off
```

### By company name (use flexible pattern — punctuation varies)

```sql
-- Flexible: matches "GENPRO INC", "GENPRO, INC.", "GEN PRO INC"
WHERE company_name ILIKE '%GENPRO%INC%'

-- Or search both name and DBA
WHERE company_name ILIKE '%CARDINAL%' OR dba_name ILIKE '%CARDINAL%'
```

### By DOT number

```sql
SELECT * FROM webwise.brokers WHERE dot_number = '2223295';
```

### Broker plus all emails

```sql
SELECT b.mc_number, b.company_name, b.primary_email, b.primary_phone, b.website,
       string_agg(e.email || ' (' || e.source || ')', ', ' ORDER BY e.confidence DESC) AS all_emails
FROM webwise.brokers b
LEFT JOIN webwise.broker_emails e ON b.mc_number = e.mc_number
WHERE b.mc_number = '322572'
GROUP BY b.mc_number, b.company_name, b.primary_email, b.primary_phone, b.website;
```

### Stats (email coverage)

```sql
SELECT
    COUNT(*) AS total_brokers,
    COUNT(primary_email) AS with_emails,
    COUNT(*) - COUNT(primary_email) AS missing_emails,
    ROUND((COUNT(primary_email)::numeric / NULLIF(COUNT(*), 0)) * 100, 2) AS email_rate_pct
FROM webwise.brokers;
```

---

## Add / Update Commands

### add_broker_contact.py (recommended)

Adds or updates email, phone, website, DOT. Creates broker row if missing. Emails stored in `broker_emails`; best email promoted to `primary_email`. Phone logic: if primary exists and different, new phone goes to `secondary_phone`.

```bash
cd /srv/projects/client/dispatch

# Email + phone + website + DOT
PYTHONPATH=. python3 app/scripts/add_broker_contact.py --mc 322572 \
  --email "carrier@tql.com" --phone "+1 (800) 580-3101" \
  --website "https://tql.com" --dot 2223295

# Email only
PYTHONPATH=. python3 app/scripts/add_broker_contact.py --mc 965005 --email "loads@freshfreight.com"

# Phone only (sets preferred_contact_method = call_to_book)
PYTHONPATH=. python3 app/scripts/add_broker_contact.py --mc 945637 --phone "+1 (602) 755-3668" --call-to-book
```

**Email handling:** Plus-addressing (e.g. `+trucksmarter`) is stripped for storage. Store canonical base; dispatch can add tags by load source.

---

## Ingestion Scripts

| Script | Source | Filter | What it loads |
|--------|--------|--------|---------------|
| `app/scripts/ingest_active_brokers.py` | FMCSA API (6eyk-hxee) | `broker_stat='A'` | MC, DOT, name, DBA, address (no phone/email) |
| `scripts/load_fmcsa_brokers.py` | CSV (az4n-8mr2.csv) | `carship` contains 'B' | ~187 brokers from sample CSV |

```bash
# Ingest all active brokers from FMCSA API (~25k+)
PYTHONPATH=. python3 app/scripts/ingest_active_brokers.py
```

Requires `DOT_API_TOKEN` in `.env` for FMCSA Socrata API.

---

## Enrichment Scripts

| Script | Purpose |
|--------|---------|
| `app/scripts/add_broker_contact.py` | Manual add/update of email, phone, website, DOT |
| `app/scripts/find_dispatch_contacts.py` | Search (DuckDuckGo, etc.) for emails/phones |
| `app/scripts/scrape_emails_from_websites.py` | Scrape emails from broker websites |
| `app/scripts/enrich_broker_websites.py` | Find website URLs via search for brokers with NULL website |
| `scripts/attach_packet_emails.py` | Parse carrier packet text, extract emails, attach to brokers |

---

## Potentially Missing Columns (for consideration)

| Column | Type | Use case |
|--------|------|----------|
| `load_board_source` | VARCHAR(50)[] or JSONB | Which boards list this broker (DAT, Truckstop, TruckSmarter) |
| `last_contact_verified` | DATE | When contact info was last confirmed |
| `contact_source` | VARCHAR(50) | Where primary contact came from (e.g. `trucksmarter`, `dat`, `manual`) |
| `mailing_street`, `mailing_city`, `mailing_state`, `mailing_zip` | VARCHAR | Mailing address (FMCSA has both physical and mailing) |
| `fmcsa_status` | VARCHAR(20) | ACTIVE, INACTIVE, OUT_OF_SERVICE |
| `operating_authority` | VARCHAR(100) | e.g. "AUTHORIZED FOR BROKER Property" |

To add any of these:

```sql
ALTER TABLE webwise.brokers ADD COLUMN IF NOT EXISTS contact_source VARCHAR(50);
ALTER TABLE webwise.brokers ADD COLUMN IF NOT EXISTS last_contact_verified DATE;
```

---

## Email Source Values

| Source | Meaning |
|--------|---------|
| `manual` | Added via add_broker_contact.py |
| `carrier_packet` | Parsed from carrier packet / forwarded email |
| `website` | Scraped from broker website |
| `search` | Found via find_dispatch_contacts.py |
| `fmcsa` | From FMCSA registration (rare) |

---

## Quick Reference

| Task | Command |
|------|---------|
| Look up by MC | `SELECT * FROM webwise.brokers WHERE mc_number = '123456';` |
| Add/update contact | `PYTHONPATH=. python3 app/scripts/add_broker_contact.py --mc 123456 --email x@y.com --phone "+1..."` |
| Ingest from FMCSA | `PYTHONPATH=. python3 app/scripts/ingest_active_brokers.py` |
| Find brokers missing email | `SELECT mc_number, company_name FROM webwise.brokers WHERE primary_email IS NULL LIMIT 20;` |
| Search by name | `WHERE company_name ILIKE '%PARTIAL%NAME%'` |

---

## Data Sources

- **FMCSA SAFER:** https://safer.fmcsa.dot.gov/CompanySnapshot.aspx — free lookup by MC/DOT
- **FMCSA QCMobile API:** https://mobile.fmcsa.dot.gov/QCDevsite/ — free API (phone, address; no email)
- **Load boards (DAT, Truckstop):** Best for per-load contact; MC# required for reliable matching
