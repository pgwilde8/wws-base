# Century Finance Integration Analysis

## Current State: Century Finance is Hardcoded

### **The Problem**
The system is currently **hardcoded to Century Finance** (`alma@centuryfinance.com`) as the only factoring company. Drivers are "locked in" because:

1. **Onboarding flow** forces all drivers to submit to Century Finance
2. **Email addresses** are hardcoded to `alma@centuryfinance.com`
3. **Gatekeeper logic** checks `factoring_referrals.status` (Century approval) before unlocking dashboard
4. **Packet sending** references "Century Finance" in UI text
5. **Admin approval page** is named `/admin/century-approvals`

---

## Where Century Finance is Hardcoded

### **1. Email Addresses (Hardcoded)**
- **`app/services/email.py`**:
  - `send_factoring_referral_email()` → `to_email = "alma@centuryfinance.com"` (default)
  - `send_century_approval_email()` → mentions "Century Finance" in body
  - `send_century_decline_email()` → mentions "Alma" and "Century Finance"

- **`app/routes/client.py`**:
  - `century_onboarding_submit()` → `to_email = "alma@centuryfinance.com"` (line 1131)
  - `submit_factoring_application()` → `to_email = "alma@centuryfinance.com"` (line 1416)

### **2. Onboarding Flow (Century-Only)**
- **`/drivers/onboarding/checkout-success`** → Redirects to `/drivers/century-onboarding` (line 1054)
- **`/drivers/century-onboarding`** → Form specifically for Century Finance referral
- **`/drivers/dashboard`** → Gatekeeper checks `factoring_referrals.status` (Century approval) before allowing dashboard access (lines 74-89)

