# src/agents/graph.py
import json
from langgraph.graph import StateGraph, END
from tools.finance_tool import get_detailed_finance, get_growth_metrics, calculate_intrinsic_dcf, get_macro_rates, get_advanced_metrics
from tools.news_tool import get_real_market_data
from agents.state import AgentState
from agents.prompts import BULL_PROMPT, BEAR_PROMPT, CLEANER_PROMPT, CHIEF_PROMPT, VALUATION_PROMPT
from core.config import Config
import streamlit as st
from agents.intent_parser import parse_user_input

def intent_node(state: AgentState):

    print(f"🎯 正在解析用户意图...")
    
    user_text = state.get("user_prompt", "")
    
    intent_data = parse_user_input(user_text)
    raw_concerns = intent_data.get("user_concerns", "无")
    if isinstance(raw_concerns, list):
        processed_concerns = "；".join(raw_concerns)
    else:
        processed_concerns = raw_concerns
    return {
        "ticker": intent_data["ticker"],
        "investment_horizon": intent_data["investment_horizon"],
        "user_concerns": processed_concerns,
        "sector": intent_data["sector"]
    }


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

# 获取当前 UI 中配置的模型（如果没有则使用默认值）
def get_configured_model(role_type: str):
    if "model_config" in st.session_state:
        return st.session_state.model_config.get(role_type, "qwen3.5-flash")
    return "qwen3.5-flash"  # 默认模型

def bull_analyst(state: AgentState):
    model_name = get_configured_model("debate_model")
    llm = Config.get_llm(temperature=0.7, model_name=model_name)
    chain = BULL_PROMPT | llm
    res = chain.invoke({
        "ticker": state["ticker"],
        "user_concerns": state.get("user_concerns", ""),
        "fundamentals": state.get("fundamental_data", {}), 
        "macro_context": state.get("macro_data", ""),       
        "sentiment": state.get("sentiment_data", "")
    })
    return {"bull_thesis": res.content}

def bear_analyst(state: AgentState):
    model_name = get_configured_model("debate_model")
    llm = Config.get_llm(temperature=0.6, model_name=model_name)
    chain = BEAR_PROMPT | llm
    res = chain.invoke({
        "ticker": state["ticker"],
        "user_concerns": state.get("user_concerns", ""),
        "fundamentals": state.get("fundamental_data", {}),
        "macro_context": state.get("macro_data", ""),
        "sentiment": state.get("sentiment_data", "")
    })    
    return {"bear_thesis": res.content}

def chief_analyst_synthesis(state: AgentState):
    model_name = get_configured_model("chief_model")
    llm = Config.get_llm(temperature=0.3, model_name=model_name)
    chain = CHIEF_PROMPT | llm
    res = chain.invoke({
        "ticker": state["ticker"],
        "investment_horizon": state.get("investment_horizon", "未指定"),
        "user_concerns": state.get("user_concerns", "无"),
        "bull_thesis": state.get("bull_thesis", ""),
        "bear_thesis": state.get("bear_thesis", ""),
        "macro_data": state.get("macro_data", ""),
        "fundamental_data": state.get("fundamental_data", {})
    })    
    return {"final_report": res.content}

def data_cleaning_node(state: AgentState):
    print("-> 🧹 首席助理正在汇总多空博弈记录...")
    # 这里我们可以扩展 CLEANER_PROMPT，让它把 bull_thesis 和 bear_thesis 整理进 Context
    context = f"""
    【多方观点】: {state.get('bull_thesis')}
    【空方观点】: {state.get('bear_thesis')}
    【宏观背景】: {state.get('macro_data')}
    【财务指标】: {state.get('fundamental_data')}
    """
    # 实际运行中可以再跑一次 LLM 进行 Token 压缩
    return {"cleaned_context": context}


def input_node(state: AgentState):
    """虚拟入口点，用于分发并行任务"""
    print(f"🚀 启动多维度专家并行调研: {state['ticker']}")
    return state


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("intent_analyzer", intent_node) # 新的起点
    # 1. 注册节点
    workflow.add_node("macro", macro_analyst)
    workflow.add_node("fundamental", fundamental_analyst)
    workflow.add_node("sentiment", sentiment_analyst)
    
    workflow.add_node("bull_expert", bull_analyst) # 新增
    workflow.add_node("bear_expert", bear_analyst) # 新增
    
    workflow.add_node("cleaner", data_cleaning_node)
    workflow.add_node("chief", chief_analyst_synthesis)

    # 2. 编排边关系
    # 第一阶段：三路并行数据采集
    workflow.set_entry_point("intent_analyzer") # 入口变为意图分析
    
    # 意图分析完成后，分发给并行的调研节点
    workflow.add_edge("intent_analyzer", "macro")
    workflow.add_edge("intent_analyzer", "fundamental")
    workflow.add_edge("intent_analyzer", "sentiment")
    
    # 第二阶段：数据齐备后，分发给多空两方进行辩论 (Fan-out)
    workflow.add_edge("sentiment", "bull_expert")
    workflow.add_edge("sentiment", "bear_expert")
    
    # 第三阶段：多空意见汇总 (Fan-in)
    workflow.add_edge(["bull_expert", "bear_expert"], "cleaner")
    
    workflow.add_edge("cleaner", "chief")
    workflow.add_edge("chief", END)

    return workflow.compile()