#!/usr/bin/env python3
"""
Attach emails from carrier packet text to webwise.brokers + webwise.broker_emails.
Extracts MC/DOT and emails from a text file (e.g. from PDF extraction or forwarded email),
inserts candidates into broker_emails, and promotes the best to brokers.primary_email if empty.

Usage (from project root, DATABASE_URL in .env or env):
  python3 scripts/attach_packet_emails.py /path/to/packet_text.txt
  python3 scripts/attach_packet_emails.py /path/to/packet.txt --evidence "packet_123.pdf"
"""
import argparse
import os
import re
import sys
from pathlib import Path

# Project root = parent of scripts/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def _load_dotenv():
    try:
        from dotenv import load_dotenv as _load
        _load(PROJECT_ROOT / ".env")
    except ImportError:
        pass

_load_dotenv()

import psycopg2

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
MC_RE = re.compile(r"\bMC[\s\-#:]*([0-9]{4,10})\b", re.IGNORECASE)
DOT_RE = re.compile(
    r"\bUSDOT[\s\-#:]*([0-9]{4,10})\b|\bDOT[\s\-#:]*([0-9]{4,10})\b",
    re.IGNORECASE,
)

# Scoring rubric: keyword weights (local part + nearby text)
POS_STRONG = {
    "loads": 50, "load": 50, "dispatch": 50, "coverage": 45,
    "ops": 40, "operations": 40, "tender": 40, "tenders": 40,
    "capacity": 35, "carrierrelations": 35, "carrier-relations": 35,
    "brokerage": 30, "logistics": 25,
}
POS_MED = {
    "carrier": 30, "carriers": 30, "setup": 25, "onboarding": 25, "onboard": 25,
    "support": 10, "compliance": 10, "contracts": 10,
}
NEG = {
    "billing": -30, "invoicing": -30, "accounting": -30, "ap": -30, "ar": -30,
    "claims": -35, "hr": -50, "careers": -50, "recruiting": -50,
    "legal": -25, "safety": -25, "it": -15, "tech": -15,
    "noreply": -80, "do-not-reply": -80,
}
NEUTRAL = {"info": 5, "contact": 5, "hello": 5}

SOURCE_BASE = {
    "carrier_packet": 40, "website": 25, "reply": 50, "fmcsa": 10, "manual": 60,
}

# Domain penalties (substring match in domain, lowercased)
PERSONAL_DOMAINS = ("gmail.com", "yahoo.com", "outlook.com", "hotmail.com")
FACTORING_DOMAIN_PARTS = ("otr", "rts", "triumphpay", "tcf", "truckingfactoring", "factoring")
NEARBY_POS = ("dispatch", "loads", "coverage")
NEARBY_NEG = ("billing", "accounting")

# Person-name heuristic: local part looks like first.last or firstlast (2+ chars)
PERSON_NAME_RE = re.compile(r"^[a-z][a-z]+(\.[a-z][a-z]+)?$")


def norm_email(e: str) -> str:
    return e.strip().lower()


def norm_mc(mc: str) -> str:
    return re.sub(r"\D+", "", mc or "").strip()


def extract_mc(text: str) -> str | None:
    m = MC_RE.search(text)
    return norm_mc(m.group(1)) if m else None


def extract_dot(text: str) -> str | None:
    m = DOT_RE.search(text)
    if not m:
        return None
    g1, g2 = m.group(1), m.group(2)
    return (g1 or g2) if (g1 or g2) else None


def extract_emails_with_context(text: str) -> list[tuple[str, str]]:
    """Return list of (email, nearby_text) for scoring. Nearby = ~40 chars each side."""
    radius = 40
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for m in EMAIL_RE.finditer(text):
        raw = m.group(0)
        e = norm_email(raw)
        if e in seen or not e or e.endswith((".png", ".jpg", ".jpeg")):
            continue
        seen.add(e)
        start = max(0, m.start() - radius)
        end = min(len(text), m.end() + radius)
        nearby = text[start:end].lower()
        out.append((e, nearby))
    return sorted(out, key=lambda x: x[0])


def _local_part(email: str) -> str:
    return email.split("@")[0].lower().replace("-", "").replace(".", "")


def _domain(email: str) -> str:
    return email.split("@")[-1].lower() if "@" in email else ""


def _broker_domain_from_website(website: str | None) -> str:
    """Normalize broker website to domain only for matching (e.g. cardlog.com)."""
    if not website or not website.strip():
        return ""
    s = website.strip().lower()
    for prefix in ("https://", "http://", "www."):
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s.split("/")[0].strip()


def score_email(
    email: str,
    source: str,
    nearby_text: str,
    broker_website_domain: str,
) -> float:
    """
    Repeatable rubric: base by source + keyword weights + domain + nearby.
    Returns confidence in [0, 1].
    """
    base = SOURCE_BASE.get(source, 40)
    local = _local_part(email)
    domain = _domain(email)
    score_val = float(base)

    # Keyword weights (local part) — sum all matches
    for kw, w in POS_STRONG.items():
        if kw in local:
            score_val += w
    for kw, w in POS_MED.items():
        if kw in local:
            score_val += w
    for kw, w in NEG.items():
        if kw in local:
            score_val += w
    for kw, w in NEUTRAL.items():
        if kw in local:
            score_val += w

    # Person-name heuristic
    local_plain = email.split("@")[0].lower()
    if PERSON_NAME_RE.match(local_plain) and not any(
        k in local for k in (*POS_STRONG, *POS_MED)
    ):
        score_val += 10

    # Domain: match broker website
    if broker_website_domain and domain == broker_website_domain:
        score_val += 25
    elif broker_website_domain and domain and domain != broker_website_domain:
        score_val -= 20

    # Personal / third-party domains
    if any(d in domain for d in PERSONAL_DOMAINS):
        score_val -= 15
    if any(p in domain for p in FACTORING_DOMAIN_PARTS):
        score_val -= 40

    # Nearby text bonus/penalty
    for kw in NEARBY_POS:
        if kw in nearby_text:
            score_val += 20
            break
    for kw in NEARBY_NEG:
        if kw in nearby_text:
            score_val -= 20
            break

    # Clamp 0–100 then return confidence in [0, 1]
    score_val = max(0.0, min(100.0, score_val))
    return round(score_val / 100.0, 3)


