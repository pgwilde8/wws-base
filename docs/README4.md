# Green Candle Dispatch — Application Reference

This document describes the **`app`** package: structure, routes, services, and data flows for the Green Candle Dispatch platform (AI-powered dispatch + $CANDLE rewards for owner-operators).

---

## 1. Project overview

**Green Candle Dispatch** is a DePIN-style SaaS for trucking: an AI dispatcher that works with load boards and factoring, plus a **2% network fee** that is partly rebated to drivers as **$CANDLE** tokens (75% to driver stash, 25% burned). Drivers see a “savings vault” with a 6-month vesting lock; the goal is a UPay-powered debit card for spendable rewards.

- **Backend:** FastAPI, Jinja2, PostgreSQL (`webwise` schema).
- **Frontend:** Jinja2 + Tailwind; HTMX for partials; optional OpenAI Assistant for site chat.
- **Integrations:** DigitalOcean Spaces (BOL storage), OTR Solutions (factoring bridge), Base/UPay (future token/card).

---

## 2. Application structure

```
app/
├── main.py                 # FastAPI app, dotenv, static mount, router includes
├── core/
│   ├── config.py           # Settings (e.g. STORAGE_BUCKET_PREFIX)
│   └── deps.py             # DB engine, Session, templates, auth, session cookie, OpenAI
├── models/
│   ├── bootstrap_db.py     # Base, engine; run as script to create webwise schema + tables
│   ├── user.py             # User ORM (webwise.users)
│   ├── trucker_profile.py  # TruckerProfile ORM (webwise.trucker_profiles)
│   ├── negotiation.py      # Negotiation, NegotiationStatus (webwise.negotiations)
│   └── notification.py    # Notification (webwise.notifications)
├── routes/
│   ├── public.py           # Public pages, testimonials, /api/chat, /find-loads
│   ├── auth.py             # Login (admin + client), logout, register-trucker, register
│   ├── admin.py            # Dashboard, revenue-stats, testimonials, negotiations, leads
│   ├── client.py           # Client dashboard, notifications, BOL upload, savings API/views
│   └── legal.py            # TOS, privacy, notice-of-assignment (private)
├── schemas/
│   └── load.py             # LoadBase, LoadResponse, LoadStatus (Pydantic)
├── services/
│   ├── ai_agent.py         # OpenAI draft for broker negotiation emails
│   ├── factoring.py        # push_invoice_to_factor (OTR-style payload, mock)
│   ├── tokenomics.py       # credit_driver_savings (6‑month lock), execute_buyback_and_send (Base)
│   ├── storage.py          # DigitalOcean Spaces: upload_bol, list_buckets
│   ├── payments.py         # RevenueService: buyback stats, trucker contribution
│   └── load_board.py       # LoadBoardService (e.g. fetch_current_loads)
├── scripts/
│   ├── add_factoring_columns.py  # Add factoring_company, referral_status to webwise.users
│   └── add_referrals.py          # Referral codes / referred_by (if used)
├── static/                 # Static files (e.g. audio for notifications)
└── templates/              # Jinja2: layout, public, admin, auth, drivers, legal, partials
```

---

## 3. Routes summary

