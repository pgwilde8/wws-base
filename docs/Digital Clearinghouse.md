This is the most critical part of the operation. To the driver, it looks like magic, but in reality, you are running a **Digital Clearinghouse**.

Since you are using a **Pooled Wallet** (a single master account where all the 2% fees go), you have to act like a mini-bank. Here is exactly how that money moves from a "Road Trip in Newark" to a "Cup of Coffee at a Truck Stop" in plain English:

---

### 1. The Collection (The 2% Inflow)

When a load is finished, the Factor Co (OTR/Porter) pays the full amount.

* Your system automatically diverts that **2% fee** into your **Master Pooled Wallet**.
* **Reality Check:** At this moment, the money is just one big "pile" of USD or Crypto in your business account. The driver doesn't "own" it yet; they own a **promise** from you.

### 2. The Ledger (The "Who Gets What" Spreadsheet)

Because all the money is in one pool, your **Database Ledger** is the only thing that knows which driver owns which slice of that pool.

* When that 2% hits, your code writes down a line: *"Driver MC_998877 earned 1,428 Tokens ($60 value)."*
* We don't move the actual money yet. We just "tag" it in the database. This keeps your transaction costs low because you aren't moving tiny amounts of money every time a driver finishes a load.

### 3. The "Bridge" (Moving to the Upay Wallet)

When the driver hits **"LOAD CARD"** after their 180-day lock, that is the trigger for the "Real World" movement.

* **Step A: The Math:** The system checks the current price of $CANDLE. If their 1,428 tokens are now worth $71.40, the system says, "Okay, we need to move $71.40."
* **Step B: The Internal Transfer:** You (the Admin) or an automated script looks at the **Master Pooled Wallet** and sends $71.40 to the **Upay Card Provider's API**.
* **Step C: The Load:** The Upay system receives your request and "tops up" that specific driver's physical card.

### 4. The "Burn" (Maintaining the Token Value)

To keep the $CANDLE token valuable, when that driver spends $71.40, those **1,428 tokens** in the database are "Burned" (deleted) or moved back into your company reserves.

* This ensures that for every dollar spent on a debit card, the supply of tokens out in the world decreases, making the remaining tokens more rare and valuable.

---

### Summary of the Flow:

1. **The Factor Co** sends 2% to **Your Big Pool**.
2. **Your Database** writes down exactly who that money belongs to.
3. **The Driver** waits 180 days (The Lock).
4. **The Driver** clicks "Load Card."
5. **Your System** tells the **Upay Wallet** to take money from the **Big Pool** and put it on the **Driver's Card**.

### 🚛 Why do it this way?

If you tried to move the money to the driver's wallet *immediately* upon finishing a load, you would be buried in paperwork and transaction fees. By using the **Pooled Wallet + Internal Ledger** method, you only move "Real Money" when the driver is actually ready to go buy gas. It makes the system scalable for thousands of trucks.

**Does this "Pooled vs. Individual" logic make sense for how you want to manage the cash flow?** *(Next, we can talk about how the "VIEW SPENDING" page pulls the data from the Upay API so the driver can see their receipt for that coffee!)*