# Green Candle Dispatch — Current System (Source of Truth)
2/16/26
**Last updated:** Use this file as the single place for "what we actually have." When you add features or change flows, update this doc. Old/legacy notes stay in other docs and are marked as such below.

---

## How to use this doc

| Goal | Do this |
|------|--------|
| **Describe the current system** | Everything in this file is current. |
| **Add something new** | Implement in code, then add a short bullet or section here. |
| **Deprecate something** | Move its description to the "Legacy / deprecated" section at the bottom, or to `docs/legacy/`. |
| **Mixed-up notes elsewhere** | Treat other files in `docs/` as reference only; this file wins for "what is live." |

---

## 1. What the app is

- **Product:** Green Candle Dispatch — freight load negotiation + driver rewards ($CANDLE, buyback, automation fuel).
- **Stack:** FastAPI, Jinja2 templates, HTMX, SQLAlchemy (raw SQL + ORM for some models), PostgreSQL schema `webwise`.
- **Entrypoint:** `app/main.py` → `uvicorn` on `PORT` (default 8990).

---

## 2. Routes (follow the code here)

| Prefix / area | Router module | Purpose |
|---------------|---------------|---------|
| `/` | `app.routes.public` | Public pages (landing, pricing, testimonials, token, etc.) |
| `/` | `app.routes.auth` | Login, register, logout (session cookie) |
| `/admin/*` | `app.routes.admin` | Admin dashboard, testimonials, negotiations (mark-won, mark-replied), drivers, cards, broker lookup, leads, etc. |
| `/admin/burn/*` | `app.routes.admin_burn` | Burn batches: create, list, get one, reserve, execute |
| `/ops/*` | `app.routes.ops_treasury` | `GET /ops/treasury` — treasury stats (admin-only) |
| `/webhooks/*` | `app.routes.webhooks` | `POST /webhooks/stripe`, `POST /webhooks/factoring` — revenue ingestion |
| `/` (client) | `app.routes.client` | Driver-facing: dashboard, negotiations, loads, factoring, debit card, savings/vault, profile, etc. |
| `/` | `app.routes.legal` | Legal pages |
| `/api/ingest/*` | `app.routes.ingest` | Ingest API |
| `/api/*` | `app.routes.api` | Scout heartbeat and other API |

Router registration: `app/main.py` (see `app.include_router(...)`).

---

## 3. Database (webwise schema)

- **Where:** PostgreSQL, schema `webwise`. Connection via `app.core.deps.engine` and `get_db()` for sessions.
- **Migrations:** Raw SQL in `sql/`. Run with: `set -a && source .env && set +a && psql "$DATABASE_URL" -f sql/<file>.sql`

### Current tables (in use)

| Table | Purpose |
|-------|---------|
| `webwise.driver_savings_ledger` | **Driver vault:** per-driver credits (amount_usd, amount_candle, unlocks_at, status). Do not change for treasury/burn. |
| `webwise.platform_revenue_ledger` | **Platform revenue:** every USD inflow (source_type, gross_amount_usd, burn_reserved_usd, burn_batch_id, status, **burn_eligible**). Revenue is RECORDED at mark-won with burn_eligible=false; factoring webhook sets burn_eligible=true. |
| `webwise.burn_batches` | **Burn audit:** each burn run (period, burn_rate_bps, usd_reserved, usd_spent, candle_burned, swap_tx_hash, burn_tx_hash, status, chain). |
| `webwise.treasury_wallets` | On-chain wallet refs (wallet_name, address, chain). |
| `webwise.users` | Auth (email, password_hash, role, etc.). |
| `webwise.trucker_profiles` | Driver profiles (mc_number, reward_tier, etc.). |
| `webwise.negotiations` | Load negotiations (load_id, trucker_id, status, final_rate, etc.). |
| `webwise.loads` | Loads (ref_id, discovered_by_id, etc.). |
| `webwise.notifications` | In-app notifications for drivers. |
| `webwise.debit_cards`, `webwise.claim_requests`, etc. | Cards and claims. |
| `webwise.brokers`, `webwise.broker_emails` | Broker data. |
| Plus: testimonials, projects, messages, load_documents, autopilot_settings, scout_status, … | See `sql/` and `app/models/` for full list. |

