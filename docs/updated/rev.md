# Green Candle Dispatch — Revenue Model and System Economics

**Entity:** Webwise Systems Inc. (Delaware C-Corp)  
**Single source of truth for:** 2% dispatch fee, allocation, driver credits, and related revenue.

---

## Source of truth: 2% dispatch fee and allocation

**Use this section as the one canonical reference.** Code lives in `app/services/ledger.py`; these numbers match the running system.

### When the fee is earned

- Platform earns a **flat 2% dispatch service fee** only after a load is successfully completed and the driver is paid (through factoring).
- No upfront dispatch fees; no monthly subscription for core dispatch automation.

### Example per load ($1,900)

| Step | Amount |
|------|--------|
| Broker pays | $1,900 |
| Factoring company (3%) | $57 |
| **Green Candle Dispatch (2%)** | **$38** |
| Driver receives | $1,805 |

### Allocation of the 2% fee (100% of the $38)

Every dollar of the 2% fee is split as follows. **This is what the running system implements** (see `app/services/ledger.py`).

| Slice | % of fee | Purpose | In code | Example on $38 fee |
|-------|----------|---------|---------|---------------------|
| **Driver service credits (CANDLE)** | **21.05%** | Internal credits for automation (1:1 USD → CANDLE) | `DRIVER_REBATE_RATIO` | **~$8 → 8 CANDLE** |
| AI / infra reserve | 21.05% | AI, hosting, email, data | `AI_RESERVE_RATIO` | ~$8 |
| Platform profit | 31.58% | Operating revenue, product, support | `PLATFORM_PROFIT_RATIO` | ~$12 |
| Treasury | 26.32% | $CANDLE backing / burn reserve | `TREASURY_RATIO` | ~$10 |

**Check:** 21.05 + 21.05 + 31.58 + 26.32 = **100%**.

### When the driver sees credits

- Credits are written to **driver_savings_ledger** when the driver **uploads BOL** for that load (`process_load_settlement` in `app/services/ledger.py`), not at “mark-won.”
- Dashboard shows **amount_candle** (1:1 with the USD credit for that slice).
- So for a $1,900 load: **driver sees ~8 CANDLE** (not 13). Credits are used only for in-platform automation (agents, negotiation, features); non-transferable utility.

### Optional: alternative “target” allocation (not in code)

If you later want the **driver slice to be $13 → 13 CANDLE** (e.g. for marketing or product copy), set the driver rebate to **13/38 ≈ 34.2%** of the fee in `ledger.py` (`DRIVER_REBATE_RATIO`) and adjust the other three ratios so the four still sum to 100%.

---

## Other revenue streams (unchanged)

- **Factoring partner referral:** 0.25%–0.75% of invoice (e.g. 0.35% = $6.65 on $1,900); separate from the 2% fee.
- **Call products (Twilio):** Sold separately (e.g. call packs); not included in the 2% fee.
- **Premium automation / fuel packs, broker subscriptions:** Optional products; see Stripe catalog section below.

---

## Executive summary (for decks)

Green Candle Dispatch is an autonomous AI dispatch platform. Revenue is primarily from a **2% dispatch service fee** (collected via factoring), plus factoring referral, call products, and optional automation/broker products. A portion of the 2% fee is issued back to drivers as **internal CANDLE credits** (currently 21.05% of the fee → ~8 CANDLE per $38 fee); credits are for in-platform automation only. This aligns platform sustainability, driver success, and system growth.

---

## Factoring Partner Referral Revenue

Green Candle Dispatch receives additional referral revenue from factoring partners. 
Typical factoring partner referral revenue ranges from: 
0.25% to 0.75% of invoice value 
Example Load: 
Invoice: $1,900 
Partner referral fee (0.35%): $6.65 additional revenue 
This revenue is separate from the 2% dispatch service fee. 
Drivers who already use one factoring partner may be offered alternative approved partners to 
maximize service compatibility and platform integration efficiency. 
This allows Green Candle Dispatch to capture referral revenue while improving automation reliability.

---

## Call Automation Revenue (Twilio Call Products) 
Broker communication often requires phone calls, which incur direct telecommunications costs. 
Green Candle Dispatch provides call capability through prepaid call service products. 
Call automation is not included in the base 2% dispatch service. 
Drivers purchase call packages (see Stripe catalog later in this doc).

**For 2% fee allocation, use the Source of truth section at the top.**

