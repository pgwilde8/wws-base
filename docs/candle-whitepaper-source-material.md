# $CANDLE White Paper — Source Material & Technical Details

**Purpose:** Accumulate all technical details needed for the $CANDLE white paper, sourced directly from codebase and documentation.

**Last Updated:** Based on current codebase as of this date.

---

## 1. The AI Dispatch Logic (Scout & Negotiator)

### The Scout: Load Board Scanning

**How It Works:**
- **Chrome Extension** (`app/green-candle-extension/`) scans load boards (DAT, Truckstop, etc.)
- Extension sends loads to `/api/loads` endpoint (`app/routes/ingest.py`)
- System analyzes profitability using `analyze_profitability()` function
- Loads stored in `webwise.loads` table with status: `NEW`, `ANALYZED`, `HIDDEN`, `WON`

**Scanning Frequency:**
- **Real-time** — Extension runs when driver browses load boards
- **Continuous** — System processes loads as they're discovered
- **Driver-Controlled** — Drivers set their own criteria via Scout Configuration (`/drivers/load-board`)

**Scout Configuration:**
- **Target Lanes:** Driver sets preferred lanes (e.g., "NJ-FL, NJ-GA")
- **Minimum Rate Per Mile:** Driver sets floor (default: $2.45/mile)
- Stored in `webwise.scout_status` table
- Used to filter and prioritize loads

**"Green Candle" Indicators (Profitable Loads):**
- System analyzes loads using `analyze_profitability()` function
- High-value loads flagged as "HOT LOAD" in logs
- Loads matching driver's criteria are surfaced immediately
- **Key File:** `app/routes/ingest.py` (lines 72-76)

**Code References:**
- Scout config: `app/routes/client.py` (lines 409-451)
- Load ingestion: `app/routes/ingest.py`
- Load model: `app/models/load.py`
- Scout status: `app/schemas/scout.py`

---

### The Negotiation: AI Rate Fighting

**How It Works:**
- AI drafts negotiation emails using `AIAgentService.draft_negotiation_email()`
- Uses OpenAI GPT-4o to write professional broker emails
- **Target Price:** Current offer + $300 (configurable)
- **Auto-Pilot Logic:** Handles broker replies automatically (`app/services/autopilot.py`)

**Negotiation Strategy:**

**1. Initial Bid:**
- AI drafts email asking broker to meet target price
- Target = Original offer + $300 (example)
- Uses driver's current location for context
- **Code:** `app/services/ai_agent.py` (lines 17-26)

**2. Auto-Pilot Response Logic:**
When broker replies, AI decides:
- **AUTO_ACCEPT:** If offer ≥ target price → Accept immediately
- **AUTO_COUNTER:** If offer ≥ floor price but < target → Counter with +$100 (up to target)
- **MANUAL_REQUIRED:** If offer < floor price → Alert driver for manual decision
- **Code:** `app/services/autopilot.py` (lines 38-70)

**3. Market Data Usage:**
- **Market Intel Engine:** `app/services/market_intel.py`
- Uses lane benchmarks (e.g., NJ→FL: $2.45/mile, FL→NJ: $1.85/mile)
- Can pull from historical won loads as database grows
- Currently uses static benchmarks, designed to evolve to dynamic data
- **Code:** `app/services/market_intel.py` (lines 9-66)

**Broker Database Usage (25k+ Brokers):**

**Current Implementation:**
- Broker database: `webwise.brokers` table
- Contains: MC number, company name, primary email, phone, address
- **25,000+ brokers** in database
- Used for: Email routing, contact information, broker identification

**Future Enhancements (Not Yet Implemented):**
- Historical rate tracking per broker
- Broker reliability scoring
- Slow-pay detection
- Double-brokering detection
- Lane-specific broker performance

**Current Broker Data Usage:**
- Email routing: Broker emails extracted and used for negotiation
- Contact lookup: MC number → broker contact info
- **Code Reference:** `docs/updated/BROKER_DATABASE_README.md`

**What the AI Uses Now:**
- Driver's preferred lanes
- Driver's minimum rate per mile
- Market lane benchmarks (static)
- Load origin/destination
- Driver's current location

