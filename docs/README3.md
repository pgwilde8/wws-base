That is a move a **Navy specialist** makes—streamlining the gear for maximum efficiency. Consolidating PayPortPro’s features directly into **Green Candle (GC)** is the right play for three reasons:

1. **Reduced Overhead:** You only maintain one database, one server, and one set of security protocols.
2. **Zero Friction:** The driver never has to "switch apps." One login, one dashboard.
3. **Data Integrity:** The "Scraped Load" data becomes the "Invoice" data instantly. No risk of typos or lost files between systems.

To absorb PayPortPro into GC, we need to build **three internal modules** inside your current FastAPI project.

---

### 1. The "Document Vault" (Storage Module)

We need a place to store the Rate-Cons and BOLs. We’ll use **DigitalOcean Spaces** (S3-compatible) so your database doesn't get bloated with heavy images.

* **What to build:** A simple file-upload service in GC.
* **The Logic:** When a driver snaps a photo of the BOL, GC uploads it to a folder labeled by their **MC Number** and the **Load ID**.

### 2. The "Packet Builder" (Verification Module)

This replaces the "Accountant." It’s a piece of Python logic that cross-references the data.

* **The "Handshake":**
* *System checks:* Does the `final_rate` in the database match the rate on the uploaded `rate_con.pdf`?
* *AI Audit:* Use a light LLM call (like GPT-4o-mini) to "read" the BOL and confirm it was signed at the destination.


* **The Result:** A "Verified" status that unlocks the next step.

### 3. The "Bank Bridge" (API Outbound)

This is the piece that talks to the factoring company (OTR, Bobtail, etc.).

* **The Action:** A function that takes your **Universal Load Contract**, grabs the URLs for the PDFs/Images, and sends a `POST` request to the factoring partner’s API.
* **The Webhook:** An endpoint in GC that waits for the bank to say, "Funding Approved." This trigger is what then kicks off the **$CANDLE buyback.**

---

### The Updated GC Architecture

| Folder | Module | Function |
| --- | --- | --- |
| `app/api/` | `scraper.py` | Receives data from the Chrome Extension. |
| `app/api/` | `billing.py` | (New) Handles BOL uploads and Invoice generation. |
| `app/services/` | `factoring_bridge.py` | (New) The logic that sends data to OTR/Triumph. |
| `app/services/` | `tokenomics.py` | Handles the 2% calculation and $CANDLE swap. |

---

### 🛠️ Let’s Build the First "Pipe"

We need the endpoint that receives the document. In your **FastAPI** project, we’ll create a route that accepts a file (the BOL) and links it to a specific Load ID.

**Shall we write the `POST /api/v1/dispatch/upload-bol` code now?** This is the moment GC officially becomes a "Billing" app.

**Would you like me to ... include the logic that automatically calculates the 2% fee the moment that file is uploaded?**

DB:
# Connect to the database
psql "postgresql://wws-admin:WwsAdmin2026%21@localhost/wws_dispatch_db"

export PGPASSWORD='WwsAdmin2026!'
psql -U wws-admin -d wws_dispatch_db -h localhost

sudo -u postgres psql -d wws_dispatch_db

-- List all tables (you should see 7 tables including driver_savings_ledger)
\dt webwise.*

-- Check if your test load was credited
SELECT * FROM webwise.driver_savings_ledger WHERE load_id = 'LOAD_123';

-- View all savings entries
SELECT * FROM webwise.driver_savings_ledger ORDER BY earned_at DESC;

-- Exit
\q