Here is your **clean, organized burn architecture** based exactly on your real Green Candle Dispatch revenue model and what you clarified.

---

# Green Candle Dispatch — Official Burn Architecture

## Core Rule (MOST IMPORTANT)

**Burn ONLY from real USD revenue received by the platform.**

Never burn from:

* internal driver service credits ($CANDLE credits)
* internal ledger entries
* non-cash accounting events

Burn only from:

* dispatch fee margin
* call pack profit
* automation purchases
* factoring referral revenue
* broker subscriptions (if enabled)

This keeps the system financially safe and sustainable.

---

# Revenue Sources → Burn Eligibility

## 1. Dispatch Fee Margin (Core Engine)

Example load:

Broker pays: $1,900
Dispatch fee (2%): $38

Allocation:

* $15 → infrastructure
* $10 → platform margin ✅ burn eligible
* $13 → driver service credits ❌ NOT burn eligible

Burn example:

If burn rate = 10%

```
$10 × 10% = $1 burned per load
```

---

## 2. Call Packs (Strongest burn source)

Example:

Driver buys call pack: $99
Cost: $1.80
Profit: $97.20

Burn example:

```
$97 × 10% = $9.70 burned
```

This is extremely powerful because margins are very high.

---

## 3. Premium Automation Purchases

Example:

Driver buys automation credits: $50
Cost: near zero
Profit: ~$50

Burn example:

```
$50 × 10% = $5 burned
```

---

## 4. Factoring Partner Referral Revenue

Example:

Referral revenue per load: $6.65

Burn example:

```
$6.65 × 10% = $0.66 burned
```

---

## 5. Broker Subscriptions (Optional — if enabled)

Example:

Broker subscription: $149/month

Burn example:

```
$149 × 10% = $14.90 burned
```

This is optional and only applies if broker subscriptions are active.

---

# Summary Table — Burn Sources

| Revenue Source       | Example Revenue | Burn @ 10% |
| -------------------- | --------------- | ---------- |
| Dispatch fee margin  | $10             | $1.00      |
| Call pack profit     | $97             | $9.70      |
| Automation purchases | $50             | $5.00      |
| Factoring referral   | $6.65           | $0.66      |
| Broker subscription  | $149            | $14.90     |

---

# Recommended Burn Rate

Start conservative:

**Launch burn rate: 5%**

Scale burn rate later:

**Growth burn rate: 10%**

Max sustainable burn rate:

**Aggressive burn rate: 15–20%**

Never exceed what platform profit can safely support.

---

# Complete Burn Flow (Step-by-Step)

Step 1 — Platform receives USD revenue
(from Stripe, factoring partners, etc.)

Step 2 — Calculate burn allocation

Example:

```
platform_revenue = $10,000
burn_rate = 10%

burn_amount = $1,000
```

Step 3 — Buy CANDLE using burn allocation

```
USD → buy CANDLE on market
```

Step 4 — Send purchased CANDLE to burn address

Example burn address:

```
0x000000000000000000000000000000000000dead
```

Step 5 — Tokens permanently removed from supply

Irreversible.

---

# Automation Architecture (Recommended)

## Database table

```
revenue_transactions
--------------------
id
amount_usd
source_type
burned (true/false)
created_at
```

---

## Burn job (weekly or daily)

Pseudo-logic:

```
SELECT SUM(amount_usd)
FROM revenue_transactions
WHERE burned = false;

burn_amount = total × burn_rate

buy CANDLE worth burn_amount

send CANDLE to burn address

UPDATE revenue_transactions
SET burned = true
```

---

# Example Monthly Burn Scenario (500 drivers)

From your model:

Platform profit ≈ $242,800/month

Burn scenarios:

5% burn → $12,140 burned/month
10% burn → $24,280 burned/month
15% burn → $36,420 burned/month

This is extremely strong.

---

# Recommended Final Allocation Structure

For each $100 of platform profit:

```
$80 → treasury
$10 → burn
$10 → operational buffer
```

This keeps system stable and sustainable.

---

# What NOT to burn from

Do NOT burn from:

```
driver service credits issued
internal credit ledger entries
unrealized revenue
treasury reserves (unless intentional)
```

Burn only from realized revenue.

---

# Best Launch Recommendation

Start with:

**10% burn from platform profit**

Executed:

**weekly**

This creates steady, predictable supply reduction without hurting operations.