**What the AI Will Use (Future):**
- Historical rates per broker per lane
- Broker payment history
- Broker reliability scores
- Real-time market rates from DAT/Truckstop API

**Code References:**
- AI Agent: `app/services/ai_agent.py`
- Auto-Pilot: `app/services/autopilot.py`
- Market Intel: `app/services/market_intel.py`
- Negotiation Model: `app/models/negotiation.py`
- Broker DB: `docs/updated/BROKER_DATABASE_README.md`

---

## 2. The $CANDLE Utility (Automation Fuel)

### The Mint/Earn: Driver Service Credits

**How Drivers Earn $CANDLE:**
- **21.05% of 2% dispatch fee** returned as service credits
- **1:1 USD → CANDLE ratio** (internal credits)
- Credits issued when driver **uploads BOL** (not when load is won)
- Stored in `webwise.driver_savings_ledger`

**Example Per Load ($1,900):**
- Broker pays: $1,900
- Factoring takes: $57 (3%)
- **Green Candle fee: $38 (2%)**
- **Driver earns: ~$8 → 8 CANDLE** (21.05% of $38)
- Driver receives: $1,805

**Code Reference:**
- `app/services/ledger.py` (lines 10-12)
- `DRIVER_REBATE_RATIO = 0.2105` (21.05%)
- Function: `process_load_settlement()` issues credits

**When Credits Are Issued:**
- **Trigger:** Driver uploads BOL (Bill of Lading)
- **Function:** `process_load_settlement()` in `ledger.py`
- **Not issued:** When load is marked "won" (only when BOL uploaded)

**Immediate Availability:**
- Credits are **immediately available** for use
- No vesting, no locking, no delays
- Stored in `driver_savings_ledger` with `unlocks_at=now()` and `status='CREDITED'`
- **Code:** `app/services/ledger.py` (lines 79-92)
- **Note:** Previous 6-month vesting was removed - all credits are immediate-use

---

### The Spend: Automation Fuel Costs

**Current $CANDLE Costs (from code):**

| Action | Cost (CANDLE) | Code Reference |
|--------|---------------|----------------|
| **Negotiation Agent** | 0.5 | `NEGOTIATION_AGENT_COST` |
| **Factoring Packet** | 0.3 | `FACTORING_PACKET_COST` |
| **Full Dispatch** | 10.0 | `FULL_DISPATCH_COST` |
| **Auto-Booking** | 10.0 | `AUTO_BOOKING_COST` |
| **Manual Email** | 0.5 | `OUTBOUND_EMAIL_COST` |
| **Voice Escalation** | 0.5 | `AI_VOICE_CALL_COST` |
| **Document Parse** | 1.0 | `DOC_PARSE_COST` |

**Code Reference:** `app/services/ledger.py` (lines 124-137)

**Example "Cost of Living" for a Driver:**

**Per Load:**
- Auto-Negotiate: 0.5 CANDLE
- Factoring Packet: 0.3 CANDLE
- **Total per load: ~0.8 CANDLE**

**Per Week (15 loads):**
- 15 loads × 0.8 = **12 CANDLE/week**
- Driver earns: 15 loads × 8 CANDLE = **120 CANDLE/week**
- **Net: +108 CANDLE/week** (earn more than spend)

**Fully Autonomous Mode:**
- Full dispatch automation: 10 CANDLE per successful load
- 15 loads/week = **150 CANDLE/week**
- Driver earns: 120 CANDLE/week
- **Net: -30 CANDLE/week** (need to buy or earn more)

**Code Reference:**
- Usage rates: `app/services/ledger.py` (lines 124-137)
- Balance check: `has_sufficient_fuel()` function (lines 140-146)
- Usage recording: `record_usage()` function (lines 149+)

---

### The Burn: 10% Profit Burn

**What Gets Burned:**
- **10% of platform profit** (from 2% dispatch fee)
- **NOT** from driver service credits
- **NOT** from internal ledger entries
- **ONLY** from real USD revenue received

**Burn Sources:**

