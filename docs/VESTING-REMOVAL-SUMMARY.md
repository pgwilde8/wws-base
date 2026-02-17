# Vesting Removal Summary

**Date:** 2026  
**Status:** ✅ Core code updated | ⏳ Documentation cleanup in progress

---

## What Changed

### Before (Legacy)
- Credits locked for 6 months (180 days)
- Status: `LOCKED` or `VESTED`
- `unlocks_at` set to future date
- Drivers had to wait to use credits

### After (Current)
- ✅ Credits **immediately available**
- ✅ Status: `CREDITED` (available) or `CONSUMED` (used)
- ✅ `unlocks_at` set to `now()` (immediate)
- ✅ Drivers can use credits right away

---

## Files Updated

### ✅ Core Services (Complete)
1. **`app/services/ledger.py`**
   - Added source of truth comment at top
   - Credits issued with `status='CREDITED'` and `unlocks_at=now()`
   - Function: `process_load_settlement()` (lines 79-92)

2. **`app/services/vesting.py`**
   - Removed `VESTED`/`LOCKED` from SQL queries
   - Updated to only use `CREDITED`/`CONSUMED`
   - Kept name for API compatibility (no vesting logic)

3. **`app/services/tokenomics.py`**
   - Deprecated old `credit_driver_savings()` function
   - Redirects to new immediate-use system

### ✅ Documentation (Complete)
1. **`docs/candle-whitepaper-source-material.md`**
   - Updated vesting section to immediate-use
   - Removed 6-month lock references

2. **`docs/legacy/vesting-removed.md`**
   - Created historical reference document
   - Explains what was removed and why

3. **`docs/current-state.md`**
   - Created source of truth document
   - Single place to check current behavior

4. **`docs/vesting-cleanup-checklist.md`**
   - Created cleanup checklist
   - Lists remaining files to update

---

## Remaining Work

### Code Files (May Need Updates)
- `app/routes/client.py` — Check for vesting UI text
- `app/routes/admin.py` — Check for vesting references
- `app/templates/drivers/savings.html` — Update UI text
- `app/templates/drivers/dashboard.html` — Update UI text
- `app/templates/drivers/partials/claim_modal.html` — Update modal

### Documentation Files (May Need Updates)
- `docs/updated/rev.md` — Check for vesting references
- `docs/updated/burn.md` — Check for vesting references
- `docs/updated/accounting.md` — Check for vesting references
- `docs/Revenue Model and System Economics.md` — Check for vesting
- `docs/exe-summary.md` — Check for vesting references
- Various other docs

---

## Quick Reference

### Current Behavior (Source of Truth)
**File:** `app/services/ledger.py`  
**Function:** `process_load_settlement()`  
**Status:** `CREDITED` (immediate)  
**unlocks_at:** `now()` (immediate)

### Balance Calculation
**File:** `app/services/vesting.py`  
**Function:** `get_available_service_balance()`  
**Logic:** Sum of `CREDITED` - `CONSUMED`  
**No vesting:** All credits count immediately

### Documentation
**Source of Truth:** `docs/current-state.md`  
**Historical:** `docs/legacy/vesting-removed.md`  
**Checklist:** `docs/vesting-cleanup-checklist.md`

---

## For Developers

**When writing new code:**
- Use `process_load_settlement()` from `ledger.py`
- Set `status='CREDITED'` and `unlocks_at=now()`
- Do NOT introduce vesting/locking

**When finding legacy code:**
- Update to immediate-use model
- Remove vesting logic
- Update documentation
- Reference `docs/legacy/vesting-removed.md`

**When unsure:**
- Check `app/services/ledger.py` — source of truth
- Check `docs/current-state.md` — current behavior
- Default: **credits are immediate-use**

---

## Search Commands

```bash
# Find vesting references in code
grep -r -i "vesting\|vest\|6 month\|6-month\|180 day\|locked\|locking" app/ sql/

# Find vesting references in docs
grep -r -i "vesting\|vest\|6 month\|6-month\|180 day\|locked\|locking" docs/

# Find legacy status values
grep -r "VESTED\|LOCKED" app/ sql/ docs/
```

---

## Status

- ✅ **Core logic:** Updated to immediate-use
- ✅ **Key services:** Updated
- ✅ **Source of truth docs:** Created
- ⏳ **Documentation cleanup:** In progress
- ⏳ **UI templates:** May need updates
- ⏳ **Marketing materials:** May need updates

---

**Next Steps:**
1. Review checklist: `docs/vesting-cleanup-checklist.md`
2. Update remaining documentation files
3. Update UI templates with vesting references
4. Test credit issuance and usage
5. Mark complete when all references removed