===========
Below is an **exact, buildable design** for (1) treasury + burn wallet structure and (2) FastAPI endpoints + jobs so burns run automatically, safely, and auditable.

I’m going to assume Base/EVM for $CANDLE, and Stripe + factoring partner deposits for USD inflows.

---

## 1) Wallet structure (minimum viable + safe)

### A. Off-chain (bank/Stripe) accounts

1. **Operating USD account (Bank/Stripe Balance)**

* Receives: factoring payouts to your business, Stripe purchases (call packs, automation credits)
* Pays: servers, OpenAI, Twilio, etc.
* Not on-chain.

2. **Burn Funding USD bucket (ledger-only)**

* Not a real account; it’s just a *ledger partition* of revenue that you earmark for burn.
* You can physically transfer weekly/monthly to USDC purchase, but the “bucket” is tracked in DB.

### B. On-chain (Base) wallets

You want *separation of duties*:

1. **Treasury Hot Wallet (Base)**

* Purpose: holds USDC and/or $CANDLE for treasury operations
* Used for: buys, liquidity, internal ops
* Key storage: secure secret manager + restricted server access

2. **Burn Executor Wallet (Base)**

* Purpose: holds only the USDC earmarked for burn *until buy executes*
* Used for: executing swaps (USDC -> $CANDLE)
* After swap: sends $CANDLE directly to burn address
* Key storage: separate secret + separate role in your infra

3. **Burn Address (Base)**

* `0x000000000000000000000000000000000000dEaD` (or your own irrecoverable address)
* Never holds keys; tokens are sent here permanently

### C. Optional “upgrade later” (recommended once money is real)

4. **Treasury Multisig (Gnosis Safe / similar)**

* Holds majority of treasury assets
* Hot wallet only sweeps to it daily/weekly

---

## 2) Data model (Postgres) — what you need to automate burns

### Table: `revenue_transactions`

Tracks ALL real USD revenue that is burn-eligible.

Fields:

* `id` (uuid)
* `source_type` (enum: `DISPATCH_FEE`, `CALL_PACK`, `AUTOMATION`, `BROKER_SUB`, `FACTOR_REFERRAL`)
* `source_ref` (text)  ← Stripe charge id, factoring remittance id, etc.
* `amount_usd_cents` (int)
* `occurred_at` (timestamptz)
* `burn_eligible` (bool) default true
* `burn_rule_id` (uuid nullable)  ← which rule applied
* `burn_reserved_usd_cents` (int) default 0  ← computed reservation amount
* `reserved_at` (timestamptz nullable)
* `burn_batch_id` (uuid nullable)
* `burned_at` (timestamptz nullable)
* `status` (enum: `RECORDED`, `RESERVED`, `BURNED`, `VOID`)

### Table: `burn_rules`

* `id`
* `name` (e.g. `v1_10pct_of_platform_profit`)
* `source_type` (nullable; if null = applies to all)
* `burn_bps` (int)  ← basis points: 1000 = 10%
* `enabled` (bool)
* `effective_from` (timestamptz)

### Table: `burn_batches`

Represents one burn run.

* `id`
* `period_start`, `period_end`
* `burn_rate_bps`
* `usd_reserved_cents`
* `usd_spent_cents`
* `tx_swap_hash` (text)
* `tx_burn_hash` (text)
* `candle_bought_wei` (numeric/decimal)
* `status` (enum: `CREATED`, `FUNDED`, `SWAPPED`, `BURNED`, `FAILED`)
* `created_at`, `executed_at`

### Table: `wallets`

* `id`
* `name` (`TREASURY_HOT`, `BURN_EXECUTOR`, `BURN_ADDRESS`)
* `chain` (`base`)
* `address`
* `role` (enum)
* `enabled`

---

## 3) Services (clean separation, easy to test)

### `RevenueService`

* `record_revenue(tx: RevenueTxIn) -> RevenueTx`
* `void_revenue(source_ref)`

### `BurnPolicyService`

* `reserve_burn_amounts(period_start, period_end) -> totals`

  * calculates `burn_reserved_usd_cents` per tx using burn rules

### `BurnExecutionService`

* `create_batch(period_start, period_end) -> BurnBatch`
* `fund_burn_wallet(batch_id)` (optional if you keep USDC already on-chain)
* `execute_swap(batch_id)` (USDC -> $CANDLE)
* `execute_burn(batch_id)` (send to burn address)
* `reconcile(batch_id)` (checks receipts + marks burned)

