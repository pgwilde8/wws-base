#!/usr/bin/env python3
"""
Load FMCSA Census CSV into webwise.brokers (Master Broker Directory).
- Reads CSV, keeps rows where carship contains 'B' (brokers).
- Cleans: strip 'MC' prefix from docket1, lowercase emails, strip whitespace.
- Upserts into webwise.brokers using mc_number as key.

Usage (from project root, with .env DATABASE_URL set):
  python scripts/load_fmcsa_brokers.py
  python scripts/load_fmcsa_brokers.py --csv path/to/az4n-8mr2.csv
"""
import argparse
import csv
import os
import re
import sys
from pathlib import Path

# Project root = parent of scripts/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def load_dotenv():
    try:
        from dotenv import load_dotenv as _load
        _load(PROJECT_ROOT / ".env")
    except ImportError:
        pass

load_dotenv()

from sqlalchemy import create_engine, text

DEFAULT_CSV = PROJECT_ROOT / "docs" / "az4n-8mr2.csv"


def _clean_mc(raw: str) -> str | None:
    """Strip whitespace and optional 'MC' prefix; return digits-only MC or None if empty."""
    if not raw:
        return None
    s = str(raw).strip().upper()
    # Remove MC prefix (e.g. "MC123" or "MC 123")
    s = re.sub(r"^MC\s*", "", s)
    s = s.strip()
    # Keep digits only for consistency (FMCSA docket1 is usually numeric)
    digits = re.sub(r"\D", "", s)
    return digits if digits else None


def _clean_email(raw: str) -> str | None:
    """Lowercase and strip; empty -> None."""
    if not raw:
        return None
    s = str(raw).strip().lower()
    return s if s else None


def _clean_str(raw: str, max_len: int | None = None) -> str | None:
    """Strip; empty -> None; optionally truncate."""
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if max_len is not None and len(s) > max_len:
        s = s[:max_len]
    return s


def main():
    ap = argparse.ArgumentParser(description="Load FMCSA broker CSV into webwise.brokers")
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Path to FMCSA Census CSV")
    ap.add_argument("--dry-run", action="store_true", help="Only print stats and sample rows, no DB write")
    args = ap.parse_args()

    csv_path = args.csv
    if not csv_path.is_file():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    database_url = os.getenv("DATABASE_URL")
    if not database_url and not args.dry_run:
        print("DATABASE_URL not set. Set it in .env or use --dry-run.", file=sys.stderr)
        sys.exit(1)

    # Read CSV and filter brokers (carship contains 'B')
    rows_read = 0
    broker_rows = []
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows_read += 1
            carship = (row.get("carship") or "").strip().upper()
            if "B" not in carship:
                continue
            broker_rows.append(row)

    # Build records with cleaned MC (required), email, phone, etc.
    records = []
    for row in broker_rows:
        raw_docket = row.get("docket1") or ""
        mc = _clean_mc(raw_docket)
        if not mc:
            continue
        records.append({
            "mc_number": mc,
            "dot_number": _clean_str(row.get("dot_number"), 20),
            "company_name": _clean_str(row.get("legal_name"), 255),
            "dba_name": _clean_str(row.get("dba_name"), 255),
            "primary_email": _clean_email(row.get("email_address")),
            "primary_phone": _clean_str(row.get("phone"), 50),
            "fax": _clean_str(row.get("fax"), 50),
            "phy_street": _clean_str(row.get("phy_street"), 255),
            "phy_city": _clean_str(row.get("phy_city"), 100),
            "phy_state": _clean_str(row.get("phy_state"), 50),
            "phy_zip": _clean_str(row.get("phy_zip"), 20),
        })

    # Dedupe by mc_number (keep last occurrence)
    by_mc = {r["mc_number"]: r for r in records}
    records = list(by_mc.values())

    print(f"Rows read: {rows_read}")
    print(f"Brokers (carship contains 'B'): {len(broker_rows)}")
    print(f"With valid MC (after clean): {len(records)}")

    # Sample validation output
    for r in list(records)[:5]:
        print(f"  MC {r['mc_number']} | {r['company_name'] or '(no name)'} | {r['primary_email'] or '(no email)'}")

    if args.dry_run:
        print("--dry-run: skipping database write.")
        return

    engine = create_engine(database_url, future=True)
    upsert_sql = text("""
        INSERT INTO webwise.brokers (
            mc_number, dot_number, company_name, dba_name,
            primary_email, primary_phone, fax,
            phy_street, phy_city, phy_state, phy_zip,
            source, updated_at
        ) VALUES (
            :mc_number, :dot_number, :company_name, :dba_name,
            :primary_email, :primary_phone, :fax,
            :phy_street, :phy_city, :phy_state, :phy_zip,
            'FMCSA', CURRENT_TIMESTAMP
        )
        ON CONFLICT (mc_number) DO UPDATE SET
            dot_number = EXCLUDED.dot_number,
            company_name = EXCLUDED.company_name,
            dba_name = EXCLUDED.dba_name,
            primary_email = EXCLUDED.primary_email,
            primary_phone = EXCLUDED.primary_phone,
            fax = EXCLUDED.fax,
            phy_street = EXCLUDED.phy_street,
            phy_city = EXCLUDED.phy_city,
            phy_state = EXCLUDED.phy_state,
            phy_zip = EXCLUDED.phy_zip,
            source = EXCLUDED.source,
            updated_at = CURRENT_TIMESTAMP
    """)

    with engine.begin() as conn:
        for r in records:
            conn.execute(upsert_sql, r)

    print(f"Upserted {len(records)} brokers into webwise.brokers.")


if __name__ == "__main__":
    main()
