// C:\Users\xyzag\OneDrive\Desktop\green-candle-scout\background.js

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "UPLOAD_DATA") {
        // 1. Grab the key that popup.js saved
        chrome.storage.local.get(['scout_api_key'], function(result) {
            const apiKey = result.scout_api_key;

            // 2. Fire the request to your VM
            fetch("http://134.199.241.56:8990/api/ingest/loads", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-Key": apiKey // THIS IS THE CRITICAL LINE
                },
                body: JSON.stringify(request.loads)
            })
            .then(response => {
                console.log("Ingest Status:", response.status);
                sendResponse({ status: "success", code: response.status });
            })
            .catch(err => {
                console.error("Upload Error:", err);
                sendResponse({ status: "error" });
            });
        });
        return true; // Keeps the communication line open for the async fetch
    }
});
================
// content.js - The Field Agent (Master Version)
alert("GC Scout is Awake!");
console.log("🕯️ Green Candle Scout Loaded");

let scanInterval = null;

// --- 1. LISTENERS ---
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "TOGGLE_SCAN") {
        if (request.state === true) startScanning();
        else stopScanning();
        sendResponse({ status: "Auto-scan toggled" });
    }
    
    if (request.action === "SCRAPE_NOW") {
        console.log("🚀 Manual Scrape Triggered");
        const data = runScraper();
        // This response goes back to popup.js to show the green "Success"
        sendResponse({ count: data.length, status: "success" });
    }
    return true; 
});

// --- 2. SCANNING CORE ---
function startScanning() {
    if (scanInterval) return;
    console.log("🟢 Auto-Scan STARTED");
    runScraper(); 
    scanInterval = setInterval(runScraper, 10000); 
}

function stopScanning() {
    console.log("🔴 Auto-Scan STOPPED");
    clearInterval(scanInterval);
    scanInterval = null;
}

function runScraper() {
    let data = [];
    const url = window.location.href;

    if (url.includes("trucksmarter.com")) {
        data = scrapeTruckSmarter();
    } else if (url.includes("dat.com")) {
        data = scrapeDAT();
    } else {
        data = scrapeGeneric();
    }
    
    if (data.length > 0) {
        console.log(`⚡ Beaming ${data.length} loads to HQ...`);
        chrome.runtime.sendMessage({ action: "UPLOAD_DATA", loads: data });
    }
    return data;
}

// --- 3. THE PRECISION SCRAPERS ---
// C:\Users\xyzag\OneDrive\Desktop\green-candle-scout\content.js
// --- 2. SCANNING CORE ---
function runScraper() {
    let data = [];
    const url = window.location.href;

    // This name MUST match the function name below
    if (url.includes("trucksmarter.com")) {
        data = scrapeTruckSmarter(); 
    } else if (url.includes("dat.com")) {
        data = scrapeDAT();
    }
    
    if (data.length > 0) {
        console.log(`⚡ Beaming ${data.length} loads to HQ...`);
        chrome.runtime.sendMessage({ action: "UPLOAD_DATA", loads: data });
    }
    return data;
}

// --- 3. THE PRECISION SCRAPER ---
function scrapeTruckSmarter() {
    let loads = [];
    const scripts = document.querySelectorAll('script');
    
    // Words that indicate a Broker/Company, NOT a City
    const junkWords = ['LLC', 'INC', 'LOGISTICS', 'TRANSPORTATION', 'FREIGHT', 'BROKERS', 'SERVICES', 'LL', 'IN'];

    scripts.forEach((script) => {
        const content = script.innerText;
        if (content.includes('self.__next_f.push') && content.includes('$')) {
            
            // 1. Find all "City, ST" patterns
            const cityRegex = /([A-Za-z\s.\-]+),\s([A-Z]{2})/g;
            const priceRegex = /\$\d{1,3}(,\d{3})*/g;
            
            let allMatches = content.match(cityRegex) || [];
            let prices = content.match(priceRegex) || [];

            // 2. Filter out the "Junk" (Brokers)
            const cleanCities = allMatches.filter(match => {
                const upper = match.toUpperCase();
                return !junkWords.some(junk => upper.includes(junk));
            });

            // 3. Pair them up
            for (let i = 0; i < prices.length; i++) {
                const origin = cleanCities[i * 2];
                const destination = cleanCities[i * 2 + 1];
                const priceValue = prices[i];

                // Only send if we have a real Origin, Destination, and a "Real" price
                if (origin && destination && priceValue.length > 2) {
                    const refId = "TS-FINAL-" + btoa(origin + destination + i).substring(0, 12);
                    
                    if (!loads.find(l => l.ref_id === refId)) {
                        loads.push({
                            ref_id: refId,
                            origin: origin,
                            destination: destination,
                            price: priceValue,
                            equipment_type: "TS-Verified",
                            raw_data: "Filtered Next.js Stream"
                        });
                    }
                }
            }
        }
    });

    console.log(`[GC Scout] Filtered out brokers. Identified ${loads.length} clean loads.`);
    return loads;
}







