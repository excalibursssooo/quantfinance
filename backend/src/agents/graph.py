# src/agents/graph.py
import json
from langgraph.graph import StateGraph, END
from src.tools.finance_tool import (
    get_detailed_finance,
    get_growth_metrics,
    get_macro_rates,
    get_advanced_metrics,
)
from src.tools.news_tool import get_real_market_data
from src.agents.state import AgentState
from src.agents.prompts import (
    BULL_PROMPT,
    BEAR_PROMPT,
    CLEANER_PROMPT,
    CHIEF_PROMPT,
    VALUATION_PROMPT,
    SMART_VALUATION_PROMPT
)
from src.core.config import Config
from src.agents.intent_parser import parse_user_input
from pydantic import BaseModel, Field
from src.tools.finance_tool import calculate_dcf, calculate_ps_valuation, calculate_ev_ebitda, calculate_historical_var

class ValuationParams(BaseModel):
    g: float = Field(description="前N年预期增长率 (例如 0.15 表示 15%)")
    tg: float = Field(description="永续增长率 (通常在 0.02 到 0.03 之间)")
    erp: float = Field(description="股权风险溢价 (结合宏观情绪给出)")
    reason: str = Field(description="参数推导的核心逻辑简述")

# 获取当前 UI 中配置的模型（如果没有则使用默认值）
def get_configured_model(state: AgentState, role_type: str):
    # 从状态中读取，如果没有则给兜底默认值
    return state.get("model_config", {}).get(role_type, "qwen3.5-flash")



def intent_node(state: AgentState):

    print(f"🎯 正在解析用户意图...")

    user_text = state.get("user_prompt", "")
    user_model = get_configured_model(state, "intent")
    intent_data = parse_user_input(user_text, model_name=user_model)
    raw_concerns = intent_data.get("user_concerns", "无")
    if isinstance(raw_concerns, list):
        processed_concerns = "；".join(raw_concerns)
    else:
        processed_concerns = raw_concerns
    
    current_ticker = state.get("ticker")
    new_ticker = intent_data.get("ticker")
    
    final_ticker = new_ticker
    if (not new_ticker or new_ticker.upper() == "UNKNOWN") and current_ticker:
        final_ticker = current_ticker
    return {
        "ticker": final_ticker,
        "investment_horizon": intent_data["investment_horizon"],
        "user_concerns": processed_concerns,
        "sector": intent_data["sector"],
    }


def macro_analyst(state: AgentState):
    print("🌍 [Parallel] 宏观专家正在进行智能调研...")
    user_model = get_configured_model(state, "intent")
    news = get_real_market_data(
        ticker=state["ticker"],
        model_name=user_model,
        concerns=f"Macro environment and Fed impact on: {state.get('user_concerns', 'general outlook')}",
        horizon=state.get("investment_horizon", "long-term")
    )
    
    rates = get_macro_rates()
    
    return {
        "macro_data": f"【实时宏观资讯】\n{news}\n【基准利率环境】\n{rates}"
    }


def fundamental_analyst(state: AgentState):
    print("-> [Parallel] 基本面专家正在拆解地利与高阶数据...")
    raw_data = get_detailed_finance(state["ticker"])
    adv_data = get_advanced_metrics(state["ticker"])  # 获取高阶指标

    return {
        "fundamental_data": raw_data,
        "advanced_metrics": adv_data,  # 写入状态
    }


def sentiment_analyst(state: AgentState):
    print("🔥 [Parallel] 情绪专家正在洞察市场人和...")
    user_model = get_configured_model(state, "intent")
    # 👈 核心修复：同样调用新版接口
    news = get_real_market_data(
        ticker=state["ticker"],
        model_name=user_model,
        # 侧重于情绪、技术面和机构持仓
        concerns=f"Market sentiment, institutional activity, and technical analysis regarding: {state.get('user_concerns', 'overall trend')}",
        # 情绪通常对中短期影响更大
        horizon="short-to-medium term" 
    )
    
    return {"sentiment_data": news}


