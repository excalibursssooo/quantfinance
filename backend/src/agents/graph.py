# src/agents/graph.py
import json
from langgraph.graph import StateGraph, END
from src.tools.finance_tool import (
    get_macro_rates,
)
from src.tools.data_repository import FinanceDataRepository
from src.tools.news_tool import get_real_market_data
from src.agents.state import AgentState, AuditReport, CleanedContext
from src.agents.prompts import (
    BULL_PROMPT,
    BEAR_PROMPT,
    BEAR_COUNTER_PROMPT,
    BULL_REBUTTAL_PROMPT,
    CLEANER_PROMPT,
    CHIEF_PROMPT,
    SMART_VALUATION_PROMPT
)
from src.core.config import Config
from src.agents.intent_parser import parse_user_input
from src.tools.finance_tool import calculate_dcf, calculate_ps_valuation, calculate_ev_ebitda, calculate_historical_var

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
    print("-> [Parallel] 基本面专家正在拆解地利与高阶数据(FMP→yFinance)")
    repo = FinanceDataRepository()
    collected = repo.collect_all(state["ticker"])

    result = {
        "fundamental_data": collected.financials.model_dump() if collected.financials else {},
        "advanced_metrics": collected.advanced.model_dump() if collected.advanced else {},
        "_data_quality": collected.data_quality,
        "_data_warnings": collected.warnings,
        "_valuation_assumptions": collected.assumptions.model_dump() if collected.assumptions else {},
        "_valuation_multiples": collected.multiples.model_dump() if collected.multiples else {},
    }

    if collected.profile:
        result["sector"] = collected.profile.sector

    if collected.data_quality < 0.3:
        print(f"⚠️ 数据质量不足 ({collected.data_quality})，标记为降级模式")
        result["_degraded"] = True
    else:
        result["_degraded"] = False

    return result


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

    # 🚨 熔断检查：数据质量不足时跳过量化估值
    if state.get("_degraded", False):
        print(f"⛔ 熔断触发: 数据质量不足 ({state.get('_data_quality', 0)})，跳过量化估值")
        return {
            "valuation_data": {
                "selected_method": "N/A",
                "reasoning": "关键财务数据缺失，无法进行量化估值",
                "key_metrics": {},
                "intrinsic_value": 0.0,
                "current_price": 0.0,
                "verdict": "无法估值 (数据不足)",
                "degradation_reason": state.get("_data_warnings", ["未知"])[0] if state.get("_data_warnings") else "关键财务数据缺失",
            },
            "var_data": {},
            "_skip_valuation": True,
        }

    user_model = get_configured_model(state, "valuation")
    fin = state.get("fundamental_data", {})
    multiples = state.get("_valuation_multiples", {})
    assumptions = state.get("_valuation_assumptions", {})

    current_price = fin.get("price", 0.0)
    shares = fin.get("shares_outstanding", 1)
    revenue = fin.get("total_revenue", 0)
    net_debt = fin.get("net_debt", 0)
    fcf = fin.get("free_cashflow", 0)
    ebitda = fin.get("ebitda", 0)

    # 动态条件路由
    sector = state.get("sector", "").lower()
    tools = [calculate_ps_valuation, calculate_ev_ebitda, calculate_dcf]
    if ("technology" in sector or "software" in sector) and (fcf is None or fcf < 0):
        print(f"💡 触发条件路由: SaaS/高增长亏损科技股，强制使用 P/S 估值")
        tools = [calculate_ps_valuation]
    elif "industrial" in sector or "auto" in sector or "manufacturing" in sector:
        print(f"💡 触发条件路由: 重资产工业股，强制使用 EV/EBITDA 估值")
        tools = [calculate_ev_ebitda]
    else:
        print(f"💡 触发条件路由: 稳健现金流企业，开放 DCF 估值")
        tools = [calculate_dcf, calculate_ev_ebitda]

    # 从硬数据中提取估值参数（不让LLM凭空猜测）
    analyst_growth_ny = assumptions.get("analyst_growth_next_year")
    historic_cagr = assumptions.get("historic_revenue_cagr_5y")
    wacc = assumptions.get("wacc")
    rf = assumptions.get("risk_free_rate", 4.5)
    beta = assumptions.get("beta")
    erp = assumptions.get("equity_risk_premium", 5.5)
    industry_pe = assumptions.get("industry_pe")
    industry_ev_ebitda = assumptions.get("industry_ev_ebitda")
    industry_ps = assumptions.get("industry_ps")
    fmp_dcf = assumptions.get("fmp_dcf_value")

    def _pct(v):
        return round(v * 100, 1) if v is not None else "N/A"

    prompt = SMART_VALUATION_PROMPT.format(
        ticker=state["ticker"], sector=sector,
        shares=shares, revenue=revenue,
        fcf=_pct(fcf) if isinstance(fcf, float) and fcf < 1 else fcf,
        ebitda=ebitda, net_debt=net_debt,
        ps_ratio=multiples.get("ps_ratio", "N/A"),
        ev_ebitda=multiples.get("ev_ebitda", "N/A"),
        analyst_growth_ny=_pct(analyst_growth_ny) if analyst_growth_ny and analyst_growth_ny < 1 else (analyst_growth_ny or "N/A"),
        historic_cagr=_pct(historic_cagr) if historic_cagr and historic_cagr < 1 else (historic_cagr or "N/A"),
        wacc=_pct(wacc) if wacc else "N/A",
        rf=_pct(rf), beta=beta or "N/A",
        erp=_pct(erp),
        industry_pe=industry_pe or "N/A",
        industry_ev_ebitda=industry_ev_ebitda or "N/A",
        industry_ps=industry_ps or "N/A",
        fmp_dcf=fmp_dcf or "N/A",
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

    var_result = calculate_historical_var.invoke({"ticker": state["ticker"]})

    return {"valuation_data": val_data, "var_data": var_result}


def error_handler_node(state: AgentState):
    """熔断处理节点：数据不足时生成降级上下文"""
    warnings = state.get("_data_warnings", [])
    quality = state.get("_data_quality", 0)
    print(f"⚠️ [熔断] 数据质量评分 {quality}，进入降级处理")
    context = (
        f"## ⚠️ 数据质量警告\n"
        f"- 数据评分: {quality}\n"
        f"- 数据源: {state.get('_data_source', '未知')}\n"
        f"- 警告: {'；'.join(warnings) if warnings else '关键财务数据缺失'}\n"
        f"- 已自动降级为纯定性分析模式，无法提供量化估值\n\n"
    )
    return {
        "cleaned_context": context,
        "audit_report": "数据不足，跳过量化审计，建议获取完整财务数据后重新分析。",
    }


def context_cleaner_node(state: AgentState):
    """去噪提炼节点：将原始数据压缩为结构化要点"""
    print("🧹 [Node] 上下文去噪提炼中...")
    model_name = get_configured_model(state, "chief_model")
    llm = Config.get_llm(temperature=0.1, model_name=model_name).with_structured_output(CleanedContext)
    import json

    macro_raw = state.get("macro_data", "缺失")
    funda_raw = json.dumps(state.get("fundamental_data", {}), ensure_ascii=False)
    adv_raw = json.dumps(state.get("advanced_metrics", {}), ensure_ascii=False)
    val_raw = json.dumps(state.get("valuation_data", {}), ensure_ascii=False)
    sent_raw = state.get("sentiment_data", "缺失")

    # 如果内容过长，截断避免超出上下文窗口
    max_len = 3000
    for raw in [macro_raw, funda_raw, adv_raw, val_raw, sent_raw]:
        if isinstance(raw, str) and len(raw) > max_len:
            raw = raw[:max_len] + "...[已截断]"

    prompt = CLEANER_PROMPT.format(
        macro_data=macro_raw, fundamental_data=funda_raw,
        advanced_metrics=adv_raw, valuation_data=val_raw,
        sentiment_data=sent_raw
    )
    try:
        res = llm.invoke(prompt)
        cleaned = (
            f"## 宏观环境\n{res.macro_summary}\n\n"
            f"## 基本面快照\n{res.fundamental_snapshot}\n\n"
            f"## 情绪判断: {res.sentiment_assessment}\n\n"
            f"## 估值摘要\n{res.valuation_summary}\n\n"
            f"**催化剂:** {'；'.join(res.key_catalysts)}\n\n"
            f"**风险:** {'；'.join(res.key_risks)}\n\n"
            f"**一句话结论:** {res.investment_conclusion_short}"
        )
        return {"cleaned_context": cleaned}
    except Exception as e:
        print(f"⚠️ 上下文提炼失败，使用原始数据: {e}")
        return {"cleaned_context": f"{macro_raw}\n\n{funda_raw}\n\n{sent_raw}"}


def debate_router(state: AgentState) -> str:
    """根据估值结果路由：正常→去噪+辩论，数据不足→熔断"""
    if state.get("_skip_valuation", False):
        return "error_handler"
    return "debate_start"


def logic_auditor(state: AgentState):
    """阶段二进阶：逻辑审计员节点，检查多空双方的漏洞（结构化输出）"""
    print("🧐 [Node] 逻辑审计员正在进行交叉审查...")
    model_name = get_configured_model(state, "chief_model")
    llm = Config.get_llm(temperature=0.2, model_name=model_name).with_structured_output(AuditReport)
    
    audit_prompt = f"""
    你是一个严苛的风控审计员。请检查以下针对 {state['ticker']} 的多头和空头观点，指出其中是否存在事实互斥、过度乐观或对宏观风险避而不谈的逻辑断层。
    多头逻辑: {state.get('bull_thesis')}
    空头逻辑: {state.get('bear_thesis')}
    估值结论: {state.get('valuation_data', {}).get('verdict')}
    """
    res = llm.invoke(audit_prompt)
    report_parts = [
        f"### 审计结论：{res.verdict}",
        f"**逻辑漏洞：** {'，'.join(res.logic_flaws)}",
        f"**风控警告：** {res.risk_warning}",
        f"**交叉审查：** {res.cross_examination}",
    ]
    return {"audit_report": "\n\n".join(report_parts)}


def bull_analyst(state: AgentState):
    """第1轮：多头初始论点"""
    print(f"🟢 [辩论 R1] 多头分析师正在构建买入逻辑...")
    model_name = get_configured_model(state, "debate_model")
    llm = Config.get_llm(temperature=0.7, model_name=model_name, streaming=True)
    cleaned = state.get("cleaned_context", "")
    chain = BULL_PROMPT | llm
    res = chain.invoke({
        "ticker": state["ticker"],
        "user_concerns": state.get("user_concerns", ""),
        "cleaned_context": cleaned,
    })
    return {
        "bull_thesis": res.content,
        "debate_round": 1,
    }


def bear_counter_analyst(state: AgentState):
    """第2轮：空头阅读多头论点后进行针对性攻击"""
    print(f"🔴 [辩论 R2] 空头分析师正在针对多头进行反击...")
    model_name = get_configured_model(state, "debate_model")
    llm = Config.get_llm(temperature=0.6, model_name=model_name, streaming=True)
    chain = BEAR_COUNTER_PROMPT | llm
    res = chain.invoke({
        "ticker": state["ticker"],
        "user_concerns": state.get("user_concerns", ""),
        "bull_thesis": state.get("bull_thesis", "多头无观点"),
    })
    return {
        "bear_thesis": res.content,
        "debate_round": 2,
    }


def bull_rebuttal_analyst(state: AgentState):
    """第3轮：多头阅读空头攻击后进行防守辩护"""
    print(f"🟢 [辩论 R3] 多头分析师正在防守辩护...")
    model_name = get_configured_model(state, "debate_model")
    llm = Config.get_llm(temperature=0.7, model_name=model_name, streaming=True)
    chain = BULL_REBUTTAL_PROMPT | llm
    res = chain.invoke({
        "ticker": state["ticker"],
        "user_concerns": state.get("user_concerns", ""),
        "bull_thesis": state.get("bull_thesis", "多头无观点"),
        "bear_counter_argument": state.get("bear_thesis", "空头未回应"),
    })
    # 将反驳追加到 bull_thesis 中，保留完整辩论历史
    return {
        "bull_thesis": state.get("bull_thesis", "") + "\n\n---\n\n### 🛡️ 多头防守辩护（第2轮）\n" + res.content,
        "debate_round": 3,
    }


def chief_analyst_synthesis(state: AgentState):
    import datetime
    print("👔 [Node] 首席总监正在撰写最终研报...")
    model_name = get_configured_model(state, "chief_model")
    llm = Config.get_llm(temperature=0.4,streaming=True,model_name=model_name)

    # 使用 cleaned_context（已提炼），避免上下文爆炸
    context = state.get("cleaned_context", "无提炼数据")
    audit = state.get("audit_report", "无")
    var = state.get("var_data", {})
    adv = state.get("advanced_metrics", {})

    additional_info = (
        f"【补充信息】\n"
        f"- VaR 风险价值: {json.dumps(var, ensure_ascii=False)}\n"
        f"- 资本配置与相对强度: {json.dumps(adv, ensure_ascii=False)}\n"
        f"- 审计意见: {audit}"
    )

    prompt = CHIEF_PROMPT.format(
        ticker=state["ticker"],
        investment_horizon=state.get("investment_horizon", "未指定"),
        user_concerns=state.get("user_concerns", "无"),
        bull_thesis=state.get("bull_thesis", "多头无观点"),
        bear_thesis=state.get("bear_thesis", "空头无观点"),
        cleaned_context=context,
        additional_info=additional_info,
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
    workflow.add_node("intent_analyzer", intent_node)
    workflow.add_node("macro", macro_analyst)
    workflow.add_node("fundamental", fundamental_analyst)
    workflow.add_node("valuation", valuation_expert)
    workflow.add_node("sentiment", sentiment_analyst)
    workflow.add_node("context_cleaner", context_cleaner_node)
    workflow.add_node("error_handler", error_handler_node)
    workflow.add_node("bull_expert", bull_analyst)
    workflow.add_node("bear_counter", bear_counter_analyst)
    workflow.add_node("bull_rebuttal", bull_rebuttal_analyst)
    workflow.add_node("auditor", logic_auditor)
    workflow.add_node("chief", chief_analyst_synthesis)

    workflow.set_entry_point("intent_analyzer")

    # 第一阶段：并行数据采集（宏观、基本面、情绪）
    workflow.add_edge("intent_analyzer", "macro")
    workflow.add_edge("intent_analyzer", "fundamental")
    workflow.add_edge("intent_analyzer", "sentiment")

    # 第二阶段：valuation 依赖 macro
    workflow.add_edge("macro", "valuation")

    # 第三阶段：条件路由 — 数据正常则去噪→对抗辩论，数据不足则熔断
    workflow.add_conditional_edges(
        "valuation",
        debate_router,
        {
            "debate_start": "context_cleaner",
            "error_handler": "error_handler",
        }
    )

    # 第四阶段：两轮对抗辩论（顺序执行: R1多头→R2空头反击→R3多头辩护）
    workflow.add_edge("context_cleaner", "bull_expert")
    workflow.add_edge("bull_expert", "bear_counter")
    workflow.add_edge("bear_counter", "bull_rebuttal")
    workflow.add_edge("bull_rebuttal", "auditor")

    # 熔断路径：直接到首席（跳过辩论和审计）
    workflow.add_edge("error_handler", "chief")

    # 第五阶段：审计 → 首席终审
    workflow.add_edge("auditor", "chief")
    workflow.add_edge("chief", END)
    return workflow