### Key SQL migration files (current)

| File | Purpose |
|------|---------|
| `sql/create_platform_treasury_burn.sql` | Creates platform_revenue_ledger, burn_batches, treasury_wallets; FK, indexes, burn_eligible. |
| `sql/migrate_platform_treasury_burn_tightening.sql` | For existing DBs: burn_eligible, reserve index, FK, chain on burn_batches. |
| `sql/create_driver_savings_ledger.sql` | Driver vault ledger (unchanged by treasury work). |

---

## 4. Key flows (current)

### Auth

- Login/register in `app.routes.auth`. Session in cookie (`SESSION_COOKIE_NAME`), signed with `SECRET_KEY`. Roles: admin, client (driver).

### Mark-won → platform revenue → burn

1. **Mark-won** (`POST /admin/negotiations/{id}/mark-won` in `app.routes.admin`): Sets negotiation to won, writes to `driver_savings_ledger` (driver vault), and inserts **platform_revenue_ledger** with source_type=DISPATCH_FEE, **burn_eligible=false**.
2. **Factoring webhook** (`POST /webhooks/factoring`): Records referral/dispatch revenue; if `load_id` present, calls `confirm_dispatch_settlement(engine, load_id)` so that load's dispatch row gets **burn_eligible=true**.
3. **Weekly burn job** (`app.jobs.weekly_burn`): Creates batch, reserves only rows with **burn_eligible=true**, burn_batch_id IS NULL, status=RECORDED, gross_amount_usd>0. Execute (swap + burn) is separate (ChainGateway placeholder).

### Driver vault (unchanged by treasury)

- `driver_savings_ledger`: credits, unlock time, status (e.g. CREDITED, CLAIMED). Claim flow in `app.services.payments` and related routes.

### Treasury visibility

- `GET /ops/treasury` (admin): total_revenue_usd, total_burned_usd, last_burn_tx_hash, last_burn_at. Implemented in `app.services.burn.get_treasury_stats`.

---

## 5. Where things live in code

| Area | Location |
|------|----------|
| App bootstrap, routes mount | `app/main.py` |
| Auth, session, engine, get_db, get_engine | `app.core.deps` |
| Treasury/burn models | `app.models.treasury` |
| Burn business logic | `app.services.burn` |
| Weekly burn job | `app.jobs.weekly_burn` |
| Admin burn API | `app.routes.admin_burn` |
| Ops treasury API | `app.routes.ops_treasury` |
| Webhooks (Stripe, factoring) | `app.routes.webhooks` |
| Mark-won + platform revenue insert | `app.routes.admin` (mark_negotiation_won) |
| Driver vault / payments | `app.services.payments`, `app.routes.client` |
| Negotiations, loads, AI | `app.services.negotiation`, `app.services.ai_*`, `app.models.negotiation` |
| Templates | `app/templates/` |
| Static | `app/static/` |
| Config / env | `.env`, `app.core.config` |

---

## 6. Legacy / other docs

- **Other files in `docs/`** (e.g. burn.md, exe-summary.md, README1–4, risks.md, seed investors, $Candle.md, etc.) may mix legacy ideas with current. **For "what is actually implemented," use this file.**
- When you deprecate a feature or an old design, either:
  - Add a short "Legacy" subsection here and point to the old doc, or
  - Move the old note to `docs/legacy/` and link from here.

---

## 7. Quick checklist for "what we have"

- [ ] FastAPI app, webwise schema, raw SQL migrations + some ORM models.
- [ ] Driver vault: `driver_savings_ledger` (unchanged).
- [ ] Platform revenue: `platform_revenue_ledger` with `burn_eligible`; mark-won inserts with burn_eligible=false; factoring webhook sets burn_eligible=true.
- [ ] Burn: `burn_batches`, reserve-only when batch CREATED and row burn_eligible=true, burn_batch_id NULL; execute_batch() for tx hashes.
- [ ] Routes: public, auth, admin, admin_burn, client, legal, ingest, api, ops_treasury, webhooks.
- [ ] Weekly job: create batch, reserve, optional DRY_RUN and MAX_BURN_USD_PER_BATCH.

---

*When in doubt: follow `app/main.py` → routers → services/models; DB = `webwise` + `sql/`.*
