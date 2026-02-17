# Green Candle Dispatch — Current System State

**Last Updated:** 2026  
**Purpose:** Single source of truth for current system behavior

---

## $CANDLE Service Credits — Immediate-Use Only

**IMPORTANT:** As of 2026, ALL $CANDLE service credits are **IMMEDIATE-USE**.

- ✅ **No vesting**
- ✅ **No locking**
- ✅ **No delays**
- ✅ **Available immediately** for automation features

**Previous 6-month vesting/locking was removed.**  
**Ignore any older docs mentioning vesting — they are legacy and deprecated.**

---

## How Credits Work

### Earning Credits
- **21.05% of 2% dispatch fee** returned as service credits
- **1:1 USD → CANDLE ratio** (internal credits)
- Credits issued when driver **uploads BOL** (Bill of Lading)
- Status: `CREDITED` (immediately available)

### Using Credits
- Credits can be used **immediately** after earning
- No waiting period
- No vesting schedule
- Status changes to `CONSUMED` when used

### Credit Costs
- Negotiation Agent: 0.5 CANDLE
- Factoring Packet: 0.3 CANDLE
- Full Dispatch: 10.0 CANDLE
- Manual Email: 0.5 CANDLE
- Voice Escalation: 0.5 CANDLE
- Document Parse: 1.0 CANDLE

---

## Code Implementation

**Source of Truth:** `app/services/ledger.py`

**Key Function:** `process_load_settlement()`
- Issues credits with `status='CREDITED'`
- Sets `unlocks_at=now()` (immediate)
- Credits available immediately

**Balance Service:** `app/services/vesting.py`
- Renamed from "VestingService" (legacy name kept for compatibility)
- Calculates available balance: `CREDITED` - `CONSUMED`
- No vesting logic — just balance calculation

---

## Database Schema

**Table:** `webwise.driver_savings_ledger`

**Status Values (Current):**
- `CREDITED` — Credits earned, available immediately
- `CONSUMED` — Credits used for automation

**Status Values (Legacy — Do Not Use):**
- `LOCKED` — Removed
- `VESTED` — Removed

**unlocks_at Column:**
- Always set to `now()` for new credits
- Kept for backward compatibility
- Ignored in logic (credits are immediate)

---

## Documentation Status

### Updated ✅
- `app/services/ledger.py` — Source of truth
- `app/services/vesting.py` — Removed vesting references
- `docs/candle-whitepaper-source-material.md` — Updated
- `docs/legacy/vesting-removed.md` — Historical reference
- `docs/current-state.md` — This file

### May Need Updates ⏳
- Various docs in `docs/updated/` folder
- Template files with UI text
- Marketing materials
- White paper drafts

---

## For Developers

**When adding new credit features:**
1. Use `process_load_settlement()` from `ledger.py`
2. Set `status='CREDITED'` and `unlocks_at=now()`
3. Do NOT introduce vesting/locking
4. Reference this document

**When finding legacy vesting code:**
1. Update to immediate-use model
2. Remove vesting logic
3. Update documentation
4. Add note in `docs/legacy/vesting-removed.md`

---

## Questions?

If you find vesting references and aren't sure:
1. Check `app/services/ledger.py` — this is the source of truth
2. Check `docs/current-state.md` — this document
3. Check `docs/legacy/vesting-removed.md` — historical context
4. When in doubt: **credits are immediate-use**