def valuation_expert(state: AgentState):
    print(f"⚖️ [Node] 智能估值专家正在决策: {state['ticker']}...")
    
    user_model = get_configured_model(state, "valuation")

    fin_data = get_detailed_finance(state["ticker"])
    fundamental = fin_data.get("fundamentals", {})
    multiples = fin_data.get("valuation_multiples", {})
    basic = fin_data.get("basic", {})
    
    current_price = basic.get("price", 0.0)
    shares = basic.get("shares_outstanding", 1)
    revenue = basic.get("total_revenue", 0)
    total_cash = fundamental.get("total_cash", 0)
    total_debt = fundamental.get("total_debt", 0)
    net_debt = total_debt - total_cash
    fcf = fundamental.get("free_cashflow", 0)
    ebitda = fundamental.get("ebitda", 0)

    # 🚨 阶段二进阶：动态条件路由，硬性约束模型可使用的工具
    sector = state.get("sector", "").lower()
    tools = [calculate_ps_valuation, calculate_ev_ebitda, calculate_dcf]  # 默认开放所有工具
    if ("technology" in sector or "software" in sector) and fcf < 0:
        print(f"💡 触发条件路由: SaaS/高增长亏损科技股，强制使用 P/S 估值")
        tools = [calculate_ps_valuation]
    elif "industrial" in sector or "auto" in sector or "manufacturing" in sector:
        print(f"💡 触发条件路由: 重资产工业股，强制使用 EV/EBITDA 估值")
        tools = [calculate_ev_ebitda]
    else:
        print(f"💡 触发条件路由: 稳健现金流企业，开放 DCF 估值")
        tools = [calculate_dcf, calculate_ev_ebitda]

    prompt = SMART_VALUATION_PROMPT.format(
        ticker=state["ticker"],
        sector=sector,
        shares=shares,       
        revenue=revenue,     
        fcf=fcf,
        ebitda=ebitda,
        net_debt=net_debt,   
        ps_ratio=multiples.get("ps_ratio", 0),
        ev_ebitda=multiples.get("ev_ebitda", 0)
    )
    
    llm = Config.get_llm(temperature=0, model_name=user_model).bind_tools(tools)
    response = llm.invoke(prompt)
    
    val_data = {
        "selected_method": "未知",
        "reasoning": "未成功调用",
        "key_metrics": {},
        "intrinsic_value": 0.0,
        "current_price": current_price,
        "verdict": "未知"
    }
    
    if response.tool_calls:
        tool_call = response.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        val_data["selected_method"] = tool_name
        val_data["reasoning"] = tool_args.pop("reasoning", "无分析逻辑")
        val_data["key_metrics"] = tool_args 
        
        if tool_name == "calculate_dcf":
            # 兼容修改后的 DCF 返回结构
            dcf_res = calculate_dcf.invoke(tool_args)
            intrinsic_val = dcf_res.get("base_intrinsic_value", 0.0)
            val_data["sensitivity"] = dcf_res.get("sensitivity_matrix", {})
        elif tool_name == "calculate_ps_valuation":
            intrinsic_val = calculate_ps_valuation.invoke(tool_args)
        elif tool_name == "calculate_ev_ebitda":
            intrinsic_val = calculate_ev_ebitda.invoke(tool_args)
        else:
            intrinsic_val = 0.0
            
        val_data["intrinsic_value"] = intrinsic_val
        if current_price > 0:
            if intrinsic_val > current_price * 1.15:
                val_data["verdict"] = "严重低估 (强烈看多)"
            elif intrinsic_val < current_price * 0.85:
                val_data["verdict"] = "存在泡沫 (估值偏高)"
            else:
                val_data["verdict"] = "估值合理"
                
    # 🚨 阶段三进阶：顺带计算风险价值 VaR
    var_result = calculate_historical_var.invoke({"ticker": state["ticker"]})
    
    return {"valuation_data": val_data, "var_data": var_result}


def logic_auditor(state: AgentState):
    """阶段二进阶：逻辑审计员节点，检查多空双方的漏洞"""
    print("🧐 [Node] 逻辑审计员正在进行交叉审查...")
    model_name = get_configured_model(state, "chief_model")
    llm = Config.get_llm(temperature=0.2, model_name=model_name)
    
    audit_prompt = f"""
    你是一个严苛的风控审计员。请检查以下针对 {state['ticker']} 的多头和空头观点，指出其中是否存在事实互斥、过度乐观或对宏观风险避而不谈的逻辑断层。
    多头逻辑: {state.get('bull_thesis')}
    空头逻辑: {state.get('bear_thesis')}
    估值结论: {state.get('valuation_data', {}).get('verdict')}
    请用 3 句话给出辛辣客观的审计意见。
    """
    res = llm.invoke(audit_prompt)
    return {"audit_report": res.content}


