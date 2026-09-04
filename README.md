# 🌾 Bizpanion — Autonomous Business Cockpit

> **Next-Generation Autonomous Financial Cockpit, Multilingual Voice RAG, PyTorch Cashflow Forecasting & Real-Time Tally Prime ERP Automation for Micro-Enterprises.**

[![Vercel Deployment](https://img.shields.io/badge/Frontend-Vercel%20Production-000000?style=for-the-badge&logo=vercel)](https://bizpanion-autonomous-cockpit.vercel.app)
[![Render Backend](https://img.shields.io/badge/Backend-Render%20Production-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://bizpanion-autonomous-cockpit-backend.onrender.com)
[![Featherless.ai](https://img.shields.io/badge/LLM-Featherless.ai%20(Qwen2.5--7B)--6366f1?style=for-the-badge)](https://featherless.ai)
[![PyTorch](https://img.shields.io/badge/ML-PyTorch%20LSTM--ee4c2c?style=for-the-badge&logo=pytorch)](https://pytorch.org)
[![Pinecone](https://img.shields.io/badge/VectorDB-Pinecone%20RAG--009688?style=for-the-badge)](https://pinecone.io)

---

## 🌐 Production Deployments

- 📱 **Live Production Web Application**: [https://bizpanion-autonomous-cockpit.vercel.app](https://bizpanion-autonomous-cockpit.vercel.app)
- ⚡ **Live Production FastAPI Backend**: [https://bizpanion-autonomous-cockpit-backend.onrender.com](https://bizpanion-autonomous-cockpit-backend.onrender.com)
- 🐙 **GitHub Repository**: [https://github.com/GouravAgarwal2716/Bizpanion-Autonomous-Cockpit](https://github.com/GouravAgarwal2716/Bizpanion-Autonomous-Cockpit)

---

## 🚀 Key Innovations & Platform Capabilities

Bizpanion is an **Autonomous Business Cockpit** designed for India's 63 Million Micro-Enterprises (Kirana Stores, Dairy Farmers, Garment Retailers, Hardware Merchants, and APMC Produce Vendors). It bridges the gap between raw sales ledgers and high-tier strategic financial advisory.

1. **Dynamic 3-Step Decision Sandbox**:
   - Merchants select real-world choices across 3 strategic dimensions (Strategy, Operations, Capital Allocation).
   - **Featherless AI (`Qwen/Qwen2.5-7B-Instruct`)** computes monthly profit gains, revenue growth, working capital required, payback days, and risk rationales in real-time.

2. **PyTorch LSTM Neural Network (`SalesLSTM`)**:
   - 2-Layer LSTM network trained on sequential daily transaction data.
   - Forecasts 30-day cash flow runway and 7-day SKU stockout velocity (`backend/models/cashflow_lstm.py`).

3. **Pinecone Vector RAG Benchmark Engine**:
   - Vector indexing (`all-MiniLM-L6-v2`) of Agmarknet mandi wholesale benchmarks and government subsidy eligibility rules (PM MITRA, PM SVANidhi, PMEGP).

4. **Multilingual Audio Companion**:
   - Generates dynamic voice briefings in **5 Indian languages** (English, Hindi, Tamil, Telugu, Kannada) matching the user's exact business name and sector.

5. **Direct Tally Prime ERP Sync & WhatsApp Dispatches**:
   - Connects to Tally Prime desktop software via HTTP XML (Port 9000).
   - Generates Executive PDF Summaries and dispatches them directly via **Twilio WhatsApp API** (`+919518948695`).

---

## 📊 System Architecture

```
Tally XML (Port 9000) / CSV ──► Data Ingestion Pipeline (Clean & Validate)
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

## 🛠️ Technology Stack & Architecture

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **LLM Inference** | **Featherless AI** (`Qwen/Qwen2.5-7B-Instruct`) | Multi-turn RAG reasoning, decision sandbox evaluation, action alert synthesis, and voice text generation. |
| **Deep Learning** | **PyTorch 2.4** (`SalesLSTM` 2-layer, 64 hidden units) | Deep learning model predicting 30-day cash flow trajectory & SKU depletion velocity. |
| **Vector Search** | **Pinecone Vector Database** + `all-MiniLM-L6-v2` | Vector indexing and semantic similarity search for market benchmarks & government schemes. |
| **ERP Gateway** | **Tally Prime HTTP XML Sync** (Port 9000) | Native XML payload parser for live DayBook ledger extraction without manual entry. |
| **Messaging** | **Twilio REST API** (WhatsApp Sandbox) | Real-time automated executive PDF report and alert dispatch. |
| **Frontend** | **Next.js 16** (App Router, Turbopack, Tailwind CSS) | Responsive Bento Grid UI in dark mode with 5-language switcher. |
| **Backend** | **FastAPI** (Python 3.12, Pydantic, Uvicorn) | Asynchronous microservices and RESTful API endpoints. |

---

## 📚 Key Resources & Project Documentation

- 📄 **[DEMO & PRESENTATION GUIDE](./JUDGE_DEMO_GUIDE.md)** — Step-by-step presentation flow, architecture details, and technical Q&A defense.
- 📽️ **[SLIDE DECK PRESENTATION](./SLIDE_DECK_PRESENTATION.md)** — 10-Slide pitch deck structure and visual framework.
- 📓 **[Kaggle PyTorch Model Notebook](./frontend/public/bizpanion_demand_lstm_kaggle.ipynb)** — PyTorch LSTM model training, validation, and serialization pipeline.

---

## ⚙️ Local Development Setup

### 1. Backend Setup (FastAPI)
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

### 2. Frontend Setup (Next.js 16)
```bash
cd frontend

# Install dependencies
npm install

# Start Next.js development server (Runs on http://localhost:3000)
npm run dev
```

### 3. Open Application
Navigate to **`http://localhost:3000`** in your browser to access the local Bizpanion Cockpit.

---

## 🔒 Security & Standards Compliance
- Zero hardcoded API keys; all configuration managed via environment variables.
- Asynchronous non-blocking HTTP requests with full error fallback boundaries.
- Native CORS enforcement and typed Pydantic request/response schemas.