### `ChainGateway` (interface)

* `get_usdc_balance(address)`
* `swap_usdc_for_candle(amount_usdc_cents) -> tx_hash, candle_amount`
* `send_candle_to_burn(candle_amount) -> tx_hash`

Implement `ChainGateway` with your chosen stack (ethers, web3.py, 0x, 1inch, Uniswap router, etc.)

---

## 4) FastAPI endpoints (exact set)

### A) Revenue ingestion (from Stripe + factoring)

1. `POST /webhooks/stripe`

* Validates Stripe signature
* On `payment_intent.succeeded` or `charge.succeeded`:

  * creates `revenue_transactions` with `source_type = CALL_PACK | AUTOMATION | BROKER_SUB`
  * status = `RECORDED`

2. `POST /webhooks/factoring`

* For OTR/Porter remittance confirmations (or a manual admin post for MVP)
* records:

  * `DISPATCH_FEE`
  * `FACTOR_REFERRAL` (if applicable)

3. `POST /admin/revenue`

* Manual entry for early MVP
* Requires admin auth

### B) Burn operations (admin-only)

4. `POST /admin/burn/batches`
   Body:

* `period_start`, `period_end`, optional `burn_rate_bps` override
  Creates a `burn_batch` and reserves burn amounts for matching revenue txs.

5. `GET /admin/burn/batches/{batch_id}`
   Shows:

* reserved USD
* eligible tx count
* status
* tx hashes (if executed)

6. `POST /admin/burn/batches/{batch_id}/execute`
   Does the full flow:

* verify reserved totals
* swap USDC -> $CANDLE
* send $CANDLE -> burn address
* mark revenue txs as burned
* mark batch burned

7. `POST /admin/burn/batches/{batch_id}/reconcile`
   Re-checks chain tx receipts and fixes status if server crashed mid-run.

### C) Public/ops visibility (read-only)

8. `GET /ops/treasury`
   Returns:

* treasury wallet address
* on-chain USDC balance
* on-chain $CANDLE balance
* last burn batch summary

---

## 5) Automation: how it runs “automatically”

### Option 1 (simple + reliable): APScheduler inside FastAPI

* Run a job every Sunday 2am:

  * create batch for last week
  * execute batch
  * log + alert

### Option 2 (best practice): Celery + Redis

* FastAPI triggers jobs
* Worker executes chain txs (safer; avoids blocking web server)

**Recommendation:** start with APScheduler if you’re moving fast, then upgrade to Celery once burns become frequent/large.

---

## 6) Safety rails (do these from day one)

1. **Max burn per batch cap**

* config: `MAX_BURN_USD_CENTS_PER_BATCH`
* prevents accidental over-burn

2. **Two-phase commit**

* Step A: reserve + create batch
* Step B: execute batch
  So you can inspect totals before execution.

3. **Idempotency keys**

* Use `source_ref` unique constraints (Stripe charge id, etc.)
* Prevent duplicates

4. **Price impact / slippage limits**

* Swap must enforce `max_slippage_bps`
* If swap fails, batch stays `FAILED`, nothing is marked burned

5. **Role-based keys**

* burn executor key cannot sweep treasury
* treasury key cannot burn (optional, but ideal)

---

## 7) Concrete endpoint payloads (examples)

### Create batch

`POST /admin/burn/batches`

```json
{
  "period_start": "2026-02-09T00:00:00Z",
  "period_end": "2026-02-16T00:00:00Z",
  "burn_rate_bps": 1000
}
```

Response:

```json
{
  "batch_id": "…",
  "usd_reserved_cents": 241400,
  "tx_count": 812,
  "status": "CREATED"
}
```

### Execute batch

`POST /admin/burn/batches/{batch_id}/execute`
Response:

```json
{
  "status": "BURNED",
  "usd_spent_cents": 241200,
  "tx_swap_hash": "0x…",
  "tx_burn_hash": "0x…",
  "candle_bought": "123456.789"
}
```

---

## 8) Implementation note for your architecture rules

You can keep this clean with your “interfaces preferred” style:

* `domain/burn/ports.py` (interfaces)
* `infra/chain/uniswap_gateway.py` (implementation)
* `app/routes/burn_admin.py` (FastAPI)
* `app/services/burn_service.py` (orchestrator)