def bull_analyst(state: AgentState):
    model_name = get_configured_model(state, "debate_model")
    llm = Config.get_llm(temperature=0.7, model_name=model_name,streaming=True)
    chain = BULL_PROMPT | llm
    res = chain.invoke(
        {
            "ticker": state["ticker"],
            "user_concerns": state.get("user_concerns", ""),
            "fundamentals": state.get("fundamental_data", {}),
            "macro_context": state.get("macro_data", ""),
            "sentiment": state.get("sentiment_data", ""),
        }
    )
    return {"bull_thesis": res.content}


def bear_analyst(state: AgentState):
    model_name = get_configured_model(state, "debate_model")
    llm = Config.get_llm(temperature=0.6, model_name=model_name,streaming=True)
    chain = BEAR_PROMPT | llm
    res = chain.invoke(
        {
            "ticker": state["ticker"],
            "user_concerns": state.get("user_concerns", ""),
            "fundamentals": state.get("fundamental_data", {}),
            "macro_context": state.get("macro_data", ""),
            "sentiment": state.get("sentiment_data", ""),
        }
    )
    return {"bear_thesis": res.content}


def chief_analyst_synthesis(state: AgentState):
    import datetime
    print("👔 [Node] 首席总监正在撰写最终研报...")
    model_name = get_configured_model(state, "chief_model")
    llm = Config.get_llm(temperature=0.4,streaming=True,model_name=model_name) 
    
    raw_context = (
        f"【宏观面】: {state.get('macro_data', '缺失')}\n"
        f"【基本面】: {json.dumps(state.get('fundamental_data', {}), ensure_ascii=False)}\n"
        f"【情绪面】: {state.get('sentiment_data', '缺失')}\n"
        f"【风险建模(VaR)】: {state.get('var_data', {})}\n"
        f"【审计员警告】: {state.get('audit_report', '无')}\n"
        f"【高阶指标】: {json.dumps(state.get('advanced_metrics', {}), ensure_ascii=False)}"
    )
    
    prompt = CHIEF_PROMPT.format(
        ticker=state["ticker"],
        investment_horizon=state.get("investment_horizon", "未指定"),
        user_concerns=state.get("user_concerns", "无"),
        bull_thesis=state.get("bull_thesis", "多头无观点"),
        bear_thesis=state.get("bear_thesis", "空头无观点"),
        cleaned_context=raw_context, 
        valuation_data=json.dumps(state.get("valuation_data", {}), ensure_ascii=False),
        time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    response = llm.invoke(prompt)
    return {"final_report": response.content}



def input_node(state: AgentState):
    """虚拟入口点，用于分发并行任务"""
    print(f"🚀 启动多维度专家并行调研: {state['ticker']}")
    return state


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("intent_analyzer", intent_node)  # 新的起点
    # 1. 注册节点
    workflow.add_node("macro", macro_analyst)
    workflow.add_node("fundamental", fundamental_analyst)
    workflow.add_node("valuation", valuation_expert)
    workflow.add_node("sentiment", sentiment_analyst)

    workflow.add_node("bull_expert", bull_analyst)
    workflow.add_node("bear_expert", bear_analyst)
    workflow.add_node("auditor", logic_auditor)
    workflow.add_node("chief", chief_analyst_synthesis)

    workflow.set_entry_point("intent_analyzer")

    # 第一阶段：获取基础数据（宏观、基本面、情绪面并行）
    workflow.add_edge("intent_analyzer", "macro")
    workflow.add_edge("intent_analyzer", "fundamental")
    workflow.add_edge("intent_analyzer", "sentiment")
    
    # 第二阶段：让 valuation 依赖 macro 的输出
    # 只要 macro 跑完了，valuation 就可以开始，这时候一定有 macro_data 了
    workflow.add_edge("macro", "valuation")

    # 第三阶段：分发给多空两方进行辩论
    workflow.add_edge("valuation", "bull_expert")
    workflow.add_edge("valuation", "bear_expert")

    workflow.add_edge("bull_expert", "auditor")
    workflow.add_edge("bear_expert", "auditor")
    
    # 审计完成后交给 Chief
    workflow.add_edge("auditor", "chief")
    workflow.add_edge("chief", END)
    return workflow
