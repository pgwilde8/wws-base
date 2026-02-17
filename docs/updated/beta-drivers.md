Yes — this is exactly the right move. You should create a **separate Beta Driver onboarding flow and isolated “Beta Environment” inside your existing system**, not a completely separate app. This lets you onboard drivers quickly without Stripe, without breaking your production billing logic, and without rewriting your architecture later.

The key is isolation at the **account level**, not the system level.

---

# The correct approach: Beta Drivers inside the same system, flagged as beta

Do NOT build a separate app.

Do NOT fork your codebase.

Instead, add a simple flag:

```
drivers.is_beta = true
```

This gives you full control.

Your existing system continues working normally.

Beta drivers bypass Stripe and billing logic automatically.

---

# What the beta flow should look like

## Step 1: Beta signup form (no Stripe)

Create a page:

```
/beta/apply
```

Form collects:

* Name
* Email
* Phone
* MC number
* Truck type
* Preferred lanes
* Factoring company (OTR, RTS, Apex, etc.)
* Experience level

This stores record in:

```
beta_driver_applications
```

status:

```
PENDING
```

---

## Step 2: You approve them manually (admin panel)

Admin clicks:

```
Approve
```

System creates real driver account:

```
drivers table:

email
password_hash
mc_number
is_beta = true
```

No Stripe customer created.

No billing created.

---

## Step 3: Driver logs in normally

They use your existing login page:

```
/login
```

System checks:

```
if driver.is_beta:
    bypass Stripe requirements
```

Everything else works normally.

---

# Step 4: Beta drivers use full system normally

They can:

* run scouts
* negotiate loads
* upload BOL
* see settlement ledger
* earn CANDLE credits

Your existing logic works unchanged.

Because revenue still comes from factoring.

Not Stripe.

---

# Step 5: Your revenue pipeline still works perfectly

When load completes:

Your system already does:

```
record_revenue()
insert driver_savings_ledger
insert platform_revenue_ledger
```

Beta drivers generate real platform revenue.

No Stripe needed.

Stripe is only needed later for call packs, automation, etc.

---

# Step 6: Add simple visual indicator for beta drivers

Example dashboard banner:

```
BETA DRIVER ACCOUNT
Setup fee waived
Special early access status
```

This makes them feel special.

---

# Minimal database change required

Just add:

```
ALTER TABLE drivers
ADD COLUMN is_beta BOOLEAN DEFAULT false;
```

That’s it.

Everything else already works.

---

# Do NOT create separate backend or separate codebase

Bad approach:

```
beta.green-candle.com
separate database
separate code
```

This creates major problems later.

You would need to migrate users manually.

Avoid this.

---

# Correct architecture model

Single system.

Single database.

Single backend.

Just:

```
drivers.is_beta = true
```

Everything else flows normally.

---

# Optional: Beta applications table

```
beta_driver_applications

id
name
email
phone
mc_number
truck_type
status (PENDING, APPROVED, REJECTED)
created_at
```

When approved → create drivers record.

---

# Your burn system works perfectly with beta drivers

Because burn triggers on:

```
platform_revenue_ledger
```

which comes from:

```
factoring settlement
```

Not Stripe.

So beta drivers contribute to burn.

Fully compatible.

---

# Real-world companies do exactly this

Uber did this.

Airbnb did this.

Stripe did this.

They onboarded users manually before automated billing.

You are doing it correctly.

---

# Your immediate implementation plan

Create:

```
/beta/apply page
beta_driver_applications table
drivers.is_beta flag
```

No other changes needed.

Your system is already ready.

---

# Result

You can onboard:

```
5 drivers
10 drivers
20 drivers
```

with zero Stripe integration needed.

Revenue flows normally.

Ledger works normally.

Burn system works normally.

Token system works normally.

---

If you want, I can write the exact SQL migration and FastAPI routes for `/beta/apply` and `/admin/beta/approve` that fit your existing project structure.

You’re set on the tech. Now the next steps are **ops + onboarding experience** so you can walk into a truck stop and reliably turn “interest” into “active loads run through the system.”

