from typing import TypedDict, Optional, Dict

class AgentState(TypedDict):
    ticker: str
    macro_data: Optional[str]
    fundamental_data: Optional[dict]
    valuation_data: Optional[dict]
    sentiment_data: Optional[str]
    # 新增：清洗后的结构化数据
    cleaned_context: Optional[str]
    final_report: str