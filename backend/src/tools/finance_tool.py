# src/tools/finance_tool.py
import yfinance as yf
import pandas as pd
from retrying import retry
from langchain_core.tools import tool
from scipy.stats import norm
import numpy as np

@tool
def calculate_historical_var(ticker: str, confidence_level: float = 0.95) -> dict:
    """
    计算单日风险价值 (VaR - Value at Risk)，用于评估极端行情下的潜在最大亏损。
    ticker: 股票代码
    confidence_level: 置信度 (如 0.95 或 0.99)
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty:
            return {"error": "VaR Data Unavailable"}
        
        returns = hist['Close'].pct_change().dropna()
        mu = np.mean(returns)
        sigma = np.std(returns)
        
        # 参数法计算 VaR (返回的是 numpy.float64)
        var_value = norm.ppf(1 - confidence_level, mu, sigma)
        
        # 强制转换为原生 float
        return {
            "confidence_level": float(confidence_level),
            "daily_var_percentage": float(round(var_value * 100, 2)), 
            "annualized_volatility": float(round(sigma * np.sqrt(252) * 100, 2))
        }
    except Exception as e:
        return {"error": str(e)}
    
@tool
def calculate_dcf(fcf: float, wacc: float, g: float, tg: float, net_debt: float, shares: int, reasoning: str = "模型根据财务数据执行了默认计算，未提供详细逻辑") -> dict:
    """
    使用DCF模型计算每股内在价值，并输出灵敏度矩阵。
    注意，tg是长期增长率(如0.02)，g是初始增长率(如0.1)，wacc是折现率(如0.08)。
    """
    try:
        def compute_value(w, term_g):
            ev = 0
            current_fcf = float(fcf)
            for i in range(1, 6):
                # 修复 1：短期预测期应该用短期初始增长率 g
                current_fcf *= (1 + float(g)) 
                ev += current_fcf / ((1 + float(w)) ** i)
            
            if float(w) <= float(term_g):
                return 0.0 
            
            terminal_value = (current_fcf * (1 + float(term_g))) / (float(w) - float(term_g))
            ev += terminal_value / ((1 + float(w)) ** 5)
            equity_value = ev - float(net_debt)
            return float(round(max(equity_value / int(shares), 0), 2))

        # 修复 2：计算基准价值和灵敏度时，传入的终端增长率应该是 tg
        base_value = compute_value(wacc, tg) 
        
        sensitivity_matrix = {
            "wacc_minus_1_pct": compute_value(wacc - 0.01, tg),
            "wacc_plus_1_pct": compute_value(wacc + 0.01, tg),
            # 这里的灵敏度波动可以只针对短期增长 g 做调整，或者另外写逻辑
            "tg_minus_1_pct": compute_value(wacc, max(0, tg - 0.01)),
            "tg_plus_1_pct": compute_value(wacc, tg + 0.01),
        }
        
        return {
            "base_intrinsic_value": base_value,
            "sensitivity_matrix": sensitivity_matrix,
            "reasoning": reasoning
        }
    except Exception as e:
        print(f"DCF Error: {e}")
        return {"base_intrinsic_value": 0.0, "reasoning": "DCF Error"}
    

@tool
def calculate_ps_valuation(revenue: float, target_ps: float, shares: int, reasoning: str = "模型根据高增长特性执行了P/S计算，未提供详细逻辑") -> float:
    """
    当公司处于高增长、FCF为负的阶段(如SaaS/初创科技)，调用此工具使用市销率(P/S)计算每股价值。
    """
    try:
        target_market_cap = float(revenue) * float(target_ps)
        return float(round(max(target_market_cap / int(shares), 0), 2))
    except Exception:
        return 0.0

@tool
def calculate_ev_ebitda(ebitda: float, target_ev_ebitda: float, net_debt: float, shares: int, reasoning: str = "模型根据重资产特性执行了EV/EBITDA计算，未提供详细逻辑") -> float:
    """
    当公司重资产、折旧高(如制造业/车企/半导体)，调用此工具使用EV/EBITDA倍数计算每股价值。
    """
    try:
        ev = float(ebitda) * float(target_ev_ebitda)
        equity_val = ev - float(net_debt)
        return float(round(max(equity_val / int(shares), 0), 2))
    except Exception:
        return 0.0


@retry(stop_max_attempt_number=3, wait_fixed=2000)
def fetch_ticker_safe(ticker: str):
    """带重试机制的基础数据抓取"""
    return yf.Ticker(ticker)


def get_macro_rates() -> dict:
    try:
        tnx = fetch_ticker_safe("^TNX")
        # 从 pandas 取出的标量是 numpy.float64，必须用 float() 包裹
        price = float(tnx.history(period="5d")['Close'].iloc[-1])
        if pd.isna(price):
            raise ValueError("NaN value received")
        return {
            "risk_free_rate": float(round(price / 100, 4)), 
            "status": "real-time"
        }
    except Exception as e:
        print(f"⚠️ [Finance Tool] 宏观利率获取失败，使用历史中枢: {e}")
        return {
            "risk_free_rate": 0.045,
            "status": "fallback_estimate"
        }

