# src/tools/news_tool.py
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from src.core.config import Config
from pydantic import BaseModel, Field

class SearchQuery(BaseModel):
    query: str = Field(description="为搜索引擎生成的精准英文搜索词")

def generate_dynamic_query(ticker: str, concerns: str, horizon: str, model_name: str) -> str:
    """内部辅助函数：使用极小参数的 LLM 动态生成搜索词"""
    llm = Config.get_llm(temperature=0.1, model_name=model_name).with_structured_output(SearchQuery)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个华尔街量化对冲基金的资料搜集员。你的任务是将用户的关切转化为一句最精准的搜索引擎查询词（Query）。必须输出英文，并以 JSON 格式返回。"), 
        ("user", "股票代码: {ticker}\n投资周期: {horizon}\n用户核心关切: {concerns}\n请生成并输出 JSON。")
    ])
    
    try:
        result = prompt | llm
        return result.invoke({"ticker": ticker, "horizon": horizon, "concerns": concerns}).query
    except Exception:
        # 兜底容错
        return f"{ticker} stock analysis {concerns} macro news"

def get_real_market_data(ticker: str, concerns: str = "general outlook", horizon: str = "long-term", model_name: str = "qwen3.5-flash-2026-02-23") -> str:
    """
    智能重构后的真实市场数据抓取工具
    """
    search = TavilySearchResults(max_results=4)
    
    # 1. 动态生成 Query
    smart_query = generate_dynamic_query(ticker, concerns, horizon, model_name)
    print(f"🔍 [News Tool] 执行智能搜索: {smart_query}")
    
    # 2. 执行搜索与容错
    try:
        results = search.invoke(smart_query)
        if not results:
            return "未检索到相关的近期市场新闻。"
            
        # 简单清洗并加入来源以增加可信度
        summary = "\n".join([f"- [{r.get('url', 'Source')}] {r.get('content', '')}" for r in results])
        return summary
    except Exception as e:
        print(f"⚠️ [News Tool] 搜索失败: {e}")
        return "外部搜索服务暂时不可用，请依赖历史知识库。"