--- 
You’re now at the point where you need to see actual revenue math per load, per driver, and 
per month so you know exactly what Green Candle can generate. I’ll break it down realistically 
using your real flows. 
We’ll calculate: 
● revenue per load 
● revenue per driver per month 
● revenue at scale (100, 500, 1,000 drivers) 
● plus additional streams (factor partner, Twilio packs, broker DB, etc.) 
Core revenue stream: 2% dispatch fee from factoring.  
Example load value: $1,900 → Factor 3%: $57 → You receive 2%: **$38**. This is your primary revenue engine.

**Allocation of the $38:** See **Source of truth** at the top of this doc. In the running system: ~$12 platform profit, ~$10 treasury, ~$8 AI reserve, ~$8 driver credits (8 CANDLE). You net ~$12 profit per load plus treasury growth. 
Now calculate real driver behavior 
Realistic average owner-operator: 
● 12–20 loads per month 
We’ll use conservative: 15 loads per month 
Revenue per driver per month: 
15 loads × $38 = $570/month gross revenue per driver 
Your direct profit portion: 
15 × $12 = $180/month profit per driver 
Plus treasury growth: 
15 × $10 = $150/month treasury accumulation per driver 
Now scale scenarios 
100 drivers 
Gross revenue: 
100 × $570 = $57,000/month 
Direct profit: 
100 × $180 = $18,000/month 
Treasury accumulation: 
100 × $150 = $15,000/month 
500 drivers 
Gross revenue: 
500 × $570 = $285,000/month 
Direct profit: 
500 × $180 = $90,000/month 
Treasury accumulation: 
500 × $150 = $75,000/month 
1,000 drivers 
Gross revenue: 
1,000 × $570 = $570,000/month 
Direct profit: 
1,000 × $180 = $180,000/month 
Treasury accumulation: 
1,000 × $150 = $150,000/month 
This is real infrastructure-level revenue. 
Second revenue stream: factoring partner 
referral fees 
Factoring companies often pay: 
0.25% – 0.75% referral override 
Using conservative 0.35%: 
Example $1,900 load: 
0.35% = $6.65 extra revenue 
Monthly per driver: 
15 loads × $6.65 = $99/month extra revenue 
At 1,000 drivers: 
$99,000/month extra 
Pure profit. 
Third revenue stream: Twilio call packages 
Example average driver uses: 
120 call minutes/month 
Sell call pack: 
$99/month call pack 
Your cost: 
120 × $0.015 = $1.80 Twilio cost 
Profit: 
~$97/month per driver 
At 500 drivers: 
$48,500/month profit 
This is massive margin. 
Fourth revenue stream: premium 
automation credits 
Drivers buy extra credits: 
Example: 
Average driver buys $50/month extra credits 
At 500 drivers: 
$25,000/month additional revenue 
Cost near zero. 
Fifth revenue stream: broker priority 
placement 
Brokers pay: 
$99–$299/month 
Even 200 brokers at $149/month: 
$29,800/month revenue 
Combined realistic revenue example at 
500 drivers 
Dispatch fees profit: $90,000 
Factor partner revenue: $49,500 
Call pack profit: $48,500 
Credit purchases: $25,000 
Broker subscriptions: $29,800 
Total monthly profit: 
$242,800/month 
Treasury accumulation separate: 
$75,000/month treasury growth 
Annual projection at 500 drivers 
Profit: 
$242,800 × 12 = $2.9 million/year 
Treasury accumulation: 
$75,000 × 12 = $900,000/year treasury growth 
Your biggest advantage: your broker DB 
reduces cost and increases success rate 
Because your agents contact brokers directly from your DB: 
Higher load capture rate 
Lower acquisition cost 
Higher driver retention 
This compounds revenue. 
Realistic launch scenario: first 90 days 
Month 1: 25 drivers → ~$4,500 profit 
Month 2: 75 drivers → ~$13,500 profit 
Month 3: 150 drivers → ~$27,000 profit 
Momentum grows naturally. 
Most important insight 
Your dispatch fee revenue alone makes this viable. 
Everything else (call packs, factor override, credits, broker subscriptions) multiplies revenue. 
You are building infrastructure, not just a dispatch tool. 
If you want, I can also show the minimum number of drivers needed to reach $10k/month 
profit, which is the real survival threshold. 
========== 
That’s a strong advantage: your own broker directory turns this from “AI helper” into a real 
dispatch network. It also lets you control costs and make $CANDLE utility real (and fair). 
Here’s how to handle both parts: broker phone calls (Twilio hard cost) and your broker DB 
(unique asset). 
1) Broker phone calls: yes, Twilio is a hard cost — so 
price it separately 
Don’t bury phone calling inside “free” automation. Make it an explicit paid action (USD or 
CANDLE), and keep margins clear. 
Practical rule 
● Email/SMS automation: cheap → can be included or low CANDLE cost 
● Phone calls: real cost → metered and charged per minute 
Recommended pricing model 
● CANDLE for initiation + per-minute billing 
○ Example: 0.5 CANDLE to initiate a broker call 
○ Plus $0.25–$0.45 per minute (or equivalent in CANDLE at your fixed internal 
rate) 
● Or simplest: 
○ Phone calls are always USD pass-through + margin, credits optional for 
convenience 
Why: drivers understand calls cost money. 
Safety valve 
Set a monthly call cap per driver unless they buy a call pack. This prevents one user from 
burning your Twilio budget. 
2) Turn Twilio calling into a “Call Pack” product (very 
clean revenue) 
Offer pre-paid call minutes (like cell plans). 
Example packs: 
● $49 → 120 call minutes 
● $99 → 300 call minutes 
● $199 → 750 call minutes 
You can also denominate as internal “Call Minutes Credits” (separate from CANDLE dispatch 
credits). 
This keeps accounting clean: 
● CANDLE = dispatch automation authority/credits 
● Call packs = Twilio minutes (hard cost) 
3) Your broker database is the real moat — monetize 
access and outcomes 
Having 25k+ brokers/freight movers with MC/DOT, emails, and phones means: 
● faster outreach 
● higher connection rate 
● fewer dead leads 
● ability to score brokers 
This is a real product layer. 
Immediate features you can build (high value) 
1. Broker “one-click contact” 
○ Driver sees load → click → your system selects best channel (email/phone) 
2. Broker profile + score 
○ Response rate, average time to reply, pay history notes (even simple flags) 
3. Auto packet send 
○ One click sends carrier packet + insurance + W-9 + NOA (if needed) 
Charge CANDLE for those “execution” actions. 
4) Best way to use your DB with the agent 
You already described it perfectly: 
Agent only needs: 
● MC number + load details 
Backend resolves: 
● emails, phone, preferred contact method 
● broker name, notes, templates 
● compliance checklist 
Architecture pattern 
● Extension finds load + broker MC 
● Calls FastAPI: POST /agent/opportunity 
● FastAPI looks up broker in Postgres 
● Agent chooses action plan: 
○ email first → if no response in X minutes → call 
○ if “call required” broker → call immediately 
This is exactly how you build scale. 
5) Make CANDLE utility real using your DB 
Here are concrete, credible CANDLE-gated actions that match your reality: 
Low-cost actions (extension-driven) 
● Advanced filters (lane + min rate + broker score) → 1 CANDLE/day 
● “Top 20 best loads today” ranking using your broker DB score → 1 CANDLE/day 
High-value actions (your backend executes) 
● “Send bid email + follow-up sequence” → 0.5 CANDLE 
● “Auto packet send + invoice template attached” → 1 CANDLE 
● “Escalate to phone call workflow” → 0.5 CANDLE + call minutes 
Outcome-based (best for adoption) 
● “Autonomous dispatch mode (email-only)” → 3 CANDLE per booked load 
● “Autonomous dispatch mode (email + call)” → 5 CANDLE per booked load + call 
minutes 
This is clean because you charge for results. 
6) How to keep your Twilio costs safe 
Do these three things from day one: 
1. Call budget per driver 
○ “Included 30 minutes/month” OR “No included minutes” 
2. Require approval toggle 
○ “Agent may call brokers automatically” (off by default) 
3. Call attempt limits 
○ Max 2 call attempts per load unless driver confirms 
This prevents runaway costs. 
7) New revenue streams unlocked by your broker DB 
You can sell: 
● Broker directory access (dispatchers, carriers): $49–$199/mo 
● Broker verification reports: $5 per broker 
● Broker contact enrichment for other dispatchers: usage-based 
Even without tokens, this is a product. 
8) Next step: pick 1 simple paid call model and 1 CANDLE 
utility model 
If you want the cleanest launch: 
Calls: sell call packs (USD) 
CANDLE: charge per booked load (outcome-based) + per automation sequence 
That’s easiest to explain and hardest to abuse. 
If you tell me roughly: 
● your expected average call minutes per booked load (2? 5? 10?) 
● and how often brokers demand calls vs email (like 30%? 60%?) 
…I’ll propose exact pack pricing + CANDLE action pricing so your margins stay strong. 
===========