| Source | Example Revenue | Burn @ 10% |
|--------|----------------|------------|
| **Dispatch fee margin** | $10 per load | $1.00 |
| **Call pack profit** | $97 per pack | $9.70 |
| **Automation purchases** | $50 per purchase | $5.00 |
| **Factoring referral** | $6.65 per load | $0.66 |
| **Broker subscription** | $149/month | $14.90 |

**Allocation of 2% Fee ($38 example):**
- Driver credits: $8 (21.05%) ❌ NOT burned
- AI/Infra reserve: $8 (21.05%) ❌ NOT burned
- **Platform profit: $12 (31.58%)** ✅ **BURN ELIGIBLE**
- Treasury: $10 (26.32%) ❌ NOT burned (backing)

**Burn Rate:**
- **Launch:** 5% of platform profit
- **Growth:** 10% of platform profit (recommended)
- **Aggressive:** 15-20% (max sustainable)

**Burn Execution:**
- Weekly or daily burn job
- Buys $CANDLE with USD from platform profit
- Sends $CANDLE to burn address
- Marks revenue transactions as `burned = true`

**Code References:**
- Burn architecture: `docs/updated/burn.md`
- Revenue model: `docs/updated/rev.md`
- Platform profit ratio: `app/services/ledger.py` (line 15)

---

## 3. The "Broker Moat" (The Data Edge)

### Current Broker Database

**Size:** 25,000+ brokers

**Data Stored:**
- MC number (primary key)
- Company name
- Primary email
- Phone numbers
- Physical address
- DOT number
- Website
- Source (FMCSA, manual, enriched)

**Tables:**
- `webwise.brokers` — One row per MC#
- `webwise.broker_emails` — Multiple emails per MC with confidence scores

**Code Reference:** `docs/updated/BROKER_DATABASE_README.md`

---

### How System Uses Broker Data (Current)

**1. Email Routing:**
- MC number → broker email lookup
- Used to send negotiation emails
- Tracks broker replies

**2. Contact Information:**
- Lookup broker contact details
- Phone numbers for escalation
- Address for verification

**3. Negotiation Tracking:**
- Links negotiations to broker MC numbers
- Tracks broker response rates
- Stores broker replies in `webwise.negotiations`

**Current Limitations:**
- No historical rate tracking per broker
- No broker reliability scoring (yet)
- No slow-pay detection (yet)
- No double-brokering detection (yet)

---

### Future Broker Data Advantages (White Paper Vision)

**1. Historical Rate Intelligence:**
- "Our AI checks historical rates for this broker on this lane"
- "We know Broker X typically pays $2.50/mile for NJ→FL"
- "We counter with confidence based on past performance"

**2. Broker Reliability Scoring:**
- "Our database identifies slow-pay brokers instantly"
- "We flag brokers with payment issues before you book"
- "Protect your bottom line with broker risk scores"

**3. Double-Brokering Detection:**
- "Our system flags potential double-brokered loads"
- "We verify broker credentials before negotiation"
- "Protect against freight fraud"

**4. Lane-Specific Performance:**
- "Broker Y pays well for NJ→GA but lowballs on GA→NJ"
- "We adjust negotiation strategy based on broker lane history"
- "Maximize rate based on broker patterns"

**Implementation Status:**
- ✅ Broker database exists (25k+ brokers)
- ✅ Email routing works
- ⏳ Historical rate tracking (future)
- ⏳ Reliability scoring (future)
- ⏳ Double-brokering detection (future)

**White Paper Angle:**
- Emphasize the **data moat** — 25k+ brokers is a competitive advantage
- Position as "We know the brokers better than anyone"
- Frame as "Protection layer" for drivers
- Future roadmap: "Building the most comprehensive broker intelligence system"

---

## 4. The NJ Beta Roadmap

### Current Beta Status

**Target:** NJ-area owner-operators and small fleets

