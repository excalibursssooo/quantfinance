
---

# 📈 Quantfin-Oracle: 多智能体 AI 投研系统

**Quantfin-Oracle** 是一款基于 **LangGraph** 和 **LLM** 构建的深度股票分析系统。它模拟了华尔街投行分析师的工作流，通过多个并行工作的专家 Agent（宏观、基本面、估值、情绪）对美股标的进行全方位透视，并动态生成具有洞察力的深度投资报告。

---

## 🌟 核心亮点
- **并行专家流 (Parallel Multi-Agent)**：采用 Fan-out/Fan-in 设计，宏观、财务、估值、情绪四个维度同步调研，极大提升分析效率。
- **动态 DCF 建模**：系统实时抓取 **10年期美债收益率** 作为无风险利率，并结合 LLM 对历史数据的推理，动态设定增长率（g）和折现率（r）。
- **数据驱动而非假设**：集成 `yfinance` 获取实时财务报表，集成 `Tavily Search` 获取 2026 最新宏观动态与市场情绪。
- **工业级架构**：基于 LangGraph 实现复杂状态管理，确保长链条推理过程中的数据一致性与容错性。
- **可视化 Web 界面**：内置 Streamlit 应用，一键生成排版精美的 Markdown 研报。
---

## 🏗️ 系统架构

系统遵循“调研 -> 推理 -> 清洗 -> 决策”的逻辑：

1.  **Input Node**: 接收股票代码（如 AAPL）。
2.  **Expert Nodes (Parallel)**:
    * **Macro Analyst**: 调研美联储政策及行业宏观环境。
    * **Fundamental Analyst**: 拆解 ROE、自由现金流与盈利质量。
    * **Valuation Expert**: 推导 DCF 参数并执行内在价值计算。
    * **Sentiment Analyst**: 监控机构持仓(13F)与市场情绪。
3.  **Data Cleaning Node**: 对各路专家返回的长文本进行脱水处理，提取关键数值指标。
4.  **Chief Analyst Node**: 综合所有维度，套用专业分析师 Checklist，生成最终结论。

---

## 🚀 快速开始

### 1. 环境准备
确保您的电脑已安装 Python 3.10+。

```bash
# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量
在项目根目录创建 `.env` 文件，并填入您的 API Key：

```env
OPENAI_API_KEY=sk-xxxx
OPENAI_API_BASE_URL=https://api.openai.com/v1 # 可选
MODEL_NAME=gpt-4o-mini
TAVILY_API_KEY=tvly-xxxx
```

### 3. 启动应用
你可以通过命令行运行，也可以启动 Web 界面。

**方式 A：启动 Web 应用（推荐）**
```bash
streamlit run app.py
```

**方式 B：命令行测试**
```bash
python main.py NVDA(可更改其他股票代码)
```

---

## 📂 项目结构

```text
├── agents/
│   ├── graph.py       # LangGraph 工作流编排
│   ├── state.py       # 系统状态定义
│   └── prompts.py     # 专家系统提示词
├── core/
│   └── config.py      # 统一模型与配置中心
|── tools/
│   ├── finance_tool.py # yfinance 财务计算工具
│   └── news_tool.py    # Tavily 实时搜索工具
├── app.py                 # Streamlit Web 入口
├── main.py                # 命令行入口
├── .env                   # 环境变量配置
└── requirements.txt       # 项目依赖
```

---

## 🛠️ 核心公式支持

系统在估值节点中内置了标准的 DCF 模型支持：

$$PV = \sum_{t=1}^{n} \frac{FCF_t}{(1+r)^t} + \frac{TV}{(1+r)^n}$$

其中 **r (WACC)** 由系统根据实时 **Beta** 值与 **无风险利率** 通过 CAPM 模型计算得出。

---

## ⚠️ 免责声明
本系统生成的所有分析报告均由人工智能基于公开数据生成，不构成任何形式的投资建议。股市有风险，投资需谨慎。

---