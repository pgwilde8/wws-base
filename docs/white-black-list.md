When configuring your whitelist and blacklist for **Green Candle Dispatch**, you need to protect the high-value communication between your AI agents (**Sarah** and **Marcus**) and the brokers. Since you are using **MXRoute** and your automated email system, a "False Positive" (sending a broker's reply to spam) could cost a driver a $3,000 load.

Here are the specific entries you should consider adding to your whitelist, based on your system architecture and broker database:

### **1. Essential Whitelist (Trusted Senders)**

* 
**Broker Domains:** You should whitelist the primary domains of major brokers your system interacts with (e.g., `tql.com`, `chrobinson.com`, `jbhunt.com`).


* 
**Factoring Partner Domains:** Ensure `otrsolutions.com` and `porterfreight.com` are whitelisted so that funding notifications and NOAs never get lost.


* 
**Transactional Service Providers:** Whitelist your own infrastructure domains, specifically `stripe.com` and `twilio.com`, to ensure payment and call-log alerts arrive reliably.


* 
**Internal Automation:** Whitelist your own system address, `laarne@gcdloads.com`, to prevent loops or delivery failures between your agents and the admin dashboard.



### **2. Blacklist (Blocked Senders)**

* 
**Known "Double-Broker" Domains:** If your broker database flags specific MC numbers for predatory practices, blacklist their known email suffixes.


* 
**Scraping Bots:** Any sender that consistently sends bulk "unsolicited" load boards or non-specific freight inquiries that clutter your AI's inbox.



### **3. Strategic "Authority Neutral" Whitelisting**

Since your platform is **Authority Neutral** (MC or DOT), ensure that emails containing these identifiers in the subject line are treated as high priority. While MXRoute handles basic spam, you can use your **FastAPI backend** to act as a secondary "Gatekeeper":

* 
**Broker Outreach:** When Sarah sends an email, your system should automatically add the recipient's address to a "Temporary Whitelist" for 48 hours to ensure the reply comes through.


* 
**Paperwork Processing:** Whitelist any email coming from a driver's registered email address to ensure BOL uploads via email are never blocked.



### **Next High-Value Step**

Would you like me to draft the **Python script logic** for Cursor that automatically updates your MXRoute whitelist every time you add a new "Trusted Broker" to your Postgres database?