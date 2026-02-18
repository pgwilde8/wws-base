# Driver Dashboard Redesign Discussion

## Current State

### Current Dashboard (`/drivers/dashboard`)
- **Header**: GCD COMMAND, dispatch email (e.g., `laarne3@gcdloads.com`), MC number, Automation Fuel ($CANDLE balance)
- **Left Column**:
  - Scout Status (Live Intelligence)
  - Automation Fuel Costs (table)
  - "When you win a load" (instructions for Manage)
- **Right Column**:
  - Active Negotiations (HTMX loads `/drivers/dashboard-active-loads`)
- **Bottom Nav**: Dashboard, Load Board, Fleet, Paperwork, Terminal, Help

### Issues Identified
1. **`/drivers/terminal`** → 404 (requires `load_id`: `/drivers/terminal/{load_id}`)
2. **`/drivers/savings`** → Legacy page (token portfolio stats)
3. Dashboard is confusing — unclear what each section/page does
4. No clear overview of "jobs the Chrome extension has picked"

---

## Available Driver Routes

| Route | Purpose | Status |
|-------|---------|--------|
| `/drivers/dashboard` | Main dashboard (Command Center) | ✅ Active |
| `/drivers/load-board` | Scout configuration & quick-launch | ✅ Active |
| `/drivers/fleet` | Fleet management | ✅ Active |
| `/drivers/uploads` | Paperwork (BOL, invoice, docs for won loads) | ✅ Active |
| `/drivers/loads/{load_id}/manage` | Unified load management (BOL, invoice, send to Century) | ✅ Active |
| `/drivers/terminal/{load_id}` | Negotiation terminal for a specific load (messages, AI suggestions) | ⚠️ Requires load_id |
| `/drivers/savings` | Legacy: Token portfolio stats (cost basis, ROI, vesting) | ⚠️ Legacy |

---

## Chrome Extension Flow

**How it works:**
1. Driver installs Chrome extension
2. Extension scrapes DAT/TruckSmarter load boards
3. Extension sends loads to `/api/scout/capture-load` (via `ingest.py`)
4. Loads appear in database → should show up somewhere for driver to see

**Current gap:** No clear page showing "jobs the extension has picked" — these loads need to be visible to the driver.

---

## Proposed Dashboard Structure

### Primary Dashboard (`/drivers/dashboard`) Should Be:

**A hub/landing page with:**
1. **Quick stats at top** (keep current header)
   - Dispatch email, MC, Fuel balance

2. **Main content: Table/Grid of links to specific pages**
   - Each row/card explains what the page does + link
   - Organized by workflow stage

3. **Key sections to showcase:**

   **A. Load Discovery & Negotiation**
   - **"Scout Picked Loads"** → Link to page showing loads the Chrome extension captured
     - Explanation: "Jobs the Chrome extension has picked from DAT/TruckSmarter"
     - Link: `/drivers/scout-loads` (or similar — may need to create)
   
   - **"Active Negotiations"** → Current section (keep)
     - Shows negotiations in progress (sent, replied, pending)
     - Link to Load Board to start new ones
   
   - **"Load Board"** → Link to `/drivers/load-board`
     - Explanation: "Configure Scout and launch negotiations"

   **B. After You Win**
   - **"Manage Load"** → Link to `/drivers/uploads` (Paperwork page)
     - Explanation: "After you win a negotiation, use Manage to upload BOL, create invoice, and send packet to Century Finance for funding"
     - Steps: (1) BOL, (2) Invoice, (3) Send to Century
   
   - **"Negotiation Terminal"** → Link to list of loads with terminal access
     - Explanation: "View broker messages and AI suggestions for active negotiations"
     - Note: Requires load_id — maybe show list of active loads with "Open Terminal" buttons?

   **C. Automation & Settings**
   - **"Automation Fuel Costs"** → Keep current table (or link to expanded view)
     - Explanation: "Costs for AI actions (negotiation, voice escalation, factoring packet, full dispatch)"
   
   - **"Fleet Management"** → Link to `/drivers/fleet`
     - Explanation: "Manage your trucks and fleet settings"
   
   - **"Savings Portfolio"** → Link to `/drivers/savings` (if keeping legacy)
     - Explanation: "View your $CANDLE token portfolio, vesting schedule, ROI"

---

## Questions for Discussion

1. **Chrome Extension Loads:**
   - Where should loads captured by the extension appear?
   - Should there be a dedicated `/drivers/scout-loads` page?
   - Or should they appear in "Active Negotiations" automatically?

2. **Terminal:**
   - Fix `/drivers/terminal` → redirect to list of active loads?
   - Or show terminal links on each load card in Active Negotiations?

3. **Savings:**
   - Keep `/drivers/savings` as legacy?
   - Or remove from nav and only link from dashboard if needed?

4. **Dashboard Layout:**
   - Prefer a **table** (rows with explanation + link)?
   - Or **cards/grid** (visual cards with icons)?
   - Or **accordion/sections** (collapsible by workflow stage)?

5. **Priority Order:**
   - What should drivers see first?
   - What's the most common workflow?

---

## Suggested Dashboard Structure (Draft)

```
┌─────────────────────────────────────────────────────────┐
│ GCD COMMAND | laarne3@gcdloads.com | MC: 123456        │
│ Automation Fuel: 10.0 $CANDLE                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ LOAD DISCOVERY & NEGOTIATION                            │
├─────────────────────────────────────────────────────────┤
│ 📡 Scout Picked Loads                                   │
│    Jobs the Chrome extension has picked from            │
│    DAT/TruckSmarter                                     │
│    [View Scout Loads →]                                 │
├─────────────────────────────────────────────────────────┤
│ 💬 Active Negotiations                                  │
│    Current negotiations in progress                      │
│    [View Active →]                                      │
├─────────────────────────────────────────────────────────┤
│ 🎯 Load Board                                            │
│    Configure Scout and launch negotiations              │
│    [Open Load Board →]                                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ AFTER YOU WIN                                           │
├─────────────────────────────────────────────────────────┤
│ 📄 Manage Load (Paperwork)                              │
│    After you win a negotiation:                         │
│    1. Upload BOL (proof of delivery)                   │
│    2. Create invoice                                    │
│    3. Send packet to Century Finance                    │
│    [Go to Paperwork →]                                  │
├─────────────────────────────────────────────────────────┤
│ 💻 Negotiation Terminal                                 │
│    View broker messages and AI suggestions              │
│    [View Terminals →]                                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ AUTOMATION & SETTINGS                                   │
├─────────────────────────────────────────────────────────┤
│ ⛽ Automation Fuel Costs                                │
│    Negotiation: 0.5 | Voice: 0.5 | Packet: 0.3         │
│    Full Dispatch: 10 $CANDLE                           │
├─────────────────────────────────────────────────────────┤
│ 🚛 Fleet Management                                      │
│    Manage your trucks and fleet settings                │
│    [Go to Fleet →]                                      │
└─────────────────────────────────────────────────────────┘
```

---

## Next Steps (After Discussion)

1. **Fix Terminal link** — either redirect to list or remove from nav
2. **Create Scout Loads page** (if needed) — show loads captured by extension
3. **Redesign dashboard** — implement table/card structure with explanations
4. **Update nav** — remove broken links, add new ones if needed
5. **Test workflow** — ensure drivers can navigate from discovery → negotiate → win → manage → fund

---

## Notes

- Keep current "Active Negotiations" section (it's working)
- Keep "Automation Fuel Costs" table (useful reference)
- Keep "When you win a load" instructions (but maybe move to table format)
- Bottom nav should match dashboard links (consistency)