No layer-collapsing, and chain execution stays out of “routes”.

---

If you tell me **which chain swap method you want** (Uniswap Router 직접, 0x API, 1inch, etc.), I’ll draft the *exact* `ChainGateway` implementation skeleton + the Alembic migration files next.


Summary
Core rule: Burn only from real USD revenue (platform profit). Never burn internal $CANDLE credits, ledger balances, or non-cash events.
Eligible sources (examples):
Source	Example	Burn @ 10%
Dispatch fee margin	$10	$1.00
Call pack profit	$97	$9.70
Automation purchases	$50	$5.00
Factoring referral	$6.65	$0.66
Broker subscription	$149	$14.90
Flow: Record USD revenue → compute burn (5–20%) → buy $CANDLE on market → send to burn address (0x...dead).
Architecture from the doc
Tables: revenue_transactions, burn_rules, burn_batches, wallets
Services: RevenueService, BurnPolicyService, BurnExecutionService, ChainGateway
Endpoints: Stripe + factoring webhooks, admin burn batch create/execute/reconcile, ops treasury view
Automation: APScheduler or Celery for weekly runs
Safety: Max per-batch cap, two-phase (reserve then execute), idempotency, slippage limits
Planning topics
1. Fit with current revenue model
The doc assumes things like call packs, broker subs, factoring referrals. Which of these exist today vs. planned?
Current setup: 2% dispatch fee, 75% driver rebate, 25% burn. Does “25% burn” already target the fee portion, or is the doc describing a new burn layer on top?
2. Revenue tracking
Is revenue already recorded per-load in your DB (e.g. settlement → fee → platform vs driver split)?
How are Stripe payments (e.g. small fleet setup) stored, and where would call packs / automation / broker subs land?
3. On-chain piece
Do you have a treasury/burn wallet setup, or is this greenfield?
Swap path: Uniswap Router on Base, 0x, 1inch, Clanker, or something else?
Where does $CANDLE live on Base (token address, liquidity, etc.)?
4. Implementation order
Phase 1: Data model (revenue tracking + burn rules) without chain execution.
Phase 2: Admin UI for creating and inspecting batches.
Phase 3: Chain execution (swap + burn).
Phase 4: Automated weekly runs and alerts.
5. Risk
Max per-batch cap, slippage limits, and who has access to the burn executor keys are critical. The doc suggests starting with 10% burn, weekly, and using APScheduler; you may want to add manual approval before execution.
6. Reporting and compliance
How do you want to expose burns (e.g. public burn log, on-chain explorer, internal reports, legal/tax)?
Any obligations for third-party audits or compliance checks?

Great question. Let’s slow this down and explain it like you’re running a real business with a real bank account — because that’s exactly what this is.

Right now, **nothing burns automatically from Stripe.** Stripe is just the starting point. The burn only happens later, after you deliberately move funds on-chain and run the burn job.

Here is the real-world flow, step by step, in plain English.

---

# Think of Stripe as your cash register

Stripe is where customers pay you USD.

Example:

* Driver buys automation credits: $50
* Stripe deposits $50 into your Stripe balance
* Later Stripe transfers it to your bank account

At this point:

* You have USD
* No crypto exists yet
* Nothing is burned yet

Your system only records this as revenue in your database.

---

# Your database records the revenue (but does not burn anything)

Your webhook inserts this:

```
platform_revenue_ledger

gross_amount_usd = 50.00
burn_eligible = true
status = RECORDED
```

This is just accounting.

It means:

> “We received $50. In the future, some portion may be used for burn.”

But the money is still sitting in Stripe or your bank.

---

# The weekly burn job calculates what SHOULD be burned

Example weekly totals:

```
Total burn-eligible revenue: $10,000
Burn rate: 10%
Burn allocation: $1,000
```

Your database creates:

```
burn_batches

usd_reserved = 1000
status = RESERVED
```

Still nothing has burned.

This is just saying:

> “We plan to burn $1,000 worth of tokens.”

The money is still USD in your bank.

---

# Now comes the important real-world step: moving USD to crypto

Stripe cannot burn tokens.

Stripe only holds USD.

So you must convert USD → USDC on Base blockchain.

This happens outside Stripe.

Example real flow:

1. Stripe → Bank account
2. Bank account → Coinbase (or similar exchange)
3. Buy USDC
4. Send USDC to your burn executor wallet on Base

