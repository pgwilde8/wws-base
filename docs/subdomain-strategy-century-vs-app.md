# Subdomain Strategy: century vs app (Discussion)

## Goal

- **century.greencandledispatch.com** → Century-specific flow (Alma experience): pricing → register-trucker → Stripe → century-onboarding.
- **app.greencandledispatch.com** → Universal portal (later: Connect Factor + card on file).
- Keep existing Century code; branch by subdomain, don’t remove it.

---

## Current Flow (No Subdomains Yet)

- **Main site** (e.g. greencandledispatch.com): `/pricing`, `/register-trucker`, then Stripe → `/drivers/onboarding/checkout-success` → `/drivers/century-onboarding`.
- All of that is one FastAPI app on one host (e.g. greencandledispatch.com → nginx → 127.0.0.1:8990).

---

## 1. Pointing pricing / register-trucker to the Century subdomain

**Idea:** Any link that should start the “Alma experience” goes to the **century** subdomain instead of the current domain.

**Options:**

### A. Same app, same routes, different host (recommended)

- **DNS:** `century.greencandledispatch.com` → same server as today.
- **Nginx:** Add a server block for `century.greencandledispatch.com` that proxies to the **same** FastAPI app (e.g. `127.0.0.1:8990`). No second app, no copied code.
- **Links:** On the main site (or wherever you want “Alma flow” to start), point “Join the Fleet” / “Get started” to:
  - `https://century.greencandledispatch.com/pricing`
  - `https://century.greencandledispatch.com/register-trucker`
- **Result:** User lands on century subdomain → same `/pricing` and `/register-trucker` as today → same Stripe → same `/drivers/century-onboarding`. No new routes, no duplicate templates.

**What to change in code (minimal):**

- Add a config or helper for “Century base URL”, e.g. `CENTURY_BASE_URL=https://century.greencandledispatch.com`.
- In templates/routes where you want to send users to the Century flow, use that base URL:
  - e.g. “Join the Fleet” → `{{ century_base_url }}/register-trucker` or `{{ century_base_url }}/pricing`.
- Optionally, pass `century_base_url` (or a boolean `is_century_site`) from a middleware that reads `Host` so the same template can say “Sign up with Century” and link to the century subdomain.

No need to “copy the code” or add a “new page with new name” for the Century flow unless you want separate paths (see B).

### B. Copy code and give the Century flow its own path names

- Add routes like `/century/pricing` and `/century/register-trucker` (or `/century/signup`) that render the **same** templates (or copies of them).
- Nginx: `century.greencandledispatch.com` → same app.
- Main site links → `https://century.greencandledispatch.com/century/register-trucker` (or `/century/pricing`).
- **Pros:** Clear in the URL that this is the “Century” flow; you could later restrict the century subdomain to only serve `/century/*` and redirect the rest to app.
- **Cons:** Duplicate route definitions (and possibly duplicate templates). More to maintain.

**Recommendation:** Start with **A** (same routes, different host + link to century subdomain). Add path-based names like `/century/...` only if you want explicit “Century-only” URLs or different nginx rules per path.

---

## 2. What actually needs to “point to” the new subdomain

Only the **entry points** that start the Alma flow need to point at the Century subdomain:

- **Links that should start the Century flow** (e.g. “Join the Fleet”, “Get the Alma experience”, primary CTA on pricing):
  - Today: `href="/register-trucker"` or `href="/pricing"`.
  - After: `href="https://century.greencandledispatch.com/register-trucker"` or `.../pricing` (or use `CENTURY_BASE_URL` in templates).

Places that currently link to pricing/register-trucker (so you can decide which should go to century):

- `public/pricing.html` → “Reserve your spot” / register-trucker, and bottom CTA.
- `public/protocol.html` → register-trucker.
- `public/services.html` → “Join the Fleet” → register-trucker.
- `public/our-token.html` → register-trucker.
- `layout/navbar.html` → pricing, register-trucker.
- `auth/client-login.html` → “Join the Fleet” → register-trucker.

You can:

- Send **all** of these to the century subdomain (everything driver-related goes through Alma), or  
- Send only some (e.g. “Get the Alma experience” / “Century funding” CTA → century; generic “Sign up” → app later).

No backend route logic has to change for “pointing” — only **link hrefs** (and optionally a base URL in config).

---

## 3. Nginx and DNS (concrete)

- **DNS:**  
  - `century.greencandledispatch.com` → same A (or CNAME) as `greencandledispatch.com` (or the server that currently serves the app).

- **Nginx:**  
  - Duplicate the existing `server { ... }` (or `location /`) that proxies to `127.0.0.1:8990`, and set `server_name century.greencandledispatch.com;`.  
  - Same proxy pass, same app. The app can read `Host: century.greencandledispatch.com` if you need to branch later (e.g. gatekeeper, or which onboarding to show).

No second app or copied code required for “pointing” pricing/register-trucker to the new subdomain.

---

## 4. Later: gatekeeper and Universal flow

When you add the Universal flow and the gatekeeper:

- **Same app** can serve both subdomains.
- In the gatekeeper (and any “onboarding” redirect logic), use the **Host** header (or a config derived from it):
  - `century.greencandledispatch.com` → require `factoring_referrals.status == 'APPROVED'` (Century flow).
  - `app.greencandledispatch.com` (or default) → allow `trucker_profiles.card_on_file == True` (Universal flow).
- No need to “copy” the gatekeeper code — one function, two branches based on host (or a “flow type” set from host).

---

## 5. Summary

| Question | Answer |
|----------|--------|
| How do we point pricing/register-trucker to the century subdomain? | Change links (and optionally a base URL in config) so they use `https://century.greencandledispatch.com/pricing` and `.../register-trucker`. No new routes required. |
| Do we need to copy code or add a new page with a new name for the Century flow? | No. Same routes and templates; they’re just reached via the century subdomain. You can add `/century/...` paths later if you want explicit Century-only URLs. |
| What do we need in infra? | DNS for `century.greencandledispatch.com`; nginx server block for that host proxying to the same FastAPI app. |
| Where do we change links? | Templates (and any redirects) that should start the “Alma” flow: e.g. pricing, register-trucker, “Join the Fleet”, “Get the Alma experience”. |

If you tell me which links should go to Century (all driver signup vs only some CTAs), I can outline the exact template/config changes next (e.g. add `CENTURY_BASE_URL` and where to use it).
