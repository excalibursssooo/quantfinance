# src/tools/finance_tool.py
import yfinance as yf
import pandas as pd
from retrying import retry
from langchain_core.tools import tool

@tool
def calculate_dcf(fcf: float, wacc: float, g: float, tg: float, net_debt: float, shares: int, reasoning: str = "模型根据财务数据执行了默认计算，未提供详细逻辑") -> float:
    """
    当自由现金流(FCF)为正且增长稳定时，调用此工具使用DCF模型计算每股内在价值。
    fcf: 最新的自由现金流
    wacc: 资本成本 (WACC)
    g: 永续增长率 (Terminal Growth Rate)
    tg: 未来5年的年均增长率 (5-Year Growth Rate)
    net_debt: 净债务
    shares: 总股本
    参数 reasoning: 请务必详细写出你为什么选择 DCF 模型，以及各个参数的推导逻辑！(重要)
    """
    try:
        ev = 0
        current_fcf = fcf
        
        for i in range(1, 6):
            current_fcf *= (1 + tg)
            ev += current_fcf / ((1 + wacc) ** i)
        
        if wacc <= g:
            return 0.0 
            
        terminal_value = (current_fcf * (1 + g)) / (wacc - g)
        ev += terminal_value / ((1 + wacc) ** 5)
        
        equity_value = ev - net_debt
        
        return round(max(equity_value / shares, 0), 2)
    except Exception as e:
        print(f"DCF Error: {e}")
        return 0.0

@tool
def calculate_ps_valuation(revenue: float, target_ps: float, shares: int, reasoning: str = "模型根据高增长特性执行了P/S计算，未提供详细逻辑") -> float:
    """
    当公司处于高增长、FCF为负的阶段(如SaaS/初创科技)，调用此工具使用市销率(P/S)计算每股价值。
    revenue: 最新的总营收
    target_ps: 目标市销率 (Target P/S Ratio)
    shares: 总股本
    参数 reasoning: 请务必详细写出你为什么弃用DCF而选择P/S，以及 target_ps 的设定逻辑！(重要)
    """
    try:
        target_market_cap = revenue * target_ps
        return round(max(target_market_cap / shares, 0), 2)
    except Exception:
        return 0.0

@tool
def calculate_ev_ebitda(ebitda: float, target_ev_ebitda: float, net_debt: float, shares: int, reasoning: str = "模型根据重资产特性执行了EV/EBITDA计算，未提供详细逻辑") -> float:
    """
    当公司重资产、折旧高(如制造业/车企/半导体)，调用此工具使用EV/EBITDA倍数计算每股价值。
    ebitda: 最新的息税折旧摊销前利润
    target_ev_ebitda: 目标 EV/EBITDA 倍数
    net_debt: 净债务
    shares: 总股本
    参数 reasoning: 请务必详细说明为何选择 EV/EBITDA 以及目标倍数的合理性！(重要)
    """
    try:
        ev = ebitda * target_ev_ebitda
        equity_val = ev - net_debt
        return round(max(equity_val / shares, 0), 2)
    except Exception:
        return 0.0


@retry(stop_max_attempt_number=3, wait_fixed=2000)
def fetch_ticker_safe(ticker: str):
    """带重试机制的基础数据抓取"""
    return yf.Ticker(ticker)