function scrapeDAT() {
    let loads = [];
    let rows = document.querySelectorAll('[data-testid="search-results-row"], .MuiDataGrid-row');
    rows.forEach((row, index) => {
        let text = row.innerText; 
        let cells = text.split('\n');
        if (cells.length > 5) {
            loads.push({
                ref_id: "DAT-" + btoa(text.substring(0,20)).substring(0, 10),
                origin: cells[0], 
                destination: cells[2], 
                price: cells.find(c => c.includes('$')) || "Negotiable",
                equipment_type: "DAT Load",
                raw_data: text
            });
        }
    });
    return loads;
}

function scrapeGeneric() {
    let loads = [];
    let rows = document.querySelectorAll("tr"); 
    rows.forEach((row) => {
        let cells = row.querySelectorAll("td");
        if (cells.length >= 3) {
            loads.push({
                ref_id: "TEST-" + Math.floor(Math.random() * 100000),
                origin: cells[0]?.innerText.trim(),
                destination: cells[1]?.innerText.trim(),
                price: cells[2]?.innerText.trim(),
                equipment_type: "Test Load",
                pickup_date: new Date().toISOString()
            });
        }
    });
    return loads;
}
=================
{
  "manifest_version": 3,
  "name": "Green Candle Scout",
  "version": "1.0",
  "permissions": [
    "activeTab",
    "scripting",
    "storage"
  ],
  "host_permissions": [
    "http://134.199.241.56:8990/*",
    "https://*.dat.com/*",
    "https://*.truckstop.com/*",
    "https://app.trucksmarter.com/*"
  ],
  "action": {
    "default_popup": "popup.html"
  },
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": [
        "http://134.199.241.56:8990/*",
        "https://*.dat.com/*",
        "https://*.truckstop.com/*",
        "https://app.trucksmarter.com/*"
      ],
      "js": ["content.js"]
    }
  ]
}
====
<!DOCTYPE html>
<html>
<head>
    <style>
        body { width: 300px; padding: 15px; font-family: 'Segoe UI', sans-serif; background: #0f172a; color: white; }
        .header { color: #10b981; font-weight: 800; font-style: italic; margin-bottom: 10px; }
        input { width: 90%; padding: 10px; margin: 10px 0; border-radius: 6px; border: 1px solid #334155; background: #1e293b; color: #fbbf24; font-family: monospace; font-size: 11px; }
        button { width: 100%; padding: 12px; background: #10b981; border: none; color: white; font-weight: bold; cursor: pointer; border-radius: 6px; margin-top: 5px; }
        button:hover { background: #059669; }
        .status { font-size: 12px; color: #94a3b8; margin-bottom: 5px; }
    </style>
</head>
<body>
    <div class="header">GREEN CANDLE SCOUT</div>
    <div class="status" id="status">Status: Not Connected</div>
    <input type="text" id="apiKey" placeholder="Paste Scout API Key here">
    <button id="saveBtn">SAVE API KEY</button>
    <hr style="border: 0.5px solid #334155; margin: 15px 0;">
    <button id="scrapeBtn" style="background: #3b82f6;">SCRAPE TRUCKSMARTER</button>
    <script src="popup.js"></script>
</body>
</html>

=================
document.addEventListener('DOMContentLoaded', function() {
    const apiKeyInput = document.getElementById('apiKey');
    const saveBtn = document.getElementById('saveBtn');
    const scrapeBtn = document.getElementById('scrapeBtn');
    const statusDiv = document.getElementById('status');

    // Load existing key
    chrome.storage.local.get(['scout_api_key'], function(result) {
        if (result.scout_api_key) {
            apiKeyInput.value = result.scout_api_key;
            statusDiv.innerText = "Status: Key Saved ✓";
            statusDiv.style.color = "#10b981";
        }
    });

    // Save key logic
    saveBtn.addEventListener('click', function() {
        const key = apiKeyInput.value.trim();
        if (key) {
            chrome.storage.local.set({ 'scout_api_key': key }, function() {
                statusDiv.innerText = "Status: Key Saved ✓";
                alert("API Key Saved!");
            });
        }
    });

    // THE FIX: The Scrape Button logic
    scrapeBtn.addEventListener('click', async () => {
        statusDiv.innerText = "Scouting loads...";
        
        // 1. Get the current active tab (TruckSmarter)
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        // 2. Tell content.js to run the scrape function
        chrome.tabs.sendMessage(tab.id, { action: "SCRAPE_NOW" }, (response) => {
            if (chrome.runtime.lastError) {
                statusDiv.innerText = "Error: Refresh the page";
                statusDiv.style.color = "#ef4444";
            } else {
                statusDiv.innerText = "Success: " + response.count + " loads sent!";
                statusDiv.style.color = "#10b981";
            }
        });
    });
});