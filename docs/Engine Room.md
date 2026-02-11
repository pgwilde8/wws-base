This is the **"Engine Room"** of your entire operation. The connection between your SaaS (Green Candle), the Driver, and OTR Solutions is what makes the "Instant Pay" possible.

It isn't magic; it is a specific legal and technical workflow.

### The Workflow: From "Empty Truck" to "Paid"

#### 1. The Setup (The "Handshake")

Before a driver can haul their first load, they must sign a **Notice of Assignment (NOA)**.

* **What it is:** A legal letter that tells brokers: *"Do not pay me directly. Pay OTR Solutions instead."*
* **Your SaaS Role:** When a driver onboards, your app generates this PDF with their signature and sends it to OTR's API. OTR now "owns" that driver's receivables.

#### 2. The Load Completion (The "Trigger")

The driver drops off the freight. They are standing on a loading dock with a piece of paper: the **Bill of Lading (BOL)**. This paper is signed by the receiver, proving the job is done.

* **The Driver's Action:** They open the Green Candle App, tap "Upload BOL," and snap a photo.
* **Your AI's Action:**
* **OCRs the Image:** Reads the text to verify the delivery address and signature match the load details.
* **Generates Invoice:** Your SaaS automatically creates a professional PDF invoice for **$3,000** (or whatever the rate is) addressed to the Broker.
* **Bundles the Packet:** It combines the Invoice + Signed BOL + Rate Confirmation into a single PDF called the "Factoring Packet."



#### 3. The API Handoff (The "Pitch")

This is where your SaaS earns its keep. Instead of the driver emailing OTR, your server talks to OTR's server.

* **The Request:** Your server sends the "Factoring Packet" to OTR via API (or secure email integration).
* **The Data:** You send key metadata: `Broker_MC_Number`, `Load_ID`, `Amount`, and `Driver_ID`.

#### 4. The Funding (The "Catch")

OTR Solutions receives the packet. Their system checks the credit of the broker.

* **Approval:** If the broker is good (e.g., C.H. Robinson, TQL), OTR approves the invoice instantly.
* **The Split:**
* **Total Load:** $3,000.
* **OTR Fee (2.5%):** -$75.
* **Net to Distribute:** $2,925.


* **The Transfer:** OTR sends an ACH or Wire Transfer to the Driver's Bank Account for **$2,925**.

#### 5. The "Green Candle" Cut (The 2% Logic)

*Wait, how do YOU get your 2% fee?*
There are two ways to handle this, depending on your integration level with OTR:

* **Option A: Split Funding (Advanced)**
* You instruct OTR (via the NOA) to *always* send 2% of the Gross to **Green Candle's Bank Account** and the rest to the Driver.
* *Result:* You get $60 wire. Driver gets $2,865 wire.
* *Pros:* Guaranteed payment. You control the money.
* *Cons:* Requires a specific agreement with OTR (called a "Split Letter").


* **Option B: Weekly Sweep (Easier)**
* OTR pays the driver 100% of the net funds.
* Your SaaS tracks this. On Friday, you charge the driver's credit card/bank account on file for the accumulated 2% fees.
* *Pros:* Easier to set up.
* *Cons:* Risk of failed payments if the driver spent the money.



**Recommendation:** Go for **Option A (Split Funding)**. OTR Solutions is tech-forward; they can likely handle a "Split Instruction" where the 2% fee is diverted directly to you. This is crucial for the "Forced Savings" model to work seamlessly.

### Summary for the Driver

You don't need to explain the API to them. You just tell them:

> *"Snap a photo of the BOL. We handle the paperwork. The money hits your bank account today, and your savings vault grows automatically."*