def get_detailed_finance(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 1. 抓取货币信息
        trading_currency = info.get("currency", "USD")          # 交易货币，比如 USD
        financial_currency = info.get("financialCurrency", "USD") # 财报货币，比如 CNY
        
        # 2. 汇率转换因子 (默认是 1.0)
        fx_rate = 1.0
        if trading_currency != financial_currency and financial_currency and trading_currency:
            try:
                # 构造外汇代码，例如 "CNYUSD=X"
                fx_ticker = f"{financial_currency}{trading_currency}=X"
                fx_info = yf.Ticker(fx_ticker).info
                # 获取汇率，比如 1 CNY = 0.14 USD
                fx_rate = fx_info.get("previousClose") or fx_info.get("regularMarketPrice") or 1.0
                print(f"💱 触发汇率转换: {financial_currency} -> {trading_currency}, 汇率: {fx_rate}")
            except Exception as e:
                print(f"⚠️ 汇率获取失败，默认使用 1.0: {e}")
        
        price = info.get("currentPrice") or info.get("previousClose") or 1.0
        market_cap_raw = info.get("marketCap", 0)
        shares = info.get("sharesOutstanding")
        if not shares and market_cap_raw > 0:
            shares = int(market_cap_raw / price)
            
        shares = shares or 1
        
        total_revenue = (info.get("totalRevenue") or 0) * fx_rate
        ebitda = (info.get("ebitda") or 0) * fx_rate
        enterprise_value = (info.get("enterpriseValue") or 0) * fx_rate
        
        real_market_cap = price * shares
        return {
            "basic": {
                "price": price,
                "revenue_growth": info.get("revenueGrowth"),
                "margin": info.get("profitMargins"),
                "enterprise_value": enterprise_value, 
                "shares_outstanding": shares,
                "total_revenue": total_revenue
            },
            "valuation_multiples": { 
                "pe_trailing": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "peg_ratio": info.get("pegRatio"),
                
                "ps_ratio": round(real_market_cap / total_revenue, 2) if total_revenue > 0 else None,
                "ev_ebitda": round(enterprise_value / ebitda, 2) if ebitda > 0 else None,
            },
            "fundamentals": {
                "roe": info.get("returnOnEquity"),
                "free_cashflow": (info.get("freeCashflow") or 0) * fx_rate, 
                "ebitda": ebitda,              
                "debt_to_equity": info.get("debtToEquity"),
                "total_cash": (info.get("totalCash") or 0) * fx_rate,
                "total_debt": (info.get("totalDebt") or 0) * fx_rate,
            }
        }
    except Exception as e:
        return {"error": f"数据抓取失败: {str(e)}"}

def get_macro_rates() -> dict:
    """
    实时抓取十年期美债收益率作为无风险利率 (Risk-Free Rate)
    修复硬编码问题：如果抓取失败，返回更合理的历史中枢，并附带错误标记。
    """
    try:
        tnx = fetch_ticker_safe("^TNX")
        price = tnx.history(period="5d")['Close'].iloc[-1]
        if pd.isna(price):
            raise ValueError("NaN value received")
        return {
            "risk_free_rate": round(price / 100, 4), 
            "status": "real-time"
        }
    except Exception as e:
        print(f"⚠️ [Finance Tool] 宏观利率获取失败，使用历史中枢: {e}")
        # 根据当前周期给出一个宏观中枢兜底，而非写死 0.042
        return {
            "risk_free_rate": 0.045, # 假设 4.5% 的中枢
            "status": "fallback_estimate"
        }

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


def get_advanced_metrics(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        cashflow = stock.cashflow
        
        # 1. 资本配置 (Capital Allocation)
        capex = "数据缺失"
        buybacks = "数据缺失"
        if not cashflow.empty:
            # 提取资本支出
            if "Capital Expenditure" in cashflow.index:
                capex = cashflow.loc["Capital Expenditure"].iloc[0]
            # 提取股票回购 (通常在现金流表中表现为负值，取绝对值)
            if "Repurchase Of Capital Stock" in cashflow.index:
                val = cashflow.loc["Repurchase Of Capital Stock"].iloc[0]
                buybacks = abs(val) if pd.notna(val) else "无回购"

        dividend_yield = info.get("dividendYield", 0)

        # 2. 相对大盘强度 (Relative Strength vs SPY)
        # 获取该股与标普500过去一年的收益率对比
        hist_stock = stock.history(period="1y")
        spy = yf.Ticker("SPY").history(period="1y")
        
        rs_1y = None
        stock_return = None
        spy_return = None
        if not hist_stock.empty and not spy.empty:
            stock_return = (hist_stock['Close'].iloc[-1] - hist_stock['Close'].iloc[0]) / hist_stock['Close'].iloc[0]
            spy_return = (spy['Close'].iloc[-1] - spy['Close'].iloc[0]) / spy['Close'].iloc[0]
            rs_1y = stock_return - spy_return

        # 3. 估值分位与护城河指标
        trailing_pe = info.get("trailingPE")
        forward_pe = info.get("forwardPE")
        # 如果 Forward PE 显著低于 Trailing PE，说明盈利预期在增长

        return {
            "capital_allocation": {
                "capex_latest": capex,
                "stock_buybacks_latest": buybacks,
                "dividend_yield": round(dividend_yield, 4) if dividend_yield else 0
            },
            "relative_strength": {
                "stock_1y_return": round(stock_return, 4) if stock_return else "N/A",
                "spy_1y_return": round(spy_return, 4) if spy_return else "N/A",
                "alpha_vs_spy": round(rs_1y, 4) if rs_1y else "N/A"
            },
            "valuation_context": {
                "trailing_pe": trailing_pe,
                "forward_pe": forward_pe,
                "price_to_book": info.get("priceToBook")
            }
        }
    except Exception as e:
        return {"error": f"高级指标抓取失败: {str(e)}"}