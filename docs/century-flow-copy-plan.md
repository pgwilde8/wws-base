# Century Flow: Copy Plan

## Approach

- **Copy** pricing, register-trucker, and onboarding to new routes with slightly changed names → Century subdomain only (you pass links manually).
- **Main site** keeps same paths; remove Century mentions from those templates.
- No branching by host in shared code; two separate flows via distinct routes and templates.

---

## 1. New Century Routes & Templates (Copy, Keep Century Copy)

| Current | Century Copy (New Name) |
|---------|-------------------------|
| `/pricing` | `/century/pricing` |
| `/register-trucker` | `/century/register-trucker` |
| `/drivers/onboarding/welcome` | `/century/onboarding/welcome` |

**Templates to copy:**

| Current Template | Century Copy |
|------------------|--------------|
| `public/pricing.html` | `public/century_pricing.html` |
| `auth/register-trucker.html` | `auth/century_register_trucker.html` |
| `drivers/onboarding_welcome.html` | `drivers/century_onboarding_welcome.html` |
| `drivers/partials/onboarding_step2b_payment.html` | `drivers/partials/century_onboarding_step2b_payment.html` |

**Century templates:** keep all Century messaging (Alma, Century Finance, approval, refund).

**Step 1 & 2:** No Century copy; they can be reused or included from the same partials. Only step2b needs a Century-specific copy.

---

## 2. Century Sub-Routes (HTMX & Checkout)

Onboarding uses HTMX and JS that hit:

- `/drivers/onboarding/check-handle`
- `/drivers/onboarding/claim-handle`
- `/drivers/onboarding/claim-mc`
- `/drivers/onboarding/create-setup-checkout` (from step2b JS)

**Option A – Century prefix routes:** Add `/century/onboarding/...` equivalents that use Century templates and a Century checkout flow.

**Option B – Shared logic, flow param:** Keep one set of routes, pass `?flow=century` (or store in session when entering from `/century/...`). More complex.

**Recommended:** Add Century routes that mirror the flow:

- `GET /century/pricing` → `century_pricing.html`
- `GET /century/register-trucker` → `century_register_trucker.html`
- `POST /century/register-trucker` → create user, redirect to `/century/onboarding/welcome`
- `GET /century/onboarding/welcome` → `century_onboarding_welcome.html` (includes step1, step2; step2b comes from claim-mc)
- `GET /century/onboarding/check-handle` → same logic, return `century_onboarding_welcome` partials where needed
- `POST /century/onboarding/claim-handle` → same logic, return `century_onboarding_step2.html` (same as main; no Century)
- `POST /century/onboarding/claim-mc` → return **century** `onboarding_step2b_payment` partial (with Century copy)
- `POST /century/onboarding/create-setup-checkout` → create Stripe session, `success_url` = existing `/drivers/onboarding/checkout-success` (which redirects to `/drivers/century-onboarding`)

`century_onboarding_welcome.html` needs HTMX targets updated to `/century/onboarding/...` instead of `/drivers/onboarding/...`.

`century_onboarding_step2b_payment.html` needs the JS fetch URL updated to `/century/onboarding/create-setup-checkout`.

---

## 3. Main Site: Remove Century

**Templates to edit (strip Century):**

| File | Changes |
|------|---------|
| `public/pricing.html` | Remove "Fast Funding Partner: Century Finance" block; change "our partner Century Finance" → "your factor" or generic wording |
| `auth/register-trucker.html` | No Century mentions; no change if already generic |
| `drivers/partials/onboarding_step2b_payment.html` | Replace Century copy with Universal: pay $25, instant access, email with app login, no approval wait; remove Century checkbox and approval text |

---

## 4. Checkout Flow Split

| Flow | create-setup-checkout | success_url | Post-payment behavior |
|------|------------------------|-------------|------------------------|
| **Century** | `/century/onboarding/create-setup-checkout` | `.../drivers/onboarding/checkout-success` | Redirect to `/drivers/century-onboarding` (existing) |
| **Universal** | `/drivers/onboarding/create-setup-checkout` | `.../drivers/onboarding/checkout-success-universal` (new) | onboard_new_driver(), email, redirect to dashboard |

- Add `checkout-success-universal` route for Universal flow.
- Add `trucker_profiles.setup_fee_paid` and gatekeeper logic (unlock when `setup_fee_paid` or Century approved).

---

## 5. Internal Links (Century Flow)

In `century_pricing.html`:

- "Join the Fleet" → `/century/register-trucker` (not `/register-trucker`)

In `century_register_trucker.html`:

- Form action → `/century/register-trucker`
- Post-success redirect → `/century/onboarding/welcome`

In `century_onboarding_welcome.html` (and step partials):

- HTMX `hx-get` / `hx-post` → `/century/onboarding/...` instead of `/drivers/onboarding/...`

---

## 6. File Summary

**New files:**
- `public/century_pricing.html` (copy of pricing, Century kept)
- `auth/century_register_trucker.html` (copy, links to `/century/...`)
- `drivers/century_onboarding_welcome.html` (copy, HTMX → `/century/onboarding/...`)
- `drivers/partials/century_onboarding_step2b_payment.html` (copy of step2b, Century kept, fetch → `/century/onboarding/create-setup-checkout`)

**New routes:**
- `GET /century/pricing`
- `GET /century/register-trucker`, `POST /century/register-trucker`
- `GET /century/onboarding/welcome`
- `GET /century/onboarding/check-handle`, `POST /century/onboarding/claim-handle`, `POST /century/onboarding/claim-mc`
- `POST /century/onboarding/create-setup-checkout`

**Modified files:**
- `public/pricing.html` – remove Century
- `drivers/partials/onboarding_step2b_payment.html` – Universal copy
- Add `checkout-success-universal`, `setup_fee_paid`, gatekeeper (for Universal flow)

---

## 7. Century URL (Manual Use)

```
https://century.greencandledispatch.com/century/pricing
https://century.greencandledispatch.com/century/register-trucker
```

Nginx: `century.greencandledispatch.com` → same app (proxy to 8990). No app-level host branching; routing is by path prefix `/century/`.

---

## 8. Implemented

- Century flow: all routes and templates added
- Main site: Century stripped from pricing and step2b (Universal copy)
- `checkout-success-universal`: onboard, email with app.greencandledispatch.com login, redirect to dashboard
- Gatekeeper: unlock if `setup_fee_paid` OR `factoring_referrals.status == 'APPROVED'`
- Migration: `sql/migrate_setup_fee_paid.sql` — run: `psql $DATABASE_URL -f sql/migrate_setup_fee_paid.sql`
