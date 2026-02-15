// background.js
// Get API key from storage (check both sync and local)
async function getApiKey() {
    return new Promise((resolve) => {
        // First try sync storage
        chrome.storage.sync.get(['scout_api_key'], (syncResult) => {
            if (syncResult.scout_api_key) {
                resolve(syncResult.scout_api_key);
                return;
            }
            // If not in sync, try local storage
            chrome.storage.local.get(['scout_api_key'], (localResult) => {
                resolve(localResult.scout_api_key || null);
            });
        });
    });
}

const BASE_URL = "http://134.199.241.56:8990";

// Send Scout heartbeat so dashboard shows "Scout Active"
async function sendHeartbeat(apiKey, lanes = ["NJ-FL"], minRpm = 2.45, active = true) {
    try {
        const response = await fetch(`${BASE_URL}/api/scout/heartbeat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": apiKey
            },
            body: JSON.stringify({ lanes, min_rpm: minRpm, active })
        });
        if (response.ok) {
            console.log("📡 Scout heartbeat sent");
        }
    } catch (e) {
        console.warn("Scout heartbeat failed:", e);
    }
}

// Check connection status
async function checkConnection() {
    const apiKey = await getApiKey();
    if (!apiKey) {
        return { connected: false, message: "No API key configured" };
    }
    
    try {
        const API_URL = `${BASE_URL}/api/ingest/loads`;
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": apiKey
            },
            body: JSON.stringify([]) // Empty test payload
        });
        
        if (response.status === 401) {
            return { connected: false, message: "Invalid API key" };
        }
        
        // Connection OK: send heartbeat so dashboard shows "Scout Active"
        await sendHeartbeat(apiKey);
        return { connected: true, message: "Connected" };
    } catch (error) {
        return { connected: false, message: "Connection failed" };
    }
}

// Update extension icon based on connection status
async function updateIcon() {
    const status = await checkConnection();
    const iconPath = status.connected 
        ? { path: { 16: "icons/icon-green-16.png", 48: "icons/icon-green-48.png", 128: "icons/icon-green-128.png" } }
        : { path: { 16: "icons/icon-gray-16.png", 48: "icons/icon-gray-48.png", 128: "icons/icon-gray-128.png" } };
    
    chrome.action.setIcon(iconPath);
    chrome.action.setBadgeText({ text: status.connected ? "✓" : "" });
    chrome.action.setBadgeBackgroundColor({ color: "#22c55e" });
}

// Check connection on startup and periodically
updateIcon();
setInterval(updateIcon, 30000); // Check every 30 seconds

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "UPLOAD_DATA") {
        (async () => {
            try {
                const apiKey = await getApiKey();
                
                if (!apiKey) {
                    sendResponse({ 
                        success: false, 
                        error: "API key not configured. Please set it in extension settings." 
                    });
                    return;
                }
                
                console.log("🚀 Sending data to HQ...", request.loads);

                const API_URL = `${BASE_URL}/api/ingest/loads`;
                console.log("📡 API Key present:", apiKey ? "Yes" : "No");
                console.log("📡 Sending to:", API_URL);

                const response = await fetch(API_URL, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-API-Key": apiKey
                    },
                    body: JSON.stringify(request.loads)
                });
                
                console.log("📡 Response status:", response.status);
                
                if (response.status === 401) {
                    sendResponse({ 
                        success: false, 
                        error: "Invalid API key. Please regenerate your key in the dashboard." 
                    });
                    await updateIcon();
                    return;
                }
                
                const data = await response.json();
                console.log("✅ HQ Response:", data);
                
                await updateIcon();
                await sendHeartbeat(apiKey);  // Dashboard shows Scout Active
                
                sendResponse({ success: true, data: data });
            } catch (error) {
                console.error("❌ HQ Connection Failed:", error);
                sendResponse({ success: false, error: error.message });
            }
        })();
        
        return true; // Required for async message handling
    }
    
    if (request.action === "CHECK_CONNECTION") {
        checkConnection().then(status => sendResponse(status));
        return true;
    }
    
    return true;
});