def lookup_mc_by_dot(conn, dot: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT mc_number FROM webwise.brokers WHERE dot_number = %s LIMIT 1",
            (dot,),
        )
        row = cur.fetchone()
        return row[0] if row else None


def broker_exists(conn, mc: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM webwise.brokers WHERE mc_number = %s LIMIT 1",
            (mc,),
        )
        return cur.fetchone() is not None


def get_broker_website(conn, mc: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT website FROM webwise.brokers WHERE mc_number = %s LIMIT 1",
            (mc,),
        )
        row = cur.fetchone()
        return row[0] if row else None


def insert_candidates(
    conn,
    mc: str,
    email_contexts: list[tuple[str, str]],
    source: str,
    evidence: str | None,
    broker_website_domain: str,
) -> None:
    with conn.cursor() as cur:
        for email, nearby_text in email_contexts:
            conf = score_email(
                email, source, nearby_text, broker_website_domain
            )
            cur.execute(
                """
                INSERT INTO webwise.broker_emails (mc_number, email, source, confidence, evidence)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (mc_number, email) DO UPDATE SET
                    confidence = GREATEST(webwise.broker_emails.confidence, EXCLUDED.confidence),
                    evidence = COALESCE(webwise.broker_emails.evidence, EXCLUDED.evidence)
                """,
                (mc, email, source, conf, evidence),
            )


PROMOTION_THRESHOLD = 0.10  # Only promote if new best is at least this much better


def promote_best(conn, mc: str) -> bool:
    """
    Set brokers.primary_email to highest-confidence candidate if empty or
    new best confidence is at least PROMOTION_THRESHOLD (0.10) higher than current.
    Returns True if primary_email was updated.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT email, confidence
            FROM webwise.broker_emails
            WHERE mc_number = %s
            ORDER BY confidence DESC, created_at DESC
            LIMIT 1
            """,
            (mc,),
        )
        row = cur.fetchone()
        if not row:
            return False
        best_email, best_conf = row

        cur.execute(
            "SELECT primary_email FROM webwise.brokers WHERE mc_number = %s LIMIT 1",
            (mc,),
        )
        broker_row = cur.fetchone()
        current_primary = (broker_row[0] or "").strip() if broker_row else ""

        if not current_primary:
            cur.execute(
                """
                UPDATE webwise.brokers
                SET primary_email = %s, source = 'enriched', updated_at = now()
                WHERE mc_number = %s
                """,
                (best_email, mc),
            )
            return True

        # Current primary set — only overwrite if new best is sufficiently better
        cur.execute(
            """
            SELECT confidence FROM webwise.broker_emails
            WHERE mc_number = %s AND email = %s LIMIT 1
            """,
            (mc, current_primary),
        )
        curr_row = cur.fetchone()
        current_conf = float(curr_row[0]) if curr_row else 0.0
        best_conf_f = float(best_conf)
        if best_conf_f >= current_conf + PROMOTION_THRESHOLD:
            cur.execute(
                """
                UPDATE webwise.brokers
                SET primary_email = %s, source = 'enriched', updated_at = now()
                WHERE mc_number = %s
                """,
                (best_email, mc),
            )
            return True
        return False


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Attach emails from carrier packet text to broker_emails and promote best to brokers.primary_email"
    )
    ap.add_argument("path", type=Path, help="Path to packet text file")
    ap.add_argument(
        "--evidence",
        type=str,
        default=None,
        help="Evidence string (default: basename of path)",
    )
    args = ap.parse_args()

    path = args.path
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL not set.", file=sys.stderr)
        sys.exit(1)

    evidence = args.evidence or path.name
    text = path.read_text(encoding="utf-8", errors="ignore")

    mc = extract_mc(text)
    dot = extract_dot(text)
    email_contexts = extract_emails_with_context(text)

    if not email_contexts:
        print("No emails found.")
        return

    with psycopg2.connect(dsn) as conn:
        if not mc and dot:
            mc = lookup_mc_by_dot(conn, dot)

        if not mc:
            print(
                "Could not find MC (or DOT->MC). Store these emails as 'unassigned' or ask user to pick broker."
            )
            print("Emails:", [e for e, _ in email_contexts[:20]])
            sys.exit(1)

        if not broker_exists(conn, mc):
            print(
                f"Broker MC {mc} not in webwise.brokers. Run load_fmcsa_brokers.py first or add the broker."
            )
            sys.exit(1)

        broker_website = get_broker_website(conn, mc)
        broker_domain = _broker_domain_from_website(broker_website)

        insert_candidates(
            conn, mc, email_contexts, "carrier_packet", evidence, broker_domain
        )
        promoted = promote_best(conn, mc)
        conn.commit()

    n = len(email_contexts)
    if promoted:
        print(f"Attached {n} emails to MC {mc}; promoted best to primary_email.")
    else:
        print(
            f"Attached {n} emails to MC {mc} (primary_email unchanged — already set or new best not 0.10+ higher)."
        )


if __name__ == "__main__":
    main()