| Area    | Paths | Purpose |
|---------|--------|--------|
| **Public** | `/`, `/about`, `/services`, `/pricing`, `/faq`, `/token`, `/contact`, `/fleet-builder` | Marketing and info pages. |
| | `/privacy-policy`, `/terms-of-service` | Legal (may point to legal templates). |
| | `/testimonials`, `/testimonials/submit` | Testimonials list + form. |
| | `/api/chat` (POST) | OpenAI Assistant chat (site widget). |
| | `/find-loads` (GET) | HTMX partial: load list. |
| **Auth** | `/login`, `/login/client`, `/admin/login` | Login choice, client login, admin login. |
| | `/auth/client` (POST), `/auth/admin` (POST) | Client/admin login. |
| | `/logout` | Clear session, redirect. |
| | `/register-trucker`, `/auth/register-trucker` (GET/POST) | Trucker signup (user + trucker_profile, factoring/referral fields). |
| | `/register` (GET/POST) | Generic register (ref_code; POST may be stub). |
| **Driver** | `/drivers/dashboard` | Driver dashboard (auth required). |
| | `/drivers/my-contribution` | HTMX partial: win count + $CANDLE contribution. |
| | `/drivers/notifications/poll`, `/drivers/notifications/{id}/read` | Notifications poll + mark read. |
| | `/negotiate/{load_id}` (POST) | AI draft for negotiation. |
| | `/loads/upload-bol` (POST) | BOL upload → Spaces, 2% fee, factoring bridge, credit driver savings. |
| | `/savings/dashboard/{mc_number}` | JSON: driver savings (locked/unlocked, next vest, history). |
| | `/savings-view`, `/savings-test` | Savings page (auth) and test endpoint. |
| **Admin** | `/admin/dashboard` | Admin dashboard (require_admin). |
| | `/admin/revenue-stats` | Buyback stats (HTMX). |
| | `/admin/testimonials/{id}/approve`, `reject` | Testimonial moderation. |
| | `/admin/negotiations/{id}/mark-replied`, `mark-won` | Negotiation workflow. |
| | `/admin/leads` | Leads dashboard (OTR_REQUESTED / EXISTING_CLIENT); redirect to login if not admin. |
| **Legal** | `/legal/terms-of-service`, `/legal/tos` | Public TOS. |
| | `/legal/privacy` | Public privacy policy. |
| | `/legal/notice-of-assignment` (GET/POST) | Private; pre-filled from logged-in driver. |

---

## 4. Key flows

### 4.1 Trucker registration

- **GET** `/register-trucker` or `/auth/register-trucker` → form (email, password, MC, carrier, factoring questions).
- **POST** `/auth/register-trucker`: create `webwise.users` (role=client, factoring_company, referral_status) and `webwise.trucker_profiles`; redirect to client dashboard or login.

### 4.2 BOL upload → factoring → driver savings

1. **POST** `/loads/upload-bol`: `load_id`, `mc_number`, `file`.
2. **Storage:** `upload_bol()` → DigitalOcean Spaces; returns public BOL URL.
3. **Fee:** 2% of `final_rate` (e.g. 3000 → $60).
4. **Factoring:** `push_invoice_to_factor(load_data_dict, bol_url)` builds OTR-style payload (payment_instructions: carrier_payout, dispatch_fee_deduction, remit_fee_to). Mock response for now.
5. **Savings:** On success, `credit_driver_savings(db, load_id, mc_number, fee_usd)` inserts into `webwise.driver_savings_ledger` with 6‑month `unlocks_at`.
6. Response includes `bank_status` and fee fields.

### 4.3 Driver savings (vault)

- **GET** `/savings/dashboard/{mc_number}`: aggregates `driver_savings_ledger` (total, locked/unlocked, next vesting date, recent rows).
- **GET** `/savings-view`: auth required; MC from profile; renders savings page with vault data.

### 4.4 Admin: revenue and wins

- **RevenueService** (in `payments.py`): from `webwise.negotiations` where status = 'won', sums `final_rate` and computes 2% `candle_buyback_usd`.
- **Admin dashboard** uses `/admin/revenue-stats` (HTMX) for buyback widget.
- **mark-won** updates negotiation and returns `buyback_accrued`; can trigger HTMX refresh for driver contribution.

### 4.5 Lead capture (Money Board)

- Registration sets `referral_status` (e.g. OTR_REQUESTED, EXISTING_CLIENT) and `factoring_company`.
- **GET** `/admin/leads`: list users where `referral_status != 'NONE'` with trucker profile; stats for OTR requested vs existing; “Send Link” (mailto) for OTR.

---

## 5. Database (webwise schema)

