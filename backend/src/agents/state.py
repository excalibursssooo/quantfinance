from typing import TypedDict, Optional, Dict, List
from pydantic import BaseModel, Field


class AuditReport(BaseModel):
    """结构化审计输出，确保 LLM 输出 100% 可解析"""
    verdict: str = Field(description="审计结论：合理/有瑕疵/严重缺陷")
    logic_flaws: List[str] = Field(description="发现的逻辑漏洞列表")
    risk_warning: str = Field(description="风控警告")
    cross_examination: str = Field(description="交叉审查意见（3句话以内）")


class CleanedContext(BaseModel):
    """上下文去噪提炼后的结构化输出"""
    macro_summary: str = Field(description="宏观环境要点，不超过150词")
    fundamental_snapshot: str = Field(description="基本面核心数据提炼")
    sentiment_assessment: str = Field(description="情绪面判断：乐观/中性/悲观")
    valuation_summary: str = Field(description="估值结论，方法+核心参数")
    key_catalysts: list[str] = Field(description="关键催化剂")
    key_risks: list[str] = Field(description="关键风险")
    investment_conclusion_short: str = Field(description="一句话投资结论")


class DebateRecord(BaseModel):
    """辩论轮次记录"""
    round: int = Field(description="轮次")
    role: str = Field(description="bull/bear")
    thesis: str = Field(description="本轮论点内容")


class AgentState(TypedDict):
    user_prompt: str
    model_config: Dict[str, str]

    ticker: str
    investment_horizon: str
    user_concerns: str
    sector: str

    macro_data: Optional[str]
    fundamental_data: Optional[dict]
    advanced_metrics: Optional[dict]
    sentiment_data: Optional[str]
    valuation_data: Optional[dict]

    var_data: Optional[dict] # 新增：VaR 风险价值数据

    bull_thesis: Optional[str]
    bear_thesis: Optional[str]

    audit_report: Optional[str]
    cleaned_context: Optional[str]

    # 辩论跟踪
    debate_round: int
    debate_history: list

    # 熔断与降级
    _degraded: Optional[bool]
    _skip_valuation: Optional[bool]
    _data_quality: Optional[float]
    _data_warnings: Optional[list]
    _data_source: Optional[str]
    _valuation_assumptions: Optional[dict]
    _valuation_multiples: Optional[dict]

    final_report: str
