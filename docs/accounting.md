It is not only possible—it’s actually the most powerful feature you can offer. In the trucking industry, transparency is rare. Most drivers feel like they’re being "nickel and dimed" by dispatchers and factors.

Providing a **"Driver Settlement Ledger"** turns your app from a tool into a financial partner. Because you’ve already built the `webwise.driver_savings_ledger` and the `negotiations` table with factoring statuses, you have 90% of the data ready.

---

## **The "Green Candle Ledger" Concept**

Think of this as a **Bank Statement for Truckers**. It should break down every load into a "Cash vs. Fuel" story.

### **1. The Data Mapping**

To give the driver this record, you just need to pull from three sources you’ve already built:

| Event | Data Source | Ledger Entry |
| --- | --- | --- |
| **Buy Fuel** | Stripe/Crypto Webhook | `DEBIT: -$50.00 |
| **Deploy Scout** | `scout_status` / `negotiations` | `CONSUMED: -1.0 $CANDLE` |
| **Load Won** | `negotiations.final_rate` | `PENDING INCOME: +$3,000.00` |
| **Dispatch Fee** | Calculation (2%) | `FEE: -$60.00` |
| **Paperwork Kickback** | `driver_savings_ledger` | `REFILL: +12.6 $CANDLE` |
| **Factoring Funded** | `factoring_status` | `FUNDED: +$2,910.00 (After Factor Fee)` |

---

### **2. The "Friendly Record" UI**

Instead of a boring spreadsheet, use a **Transaction Timeline** on a new page called `settlements.html`.

**Cursor Prompt for the Ledger View:**
"Create a `settlements.html` page that pulls from `driver_savings_ledger` and `negotiations`.

1. **The Header:** Show 'Lifetime Earnings' and 'Total Fuel Earned'.
2. **The List:** Create a vertical timeline of 'Events'.
3. **Color Coding:** - **Green** for money coming in (Factoring/Refills).
* **Amber** for Pending (Loads won but not yet factored).
* **Red/White** for costs (CANDLE bought or fees).


4. **Detail View:** Let the driver click an entry to see the BOL and Rate Con associated with that specific money move."

---

### **3. Why this is the "Kill Shot" for Competitors**

Most dispatchers just send a text saying "I got you $2,500." With your system, the driver gets:

* **Accountability:** They see the 2% fee was exactly $50.
* **Integrity:** They see the 21.05% rebate was applied correctly.
* **Proof:** They see the timestamp of when the factor (OTR) was notified.

---

### **4. The "Account Friendly" Export**

At the end of the year, truckers have to do taxes. If you add a **"Download Tax Summary"** button that zips all their BOLs and a CSV of their fees, they will stay with **Green Candle Dispatch** forever just to avoid that headache.

---

### **Strategic Next Step**

Since you have the `driver_savings_ledger` already recording `CREDITED` and `CONSUMED` statuses, we can build the **"Money & Fuel" Timeline** tomorrow. It’s a great way to start the day because it visualizes all the hard work you’ve done so far.

**Would you like me to draft the SQL query that joins the Ledger and Negotiations tables so you can see what a "Combined Statement" looks like?** It’ll show you exactly how "Account Friendly" your data already is.