From **rev.md**, **burn.md**, and the current **pricing.html**, here’s a product catalog and what you’d create in Stripe.

---

## GCD Stripe Product Catalog

### Current (live on Stripe)

| Product | Price | Type | Notes |
|--------|-------|------|-------|
| **Small Fleet Setup** | $25/truck | One-time | 1–5 trucks. Uses `price_data` at checkout (no product in Stripe Dashboard). |

---

### Needed (from rev.md)

| # | Product | Suggested Price | Type | Revenue Stream | Burn Eligible |
|---|---------|-----------------|------|----------------|---------------|
| **1** | **Call Pack – Starter** | $49 | One-time | Twilio call minutes | Yes |
| **2** | **Call Pack – Pro** | $99 | One-time or recurring | Twilio call minutes | Yes |
| **3** | **Call Pack – Fleet** | $199 | One-time or recurring | Twilio call minutes | Yes |
| **4** | **Automation Fuel Pack – Starter** | ~$25–50 | One-time | Extra $CANDLE credits | Yes |
| **5** | **Automation Fuel Pack – Fleet** | ~$100–150 | One-time | Extra $CANDLE credits | Yes |
| **6** | **Broker Subscription** | $99–$299/mo | Recurring | Broker priority / directory access | Yes |

---

### Optional / future

