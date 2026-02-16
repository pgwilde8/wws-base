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