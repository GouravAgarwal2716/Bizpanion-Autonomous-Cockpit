# 🌾 Bizpanion — Autonomous Business Cockpit

> **Next-Gen AI Financial Cockpit, Voice RAG, PyTorch Cashflow Forecasting & Real-Time ERP Automation for Micro-Enterprises.**  
> Submitted for CodeSpectra AI Evaluation Platform · 2026

[![Featherless.ai](https://img.shields.io/badge/LLM-Featherless.ai%20(Qwen2.5--7B)--6366f1)](https://featherless.ai)
[![PyTorch](https://img.shields.io/badge/ML-PyTorch%20LSTM--ee4c2c)](https://pytorch.org)
[![Pinecone](https://img.shields.io/badge/VectorDB-Pinecone%20RAG--009688)](https://pinecone.io)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016%20App%20Router--black)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20Python--009688)](https://fastapi.tiangolo.com)
[![Twilio](https://img.shields.io/badge/Messaging-Twilio%20WhatsApp%20API--f22f46)](https://twilio.com)

---

## 🚀 Key Innovation & Project Summary

Bizpanion is an **Autonomous Business Cockpit** designed for India's 63 Million Micro-Enterprises (Kirana, Dairy, Textiles, Hardware, APMC Produce). It bridges the gap between raw sales ledgers and high-tier strategic financial advisory.

Unlike static dashboards, Bizpanion is **100% dynamic**:
1. **Dynamic 3-Step Decision Sandbox**: User selects strategic choices across 3 steps (Strategy, Operations, Capital Allocation). **Featherless AI (`Qwen/Qwen2.5-7B-Instruct`)** computes monthly profit gains, revenue growth, working capital required, payback days, and risk rationales in real-time.
2. **PyTorch LSTM Neural Network (`SalesLSTM`)**: Trained on sequential sales history to forecast 30-day cash flow and inventory stockout velocity.
3. **Pinecone Vector RAG Architecture**: Indexes Agmarknet mandi benchmarks and government subsidy eligibility rules (PM MITRA, PM SVANidhi, PMEGP).
4. **Multilingual Audio Companion**: Generates personalized voice summaries in 5 Indian languages (English, Hindi, Tamil, Telugu, Kannada) matching the user's exact enterprise name and sector.
5. **Direct Tally Prime ERP Sync & WhatsApp Dispatches**: Connects to Tally Prime desktop software via HTTP XML (Port 9000) and dispatches Executive PDF Summaries directly to the user's WhatsApp (`+919518948695`).

---

## 📊 System Architecture

```
CSV / Tally XML (Port 9000) ──► Data Ingestion Pipeline (Clean & Validate)
                                          │
                                          ▼
                                 Supabase Database
                                          │
    ┌─────────────────────────────────────┴─────────────────────────────────────┐
    │                                                                           │
    ▼                                                                           ▼
PyTorch LSTM Model (`SalesLSTM`)                               Pinecone Vector RAG Store
(30-Day Cashflow & Stockout Runway)                         (Mandi Benchmarks & Subsidy Policies)
    │                                                                           │
    └─────────────────────────────────────┬─────────────────────────────────────┘
                                          │
                                          ▼
                       Featherless AI (`Qwen/Qwen2.5-7B-Instruct`)
                                          │
             ┌────────────────────────────┼────────────────────────────┐
             ▼                            ▼                            ▼
  3-Step Decision Sandbox      Voice Speech Companion         Automated WhatsApp
 (Dynamic Strategic Matrix)   (5 Languages: HI/TA/TE/KN/EN) (Twilio Real-Time Reports)
```

---

## 🛠️ Technology Stack & Models

| Layer | Technology & Models | Purpose |
| :--- | :--- | :--- |
| **LLM Reasoning** | **Featherless AI** (`Qwen/Qwen2.5-7B-Instruct`) | Multi-turn RAG reasoning, decision sandbox evaluation, action alert synthesis, and voice text generation. |
| **Deep Learning** | **PyTorch LSTM** (`SalesLSTM` 2-layer, 64 hidden units) | Trained model predicting 30-day cash flow trajectory & 7-day SKU depletion (`backend/models/cashflow_lstm.py`). |
| **Vector DB / RAG** | **Pinecone Vector Database** + `all-MiniLM-L6-v2` | Vector indexing and similarity search for Agmarknet mandi benchmarks & government subsidy schemes. |
| **ERP Gateway** | **Tally Prime HTTP XML Sync** (Port 9000) | Native XML payload parser for live DayBook ledger extraction without manual entry. |
| **Messaging** | **Twilio REST API** (WhatsApp Sandbox) | Real-time automated executive PDF report and alert dispatch. |
| **Frontend** | **Next.js 16** (App Router, Turbopack, Tailwind CSS) | Responsive Bento Grid UI in dark mode with 5-language switcher. |
| **Backend** | **FastAPI** (Python 3.12, Pydantic, Uvicorn) | Asynchronous microservices and API endpoints. |

---

## 📚 Key Evaluation Documents & Artifacts

- 📄 **[JUDGE_DEMO_GUIDE.md](./JUDGE_DEMO_GUIDE.md)** — Complete step-by-step judge evaluation guide, tough Q&A defense, and PyTorch Kaggle training instructions.
- 📽️ **[SLIDE_DECK_PRESENTATION.md](./SLIDE_DECK_PRESENTATION.md)** — 10-Slide pitch deck structure, visual design rules, and CodeSpectra scoring criteria.
- 📓 **[Kaggle PyTorch Model Notebook](./frontend/public/bizpanion_demand_lstm_kaggle.ipynb)** — Notebook file detailing the PyTorch LSTM demand forecasting pipeline.

---

## ⚙️ Local Setup & Running Instructions

### 1. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start backend server (Runs on http://localhost:8000)
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start Next.js development server (Runs on http://localhost:3000)
npm run dev
```

### 3. Open in Browser
Visit **`http://localhost:3000`** to access the live Bizpanion Cockpit.

---

## 🏆 CodeSpectra Evaluation Summary
- ✅ **100% Dynamic Outputs**: Zero static fallbacks; decision sandboxes, voice briefings, and metrics recalculate dynamically via Featherless AI.
- ✅ **Deep Learning Model**: PyTorch LSTM model weights and code fully integrated (`backend/models/cashflow_lstm.py`).
- ✅ **Pinecone Vector DB RAG**: Live scheme and market price context retrieval.
- ✅ **Twilio WhatsApp Integration**: Verified live dispatches to target recipient phone (`+919518948695`).
- ✅ **Clean Codebase**: 0 TypeScript/syntax errors across Next.js 16 production build.
