# Legacy Vesting Removal — Historical Reference

**Date Removed:** 2026  
**Status:** All vesting/locking removed — credits are immediate-use only

---

## What Was Removed

**Previous System (Legacy):**
- Credits were locked for 6 months (180 days)
- Status: `LOCKED` or `VESTED`
- `unlocks_at` timestamp set to 6 months in future
- Drivers had to wait to use credits

**Current System (Active):**
- Credits are **immediately available**
- Status: `CREDITED` (available) or `CONSUMED` (used)
- `unlocks_at` set to `now()` (immediate)
- Drivers can use credits right away

---

## Why It Was Removed

1. **Simpler UX** — Drivers want immediate access to automation
2. **SEC Safety** — Immediate-use credits are rebates, not securities
3. **User Feedback** — Drivers found 6-month lock frustrating
4. **Product Evolution** — System evolved to immediate-use model

---

## What Was Replaced With

**Immediate-Use Service Credits:**
- Credits issued with `status='CREDITED'` and `unlocks_at=now()`
- Available immediately for automation features
- No waiting period
- No vesting schedule

**Code Implementation:**
- `app/services/ledger.py` → `process_load_settlement()` issues immediate credits
- `app/services/vesting.py` → Renamed to balance service (no vesting logic)
- All SQL queries updated to use `CREDITED`/`CONSUMED` only

---

## Files Updated

### Core Services
- ✅ `app/services/ledger.py` — Immediate credits (`unlocks_at=now()`, `status='CREDITED'`)
- ✅ `app/services/vesting.py` — Removed VESTED/LOCKED from SQL queries
- ✅ `app/services/tokenomics.py` — Deprecated old vesting function

### Documentation
- ✅ `docs/candle-whitepaper-source-material.md` — Updated to immediate-use
- ✅ This file — Historical reference

### Still Need Updates
- ⏳ `docs/updated/rev.md` — May have vesting references
- ⏳ `docs/updated/burn.md` — May have vesting references
- ⏳ `docs/updated/$Candle.md` — May have vesting references
- ⏳ Various template files — May have UI text about vesting

---

## For Future Developers

**DO NOT:**
- Re-introduce vesting/locking without discussion
- Use `VESTED` or `LOCKED` status values
- Set `unlocks_at` to future dates
- Reference 6-month vesting in new code

**DO:**
- Use `CREDITED` status for new credits
- Set `unlocks_at=now()` for immediate availability
- Reference this document if you find old vesting code
- Update any docs you find with vesting references

---

## Search Terms to Find Legacy References

If you're cleaning up, search for:
- `vesting`, `vest`
- `6 month`, `6-month`, `180 day`, `180-day`
- `unlocks_at` (except `now()`)
- `LOCKED`, `VESTED` status values
- `mark_vested`, `vest_credits` function names

---

## Current Source of Truth

**File:** `app/services/ledger.py`  
**Function:** `process_load_settlement()`  
**Line:** 79-92

This is the authoritative implementation. All credits are immediate-use.