Now your burn wallet holds:

```
1000 USDC
```

This is crypto and can be used to burn.

---

# Now your ChainGateway executes the burn

This is the automated step you built.

It does two things:

Step 1 — swap USDC → CANDLE

```
1000 USDC → 85,000 CANDLE
```

Step 2 — send CANDLE to burn address

```
85,000 CANDLE → 0x000...dead
```

That address has no private key.

The tokens are permanently destroyed.

---

# Then your database marks it complete

Your system updates:

```
burn_batches

status = BURNED
burn_tx_hash = 0xabc...
```

and

```
platform_revenue_ledger

status = BURNED
```

Now the burn is complete and auditable.

---

# Important truth: Stripe NEVER burns anything automatically

Stripe cannot access blockchain.

Stripe cannot destroy tokens.

Stripe only holds USD.

Your burn only happens when ALL of these steps occur:

1. Revenue recorded
2. Burn batch created
3. USD converted to USDC
4. ChainGateway swaps USDC → CANDLE
5. ChainGateway sends CANDLE to burn address

Only then are tokens burned.

---

# Your system separates accounting from execution

Think of it like this:

Stripe / Bank = money storage
Database = accounting ledger
ChainGateway = execution engine
Blockchain = destruction mechanism

Each has a separate role.

---

# Simple visual version

Stripe receives money:

```
Driver pays $50 → Stripe
```

Database records it:

```
platform_revenue_ledger → $50 recorded
```

Weekly burn calculates:

```
burn_batches → $5 allocated to burn
```

You move money to blockchain:

```
Bank → Coinbase → USDC → Burn wallet
```

ChainGateway executes burn:

```
USDC → buy CANDLE → send to burn address
```

Tokens destroyed forever.

---

# What is automatic vs manual right now

Automatic:

* recording revenue
* calculating burn allocation
* creating burn batches
* executing swap + burn once USDC exists in wallet

Manual:

* moving USD from bank to blockchain (buy USDC)

Later you can automate treasury funding too, but this is safest for launch.

---

# What you have built is essentially a treasury system

Your system now behaves like a real crypto protocol treasury:

It tracks revenue
allocates burn
executes burn
records burn permanently

with full audit trail.

---

# Most important takeaway

Stripe does NOT burn anything.

Your burn only happens when you move funds to blockchain and run the burn job.

Your database controls when burn SHOULD happen.

Your ChainGateway controls when burn DOES happen.

---

If you want, I can draw a simple diagram of your exact system showing Stripe → DB → Treasury → ChainGateway → Burn so it becomes crystal clear visually.

Yes — **Transak is one option**, but it’s important to understand that **Transak is not required**, and in your case it may not even be the best first choice.

Let’s break down the real options for moving USD → USDC → your burn wallet.

---

# What you actually need: a way to convert USD into USDC on Base

Your ChainGateway can only burn tokens that already exist in your burn wallet.

So you need a bridge between:

```
USD (bank / Stripe)
        ↓
USDC (Base blockchain)
        ↓
Burn executor wallet
```

There are 3 main ways to do this.

---

# Option 1 — Coinbase (RECOMMENDED for you)

This is the easiest and safest.

Flow:

```
Stripe → Bank → Coinbase → Buy USDC → Send to burn wallet
```

Steps:

1. Create Coinbase account for your business (Web Wise Solutions LLC)
2. Transfer USD from bank to Coinbase
3. Buy USDC
4. Click "Send"
5. Enter your burn executor wallet address
6. Select network: Base
7. Send

Done.

Now your ChainGateway can burn.

No special approval needed beyond normal Coinbase verification.

This is the best starting point.

---

# Option 2 — Coinbase API (fully automated later)

Once comfortable, you can automate treasury funding.

Flow:

```
Stripe → Bank → Coinbase API → Buy USDC → Send automatically
```

Your backend triggers it.

This removes manual step.

But start manual first.

---

# Option 3 — Transak (NOT needed unless users are buying directly)

Transak is a fiat-to-crypto provider often used when:

* users buy crypto directly inside your app
* you want embedded fiat onramps

Example:

User opens your app → buys $CANDLE → Transak handles card payment → delivers tokens

But your burn treasury is different.

You are converting your own revenue, not selling tokens to users.

So Transak is unnecessary for treasury burns.

---

# What your ChainGateway actually does