- **users** — id, email, password_hash, role, is_active, factoring_company, referral_status, referred_by, referral_code, created_at, last_login.
- **trucker_profiles** — id, user_id, display_name, carrier_name, mc_number, truck_identifier, created_at, updated_at.
- **negotiations** — id, load_id, origin, destination, rates, ai_draft_*, broker_reply, status, trucker_id, created_at, updated_at.
- **notifications** — id, trucker_id, message, notif_type, is_read, created_at.
- **driver_savings_ledger** — id, driver_mc_number, load_id, amount_usd, amount_candle, earned_at, unlocks_at, status (LOCKED/VESTED/CLAIMED), tx_hash.
- **testimonials** — id, client_name, email, testimonial_text, rating, is_approved, etc.
- **projects** — demo/placeholder.

Bootstrap: run `python -m app.models.bootstrap_db` (or equivalent) with `DATABASE_URL` set; creates schema and tables, seeds admin (and optional client) if empty.

---

## 6. Services (short reference)

| Service | Role |
|--------|------|
| **factoring** | `push_invoice_to_factor(load_data, bol_url)` → invoice payload + payment_instructions; mock success. |
| **tokenomics** | `credit_driver_savings(db, load_id, mc_number, fee_usd)` → insert into driver_savings_ledger (6‑month lock). Optional `execute_buyback_and_send` (Base/web3). |
| **storage** | DO Spaces: `upload_bol(file, mc_number, load_id)` → URL; `list_buckets()`. |
| **payments** | `RevenueService.get_weekly_buyback_stats(db)`, `get_buyback_stats_from_engine(engine)`, `get_trucker_contribution(engine, trucker_id)`. |
| **ai_agent** | `AIAgentService.draft_negotiation_email(load_data)` → OpenAI broker-negotiation draft. |
| **load_board** | `LoadBoardService.fetch_current_loads()` → used by `/find-loads`. |

---

## 7. Configuration (environment)

- **Database:** `DATABASE_URL` (PostgreSQL).
- **Session:** `SECRET_KEY`, `SESSION_COOKIE_NAME`, `SESSION_TTL_MINUTES`.
- **OpenAI:** `OPENAI_API_KEY`, `ASSISTANT_ID` (for `/api/chat`).
- **DigitalOcean Spaces:** `DO_SPACES_KEY`, `DO_SPACES_SECRET`, `DO_SPACES_REGION`, `DO_SPACES_BUCKET`, `DO_SPACES_ENDPOINT`.
- **Bootstrap:** `ADMIN_EMAIL`, `ADMIN_PASSWORD`, optional `CLIENT_EMAIL` / `CLIENT_PASSWORD`.
- **Tokenomics (optional):** `WEB3_PROVIDER_URL`, `WALLET_PRIVATE_KEY`, `WALLET_ADDRESS`.

---

## 8. Run and bootstrap

```bash
cd /srv/projects/client/dispatch
source .venv/bin/activate   # or .venv\Scripts\activate on Windows

# One-time DB setup
python -m app.models.bootstrap_db

# Run app (default port 8990)
uvicorn app.main:app --host 0.0.0.0 --port 8990 --reload
```

- **Public:** `/`, `/services`, `/pricing`, `/faq`, `/token`, etc.
- **Client login:** `/login/client` → dashboard, `/savings-view`.
- **Admin:** `/admin/login` (e.g. admin@example.com / changeme123) → `/admin/dashboard`, `/admin/leads`.

---

## 9. Related project files

- **docs/** — README.MD (vision/whitepaper), README1.md (URLs/commands), DB_COMMANDS.md, risks.md, One-Pager.
- **sql/create_driver_savings_ledger.sql** — Standalone DDL for driver_savings_ledger.
- **create_test_client.py**, **test_bol_upload.py**, **test_savings_credit.py**, **test_savings_dashboard.py** — Local/test helpers.
- **TROUBLESHOOTING.md** — Common issues (DB, env, savings credit).

This README focuses on the **app** package; for product vision and roadmap see the main README and docs in the repo root.
