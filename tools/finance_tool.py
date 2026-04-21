# src/tools/finance_tool.py
import yfinance as yf

def get_detailed_finance(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "basic": {
                "price": info.get("currentPrice"),
                "revenue_growth": info.get("revenueGrowth"),
                "margin": info.get("profitMargins"),
            },
            "valuation": {
                "pe_trailing": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "peg_ratio": info.get("pegRatio"),
            },
            "fundamentals": {
                "roe": info.get("returnOnEquity"),
                "free_cashflow": info.get("freeCashflow"),
                "debt_to_equity": info.get("debtToEquity"),
            }
        }
    except Exception as e:
        return {"error": f"财务数据抓取失败: {str(e)}"}

def get_macro_rates() -> dict:
    """实时抓取十年期美债收益率作为无风险利率 (Risk-Free Rate)"""
    try:
        tnx = yf.Ticker("^TNX")
        # ^TNX 的报价是百分比，如 4.25 表示 4.25%
        rf_rate = tnx.fast_info.last_price / 100.0 
        return {"risk_free_rate": round(rf_rate, 4)}
    except:
        return {"risk_free_rate": None}

def get_growth_metrics(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    info = stock.info
    financials = stock.financials
    
    recent_growth = None
    if "Total Revenue" in financials.index and len(financials.columns) > 1:
        revs = financials.loc["Total Revenue"]
        if revs.iloc[1] and revs.iloc[1] > 0:
            recent_growth = (revs.iloc[0] - revs.iloc[1]) / revs.iloc[1]
            
    return {
        "historic_revenue_growth": round(recent_growth, 4) if recent_growth else "数据缺失",
        "analyst_growth_estimate": info.get("earningsQuarterlyGrowth"),
        "beta": info.get("beta"), # 提取真实 Beta 供计算 WACC
        "industry": info.get("industry"),
        "sector": info.get("sector")
    }

def calculate_intrinsic_dcf(ticker: str, growth_rate: float, terminal_growth: float, discount_rate: float) -> dict:
    """纯逻辑计算器，不带有任何默认预设值"""
    stock = yf.Ticker(ticker)
    cashflow = stock.cashflow
    
    if "Free Cash Flow" not in cashflow.index:
        return {"error": "无法获取最新 FCF 数据，无法计算 DCF"}
        
    current_fcf = cashflow.loc["Free Cash Flow"].iloc[0]
    shares = stock.info.get("sharesOutstanding")
    
    if not current_fcf or not shares or current_fcf <= 0:
        return {"error": "现金流为负或股本数据缺失，DCF 失效"}
    
    fcf_list = []
    pv_fcf = 0
    for t in range(1, 6):
        future_fcf = current_fcf * ((1 + growth_rate) ** t)
        pv = future_fcf / ((1 + discount_rate) ** t)
        fcf_list.append(pv)
        pv_fcf += pv
        
    final_fcf = current_fcf * ((1 + growth_rate) ** 5)
    tv = (final_fcf * (1 + terminal_growth)) / (discount_rate - terminal_growth)
    pv_tv = tv / ((1 + discount_rate) ** 5)
    
    intrinsic_value = pv_fcf + pv_tv
    value_per_share = intrinsic_value / shares
    current_price = stock.info.get("currentPrice", 0)
    
    margin_of_safety = 0
    if value_per_share > 0:
        margin_of_safety = round((1 - current_price / value_per_share) * 100, 2)
    
    return {
        "applied_g": growth_rate,
        "applied_tg": terminal_growth,
        "applied_wacc": discount_rate,
        "intrinsic_value_per_share": round(value_per_share, 2),
        "current_price": current_price,
        "margin_of_safety_percent": margin_of_safety
    }