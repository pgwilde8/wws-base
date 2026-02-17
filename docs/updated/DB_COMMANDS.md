# PostgreSQL Commands for `wws_dispatch_db`

Quick reference for navigating and querying the dispatch database.

## Connection

```bash
# Method 1: Connect via localhost (uses password auth, not peer auth)
psql -U wws-admin -d wws_dispatch_db -h localhost

# Method 2: Using connection string (recommended)
psql "postgresql://wws-admin:WwsAdmin2026%21@localhost/wws_dispatch_db"

# Method 3: Via postgres superuser (if peer auth is required)
sudo -u postgres psql -d wws_dispatch_db
# Then inside psql: \c wws_dispatch_db

# Method 4: Set PGPASSWORD environment variable
export PGPASSWORD='WwsAdmin2026!'
psql -U wws-admin -d wws_dispatch_db -h localhost
```

**Note:** If you get "Peer authentication failed", use `-h localhost` to force TCP/IP connection with password authentication instead of Unix socket peer authentication.

---

## Basic Navigation

```sql
-- List all databases
\l

-- Connect to a database (if already in psql)
\c wws_dispatch_db

-- List all schemas
\dn

-- List all tables in current schema
\dt

-- List all tables in webwise schema
\dt webwise.*

-- Describe a table structure
\d webwise.driver_savings_ledger

-- Describe all columns in detail
\d+ webwise.driver_savings_ledger

-- List all indexes
\di

-- Show current database
SELECT current_database();

-- Show current schema
SELECT current_schema();

-- Exit psql
\q
```

---

## Schema & Tables

```sql
-- Switch to webwise schema
SET search_path TO webwise;

-- List all tables in webwise schema
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'webwise'
ORDER BY table_name;

-- Count tables in webwise schema
SELECT COUNT(*) 
FROM information_schema.tables 
WHERE table_schema = 'webwise';

-- Show table columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'webwise' 
  AND table_name = 'driver_savings_ledger'
ORDER BY ordinal_position;
```

---

## Driver Savings Ledger Queries

```sql
-- View all savings entries
SELECT * FROM webwise.driver_savings_ledger ORDER BY earned_at DESC;

-- View locked savings (not yet vested)
SELECT 
    driver_mc_number,
    load_id,
    amount_usd,
    amount_candle,
    earned_at,
    unlocks_at,
    status
FROM webwise.driver_savings_ledger
WHERE status = 'LOCKED'
ORDER BY unlocks_at ASC;

-- View total savings per driver
SELECT 
    driver_mc_number,
    COUNT(*) as total_loads,
    SUM(amount_usd) as total_usd,
    SUM(amount_candle) as total_candle,
    MIN(unlocks_at) as earliest_unlock
FROM webwise.driver_savings_ledger
GROUP BY driver_mc_number
ORDER BY total_candle DESC;

-- View savings that are ready to unlock (vested)
SELECT 
    driver_mc_number,
    load_id,
    amount_candle,
    earned_at,
    unlocks_at,
    NOW() as current_time,
    unlocks_at - NOW() as time_until_unlock
FROM webwise.driver_savings_ledger
WHERE status = 'LOCKED' 
  AND unlocks_at <= NOW()
ORDER BY unlocks_at ASC;

-- View claimed savings (already sent to wallet)
SELECT * FROM webwise.driver_savings_ledger 
WHERE status = 'CLAIMED'
ORDER BY earned_at DESC;
```

---

## User & Trucker Queries

```sql
-- List all users
SELECT id, email, role, is_active, created_at 
FROM webwise.users 
ORDER BY created_at DESC;

-- List all trucker profiles
SELECT 
    tp.id,
    tp.display_name,
    tp.carrier_name,
    tp.mc_number,
    u.email,
    tp.created_at
FROM webwise.trucker_profiles tp
LEFT JOIN webwise.users u ON tp.user_id = u.id
ORDER BY tp.created_at DESC;

-- Find trucker by MC number
SELECT * FROM webwise.trucker_profiles 
WHERE mc_number = 'MC_998877';

-- View trucker with their savings balance
SELECT 
    tp.mc_number,
    tp.display_name,
    COUNT(dsl.id) as total_entries,
    COALESCE(SUM(dsl.amount_candle), 0) as total_candle_locked
FROM webwise.trucker_profiles tp
LEFT JOIN webwise.driver_savings_ledger dsl ON tp.mc_number = dsl.driver_mc_number
WHERE dsl.status = 'LOCKED' OR dsl.status IS NULL
GROUP BY tp.id, tp.mc_number, tp.display_name
ORDER BY total_candle_locked DESC;
```