Here’s the exact “beta family” onboarding playbook from this point.

---

## 1) Build your “Beta Family” onboarding assets

### A) One-page flyer (print + QR)

Must include only:

* **1 sentence**: “AI dispatch that only charges 2% after you get paid.”
* 3 bullets:

  * Finds loads + drafts broker emails
  * Paperwork + factoring packet support
  * Settlement ledger (see every dollar + reward)
* QR code → `/beta/apply`

### B) One short onboarding message (SMS template)

After approval, text:

* login URL
* email
* temp password
* what to do first (below)

Example structure:

1. “Login”
2. “Set your lanes + truck”
3. “Run your first scout”
4. “Reply ‘HELP’ anytime”

---

## 2) Your “Beta Driver Setup” inside the app (first login checklist)

When a beta logs in, they should see a simple “3-step” screen:

1. **Confirm MC + truck type**
2. **Set lanes + min rate**
3. **Connect factoring choice** (even just “OTR / Other”)

This reduces confusion and support load.

*(Even if the backend can run without it, it’s worth it for adoption.)*

---

## 3) Your weekly cadence for beta drivers

Your goal is not “20 signups.”
Your goal is “20 drivers who run loads.”

Set a cadence:

### Day 0–2 (after signup)

* get them to run **one scout**
* get them to **reply to one broker email**
* get them to understand “I don’t pay unless I get paid”

### Week 1

* 1 load booked through your system
* BOL uploaded
* factoring status confirmed

### Week 2–4

* 2 loads/week per driver (ideal)
* settlement ledger starts looking like a bank statement
* collect testimonials

---

## 4) Collect proof while they use it (this is huge)

Create a simple “Beta Proof Checklist” per driver:

* ✅ first load booked
* ✅ first broker reply
* ✅ first BOL uploaded
* ✅ first factoring funded
* ✅ screenshot settlement ledger
* ✅ one sentence testimonial

Those screenshots become your sales page.

---

## 5) Add 2 admin tools that make onboarding painless

You already have:

* list pending
* approve
* reset password

Add these two quick admin endpoints/pages (optional but worth it):

1. **Approve + auto-text** (later)
2. **Driver activity view**

   * last scout run
   * last negotiation
   * last load funded

This helps you know who needs help.

---

## 6) Make beta drivers feel like “family”

This is retention.

### A) Private group

Pick one:

* WhatsApp group
* Facebook group
* Discord (but truckers prefer WhatsApp/Facebook)

Name it:
**Green Candle Beta Family**

### B) Weekly “wins” message

Every Friday:

* “Loads booked this week”
* “Fastest funding time”
* “Highest rate won”
* “Total fees saved vs 10% dispatch”

This motivates usage.

---

## 7) What you should do at the NJ turnpike stops

You’re not selling software. You’re recruiting early partners.

Script:

1. “How many loads a week do you run?”
2. “Do you hate dispatchers taking 10%?”
3. “We built an AI dispatch. You pay nothing upfront. Only 2% after OTR pays you.”
4. “Want to beta test? Takes 60 seconds.”

Then open `/beta/apply` on your phone and fill it in with them.

---

## 8) When to stop recruiting and start stabilizing

Once you hit:

* **10 drivers running loads**
* **at least 20 completed loads total**
* **factoring funded confirmations are consistent**

Pause recruiting and fix bugs hard for a week.

Then resume.

That’s how you avoid drowning in support.

---

## 9) When token becomes reasonable

Do not rush token until:

* settlement ledger is rock solid
* revenue ledger is accurate
* factoring confirmation is consistent

Once you have 20 active drivers and clean proof, token launch becomes easy.

---

## Your next “3 concrete actions” (do these now)

1. Create `/beta/apply` QR flyer (print 100)
2. Set up “Beta Family” WhatsApp/Facebook group
3. Draft the SMS message you send after approval

If you paste your current flyer text (or even rough notes), I’ll turn it into a one-page print-ready version with the exact copy and layout.
