Building a project with your background—Navy grit plus modern dev skills—demands a README that is as functional as a flight manual but as visionary as a tech whitepaper.

Since we are going with **Jinja2 + FastAPI** for V1, the README should reflect a "High-Performance Simplicity" philosophy.

---

# README.md: Green Candle Dispatch 🕯️🚛

## 📖 Project Overview

**Green Candle Dispatch** is a DePIN (Decentralized Physical Infrastructure Network) SaaS designed to eliminate the two biggest killers of small-fleet profitability: **administrative bloat** and **"deadhead" miles**.

By leveraging an autonomous AI Dispatcher, we allow owner-operators (1-5 trucks) to outsource their rate negotiation and paperwork to a digital agent. Every successful mile driven strengthens the network through a programmatic token buyback engine.

### The Problem

* **The Paperwork Tax:** Small fleets spend 15+ hours a week on BOL uploads and broker emails.
* **The Middleman Gap:** Factoring companies take 3-5%, but the value never returns to the driver.
* **Deadhead Miles:** Trucks driving empty because they can’t find/negotiate a return load fast enough.

### The Solution: "Proof of Freight"

We move the industry from speculative hype to real-world utility. Our "Green Candle" flywheel ensures that as trucks move, the network grows.

---

## ✨ Key Features

* **🤖 AI Dispatcher (FastAPI + LLM):** 24/7 monitoring of load boards. Automates initial broker outreach and rate negotiation via email.
* **📄 One-Tap BOL Processing:** Truckers upload a photo; the AI extracts data and prepares it for the factoring company.
* **🕯️ $CANDLE Buyback Bridge:** A 2% "Network Fee" is captured from every paid load and instantly converted into $CANDLE tokens via our Transak-Stripe bridge.
* **📱 PWA First:** A high-performance, mobile-first web app (Jinja2/Tailwind) that works in low-signal areas.

---

## ⚙️ The Technical Stack (V1)

* **Backend:** FastAPI (Python 3.12+)
* **Frontend:** Jinja2 Templates + HTMX (for SPA-like interactivity without the React bloat)
* **Styling:** Tailwind CSS (Mobile-first)
* **Database:** PostgreSQL (via SQLAlchemy/Supabase)
* **Blockchain:** Base (L2) via Clanker Launchpad
* **Payments/Fiat:** Transak API + Stripe

---

## 📈 Economic Model (The Whitepaper Core)

We don't rely on "new buyers" to sustain token value. We rely on **ton-miles**.

1. **Revenue Generation:** A truck completes a $5,000 load.
2. **Fee Capture:** $100 (2%) is collected as the "Green Candle Network Fee."
3. **Programmatic Buyback:** The $100 is sent to the Transak Bridge, which executes a market buy of **$CANDLE** on Uniswap (Base).
4. **Value Accrual:** This creates constant, non-speculative buy pressure.
* *Milestone:* 50 trucks @ $7.5k/week = **$30,000/month in automated buy pressure.**



---

## 🚀 Roadmap

* [x] **Phase 0:** Domain Secured (greencandledispatch.com)
* [ ] **Phase 1:** MVP Launch (Jinja2/FastAPI) - 5 Alpha Trucks
* [ ] **Phase 2:** $CANDLE Token Launch via Clanker (Base)
* [ ] **Phase 3:** Automated Transak-to-Base Bridge Integration
* [ ] **Phase 4:** Scale to 50-truck "Proof of Freight" Network

---

## 🛠️ Local Development

```bash
# Clone the repo
git clone https://github.com/your-repo/green-candle-dispatch.git

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn main:app --reload

```

---

## 🤝 Selling the Vision

**To Truckers:** "Stop chasing brokers. Let the AI handle the talk so you can handle the turn. Earn $CANDLE rewards for every mile you deliver."

**To Investors:** "Real-yield DePIN. No inflation. Just real-world logistics revenue fueling a constant buyback engine. $CANDLE is the currency of the open road."

---
