# Troubleshooting Guide

## Savings Ledger Not Showing Entries

If you run `test_bol_upload.py` and the database shows no entries, check:

### 1. Is the FastAPI Server Running?

The test script makes HTTP requests to `http://127.0.0.1:8990`. You need the server running:

```bash
# Start the server
cd /srv/projects/client/dispatch
uvicorn app.main:app --host 0.0.0.0 --port 8990 --reload

# In another terminal, run the test
python test_bol_upload.py
```

### 2. Check Server Logs

Look for these messages in the server output:
- `✅ BOL Uploaded. Fee Calculated: $60.0`
- `🏦 BANK SAYS: Invoice received. Funding scheduled for 2:00 PM EST.`
- `🔒 SAVINGS: MC_998877 earned 60.0 $CANDLE (Locked until YYYY-MM-DD) [ID: X]`

If you see `❌ DATABASE ERROR`, check the error message.

### 3. Verify Database Connection

```bash
# Test direct database access
export PGPASSWORD='WwsAdmin2026!'
psql -U wws-admin -d wws_dispatch_db -h localhost -c "SELECT COUNT(*) FROM webwise.driver_savings_ledger;"
```

### 4. Test the Function Directly

```bash
# This bypasses FastAPI and tests the function directly
python test_savings_credit.py
```

If this works but the HTTP route doesn't, the issue is in the FastAPI route/session handling.

### 5. Common Issues

**Issue: "Peer authentication failed"**
- Solution: Use `-h localhost` flag: `psql -U wws-admin -d wws_dispatch_db -h localhost`

**Issue: Function works but entries don't persist**
- Check if `db.commit()` is being called
- Check server logs for rollback messages
- Ensure no exceptions are being silently caught

**Issue: "DATABASE_URL not set"**
- Check `.env` file exists in project root
- Verify `DATABASE_URL` is set correctly
- Run bootstrap: `python -m app.models.bootstrap_db`

### 6. Verify Entry Was Created

```sql
-- Check latest entries
SELECT * FROM webwise.driver_savings_ledger ORDER BY earned_at DESC LIMIT 5;

-- Check specific load
SELECT * FROM webwise.driver_savings_ledger WHERE load_id = 'LOAD_123';

-- Check by MC number
SELECT * FROM webwise.driver_savings_ledger WHERE driver_mc_number = 'MC_998877';
```
