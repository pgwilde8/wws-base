# Vesting Cleanup Checklist

Use this checklist to systematically remove all legacy vesting references.

---

## ✅ Completed

- [x] `app/services/ledger.py` — Added source of truth comment
- [x] `app/services/vesting.py` — Removed VESTED/LOCKED from SQL queries
- [x] `app/services/tokenomics.py` — Deprecated old vesting function
- [x] `docs/candle-whitepaper-source-material.md` — Updated to immediate-use
- [x] `docs/legacy/vesting-removed.md` — Created historical reference
- [x] `docs/current-state.md` — Created source of truth document

---

## ⏳ To Do

### Code Files
- [ ] `app/routes/client.py` — Check for vesting UI text/comments
- [ ] `app/routes/admin.py` — Check for vesting references
- [ ] `app/templates/drivers/savings.html` — Update UI text
- [ ] `app/templates/drivers/dashboard.html` — Update UI text
- [ ] `app/templates/drivers/partials/claim_modal.html` — Update modal text
- [ ] `app/models/claims.py` — Check model for vesting fields
- [ ] `sql/create_driver_savings_ledger.sql` — Check migration comments

### Documentation Files
- [ ] `docs/updated/rev.md` — Remove vesting references
- [ ] `docs/updated/burn.md` — Remove vesting references
- [ ] `docs/updated/$Candle.md` — Remove vesting references
- [ ] `docs/updated/accounting.md` — Remove vesting references
- [ ] `docs/Revenue Model and System Economics.md` — Remove vesting references
- [ ] `docs/exe-summary.md` — Remove vesting references
- [ ] `docs/README.MD` — Remove vesting references
- [ ] `docs/updated-plan.md` — Remove vesting references
- [ ] `docs/seed investors.md` — Remove vesting references

### Template/Marketing Files
- [ ] `app/templates/public/protocol.html` — Update public-facing text
- [ ] `app/templates/public/services.html` — Update service descriptions
- [ ] `app/templates/legal/privacy.html` — Check for vesting mentions
- [ ] `app/templates/legal/tos.html` — Check for vesting mentions
- [ ] `docs/"One-Pager" flyer.md` — Update marketing copy

---

## Quick Search Commands

```bash
# Find all vesting references in code
grep -r -i "vesting\|vest\|6 month\|6-month\|180 day\|locked\|locking" app/ sql/ --exclude-dir=__pycache__

# Find all vesting references in docs
grep -r -i "vesting\|vest\|6 month\|6-month\|180 day\|locked\|locking" docs/

# Find specific status values
grep -r "VESTED\|LOCKED" app/ sql/ docs/ --exclude-dir=__pycache__

# Find unlocks_at usage (except now())
grep -r "unlocks_at" app/ sql/ docs/ --exclude-dir=__pycache__ | grep -v "now()"
```

---

## Replacement Patterns

### Old → New

**Code Comments:**
- `# Credits vest over 6 months` → `# Credits are immediate-use`
- `# Locked for 180 days` → `# Available immediately`
- `# Vesting period` → `# Immediate availability`

**Status Values:**
- `'LOCKED'` → `'CREDITED'`
- `'VESTED'` → `'CREDITED'`
- Remove `VESTED`/`LOCKED` from SQL `IN` clauses

**Documentation:**
- `"Credits vest over 6 months"` → `"Credits are issued immediately"`
- `"Locked until unlock date"` → `"Available immediately"`
- `"6-month vesting period"` → `"Immediate-use credits"`

**UI Text:**
- `"Your credits will unlock in X days"` → `"Your credits are available now"`
- `"Vesting schedule"` → `"Credit balance"`
- `"Locked credits"` → `"Available credits"`

---

## Testing After Cleanup

1. **Test credit issuance:**
   - Complete a load
   - Upload BOL
   - Verify credits appear immediately
   - Verify status is `CREDITED`

2. **Test credit usage:**
   - Use credits for automation
   - Verify balance decreases
   - Verify status changes to `CONSUMED`

3. **Test balance calculation:**
   - Check driver dashboard
   - Verify balance = CREDITED - CONSUMED
   - Verify no vesting delays

---

## Notes

- Keep `unlocks_at` column in database for backward compatibility
- Set `unlocks_at=now()` for all new credits
- Ignore `unlocks_at` in balance calculations
- `VestingService` name kept for API compatibility (no vesting logic)

---

**Last Updated:** 2026  
**Status:** In Progress
