# 📈 QuantFinance AI Agent

> **An intelligent, multi-agent quantitative finance analysis platform driven by LLMs and LangGraph.**

QuantFinance AI Agent is a full-stack application that simulates a Wall Street Investment Committee. By orchestrating multiple specialized AI "experts" (Macro Analyst, Fundamental Analyst, Valuation Expert, Bull/Bear Debaters, and a Chief Investment Officer), it transforms a simple user query into a comprehensive, data-driven, and objectively balanced investment research report.

---

## ✨ Key Features

* **🧠 Multi-Agent Orchestration:** Powered by LangGraph, the system executes a complex DAG (Directed Acyclic Graph) workflow. It parses intent, parallelizes data gathering, debates theses, and synthesizes a final verdict.
* **📊 Real-Time Market Data:** Integrates `yfinance` and `Tavily` search to pull real-time stock data, historical financials, macro-economic indicators, and sentiment news.
* **🧮 Dynamic Valuation Modeling:** Automatically selects and calculates the best valuation model (DCF, P/S, EV/EBITDA) based on company fundamentals, adjusting parameters like WACC, terminal growth rate, and equity risk premium dynamically.
* **⚡ Streaming UI:** Utilizes Server-Sent Events (SSE) via FastAPI to stream the AI's thought process and stage completion status directly to a modern, responsive React (Next.js) frontend.
* **⚔️ Red Teaming / Debate Framework:** Forces a structural debate between a "Bull Expert" (optimist) and a "Bear Expert" (pessimist) to eliminate bias before the Chief Investment Officer makes a final call.

---

## 🏗️ System Architecture & Workflow

The analysis pipeline strictly follows this lifecycle:

1.  **Intent Parsing (`intent_analyzer`):** Extracts the target ticker, investment horizon, user concerns, and sector from natural language.
2.  **Parallel Data Gathering:**
    * `macro_analyst`: Fetches broad economic data and interest rates.
    * `fundamental_analyst`: Extracts P/E, EPS, growth metrics, and capital allocation.
    * `sentiment_analyst`: Analyzes recent news and market sentiment.
3.  **Valuation (`valuation_expert`):** Calculates intrinsic value using mathematical models.
4.  **Debate Phase:**
    * `bull_expert`: Constructs the strongest possible buy thesis.
    * `bear_expert`: Actively seeks flaws, risks, and constructs a sell thesis.
5.  **Synthesis (`chief_analyst_synthesis`):** The CIO weighs all evidence, directly addresses user concerns, and outputs the final IC (Investment Committee) Report.

---

## 📂 Project Structure

### Backend (Python / AI Core)
* **`src/agents/graph.py`**: The brain of the application. Defines the LangGraph state machine, nodes, and edges for the multi-agent workflow.
* **`src/agents/state.py`**: Defines the `AgentState` TypedDict, acting as the shared memory/context passed between all AI nodes.
* **`src/agents/prompts.py`**: Contains the highly engineered system prompts that give each AI expert its specific persona and task rules.
* **`src/agents/intent_parser.py`**: Uses structured LLM outputs to cleanly parse chaotic user input into a JSON format.
* **`src/tools/finance_tool.py`**: The quantitative engine. Interfaces with `yfinance` and contains mathematical tools for DCF calculation, historical returns, and metric extraction.
* **`src/tools/news_tool.py`**: The qualitative engine. Dynamically generates search queries and fetches real-time market news using Tavily.
* **`server.py`**: A FastAPI application that serves the LangGraph workflow via a `/api/analyze` endpoint. It uses SSE (Server-Sent Events) to stream real-time state updates to the frontend.

### Frontend (React / Next.js)
* **`page.tsx`**: The main user interface. Built with React, Tailwind CSS, and Framer Motion. It handles the SSE connection, displays real-time loading states for each agent, and renders the final markdown reports beautifully.

---

## 💻 Tech Stack

**Backend & AI:**
* **Python 3.10+**
* **LangChain & LangGraph:** For agent orchestration and LLM pipeline management.
* **FastAPI:** High-performance web framework for the API and SSE streaming.
* **Pydantic:** Data validation and structured output schema definition.
* **yfinance & pandas:** Financial data fetching and manipulation.
* **Tavily API:** Real-time web search for news and macro data.

**Frontend:**
* **React (Next.js):** UI framework.
* **Tailwind CSS:** Utility-first styling.
* **Framer Motion:** Smooth, physics-based animations for the UI loading states.
* **Lucide React:** Beautiful, consistent iconography.

---

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* Node.js 18+
* API Keys for your chosen LLM (e.g., OpenAI/Anthropic) and Tavily Search.

### 1. Backend Setup
```bash
# Clone the repository and navigate to the backend directory
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install fastapi uvicorn langgraph langchain yfinance pandas pydantic retrying tavily-python

# Set your environment variables (create a .env file)
export OPENAI_API_KEY="your-api-key"
export TAVILY_API_KEY="your-tavily-key"

# Run the FastAPI server
uvicorn server:app --reload --port 8000
```

### 2. Frontend Setup
```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Run the development server
npm run dev
```

### 3. Usage
1. Open `http://localhost:3000` in your browser.
2. Enter a prompt like: *"I am considering buying NVDA for the long term, but I am worried about AI hardware market saturation. Should I invest?"*
3. Watch the multi-agent system work in real-time as the UI lights up, and review the final Investment Committee report!