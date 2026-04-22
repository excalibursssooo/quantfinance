from langchain_community.tools.tavily_search import TavilySearchResults

def get_real_market_data(ticker: str) -> str:
    search = TavilySearchResults(max_results=3)
    # 结合分析师建议的搜索关键词
    query = f"{ticker} stock analysis 2026 Fed interest rate impact macro news"
    results = search.invoke(query)
    
    # 简单清洗结果
    summary = "\n".join([f"- {r['content']}" for r in results])
    return summary