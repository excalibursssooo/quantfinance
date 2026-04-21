
---

# 📈 Quantfin-Oracle: 多智能体投研系统

**Quantfin-Oracle** 是一款基于 **LangGraph** 和 **LLM** 构建的深度股票分析系统。它不仅模拟了华尔街投行分析师的工作流，更引入了**自动熔断机制**与**人工干预控制**，确保在波动的 API 环境下依然保持极高的系统稳定性。

---

## 🌟 核心亮点

- **并行专家流 (Parallel Multi-Agent)**：采用 Fan-out/Fan-in 设计，宏观、财务、估值、情绪四个维度同步调研。
- **工业级容错 (Circuit Breaker)**：引入全局异常捕获机制，任何节点（API 超时、格式错误）出错均会即时触发系统熔断，防止无效计算消耗 Token。
- **动态 DCF 建模**：实时抓取十年期美债收益率（^TNX）作为无风险利率，结合 CAPM 模型动态推导 WACC。

---

## 🏗️ 系统架构

系统遵循“意图识别 -> 调研 -> 熔断保护 -> 决策”的逻辑：


1.  **Intent Parser**: 利用结构化输出识别 Ticker 和用户核心关切。
2.  **Expert Nodes (Parallel)**:
    * **Macro Analyst**: 调研美联储政策及行业宏观环境。
    * **Fundamental Analyst**: 提取 CapEx、回购及 ROE 等高质量指标。
    * **Valuation Expert**: 推导 DCF 参数并执行内在价值计算。
    * **Sentiment Analyst**: 监控 13F 持仓与技术面情绪。
3.  **Circuit Breaker**: 全局监听 `app_graph.stream()`，捕获任何节点的 `ValidationError` 或 `APIError`。
4.  **Chief Analyst**: 综合所有脱水数据，生成具备“机构感”的深度研报。

---

## 🚀 快速开始

### 1. 配置环境变量
在 `.env` 文件中填入您的配置：

```env
OPENAI_API_KEY=sk-xxxx
OPENAI_API_BASE_URL=https://api.openai.com/v1
MODEL_NAME=qwen3.6-flash # 或 deepseek-v3.2, gpt-4o
TAVILY_API_KEY=tvly-xxxx
```

### 2. 启动系统
```bash
streamlit run app.py
```

---

## 📂 项目结构

```text
├── agents/
│   ├── graph.py       # LangGraph 工作流编排（含 Fan-out 逻辑）
│   ├── intent_parser.py # 强鲁棒性的意图解析器
│   ├── state.py       # 系统 TypedDict 状态定义
│   └── prompts.py     # 专家系统提示词
├── core/
│   └── config.py      # 模型与 API 统一配置中心
|── tools/
│   ├── finance_tool.py # YFinance 财务及 DCF 计算工具
│   └── news_tool.py    # Tavily 实时搜索工具
├── app.py             # 支持流式输出与紧急停止的 Streamlit 入口
├── .env               # 环境变量
└── requirements.txt   # 项目依赖
```

---

## ⚠️ 免责声明
本系统生成的所有分析报告均由人工智能基于公开数据生成，不构成投资建议。**AI 可能会产生幻觉，请务必核实计算结果。**

---