**Beta Stages (from code):**
1. **APPROVED** — Application approved
2. **LOGGED_IN** — Driver logs in
3. **PROFILE_COMPLETED** — Profile setup done
4. **FIRST_SCOUT** — First load scan
5. **FIRST_NEGOTIATION** — First negotiation attempt
6. **FIRST_LOAD_WON** — First load secured
7. **FIRST_LOAD_FUNDED** — First load paid (BOL uploaded)
8. **ACTIVE** — Derived: FIRST_LOAD_FUNDED + activity within 14 days

**Code Reference:** `app/services/beta_activation.py` (lines 16-36)

---

### Milestone 1: Founding Drivers (First 3 Owner-Operators)

**Goal:** Onboard first 3 NJ owner-operators

**Requirements:**
- MC number
- Phone + email
- Preferred lanes
- Factoring company (if using)

**Process:**
1. Driver applies at `/beta/apply`
2. Admin approves (`/admin/beta`)
3. Login credentials sent within 24 hours
4. Driver completes onboarding
5. Driver sets Scout configuration (lanes, min rate)

**Success Metrics:**
- 3 drivers approved
- 3 drivers logged in
- 3 drivers completed profiles
- 3 drivers scanned first load

**Code References:**
- Beta apply: `app/routes/beta_apply.py`
- Admin approval: `app/routes/admin_beta.py`
- Onboarding: `app/services/onboarding.py`

---

### Milestone 2: Factoring Webhook Integration

**Goal:** Instant $CANDLE rewards when factoring funds driver

**Current Flow:**
- Driver uploads BOL → Credits issued
- Manual process (driver uploads, admin processes)

**Future Flow:**
- Factoring webhook → Automatic credit issuance
- Real-time $CANDLE rewards
- No manual intervention

**Implementation:**
- Webhook endpoint: `/webhooks/factoring` (exists)
- Needs: Factoring partner integration
- Function: `process_load_settlement()` auto-triggers

**Code References:**
- Webhooks: `app/routes/webhooks.py`
- Settlement: `app/services/ledger.py` → `process_load_settlement()`

---

### Milestone 3: National Expansion via Scout Heartbeat API

**Goal:** Expand beyond NJ using automated load scanning

**Current:**
- Chrome Extension (manual scanning)
- Driver browses load boards
- Extension sends loads to API

**Future:**
- **Scout Heartbeat API** — Automated scanning
- System scans load boards continuously
- Alerts drivers when matching loads appear
- No manual browsing required

**Implementation:**
- API endpoint: `/api/scout/update` (exists)
- Needs: Automated scanning service
- Needs: Load board API integration (DAT/Truckstop)

**Code References:**
- Scout API: `app/routes/api.py` (lines 26-69)
- Load board service: `app/services/load_board.py`

---

## 5. Real-World Assets (RWA) Angle

### Why $CANDLE is Backed by Real Freight Movement

**Every Load = Real Revenue:**

**Example: Elizabeth, NJ → Philadelphia, PA**
1. **Load completed:** Driver delivers freight
2. **Broker pays:** $1,900 invoice
3. **Factoring funds:** Driver receives $1,805
4. **Platform earns:** $38 dispatch fee
5. **Driver earns:** 8 CANDLE (21.05% of fee)
6. **Platform burns:** ~$1.20 worth of CANDLE (10% of $12 profit)

**The Cycle:**
- Real freight moves → Real revenue generated → Real $CANDLE earned → Real $CANDLE burned
- Not speculative — backed by actual logistics operations
- Every CANDLE represents a completed load
- Supply reduction tied to platform growth

**White Paper Emphasis:**
- "Every $CANDLE is backed by real freight movement"
- "Supply reduction tied to platform revenue growth"
- "Unlike meme coins, $CANDLE has real-world utility and backing"
- "RWA (Real-World Assets) tokenomics — freight-backed token"

---

## 6. Key Metrics for White Paper

### Per Load Economics ($1,900 example)

| Metric | Value |
|--------|-------|
| Broker pays | $1,900 |
| Factoring fee (3%) | $57 |
| **Green Candle fee (2%)** | **$38** |
| Driver receives | $1,805 |
| **Driver earns CANDLE** | **8 CANDLE** |
| Platform profit | $12 |
| **CANDLE burned** | **~$1.20 worth** |

