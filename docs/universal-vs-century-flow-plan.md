# Universal vs Century Flow: Plan

## Summary

**Main website (greencandledispatch.com / app.greencandledispatch.com):**  
We don't care who they use. New Universal flow: pay $25/truck → get email → login to app → dashboard unlocks immediately. No Century approval wait.

**Century (century.greencandledispatch.com):**  
Manual referral path. When you find "new guys with no factor" who want out, you send them to Century. Alma experience, high-touch, approval-based.

---

## Current State

| Step | Current (Century) |
|------|-------------------|
| 1 | register-trucker → onboarding (name, MC) → step 2b |
| 2 | Stripe $25/truck checkout |
| 3 | checkout-success → redirect to **century-onboarding** |
| 4 | Driver submits Century form → factoring_referrals (PENDING) |
| 5 | Admin approves → onboard_new_driver(), approval email, dashboard unlocks |
| Gatekeeper | Dashboard locked until factoring_referrals.status == 'APPROVED' |

---

## New State: Two Flows

### Universal Flow (main site)

| Step | New behavior |
|------|--------------|
| 1 | Same: register-trucker → onboarding → step 2b |
| 2 | Same: Stripe $25/truck checkout |
| 3 | checkout-success → **call onboard_new_driver()** → send welcome email with **app.greencandledispatch.com** login → redirect to dashboard |
| 4 | — (no Century form) |
| 5 | — (no approval wait) |
| Gatekeeper | Unlock if `setup_fee_paid == true` (new column) |

### Century Flow (century subdomain)

| Step | Unchanged |
|------|-----------|
| 1–3 | Same as current (checkout-success → century-onboarding) |
| 4 | Same: submit Century form → factoring_referrals |
| 5 | Same: admin approves → onboard_new_driver(), email, unlock |
| Gatekeeper | Unlock if factoring_referrals.status == 'APPROVED' |

---

## How We Branch

**Host header** (or `request.base_url`):

- `century.greencandledispatch.com` → Century flow
- `greencandledispatch.com`, `app.greencandledispatch.com`, or default → Universal flow

In `checkout-success`:

```python
host = request.headers.get("host", "")
if "century." in host.lower():
    # Century: redirect to century-onboarding (current)
    return RedirectResponse(url="/drivers/century-onboarding", status_code=303)
else:
    # Universal: onboard immediately, email, redirect to dashboard
    onboard_new_driver(...)
    send_onboarding_comms(login_url="https://app.greencandledispatch.com/login/client")
    # Set setup_fee_paid on trucker_profile
    return RedirectResponse(url="/drivers/dashboard", status_code=303)
```

---

## Gatekeeper Change

**Current:**

```python
if century_status is None:
    return RedirectResponse(url="/drivers/century-onboarding", ...)
```

**New:**

```python
# Unlock if: Century approved OR Universal (paid setup fee)
if factoring_referrals.status == 'APPROVED':
    pass  # allow
elif trucker_profile.setup_fee_paid:
    pass  # Universal flow, allow
elif century_status is None and not setup_fee_paid:
    return RedirectResponse(url="/drivers/century-onboarding", ...)
```

---

## Database Change

Add to `trucker_profiles`:

```sql
ALTER TABLE webwise.trucker_profiles
ADD COLUMN IF NOT EXISTS setup_fee_paid BOOLEAN DEFAULT false;
```

- **Universal checkout-success:** Set `setup_fee_paid = true` when we onboard immediately.
- **Century flow:** Leave false; unlock via factoring_referrals.status.

---

## Email / Login URL

**Universal flow:** Welcome email login URL = `https://app.greencandledispatch.com/login/client`

**Century flow:** Keep current `LOGIN_URL` (or use century subdomain if they stay there).

`notifications.send_onboarding_comms()` already takes a `login_url`-like concept via `BASE_URL` / `LOGIN_URL`. Add `APP_BASE_URL` or pass explicit login URL for Universal.

---

## What Stays the Same

- $25/truck Stripe product (already exists)
- `create_setup_checkout_session`, `retrieve_and_verify_session`
- register-trucker, onboarding steps 1 and 2b
- `onboard_new_driver()` (called at different times: checkout-success for Universal, admin-approve for Century)
- Century onboarding form, admin approvals, Alma emails
- `century.greencandledispatch.com` = Century flow (once subdomain is wired)

---

## Implementation Checklist

1. **Migration:** Add `setup_fee_paid` to `trucker_profiles`.
2. **checkout-success:** Branch on Host; Universal path: onboard_new_driver, set setup_fee_paid, send email with app login URL, redirect to dashboard.
3. **Gatekeeper (dashboard):** Unlock if `factoring_referrals.status == 'APPROVED'` **OR** `trucker_profiles.setup_fee_paid == true`.
4. **Notifications:** Use app.greencandledispatch.com login URL for Universal welcome email.
5. **Nginx/DNS:** Ensure `app.greencandledispatch.com` points at the app (for login links in emails).

---

## Century as Manual Referral

- Main site links (pricing, register-trucker) stay on main domain → Universal flow.
- You give Century to specific drivers by sending them to `https://century.greencandledispatch.com/register-trucker` (or equivalent).
- No code duplication: same app, same routes; behavior branches on Host.
