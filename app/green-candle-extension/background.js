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