// popup.js
document.addEventListener('DOMContentLoaded', async () => {
    const apiKeyInput = document.getElementById('apiKeyInput');
    const saveBtn = document.getElementById('saveBtn');
    const scrapeBtn = document.getElementById('scrapeBtn');
    const statusDiv = document.getElementById('status');
    const connectionStatus = document.getElementById('connectionStatus');
    
    // Load saved API key (check both sync and local)
    chrome.storage.sync.get(['scout_api_key'], (syncResult) => {
        if (syncResult.scout_api_key) {
            apiKeyInput.value = syncResult.scout_api_key;
            checkConnection();
        } else {
            chrome.storage.local.get(['scout_api_key'], (localResult) => {
                if (localResult.scout_api_key) {
                    apiKeyInput.value = localResult.scout_api_key;
                    checkConnection();
                }
            });
        }
    });
    
    // Save API key (save to both sync and local for redundancy)
    saveBtn.addEventListener('click', async () => {
        const apiKey = apiKeyInput.value.trim();
        if (!apiKey) {
            statusDiv.textContent = 'Please enter an API key';
            statusDiv.className = 'status-error';
            return;
        }
        
        // Save to both storage locations
        chrome.storage.sync.set({ scout_api_key: apiKey }, () => {
            chrome.storage.local.set({ scout_api_key: apiKey }, () => {
                statusDiv.textContent = 'API key saved!';
                statusDiv.className = 'status-success';
                checkConnection();
            });
        });
    });
    
    // Check connection status
    async function checkConnection() {
        const apiKey = apiKeyInput.value.trim();
        if (!apiKey) {
            connectionStatus.innerHTML = '<span class="status-indicator disconnected"></span>Not configured';
            scrapeBtn.disabled = true;
            return;
        }
        
        connectionStatus.innerHTML = '<span class="status-indicator disconnected"></span>Checking...';
        
        chrome.runtime.sendMessage({ action: 'CHECK_CONNECTION' }, (response) => {
            if (chrome.runtime.lastError) {
                connectionStatus.innerHTML = '<span class="status-indicator disconnected"></span>Error';
                scrapeBtn.disabled = true;
                return;
            }
            
            if (response && response.connected) {
                connectionStatus.innerHTML = '<span class="status-indicator connected"></span>Connected';
                scrapeBtn.disabled = false;
            } else {
                connectionStatus.innerHTML = `<span class="status-indicator disconnected"></span>${response?.message || 'Disconnected'}`;
                scrapeBtn.disabled = true;
            }
        });
    }
    
    // Scrape button
    scrapeBtn.addEventListener('click', async () => {
        statusDiv.textContent = 'Scraping page...';
        statusDiv.className = '';
        scrapeBtn.disabled = true;
        
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            chrome.tabs.sendMessage(tabs[0].id, { action: "SCRAPE_NOW" }, (response) => {
                if (chrome.runtime.lastError) {
                    statusDiv.textContent = 'Error: Refresh the page and try again';
                    statusDiv.className = 'status-error';
                    scrapeBtn.disabled = false;
                } else if (response && response.status === 'success') {
                    statusDiv.textContent = `✅ Sent ${response.count} loads to HQ!`;
                    statusDiv.className = 'status-success';
                    scrapeBtn.disabled = false;
                } else {
                    statusDiv.textContent = response?.error || 'No loads found on this page';
                    statusDiv.className = response?.error ? 'status-error' : '';
                    scrapeBtn.disabled = false;
                }
            });
        });
    });
    
    // Check connection when API key changes
    apiKeyInput.addEventListener('input', () => {
        const apiKey = apiKeyInput.value.trim();
        if (apiKey) {
            checkConnection();
        } else {
            connectionStatus.innerHTML = '<span class="status-indicator disconnected"></span>Not configured';
            scrapeBtn.disabled = true;
        }
    });
    
    // Initial connection check
    checkConnection();
});
