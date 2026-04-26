# QuantFinance AI Agent

> A production-grade multi-agent quantitative investment research platform powered by LangGraph, simulating a full Wall Street Investment Committee (IC) workflow.

## Overview

QuantFinance AI Agent orchestrates **10+ specialized AI agents** to transform a natural language investment query into a rigorous, data-driven IC report. The architecture mirrors real-world sell-side research: intent parsing → parallel data collection → professional valuation → adversarial debate → risk audit → CIO synthesis.

## Architecture & Workflow

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 1: Intent Parsing                                │
│  ├── intent_analyzer  →  ticker, horizon, concerns      │
└─────────────────────────────────────────────────────────┘
    │
    ├──────────────────────┬──────────────────────┐
    ▼                      ▼                      ▼
┌──────────┐         ┌──────────┐          ┌──────────┐
│  macro   │         │fundamental│          │sentiment │
│ analyst  │         │ analyst   │          │ analyst  │
│(Tavily + │         │(yFinance  │          │(Tavily)  │
│ rates)   │         │ → FMP)    │          │          │
└────┬─────┘         └────┬──────┘          └────┬─────┘
     └──────────┬─────────┘──────────────────────┘
                ▼
    ┌───────────────────┐
    │  valuation_expert │  ← Dynamic method routing (DCF/PS/EV-EBITDA)
    │  with hard data   │      + circuit breaker on data quality
    │  (CAPM WACC,      │
    │   analyst growth) │
    └────────┬──────────┘
             │
    ┌────────┴────────┐
    ▼                  ▼
┌─────────┐    ┌──────────────┐
│context_ │    │ error_handler│  ← Melt circuit (data quality < 0.3)
│ cleaner  │    └──────┬───────┘
└────┬─────┘           │
     ▼                 │
┌─────────┐            │
│bull R1  │            │
└────┬────┘            │
     ▼                 │
┌─────────┐            │
│bear     │            │
│counter  │            │
└────┬────┘            │
     ▼                 │
┌─────────┐            │
│bull     │            │
│rebuttal │            │
└────┬────┘            │
     ▼                 │
┌─────────┐            │
│ auditor │            │
└────┬────┘            │
     ▼                 ▼
┌─────────────────────────┐
│  chief (CIO) synthesis  │  ← Human-in-the-loop valuation tweak
│  → Final IC Report      │
└─────────────────────────┘
```

## Key Features

### Production-Grade Data Layer
- **yFinance primary + FMP secondary**: Dual data source with automatic field-level merging
- **Data quality scoring**: Every data point scored 0.0–1.0; < 0.3 triggers circuit breaker
- **Dynamic ERP**: Equity Risk Premium calculated as `SPY earnings yield - risk-free rate`, not hardcoded

### Professional Investment Banking Valuation
- **No LLM parameter guessing**: WACC = CAPM (rf + β × ERP), growth = analyst consensus
- **Hard data anchors**: Industry multiples, FMP reference DCF, historical CAGR all injected into prompt
- **LLM only adjusts within bounds** (±20% for growth, ±10% for WACC) with mandatory reasoning

### Adversarial Multi-Round Debate
- **R1**: Bull constructs strongest buy thesis from cleaned context
- **R2**: Bear counters with specific logic刺穿 (puncture attacks)
- **R3**: Bull rebuts with data-backed defense
- Auditor then cross-examines the full debate history

### Context Memory Optimization
- **Context cleaner node**: Compresses raw macro/fundamental/sentiment data → structured 200-word summary
- All downstream nodes consume `cleaned_context` instead of raw JSON, preventing context overflow

### Human-in-the-Loop
- Valuation parameters (WACC, terminal growth, target multiples) can be adjusted via UI before final report
- System pauses at `chief` node, waits for CIO confirmation

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Orchestration** | LangGraph (StateGraph, interrupt, checkpoint via PostgreSQL) |
| **Backend** | Python 3.10+, FastAPI, SSE streaming |
| **Valuation Engine** | yfinance, FMP API, scipy (VaR), pandas |
| **Search/News** | Tavily API (dynamic query generation) |
| **Data Validation** | Pydantic v2 (all intermediary outputs) |
| **LLM Providers** | DashScope/Qwen, OpenAI-compatible DeepSeek, Claude |
| **Persistence** | PostgreSQL 15 (AsyncPostgresSaver) |
| **Frontend** | Next.js 16, React 19, Tailwind CSS v4, Framer Motion 12 |

## Project Structure

```
quantfinance/
├── backend/
│   ├── server.py                          # FastAPI entry + SSE streaming
│   ├── requirements.txt
│   ├── .env                               # API keys (gitignored)
│   └── src/
│       ├── core/
│       │   └── config.py                  # LLM factory (model routing)
│       ├── agents/
│       │   ├── graph.py                   # LangGraph state machine (10 nodes)
│       │   ├── state.py                   # AgentState + structured models
│       │   ├── prompts.py                 # System prompts for all agents
│       │   └── intent_parser.py           # Structured intent extraction
│       └── tools/
│           ├── finance_tool.py            # DCF/PS/EV-EBITDA/VaR calculators
│           ├── data_repository.py         # yFinance→FMP data layer
│           └── news_tool.py               # Tavily search + dynamic query
├── frontend/
│   ├── app/
│   │   ├── page.tsx                       # Main UI (SSE, real-time flow)
│   │   ├── layout.tsx
│   │   └── globals.css
│   └── package.json
├── docker-compose.yml                     # PostgreSQL 15
└── AGENTS.md                              # LLM behavioral guidelines
```

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 15 (or Docker)
- API keys: LLM provider, Tavily, FMP

### Setup

```bash
# 1. Database
docker-compose up -d

# 2. Backend
cd backend
python -m venv venv && venv\Scripts\activate  # Windows: `venv\Scripts\activate`
pip install -r requirements.txt
# Edit .env with your API keys
uvicorn server:app --reload --port 8000

# 3. Frontend
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Enter a query like:
> *"Analyze TSLA. I'm worried about margin compression and plan to hold long-term."*

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze` | POST | Start/resume analysis (SSE stream) |
| `/api/feedback` | POST | Submit valuation parameter tweaks |

## Roadmap & TODO

- [ ] **AgentState Pydantic modelization**: Convert TypedDict to full Pydantic for better checkpointing
- [ ] **Citation tracing**: Show source data popups on citation markers `[1]` in final report
- [ ] **Backtesting node**: Earnings surprise history → management credibility score
- [ ] **Server-side rendering**: Migrate SSE to WebSocket for production resilience
- [ ] **Unit tests**: Pytest for graph nodes, tool functions, and prompt formatting
- [ ] **CI/CD**: GitHub Actions for lint + typecheck + test
- [ ] **Multi-tenant thread isolation**: Per-user thread namespacing in PostgreSQL
