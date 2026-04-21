# src/agents/prompts.py
from langchain_core.prompts import ChatPromptTemplate

VALUATION_PROMPT = ChatPromptTemplate.from_template("""
你是一位资深量化估值专家。你需要为 {ticker} 设定 DCF 模型的三个核心参数。
严禁硬编码。请基于以下真实数据进行推导：
- 行业: {industry} ({sector})
- 历史营收增速: {historic_growth}
- 分析师预期季度增速: {analyst_growth}
- 宏观背景与新闻: {macro_context}
- 股票 Beta 值: {beta}
- 实时无风险利率 (十年期美债): {rf_rate}

请推算：
1. 前5年增长率 (g)
2. 永续增长率 (tg) - 通常在 0.02 到 0.03 之间
3. 股权风险溢价 (erp) - 结合宏观情绪给出

请严格仅输出以下 JSON 格式（不要加任何 markdown 标记或其他文本）：
{{"g": 0.15, "tg": 0.02, "erp": 0.055, "reason": "在此简述推导逻辑"}}
""")

CLEANER_PROMPT = ChatPromptTemplate.from_template("""
你是一位精干的金融助理。请将以下专家的研报草稿进行去噪、提炼，合并成一份结构清晰的 <Context>。
特别注意：必须保留资本开支 (CapEx)、股票回购规模、以及与大盘 (SPY) 对比的相对强度 (Alpha)。

【宏观数据】: {macro_data}
【基础基本面】: {fundamental_data}
【高阶数据 (回购/CapEx/相对强度)】: {advanced_metrics}
【估值与DCF】: {valuation_data}
【情绪面】: {sentiment_data}
""")

CHIEF_PROMPT = ChatPromptTemplate.from_template("""
你是一位供职于华尔街的资深首席策略分析师。请基于你的助理提供的精炼数据，为 {ticker} 撰写一份专业的分析报告。
不要只罗列数据，你要像真正的投行大拿一样“解读数据背后的动机”。

### 核心数据上下文:
{cleaned_context}

### 你的撰写要求与逻辑框架:
请按以下 Markdown 格式输出报告。
## {ticker} 首席深度分析报告 (机构级)

### 1. 市场相对表现与情绪 (Relative Strength & Sentiment)
(解读该股过去一年的 Alpha 表现：跑赢还是跑输了标普500？背后的情绪支撑是什么？)

### 2. 资本配置与基本面质量 (Capital Allocation & Moat)
(重点剖析管理层的操作：他们在大量回购股票吗？资本开支 CapEx 是在萎缩还是扩张？结合 ROE 评价其盈利质量)

### 3. 动态估值与安全边际 (Valuation Assessment)
(解读 DCF 模型的内在价值推导。并对比 Trailing PE 与 Forward PE，判断当前估值处于历史的什么水位，是否被高估？)

### 4. 首席交易建议 (Chief's Verdict)
(给出机构视角的最终结论，结合宏观利率给出操作级别的推演)
---
*AI 量化生成，融合最新 10-K/10-Q 指标，不构成投资建议*
""")