Your ChainGateway does NOT touch USD.

It only works once USDC exists in your wallet.

Example:

Before burn wallet:

```
Wallet balance:
USDC: 1000
CANDLE: 0
```

ChainGateway executes:

```
swap USDC → CANDLE
```

After swap:

```
USDC: 0
CANDLE: 85,000
```

Then burn:

```
transfer CANDLE → burn address
```

After burn:

```
USDC: 0
CANDLE: 0
```

Tokens destroyed.

---

# Important: Stripe will never automatically move money to blockchain

Stripe only handles USD.

You must convert USD → USDC using Coinbase (or similar).

ChainGateway cannot access Stripe or your bank.

---

# Your full real-world flow (exact)

Revenue happens:

```
Driver pays → Stripe → Bank account
```

Treasury funding:

```
Bank account → Coinbase → Buy USDC → Send to burn wallet
```

Burn execution:

```
Burn wallet → ChainGateway swaps → burns tokens
```

Database records:

```
burn_batches → status = BURNED
```

---

# What I recommend you do right now

Step 1:
Create Coinbase account for your business

Step 2:
Create your burn executor wallet

Step 3:
Send small test amount ($10 USDC)

Step 4:
Run execute_batch()

Step 5:
Verify burn transaction on BaseScan

---

# Simple analogy

Stripe = cash register
Coinbase = currency exchange
Burn wallet = furnace fuel tank
ChainGateway = furnace
Burn address = incinerator

Stripe gives you fuel money.

Coinbase converts fuel money into fuel.

ChainGateway burns the fuel.

---

If you want, I can show exactly how to create the burn executor wallet and store its key safely on your DigitalOcean server.

No — **ChainGateway is not a company, not a service, and nothing you apply for.**

It’s just **code that you already own and run inside your own app.**

Think of it like this:

* Stripe → external company (you applied)
* Coinbase → external company (you apply)
* Transak → external company (you apply)

But:

* ChainGateway → **your own Python class running on your server**

You built it (or I helped you build it). It’s part of your backend.

---

# What ChainGateway actually is

It’s simply a piece of code that does this:

```
connect to Base blockchain
send transactions from your burn wallet
swap USDC → CANDLE
send CANDLE → burn address
```

It uses your wallet’s private key.

No application required.

No approval required.

No account required.

---

# Real-world analogy

Think of ChainGateway like a robot arm in your own factory.

You don’t apply to use your own robot.

You install it and control it.

But the robot still needs raw materials.

Those materials come from Coinbase.

---

# What you DO need accounts for

These are the real external things:

### 1. Coinbase (or similar exchange)

Purpose:

Convert USD → USDC

This is required.

---

### 2. Base RPC provider (optional but recommended)

Examples:

* Alchemy
* Infura
* QuickNode

They let your ChainGateway talk to blockchain faster and more reliably.

You already have:

```
BASE_RPC_URL
```

You can use public Base RPC at first.

---

### 3. Your burn executor wallet

This is just a crypto wallet you control.

It has:

```
public address  → safe to share
private key     → must stay secret
```

ChainGateway uses the private key to sign burn transactions.

---

# Where ChainGateway lives in your system

Inside your project:

```
/srv/projects/client/dispatch/app/infra/chain/uniswap_v3_base.py
```

Your weekly burn job calls it:

```
run_weekly_burn()
    → ChainGateway.swap_usdc_to_candle()
    → ChainGateway.burn_candle()
```

---

# Visual flow of your real system

```
Driver pays → Stripe → Bank
                     ↓
                 Coinbase
                     ↓
                 Buy USDC
                     ↓
             Send to burn wallet
                     ↓
              ChainGateway (your code)
                     ↓
          Swap USDC → CANDLE
                     ↓
          Send CANDLE → burn address
                     ↓
             Tokens destroyed forever
```

---

# What you need to do next (practically)

Nothing new to apply for regarding ChainGateway.

You already have it.

You just need:

1. Coinbase account
2. Burn executor wallet funded with USDC
3. Run your weekly burn job

---

# The most important concept to remember

ChainGateway is just your automation tool.

It cannot access your bank.

It cannot access Stripe.

It only controls your crypto wallet.

It executes blockchain transactions using funds already in that wallet.

---

If you want, I can show you exactly how to create the burn executor wallet safely on your DigitalOcean server so ChainGateway can use it securely.

