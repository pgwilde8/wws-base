# 🕯️ Green Candle Scout - Chrome Extension

**Field Agent for Load Board Data Ingestion**

This Chrome Extension acts as a "Side-Saddle" scraper, allowing drivers to send load board data directly to the Green Candle Dispatch backend.

---

## 📦 Installation

1. **Open Chrome Extensions Page:**
   - Navigate to `chrome://extensions/`
   - OR: Chrome Menu → More Tools → Extensions

2. **Enable Developer Mode:**
   - Toggle "Developer mode" switch (top right)

3. **Load the Extension:**
   - Click "Load unpacked"
   - Select this folder: `/srv/projects/client/dispatch/app/green-candle-extension`

4. **Verify Installation:**
   - You should see "Green Candle Scout" in your extensions list
   - The extension icon (🕯️) should appear in your Chrome toolbar

---

## 🧪 Testing (Local Development)

### Step 1: Start Your FastAPI Server

```bash
cd /srv/projects/client/dispatch
python3 -m uvicorn app.main:app --reload --port 8990
```

### Step 2: Open Test Page

Navigate to: **http://localhost:8990/test-loads**

This page contains a simple HTML table with sample load data.

### Step 3: Scrape the Page

1. Click the **Green Candle Scout** extension icon (🕯️)
2. Click the green **"SCRAPE PAGE"** button
3. Watch the status update: `"Sent X loads!"`

### Step 4: Verify Data Ingestion

**Check Server Console:**
```
🚀 Sending data to HQ... [{...}, {...}]
✅ HQ Response: {status: "success", new_loads: 4, ...}
```

**Check Database:**
```sql
SELECT * FROM webwise.loads ORDER BY created_at DESC LIMIT 10;
```

You should see the 4 test loads (Newark→Miami, Chicago→Dallas, LA→Phoenix, Atlanta→Charlotte).

---

## 🔧 How It Works

### Architecture

1. **popup.html** → User clicks "SCRAPE PAGE" button
2. **popup.js** → Sends message to content script
3. **content.js** → Scrapes the current page's HTML table
4. **background.js** → POSTs JSON to FastAPI `/api/ingest/loads`
5. **FastAPI Backend** → Stores data in `webwise.loads` table

### File Structure

```
green-candle-extension/
├── manifest.json      # Extension configuration & permissions
├── popup.html         # UI (the button interface)
├── popup.js           # Button click handler
├── content.js         # Page scraper (runs on every page)
└── background.js      # API courier (sends data to backend)
```

---

## 🎯 Production Setup (DAT/Truckstop)

When ready to target real load boards:

1. **Update `content.js`:**
   - Replace generic `tr` selector with DAT-specific classes (e.g., `.dat-row`)
   - Extract DAT-specific fields (broker name, equipment type, etc.)

2. **Update `manifest.json`:**
   - Add production API URL to `host_permissions`
   - Update `API_URL` in `background.js`

3. **Test on Real Load Board:**
   - Driver logs into DAT/Truckstop
   - Extension automatically scrapes visible loads
   - Data flows to backend for AI evaluation

---

## 🐛 Troubleshooting

**"Error: Refresh Page"**
- The content script didn't inject properly
- Refresh the page and try again

**"HQ Connection Failed"**
- Check that FastAPI server is running on port 8990
- Verify CORS is enabled (if testing from different origin)
- Check browser console (F12) for detailed error

**No Data in Database**
- Check server logs for ingestion errors
- Verify `webwise.loads` table exists (`bootstrap_db.py`)
- Check database connection in `.env`

---

## 📝 Notes

- **Current Mode:** Generic table scraper (works on any HTML table)
- **Future Mode:** DAT/Truckstop-specific selectors
- **API Endpoint:** `POST http://localhost:8990/api/ingest/loads`
- **Data Format:** JSON array of load objects

---

**Status:** ✅ Ready for Local Testing

updated readme:
I remember the "Scout" extension well. It’s the "eyes and ears" of the whole Green Candle operation. While the dashboard is the Command Center, the extension is the **forward-deployed scout** that lives on the load boards (DAT and Truckstop) to feed the beast.

Here is the breakdown of its architecture and functionality for your **README.md**.

---

## **Project: Green Candle Scout (Chrome Extension)**

### **The Mission**

The Scout extension bridges the gap between third-party load boards and your private PostgreSQL database. It eliminates manual data entry by "scraping" load details and injecting a **"Deploy Scout"** button directly into the broker's interface.

---

### **Core Components**

#### **1. The Manifest (`manifest.json`)**

* **Permissions:** `activeTab`, `storage`, and `scripting`.
* **Host Permissions:** Specifically targeted at `*.dat.com` and `*.truckstop.com`.
* **Background Service Worker:** Manages the "Heartbeat" to let the server know the driver is active.

#### **2. The Content Script (`scout.js`)**

This is the "Infiltrator."

* **DOM Observer:** It watches for the specific HTML elements (divs and spans) where DAT/Truckstop display the **Rate, Origin, Destination, and MC Number.**
* **Button Injection:** It injects a "Green Candle" branded button next to the "Book Now" or "Contact" buttons.
* **Data Extraction:** When clicked, it grabs the load metadata and sends a JSON payload to your FastAPI endpoint: `/api/scout/capture-load`.

#### **3. The Popup (`popup.html / popup.js`)**

* **Identity Sync:** Shows the driver they are logged in as `{{display_name}}@gcdloads.com`.
* **Fuel Gauge:** Displays a mini-version of the **$CANDLE** balance so the driver knows if they have enough "fuel" to deploy an agent.
* **Toggle:** A simple On/Off switch for the "Auto-Negotiate" feature.

---

### **The "Heartbeat" Logic**

One of the most important things we discussed was the **Heartbeat**.

* Every 60 seconds, the extension pings your server.
* This updates the `scout_status` table in your DB.
* **Why?** So your dashboard can show a green "Scout Online" pulse, giving the driver confidence that the link is active.

---

### **Drafting the README.md**

```markdown
# Green Candle Scout Extension

The edge-deployed component of the Green Candle Dispatch system.

## Features
- **Load Capture:** One-click extraction of load data from DAT/Truckstop.
- **Identity Injection:** Injects GCD credentials into broker email forms.
- **Real-time Sync:** Connects directly to the GCD Command Center via FastAPI.
- **Fuel Monitoring:** Displays $CANDLE balance in the browser toolbar.

## Installation
1. Open Chrome and navigate to `chrome://extensions/`.
2. Enable **Developer Mode**.
3. Click **Load Unpacked** and select this directory.
4. Log in using your `gcdloads.com` credentials.

## Technical Flow
1. **Identify:** Detects load board DOM structures.
2. **Capture:** Extracts `MC_NUMBER`, `RATE`, `WEIGHT`, and `LANE`.
3. **Transmit:** Sends POST request to `https://134.199.241.56:8990/api/scout/capture`.
4. **Negotiate:** Triggers the "Sarah" or "Marcus" AI agent to start the email thread.

```

---

### **The Part We Still Need to Polish**

If I recall, we were working on making sure the **Session Token** stays valid between the main website and the extension so the driver doesn't have to log in twice.

**Would you like me to write the specific `scout.js` logic for the DAT Load Board so you can drop it into the extension folder?** This would target the specific CSS selectors for the current 2026 version of DAT.