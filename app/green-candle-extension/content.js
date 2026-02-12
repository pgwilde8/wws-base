// content.js
console.log("🕯️ Green Candle Spy is Active");

// Inject overlay styles
const style = document.createElement('style');
style.textContent = `
    .gc-scout-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
        color: #0f172a;
        font-size: 10px;
        font-weight: bold;
        padding: 4px 8px;
        border-radius: 4px;
        margin-left: 8px;
        cursor: pointer;
        box-shadow: 0 2px 4px rgba(34, 197, 94, 0.3);
    }
    .gc-scout-badge:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 8px rgba(34, 197, 94, 0.5);
    }
    .gc-scout-overlay {
        position: fixed;
        top: 20px;
        right: 20px;
        background: #0f172a;
        border: 2px solid #22c55e;
        border-radius: 12px;
        padding: 16px;
        z-index: 10000;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        min-width: 300px;
        font-family: sans-serif;
        color: white;
    }
    .gc-scout-overlay h4 {
        margin: 0 0 12px 0;
        color: #22c55e;
        font-size: 14px;
    }
    .gc-scout-overlay p {
        margin: 4px 0;
        font-size: 12px;
        color: #94a3b8;
    }
    .gc-scout-overlay .close {
        position: absolute;
        top: 8px;
        right: 8px;
        background: none;
        border: none;
        color: #64748b;
        cursor: pointer;
        font-size: 18px;
    }
`;
document.head.appendChild(style);

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "SCRAPE_NOW") {
        let data = scrapeLoadBoard();
        
        if (data.length > 0) {
            // Send to Background (The Courier)
            chrome.runtime.sendMessage({ action: "UPLOAD_DATA", loads: data }, (response) => {
                if (response && response.success) {
                    showToast(`✅ ${data.length} loads sent to HQ! ${response.data?.hot || 0} high-value loads detected.`);
                    sendResponse({ status: "success", count: data.length });
                } else {
                    showToast(`❌ Error: ${response?.error || 'Failed to send data'}`);
                    sendResponse({ status: "error", error: response?.error });
                }
            });
        } else {
            sendResponse({ status: "empty", count: 0 });
        }
        return true; // Required for async message handling
    }
    return true;
});

function scrapeLoadBoard() {
    let loads = [];
    
    // STRATEGY: Look for generic table rows first (for testing)
    // In production, we will target specific DAT classes like '.dat-row'
    let rows = document.querySelectorAll("tr"); 

    rows.forEach((row, index) => {
        let cells = row.querySelectorAll("td");
        if (cells.length > 3) {
            // Very basic logic: Assuming col 0 is Origin, col 1 is Dest, col 2 is Price
            // We will refine this for DAT specific columns later
            let origin = cells[0]?.innerText.trim();
            let dest = cells[1]?.innerText.trim();
            let price = cells[2]?.innerText.trim();
            
            // Generate a fake Ref ID if none exists (for testing)
            let refId = "REF-" + Math.floor(Math.random() * 100000) + "-" + index;

            if (origin && dest) {
                // Calculate potential reward (2% of price)
                let cleanPrice = parseFloat(price.replace(/[^0-9.]/g, ''));
                let rewardUsd = cleanPrice * 0.02;
                let gasGallons = rewardUsd / 4.0; // $4/gal diesel
                
                // Add badge to row if it's a high-value load
                if (cleanPrice >= 2000 && !row.querySelector('.gc-scout-badge')) {
                    let badge = document.createElement('span');
                    badge.className = 'gc-scout-badge';
                    badge.innerHTML = `🕯️ GC: +$${rewardUsd.toFixed(2)} (${gasGallons.toFixed(1)} gal)`;
                    badge.title = `Green Candle Reward: $${rewardUsd.toFixed(2)} = ${gasGallons.toFixed(1)} gallons of free fuel`;
                    cells[2]?.appendChild(badge);
                }
                
                loads.push({
                    ref_id: refId,
                    origin: origin,
                    destination: dest,
                    price: price,
                    equipment_type: "Van", // Default for now
                    pickup_date: new Date().toISOString()
                });
            }
        }
    });

    console.log(`[Green Candle] Found ${loads.length} potential loads.`);
    return loads;
}

function showToast(message) {
    // Remove existing toast
    const existing = document.getElementById('gc-scout-toast');
    if (existing) {
        existing.remove();
    }
    
    const toast = document.createElement('div');
    toast.id = 'gc-scout-toast';
    toast.className = 'gc-scout-overlay';
    toast.innerHTML = `
        <button class="close" onclick="this.parentElement.remove()">×</button>
        <h4>🕯️ Green Candle Scout</h4>
        <p>${message}</p>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 5000);
}

// Auto-enhance page on load (add badges to high-value loads)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
            scrapeLoadBoard(); // This will add badges
        }, 1000);
    });
} else {
    setTimeout(() => {
        scrapeLoadBoard(); // This will add badges
    }, 1000);
}