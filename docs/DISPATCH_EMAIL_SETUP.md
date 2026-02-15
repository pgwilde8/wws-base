# Dispatch Email Setup: pgwilde@gcdloads.com and Driver Emails

## Strategy: Catch-All (No Per-Address Creation)

**gcdloads.com uses a catch-all** — all *@gcdloads.com deliver to `dispatch@gcdloads.com`. No need to create aliases per driver.

---

## What Happens When a Driver Claims a Handle

`onboarding_claim_handle` (Step 1) does **only**:

1. **Database** — INSERT or UPDATE `trucker_profiles` with `display_name = "pgwilde"`
2. **Next step** — Returns `onboarding_step2.html` (MC/DOT form)

No email-provider API calls. No alias creation.

---

## How Emails Work

| Flow | How |
|------|-----|
| **Outbound** | Send FROM `pgwilde+load123@gcdloads.com` via MXRoute SMTP |
| **Inbound** | Brokers reply to `pgwilde+load123@gcdloads.com` → catch-all delivers to `dispatch@gcdloads.com` → `inbound_listener.py` reads it |

---

## Do Not Implement

- DirectAdmin API
- Per-driver alias creation

Rely purely on catch-all.
