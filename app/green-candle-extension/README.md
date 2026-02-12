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
