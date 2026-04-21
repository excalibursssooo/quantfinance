# src/agents/state.py
from typing import TypedDict, Optional

class AgentState(TypedDict):
    user_prompt: str

    ticker: str
    investment_horizon: str
    user_concerns: str
    sector: str
    
    macro_data: Optional[str]
    fundamental_data: Optional[dict]
    advanced_metrics: Optional[dict]
    sentiment_data: Optional[str]
    
    bull_thesis: Optional[str]  
    bear_thesis: Optional[str]  
    
    cleaned_context: Optional[str]
    final_report: str