---

## Negotiations & Loads

```sql
-- View all negotiations
SELECT 
    id,
    load_id,
    origin,
    destination,
    original_rate,
    final_rate,
    status,
    created_at
FROM webwise.negotiations
ORDER BY created_at DESC;

-- View won negotiations (completed loads)
SELECT * FROM webwise.negotiations 
WHERE status = 'won'
ORDER BY final_rate DESC;

-- Count negotiations by status
SELECT status, COUNT(*) as count
FROM webwise.negotiations
GROUP BY status;
```

---

## Notifications

```sql
-- View unread notifications
SELECT * FROM webwise.notifications 
WHERE is_read = false
ORDER BY created_at DESC;

-- View notifications for a specific trucker
SELECT n.*, tp.mc_number, tp.display_name
FROM webwise.notifications n
JOIN webwise.trucker_profiles tp ON n.trucker_id = tp.id
WHERE tp.mc_number = 'MC_998877'
ORDER BY n.created_at DESC;

-- Count unread notifications per trucker
SELECT 
    tp.mc_number,
    tp.display_name,
    COUNT(*) as unread_count
FROM webwise.notifications n
JOIN webwise.trucker_profiles tp ON n.trucker_id = tp.id
WHERE n.is_read = false
GROUP BY tp.id, tp.mc_number, tp.display_name
ORDER BY unread_count DESC;
```

---

## Useful Maintenance Commands

```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'webwise'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Count rows in all tables
SELECT 
    'webwise.' || table_name as table_name,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_schema = 'webwise' AND table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'webwise'
ORDER BY table_name;

-- Quick row counts (manual)
SELECT COUNT(*) FROM webwise.users;
SELECT COUNT(*) FROM webwise.trucker_profiles;
SELECT COUNT(*) FROM webwise.driver_savings_ledger;
SELECT COUNT(*) FROM webwise.negotiations;
SELECT COUNT(*) FROM webwise.notifications;

-- Vacuum analyze (optimize database)
VACUUM ANALYZE webwise.driver_savings_ledger;
```

---

## Testing & Sample Data

```sql
-- Insert a test savings entry (if needed)
INSERT INTO webwise.driver_savings_ledger 
(driver_mc_number, load_id, amount_usd, amount_candle, unlocks_at, status)
VALUES 
('MC_998877', 'LOAD_TEST_001', 60.00, 60.0000, NOW() + INTERVAL '6 months', 'LOCKED')
RETURNING id;

-- Update status to VESTED (for testing unlock flow)
UPDATE webwise.driver_savings_ledger
SET status = 'VESTED'
WHERE driver_mc_number = 'MC_998877' 
  AND unlocks_at <= NOW()
  AND status = 'LOCKED';

-- Mark notification as read
UPDATE webwise.notifications
SET is_read = true
WHERE id = 1;
```

---

## Export/Import

```bash
# Export table to CSV
psql -U wws-admin -d wws_dispatch_db -c "\COPY webwise.driver_savings_ledger TO '/tmp/savings_ledger.csv' CSV HEADER"

# Export entire schema
pg_dump -U wws-admin -d wws_dispatch_db -n webwise > webwise_schema_backup.sql

# Restore from backup
psql -U wws-admin -d wws_dispatch_db < webwise_schema_backup.sql
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `\l` | List databases |
| `\c dbname` | Connect to database |
| `\dt` | List tables |
| `\dt schema.*` | List tables in schema |
| `\d tablename` | Describe table |
| `\dn` | List schemas |
| `\di` | List indexes |
| `\q` | Quit psql |
| `\?` | Help |
| `\h SELECT` | Help for SELECT command |

---

## Common Workflows

### Check if a load was credited
```sql
SELECT * FROM webwise.driver_savings_ledger 
WHERE load_id = 'LOAD_123';
```

### View driver's complete savings history
```sql
SELECT 
    load_id,
    amount_usd,
    amount_candle,
    earned_at,
    unlocks_at,
    status,
    CASE 
        WHEN unlocks_at <= NOW() THEN 'Ready to Claim'
        ELSE 'Locked'
    END as claim_status
FROM webwise.driver_savings_ledger
WHERE driver_mc_number = 'MC_998877'
ORDER BY earned_at DESC;
```

### Find all loads ready for claiming
```sql
SELECT 
    driver_mc_number,
    load_id,
    amount_candle,
    unlocks_at,
    NOW() - unlocks_at as days_unlocked
FROM webwise.driver_savings_ledger
WHERE status = 'LOCKED' 
  AND unlocks_at <= NOW()
ORDER BY unlocks_at ASC;
```