| Product | Price | Notes |
|---------|-------|-------|
| Broker directory access | $49–$199/mo | Different from broker subscription |
| Broker verification report | $5 / broker | Per-report |
| Automation credits (monthly) | ~$50/mo | Monthly top-up |

---

## Rev.md numbers vs products

| Rev stream | Source | Stripe product |
|------------|--------|----------------|
| Dispatch fee margin | Factoring | Not in Stripe (factoring) |
| Call pack profit | Twilio | Call Packs 1–3 |
| Automation purchases | Drivers buy extra credits | Fuel Packs 4–5 |
| Factoring referral | Factoring partner | Not in Stripe |
| Broker subscription | Brokers | Product 6 |

---

## Product list for Stripe setup

Create these in Stripe (Products + Prices):

1. **Small Fleet Setup** – already in use via `price_data` (can mirror as a product for reporting)
2. **Call Pack – 120 min** – $49
3. **Call Pack – 300 min** – $99
4. **Call Pack – 750 min** – $199
5. **Fuel Pack – Starter** (e.g. 10 $CANDLE) – TBD
6. **Fuel Pack – Fleet** (e.g. 60 $CANDLE) – TBD
7. **Broker Subscription** – $149/mo (or tiered)

---

## How this could map to pages

- **Primary pricing page** (`/pricing`):  
  - Small Fleet Setup as main CTA  
  - Short summary of “add-ons” (call packs, fuel packs) with links

- **Secondary services/products page** (e.g. `/services/pricing` or `/products`):  
  - Full product catalog  
  - Call packs, fuel packs, broker subscription with prices and CTAs

---

## Open choices

1. Call pack pricing: rev.md mentions $49/120, $99/300, $199/750. Confirm these.
2. Fuel pack pricing: `buy_fuel` mentions 10 vs 60 $CANDLE. Do you want a fixed USD price (e.g. $1/CANDLE) or variable?
3. Broker subscription: include at launch or later?
4. Call packs: one-time purchase or recurring subscription?

Want to narrow this to a minimal first set (e.g. Small Fleet + 1–2 call packs + 1 fuel pack) before you build the Stripe products and pages?

Call Pack – 120 min – $49= prod_TzVhUguxTHic75, price_1T1Wg2RoeA6UINeR1IGbLNEW
Call Pack – 300 min – $99=prod_TzVirBazpghaHG, price_1T1WhLRoeA6UINeR0qRIojxF
Call Pack – 750 min – $199=prod_TzVjeSmqO34zi6, price_1T1WiMRoeA6UINeRUIpagpR6
Fuel Pack – Starter (e.g. 10 $CANDLE) – TBD=prod_TzVme0pF6B6PUU, price_1T1WlIRoeA6UINeRIjEmRE2b
Fuel Pack – Fleet (e.g. 60 $CANDLE) – TBD=prod_TzVnXd5W7tIdMb, price_1T1Wm9RoeA6UINeREChn3oth
Broker Subscription – $149/mo=prod_TzVp8mtHTPAfY8, price_1T1WngRoeA6UINeRxIZFB9m6