### **3. Database Schema**
- **`webwise.factoring_referrals`** table:
  - Has `current_factoring_company` field (driver's existing factor)
  - Has `status` field (PENDING, CONTACTED, APPROVED, DECLINED) — but this is Century-specific
  - **Missing:** `factoring_partner` or `referral_to` field to track WHICH factoring company the referral is for

- **`webwise.users`** table:
  - Has `factoring_company` field (driver's current/existing factor)
  - This is used in `send_packet_to_factor()` (line 136) but not stored per-driver preference

### **4. UI Text (Century-Specific)**
- **Templates**:
  - `drivers/century_onboarding.html` → "Century Finance Funding Application"
  - `drivers/load_manage.html` → "Send to Century Finance" (line 275)
  - `drivers/partials/factoring_sent_success.html` → "Packet sent to Century Finance"
  - `drivers/dashboard2.html` → mentions "Century Finance" in instructions
  - `emails/welcome_onboarding.html` → mentions "Century Finance"

### **5. Admin Approval**
- **`/admin/century-approvals`** → Admin page to approve/decline Century referrals
- **`approve_century_referral()`** → Calls `send_century_approval_email()` (hardcoded Century)
- **`decline_century_referral()`** → Calls `send_century_decline_email()` (hardcoded Century)

### **6. Packet Sending**
- **`app/services/factoring.py`**:
  - `send_packet_to_factor()` → Reads `factoring_company` from `users` table (line 136) but doesn't use it
  - `push_invoice_to_factor()` → Generic API endpoint (not Century-specific, but not used)
  - **Issue:** The packet is sent but there's no logic to route to different factoring companies

---

## What Needs to Change for Multi-Factor Support

### **1. Database Schema Changes**

**Option A: Add `factoring_partner` to `factoring_referrals`**
```sql
ALTER TABLE webwise.factoring_referrals
ADD COLUMN factoring_partner VARCHAR(100) DEFAULT 'CENTURY_FINANCE';
-- Values: 'CENTURY_FINANCE', 'OTR_SOLUTIONS', 'OTHER', etc.
```

**Option B: Store driver's preferred/approved factoring company**
```sql
ALTER TABLE webwise.trucker_profiles
ADD COLUMN approved_factoring_partner VARCHAR(100);
-- After approval, store which factor they're using
```

**Option C: Separate table for factoring partners**
```sql
CREATE TABLE webwise.factoring_partners (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,  -- 'Century Finance', 'OTR Solutions'
    email VARCHAR(255) NOT NULL, -- 'alma@centuryfinance.com'
    api_endpoint VARCHAR(255),
    is_active BOOLEAN DEFAULT true
);
```

### **2. Onboarding Flow Changes**

**Current:** Payment → Century Form → Admin Approve → Dashboard Unlock

**New:** Payment → **Select/Choose Factoring Company** → Submit to that company → Admin Approve → Dashboard Unlock

- Change `/drivers/century-onboarding` → `/drivers/factoring-onboarding` (generic)
- Add dropdown/selection: "Which factoring company do you want to use?"
- Store choice in `factoring_referrals.factoring_partner`

### **3. Email Routing**

**Change:** `send_factoring_referral_email()` to accept `factoring_partner` parameter and route to correct email:
- Century Finance → `alma@centuryfinance.com`
- OTR Solutions → `support@otrsolutions.com` (example)
- Other → configurable

### **4. Gatekeeper Logic**

**Current:** Checks `factoring_referrals.status` (assumes Century)

**New:** Check `factoring_referrals.status` AND `factoring_partner` matches driver's approved partner

### **5. Packet Sending**

**Current:** `send_packet_to_factor()` reads `factoring_company` from users but doesn't use it

**New:** 
- Read driver's **approved factoring partner** from `trucker_profiles.approved_factoring_partner`
- Route packet to that partner's API endpoint or email
- Update `push_invoice_to_factor()` to accept `factoring_partner` parameter

### **6. Admin Approval**

**Current:** `/admin/century-approvals` → Century-specific

**New:** `/admin/factoring-approvals` → Filter by `factoring_partner`, show all pending referrals

### **7. UI Text**

**Change:** Replace "Century Finance" with:
- Dynamic text based on driver's approved partner
- Generic "factoring company" or "your factor"
- Or show partner name: "Send to [Partner Name]"

---

## Recommended Approach

### **Phase 1: Make Century Optional (Quick Fix)**
1. Add `factoring_partner` column to `factoring_referrals` (default 'CENTURY_FINANCE')
2. Add `approved_factoring_partner` to `trucker_profiles`
3. Update onboarding form to allow "Skip Century" or "Use my existing factor"
4. If driver has existing `factoring_company` in `users.factoring_company`, auto-populate and skip Century referral
5. Gatekeeper: Allow dashboard if `factoring_referrals.status = 'APPROVED'` OR if driver has `factoring_company` set (existing factor)

### **Phase 2: Multi-Partner Support (Full Solution)**
1. Create `factoring_partners` table with partner configs
2. Update onboarding to show partner selection
3. Route emails/packets based on `factoring_partner`
4. Admin page shows all partners' referrals
5. Packet sending routes to correct partner API/email

---

## Key Questions to Answer

1. **Do drivers already have factoring companies?** 
   - Yes → `users.factoring_company` field exists and may be populated
   - Use this to skip Century referral if they already have a factor

2. **Do you want to support multiple factoring partners?**
   - Yes → Build partner config system
   - No → Just make Century optional, allow drivers to use existing factor

3. **How should packet sending work?**
   - Email-based (current: email to alma@centuryfinance.com)
   - API-based (future: push to partner's API endpoint)
   - Both (email fallback if API fails)

4. **What happens if driver switches factors?**
   - Update `trucker_profiles.approved_factoring_partner`
   - Future packets go to new partner
   - Historical packets stay with old partner

---

## Files That Need Changes

### **High Priority**
- `app/routes/client.py` → `century_onboarding_submit()`, dashboard gatekeeper
- `app/services/email.py` → `send_factoring_referral_email()`, approval/decline emails
- `app/templates/drivers/century_onboarding.html` → Make generic or add partner selection
- `app/routes/admin.py` → `century_approvals_page()` → Make generic

### **Medium Priority**
- `app/services/factoring.py` → `send_packet_to_factor()` → Route to correct partner
- `app/templates/drivers/load_manage.html` → Replace "Century Finance" with dynamic text
- `app/templates/drivers/dashboard2.html` → Update instructions

### **Low Priority**
- Email templates → Make partner-agnostic
- Admin approval emails → Genericize

---

## Next Steps

1. **Decide:** Multi-partner support OR just make Century optional?
2. **If optional:** Use existing `users.factoring_company` to skip Century referral
3. **If multi-partner:** Build partner config system and routing logic
4. **Test:** Ensure drivers with existing factors can use the system without Century
