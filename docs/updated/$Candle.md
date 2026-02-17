Great — since you already have a **Coinbase business (corporate) account**, you’re 90% of the way there. Now your goal is simply to move **USDC from Coinbase → your burn executor wallet on Base**, so your ChainGateway can execute burns.

Here is the exact step-by-step process.

---

# Step 1 — Create your burn executor wallet (one time)

This wallet is controlled by your server and used only for burns.

On your DigitalOcean server:

```bash
cd /srv/projects/client/dispatch
source venv/bin/activate
python -c "from eth_account import Account; acct=Account.create(); print('ADDRESS:', acct.address); print('PRIVATE_KEY:', acct.key.hex())"
```

Output will look like:

```
ADDRESS: 0xAbC123...
PRIVATE_KEY: 0x8912...
```

Immediately copy both.

---

## Save private key securely in your `.env`

Edit:

```
/srv/projects/client/dispatch/.env
```

Add:

```
BURN_EXECUTOR_PRIVATE_KEY=0x8912...
BURN_EXECUTOR_ADDRESS=0xAbC123...
```

Restart your app after saving.

---

# Step 2 — Add wallet to your treasury_wallets table

Connect to your database:

```bash
psql "$DATABASE_URL"
```

Insert:

```sql
INSERT INTO webwise.treasury_wallets (wallet_name, address, chain)
VALUES ('BURN_EXECUTOR', '0xAbC123...', 'base');
```

---

# Step 3 — Send USDC from Coinbase to your burn wallet

Log into Coinbase business account.

Click:

**Assets → USDC**

Click:

**Send**

Paste your burn wallet address:

```
0xAbC123...
```

Select network:

**Base**

(This is critical — must be Base, not Ethereum)

Send small test amount first:

```
$5 USDC
```

Click Send.

Wait 10–20 seconds.

---

# Step 4 — Verify wallet received USDC

Go to:

[https://basescan.org](https://basescan.org)

Paste your wallet address.

You should see:

```
USDC balance: 5
```

Now ChainGateway can use it.

---

# Step 5 — Test your ChainGateway manually

Activate your Python environment:

```bash
cd /srv/projects/client/dispatch
source venv/bin/activate
```

Run:

```python
from app.infra.chain.uniswap_v3_base import UniswapV3BaseGateway
gw = UniswapV3BaseGateway()
print("USDC:", gw.get_usdc_balance())
```

You should see:

```
USDC: 5.0
```

---

# Step 6 — Execute your first burn test

In your weekly burn job, run:

```python
run_weekly_burn(burn_rate_bps=1000, execute_on_chain=True)
```

This will:

* swap USDC → CANDLE
* send CANDLE → burn address
* update burn_batches table

---

# Step 7 — Verify burn transaction

Go to:

[https://basescan.org](https://basescan.org)

Search your burn executor wallet.

You will see:

```
Swap transaction
Burn transaction → 0x000...dead
```

Burn complete.

---

# Your permanent operational flow going forward

Weekly:

1. Login Coinbase
2. Send USDC to burn wallet
3. Burn job executes automatically

Done.

Later this can be automated via Coinbase API.

---

# Important security rules

Never:

* commit private key to git
* share private key
* store private key in frontend

Only store in:

```
.env
```

on your server.

---

# Your system is now ready to run real burns

Coinbase supplies USDC
ChainGateway executes burn
Database tracks everything

---

If you want, I can also show you how to create a **separate treasury wallet + separate burn wallet**, which is best practice once amounts get larger.
Good timing to ask this — because **you should NOT fund the burn wallet yet if $CANDLE isn’t live and liquid on Base.** You need liquidity first, otherwise the swap will fail or produce bad prices.

Let’s break this into the correct order and safe starting amounts.

---

# First: Do NOT send significant USDC yet

Right now, since:

* $CANDLE is not deployed or not liquid yet
* No Uniswap pool exists
* No price exists

Your ChainGateway cannot swap USDC → CANDLE.

If you try, the transaction will fail.

So start with **$0–$10 max just for testing connectivity**, not burn.

---

# You must complete these steps first (in order)

## Step 1 — Deploy $CANDLE token (Clanker)

Clanker will create your token contract.

After deployment you’ll have:

```
CANDLE token address
```

Example:

```
0xabc...123
```

---

## Step 2 — Create liquidity pool on Uniswap (Base)

This is critical.

You must supply initial liquidity.

Example starting liquidity:

```
$500 USDC
+
equivalent $500 CANDLE
```

Total pool value: $1,000

This allows swaps to work.

Without liquidity, burn cannot function.

---

## Step 3 — Verify swap works manually

Test swap using Uniswap UI:

[https://app.uniswap.org](https://app.uniswap.org)

Network: Base

Swap:

```
USDC → CANDLE
```

If swap succeeds, ChainGateway will work.

---

# Only AFTER liquidity exists should you fund burn wallet

Start small.

Recommended initial burn wallet funding:

```
$25–$50 USDC
```

This lets you:

* test burn pipeline safely
* verify accounting
* verify swaps work
* verify burn tx logs correctly

No need for more early.

---

# After your platform generates real revenue

Your burn wallet funding should match burn allocation.

Example:

If weekly burn allocation:

```
$320 reserved
```

Send:

```
$320 USDC
```

to burn wallet.

ChainGateway burns it.

---

# Recommended starting amounts for full launch

Liquidity pool:

```
$500–$2,000 USDC
+
equal CANDLE
```

Burn wallet:

```
$50–$200 USDC
```

Treasury wallet:

```
optional reserve
```

---

# Why liquidity is required first

Your burn system executes:

```
swap USDC → CANDLE
```

That requires someone selling CANDLE.

Liquidity pool provides that counterparty.

Without liquidity:

```
swap fails
```

---

# Safe launch checklist for you

Order matters:

1. Deploy CANDLE via Clanker
2. Add Uniswap liquidity pool
3. Test swap manually
4. Send $25 USDC to burn wallet
5. Run burn job test
6. Verify burn tx on BaseScan
7. Scale up as revenue grows

---

# Very important early-stage advice

Burns are not useful without liquidity.

Liquidity first.

Burn second.

Revenue third.

Then burn grows automatically.

---

# Simple recommendation for your exact situation today

Since $CANDLE isn’t live yet:

Send:

```
$0 USDC for burn
```

Wait until token + liquidity exists.

Once live, send:

```
$25 USDC
```

and test burn.

---

If you want, I can also recommend **exact initial token supply, liquidity ratio, and burn rate** so $CANDLE launches cleanly and sustainably.
