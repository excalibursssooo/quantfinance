# src/agents/graph.py
import json
from langgraph.graph import StateGraph, END
from tools.finance_tool import get_detailed_finance, get_growth_metrics, calculate_intrinsic_dcf, get_macro_rates, get_advanced_metrics
from tools.news_tool import get_real_market_data
from agents.state import AgentState
from agents.prompts import VALUATION_PROMPT, CLEANER_PROMPT, CHIEF_PROMPT
from core.config import Config

def macro_analyst(state: AgentState):
    print("-> [Parallel] 宏观专家正在调研...")
    news = get_real_market_data(f"{state['ticker']} current macro economy federal reserve interest rate impact")
    return {"macro_data": news}

def fundamental_analyst(state: AgentState):
    print("-> [Parallel] 基本面专家正在拆解地利与高阶数据...")
    raw_data = get_detailed_finance(state["ticker"])
    adv_data = get_advanced_metrics(state["ticker"]) # 获取高阶指标
    
    return {
        "fundamental_data": raw_data.get("fundamentals"),
        "advanced_metrics": adv_data  # 写入状态
    }

def sentiment_analyst(state: AgentState):
    print("-> [Parallel] 情绪专家正在观察人和...")
    news = get_real_market_data(f"{state['ticker']} institutional ownership technical analysis sentiment")
    return {"sentiment_data": news}

def valuation_expert(state: AgentState):
    print(f"-> [Expert] 估值专家正在动态推导 {state['ticker']} 的 DCF 参数...")
    
    growth_data = get_growth_metrics(state['ticker'])
    macro_rates = get_macro_rates()
    
    # 获取无风险利率，若抓取失败则由 LLM 推测
    rf_rate = macro_rates.get("risk_free_rate")
    beta = growth_data.get("beta")
    
    # 启用 LLM 进行参数推理
    llm = Config.get_llm(temperature=0.0)
    chain = VALUATION_PROMPT | llm
    
    response = chain.invoke({
        "ticker": state['ticker'],
        "industry": growth_data.get('industry', 'Unknown'),
        "sector": growth_data.get('sector', 'Unknown'),
        "historic_growth": growth_data.get('historic_revenue_growth', 'Unknown'),
        "analyst_growth": growth_data.get('analyst_growth_estimate', 'Unknown'),
        "macro_context": state.get('macro_data', 'Unknown')[:1000],
        "beta": beta if beta else "未知，请根据行业平均估算",
        "rf_rate": rf_rate if rf_rate else "未能抓取，请根据目前美联储基准利率估算"
    })
    
    # 严格解析 JSON
    try:
        raw_output = response.content.strip().strip('```json').strip('```')
        params = json.loads(raw_output)
        g = float(params.get("g", 0.10))
        tg = float(params.get("tg", 0.02))
        erp = float(params.get("erp", 0.05))
        reason = params.get("reason", "无")
    except Exception as e:
        print(f"⚠️ 参数解析失败，采用保守估计: {e}")
        g, tg, erp, reason = 0.08, 0.02, 0.05, "解析错误，启用保守兜底值"

    # 根据 CAPM 计算 WACC (r)
    calc_rf = rf_rate if rf_rate else 0.04
    calc_beta = beta if beta else 1.0
    wacc = calc_rf + (calc_beta * erp)

    # 传入纯逻辑计算器
    dcf_results = calculate_intrinsic_dcf(
        ticker=state['ticker'], 
        growth_rate=g, 
        terminal_growth=tg, 
        discount_rate=wacc
    )
    dcf_results["logic_proof"] = reason # 保存 LLM 的推理逻辑
    
    return {"valuation_data": dcf_results}

def data_cleaning_node(state: AgentState):
    print("-> [Process] 首席助理正在清洗、脱水数据...")
    llm = Config.get_llm(temperature=0.1)
    chain = CLEANER_PROMPT | llm
    
    res = chain.invoke({
        "macro_data": state.get("macro_data"),
        "fundamental_data": state.get("fundamental_data"),
        "advanced_metrics": state.get("advanced_metrics"), # 新增
        "valuation_data": state.get("valuation_data"),
        "sentiment_data": state.get("sentiment_data")
    })
    return {"cleaned_context": res.content}

def chief_analyst_synthesis(state: AgentState):
    print("-> [Merge] 首席分析师开始撰写深度报告...")
    llm = Config.get_llm(temperature=0.3)
    chain = CHIEF_PROMPT | llm
    
    res = chain.invoke({
        "ticker": state["ticker"],
        "cleaned_context": state.get("cleaned_context", "无清洗数据")
    })
    return {"final_report": res.content}


def input_node(state: AgentState):
    """虚拟入口点，用于分发并行任务"""
    print(f"🚀 启动多维度专家并行调研: {state['ticker']}")
    return state

def build_graph():
    workflow = StateGraph(AgentState)

    # 1. 注册所有节点
    workflow.add_node("start_router", input_node) # 新增起始路由
    workflow.add_node("macro", macro_analyst)
    workflow.add_node("fundamental", fundamental_analyst)
    workflow.add_node("valuation", valuation_expert)
    workflow.add_node("sentiment", sentiment_analyst)
    workflow.add_node("cleaner", data_cleaning_node)
    workflow.add_node("chief", chief_analyst_synthesis)

    # --- 2. 重新编排边 (Fan-out 逻辑) ---
    # 改变策略：先调研宏观和基本面，再进行估值推理
    workflow.set_entry_point("start_router")

    # 第一阶段：调研
    workflow.add_edge("start_router", "macro")
    workflow.add_edge("start_router", "fundamental")
    workflow.add_edge("start_router", "sentiment")

    # 第二阶段：估值（等待宏观结果回传）
    workflow.add_edge("macro", "valuation") 

    # 第三阶段：汇总
    workflow.add_edge("fundamental", "cleaner")
    workflow.add_edge("valuation", "cleaner") # 现在 valuation 包含了 macro 的信息
    workflow.add_edge("sentiment", "cleaner")

    workflow.add_edge("cleaner", "chief")
    workflow.add_edge("chief", END)

    return workflow.compile()