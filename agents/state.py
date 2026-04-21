from typing import TypedDict, Optional

class AgentState(TypedDict):
    ticker: str
    macro_data: Optional[str]
    fundamental_data: Optional[dict]
    advanced_metrics: Optional[dict]
    valuation_data: Optional[dict]
    sentiment_data: Optional[str]
    cleaned_context: Optional[str]
    final_report: str