### Per Driver Per Month (15 loads)

| Metric | Value |
|--------|-------|
| Loads completed | 15 |
| Platform revenue | $570 |
| Platform profit | $180 |
| **CANDLE burned** | **~$18 worth** |
| Driver earns CANDLE | 120 CANDLE |
| Driver spends CANDLE | ~12 CANDLE |
| **Driver net CANDLE** | **+108 CANDLE** |

### At Scale (1,000 drivers)

| Metric | Value |
|--------|-------|
| Monthly loads | 15,000 |
| Platform revenue | $570,000 |
| Platform profit | $180,000 |
| **CANDLE burned/month** | **~$18,000 worth** |
| Driver CANDLE earned | 120,000 CANDLE |
| **Annual burn** | **~$216,000 worth** |

---

## 7. Technical Architecture Summary

### Core Components

1. **Chrome Extension** — Load board scanning
2. **FastAPI Backend** — API and business logic
3. **PostgreSQL Database** — Loads, brokers, negotiations, ledger
4. **OpenAI Integration** — AI negotiation drafting
5. **Email System** — Broker communication
6. **Factoring Integration** — Payment processing
7. **Blockchain Integration** — $CANDLE token (Base/EVM)

### Key Services

- `ledger.py` — CANDLE credits and usage
- `ai_agent.py` — Negotiation email drafting
- `autopilot.py` — Auto-negotiation logic
- `market_intel.py` — Lane rate benchmarks
- `beta_activation.py` — Driver onboarding tracking
- `burn.py` — Token burn mechanics

---

## 8. White Paper Sections Needed

### Executive Summary
- Real-World Assets (RWA) angle
- Freight-backed tokenomics
- 2% fee model
- 21.05% driver rebate
- 10% profit burn

### The Problem
- Traditional dispatch takes 10% cut
- Drivers miss profitable loads
- Manual negotiation is slow
- Paperwork is time-consuming

### The Solution
- AI-powered dispatch
- 2% flat fee
- Automated negotiation
- Instant paperwork
- $CANDLE automation fuel

### The Technology
- Scout: Real-time load scanning
- Negotiator: AI rate fighting with market data
- Broker Moat: 25k+ broker database
- Automation: CANDLE-gated features

### The Tokenomics
- Earn: 21.05% of fee → CANDLE (immediate-use)
- Spend: Automation fuel costs
- Burn: 10% of platform profit
- Availability: Immediate (no vesting, no locking)

### The Roadmap
- Milestone 1: Founding drivers (NJ)
- Milestone 2: Factoring webhook
- Milestone 3: National expansion

### The Team
- (Add team info)

### The Vision
- Become the standard for owner-operator dispatch
- Build the largest broker intelligence database
- Create sustainable tokenomics backed by real freight

---

## Files Referenced

### Code Files
- `app/services/ledger.py` — CANDLE credits and costs
- `app/services/ai_agent.py` — AI negotiation
- `app/services/autopilot.py` — Auto-negotiation logic
- `app/services/market_intel.py` — Lane benchmarks
- `app/services/beta_activation.py` — Beta stages
- `app/routes/ingest.py` — Load ingestion
- `app/routes/api.py` — Scout API
- `app/models/negotiation.py` — Negotiation model

### Documentation Files
- `docs/updated/rev.md` — Revenue model
- `docs/updated/burn.md` — Burn architecture
- `docs/updated/BROKER_DATABASE_README.md` — Broker DB
- `docs/Revenue Model and System Economics.md` — Economics

---

## Next Steps for White Paper

1. ✅ **Technical details gathered** (this document)
2. ⏳ **Write Executive Summary** (RWA angle)
3. ⏳ **Write Problem/Solution sections**
4. ⏳ **Write Technology section** (Scout/Negotiator details)
5. ⏳ **Write Tokenomics section** (earn/spend/burn)
6. ⏳ **Write Roadmap section** (NJ beta milestones)
7. ⏳ **Add team/vision sections**
8. ⏳ **Design and formatting**

---

**This document serves as the source of truth for all technical details in the $CANDLE white paper.**
