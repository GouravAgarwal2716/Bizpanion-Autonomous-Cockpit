# 🌾 Bizpanion — Autonomous Business Cockpit

> **Zero-prompt, voice-first AI cockpit for rural & semi-urban micro-entrepreneurs in India.**  
> Built for Build by Sunset Hackathon · Sep 4–5, 2026

[![Featherless.ai](https://img.shields.io/badge/Powered%20by-Featherless.ai-6366f1)](https://featherless.ai)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2014-black)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/Agents-LangGraph-ff6b35)](https://langchain-ai.github.io/langgraph/)

---

## 🎯 The Problem

Rural entrepreneurs — vegetable vendors, kirana shop owners, dairy farmers — are leaving money on the table every day because they lack access to:
- Real-time market price comparisons
- Demand forecasting for inventory
- Government scheme deadlines they qualify for
- Instant alerts when something needs their attention

They can't afford software consultants. They don't have time to stare at dashboards.

## 💡 The Solution

Bizpanion watches their real data (uploaded CSV or live Tally sync) against real market prices (Agmarknet) and **only interrupts them on WhatsApp when something genuinely needs their attention** — not on every small fluctuation.

**No chat box. No prompting. Pure autonomous action.**

---

## 🏗️ Architecture

```
CSV / Tally XML → Data Pipeline (Profile → Clean → Validate)
                          ↓
                   Supabase (Postgres)
                          ↓
              LangGraph Agent Pipeline:
    Trigger → Planner → [Data | RAG | Forecast] →
    Anomaly Detection → Severity → Verifier → Advisor
                          ↓                    ↓
                   Action Feed          IF severity=HIGH:
                   (always)             WhatsApp (Twilio)
                          ↓
                   Featherless TTS → Voice Audio
```

### The 4 Anomaly Checks (all real, computable, grounded)

| Check | Data Source | Method |
|-------|-------------|--------|
| **Underpricing** | User's transactions vs Agmarknet | If user price >15% below regional modal price |
| **Stock Depletion** | Inventory + Demand Forecast | If stock runs out in <7 days at predicted rate |
| **Scheme Deadline** | RAG on govt scheme PDFs | If eligible scheme deadline within 7 days |
| **Sales Anomaly** | Transaction history | Z-score deviation >2σ from 30-day rolling avg |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router) + Tailwind CSS |
| Backend | FastAPI + LangGraph |
| LLM + Embeddings + TTS | **Featherless.ai** (Llama 3.1 70B, Qwen3-Embedding-8B, Kokoro TTS) |
| Database | Supabase (Postgres + Auth) |
| Vector Store | Pinecone |
| Forecasting | PyTorch LSTM → Prophet → Rolling Average (fallback chain) |
| WhatsApp | Twilio WhatsApp Sandbox API |
| Market Data | Agmarknet (data.gov.in) |
| Languages | English, Hindi, Tamil, Telugu, Kannada |
| Deploy | Vercel (frontend) + Railway (backend) |

---

## 🚀 Setup & Running

### Prerequisites
- Node.js 20+
- Python 3.12+
- Accounts: [Featherless.ai](https://featherless.ai), [Supabase](https://supabase.com), [Pinecone](https://pinecone.io), [Twilio](https://twilio.com)

### 1. Database Setup

```sql
-- In Supabase SQL Editor, run:
backend/supabase/migrations/001_init.sql
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt

# Copy and fill in your API keys
cp .env.example .env

# Seed market price data (Agmarknet)
python scripts/seed_market_data.py

# Generate test CSV data
python scripts/generate_test_data.py

# Start the server
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local  # Fill in Supabase keys + backend URL
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 4. PyTorch Model (Optional — improves forecast accuracy)

1. Open `kaggle_notebook/bizpanion_lstm_train.ipynb` on [Kaggle](https://kaggle.com)
2. Add dataset: [Indian Vegetable Price Dataset](https://www.kaggle.com/datasets/datahack-studio/vegetable-and-fruits-price-in-india)
3. Enable GPU accelerator → Run All
4. Download `forecast_model.pt` from the output panel
5. Place it at `backend/models/forecast_model.pt`

Without the weights file, the system automatically falls back to Prophet (still accurate forecasting).

### 5. Tally Prime Integration

1. In Tally Prime: **Help → TDL Management → HTTP Port** → Set to `9000`
2. In the app: **Data Sync → Tally Sync → Check Connection → Sync**

---

## 📁 Test Data

Pre-generated test files are in `backend/test_data/`:

| File | Purpose |
|------|---------|
| `ramesh_vegetable_stall_clean.csv` | Clean 200-row dataset (baseline demo) |
| `priya_kirana_messy_ledger.csv` | 300-row messy CSV with Hindi headers, mixed date formats, missing values — shows the cleaning pipeline |
| `anomaly_demo_underpricing.csv` | 50 days of data with deliberate 33% underpricing in last 5 days → **triggers WhatsApp alert** |
| `festival_season_high_demand.csv` | 3x demand spike → triggers stock depletion alert |
| `tally_export_vouchers.xml` | Synthetic Tally XML for import testing |

---

## 🎙️ Demo Script (3 minutes)

1. **0:00–0:20** — Walk through the 5 pages: Home, Data Sync, Action Feed, Reports, Settings
2. **0:20–1:00** — Upload `priya_kirana_messy_ledger.csv` → watch the cleaning pipeline animate live
3. **1:00–1:45** — Upload `anomaly_demo_underpricing.csv` → Action Card appears with specific numbers: "Your onion price ₹12/kg is 33% below the Lasalgaon market rate of ₹18/kg"
4. **1:45–2:20** — **Live moment:** WhatsApp message arrives on the pre-registered phone in the user's language
5. **2:20–2:50** — Tap "Play Briefing" → hear the voice summary in selected language
6. **2:50–3:00** — Close: "From messy data to a grounded alert to a real WhatsApp — zero prompts typed."

---

## 🌐 Deployment

### Backend (Railway)
```bash
# railway.toml already configured
railway up
```

### Frontend (Vercel)
```bash
vercel --prod
```

Set environment variables in both platforms matching `.env.example` and `.env.local`.

---

## 👥 Team

Built during Build by Sunset Hackathon · September 4–5, 2026

---

## 📄 License

MIT
