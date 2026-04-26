# src/tools/data_repository.py
"""
数据仓库层 (Repository Pattern)
数据源降级策略: FMP -> yFinance -> Error
"""
import os
import json
import httpx
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

FMP_API_KEY = os.getenv("FMP_API_KEY")
FMP_BASE = "https://financialmodelingprep.com/stable"

# ====== Pydantic 数据模型 ======

class FinancialData(BaseModel):
    price: float = 0.0
    shares_outstanding: int = 1
    total_revenue: float = 0.0
    ebitda: float = 0.0
    free_cashflow: float = 0.0
    total_cash: float = 0.0
    total_debt: float = 0.0
    net_debt: float = 0.0
    enterprise_value: float = 0.0
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    profit_margin: Optional[float] = None
    revenue_growth: Optional[float] = None

class ValuationMultiples(BaseModel):
    pe_trailing: Optional[float] = None
    forward_pe: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    peg_ratio: Optional[float] = None

class AdvancedMetricsData(BaseModel):
    capex: Optional[float] = None
    stock_buybacks: Optional[float] = None
    dividend_yield: float = 0.0
    stock_1y_return: Optional[float] = None
    spy_1y_return: Optional[float] = None
    alpha_vs_spy: Optional[float] = None
    beta: Optional[float] = None

class ValuationAssumptions(BaseModel):
    historic_revenue_cagr_5y: Optional[float] = None
    analyst_growth_next_year: Optional[float] = None
    analyst_growth_next_5y: Optional[float] = None
    risk_free_rate: float = 0.045
    beta: Optional[float] = None
    equity_risk_premium: float = 0.055
    cost_of_equity: Optional[float] = None
    cost_of_debt: Optional[float] = None
    wacc: Optional[float] = None
    industry_pe: Optional[float] = None
    industry_ev_ebitda: Optional[float] = None
    industry_ps: Optional[float] = None
    fmp_dcf_value: Optional[float] = None

class CompanyProfile(BaseModel):
    ticker: str
    sector: str = "Unknown"
    industry: str = "Unknown"
    market_cap: float = 0.0

class CollectedData(BaseModel):
    profile: Optional[CompanyProfile] = None
    financials: Optional[FinancialData] = None
    multiples: Optional[ValuationMultiples] = None
    advanced: Optional[AdvancedMetricsData] = None
    assumptions: Optional[ValuationAssumptions] = None
    data_quality: Optional[float] = 0.0
    source: str = "none"
    warnings: list[str] = []


class FinanceDataRepository:
    """统一数据仓库，自动降级: FMP -> yFinance"""

    def __init__(self):
        self.fmp_api_key = FMP_API_KEY

    # ========== FMP 层 ==========

    def _fmp_get(self, endpoint: str, ticker: str, extra: str = "") -> Optional[list]:
        """FMP stable API GET 请求，自动拼接 symbol 和 apikey"""
        if not self.fmp_api_key:
            return None
        url = f"{FMP_BASE}/{endpoint}?symbol={ticker}&apikey={self.fmp_api_key}{extra}"
        try:
            resp = httpx.get(url, timeout=15.0)
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, list) else [data]
            resp_text = resp.text[:200] if resp.text else ""
            print(f"[FMP] HTTP {resp.status_code} for {endpoint}/{ticker}: {resp_text}")
            return None
        except Exception as e:
            print(f"[FMP] 请求失败 {endpoint}/{ticker}: {e}")
            return None

    def _fmp_get_financials(self, ticker: str) -> Optional[FinancialData]:
        inc = self._fmp_get("income-statement", ticker, "&limit=1")
        bal = self._fmp_get("balance-sheet-statement", ticker, "&limit=1")
        cf = self._fmp_get("cash-flow-statement", ticker, "&limit=1")
        metrics = self._fmp_get("key-metrics", ticker, "&limit=1")
        if not inc:
            return None

        inc_data = inc[0]
        revenue = float(inc_data.get("revenue", 0))
        ebitda = float(inc_data.get("ebitda", 0))
        rd_expenses = float(inc_data.get("researchAndDevelopmentExpenses", 0))

        total_cash = 0.0
        total_debt = 0.0
        if bal:
            total_cash = float(bal[0].get("cashAndShortTermInvestments", 0))
            total_debt = float(bal[0].get("totalDebt", 0))

        fcf = 0.0
        if cf:
            fcf = float(cf[0].get("freeCashFlow", 0))

        roe = None
        debt_to_equity = None
        revenue_growth = None
        if metrics:
            roe = float(metrics[0]["roe"]) if metrics[0].get("roe") else None
            debt_to_equity = float(metrics[0]["debtToEquity"]) if metrics[0].get("debtToEquity") else None
            revenue_growth = float(metrics[0]["revenueGrowth"]) if metrics[0].get("revenueGrowth") else None

        price = 0.0
        shares = 1
        ev = 0.0
        profile = self._fmp_get("profile", ticker)
        if profile:
            price = float(profile[0].get("price", 0))
            shares = int(profile[0].get("sharesOutstanding", 1))
            ev = float(profile[0].get("enterpriseValue", 0))

        return FinancialData(
            price=price,
            shares_outstanding=shares,
            total_revenue=revenue,
            ebitda=ebitda,
            free_cashflow=fcf,
            total_cash=total_cash,
            total_debt=total_debt,
            net_debt=total_debt - total_cash,
            enterprise_value=ev,
            roe=roe,
            debt_to_equity=debt_to_equity,
            profit_margin=float(inc_data.get("netMargin", 0)) if inc_data.get("netMargin") else None,
            revenue_growth=revenue_growth,
        )

    def _fmp_get_multiples(self, ticker: str) -> Optional[ValuationMultiples]:
        ratios = self._fmp_get("ratios", ticker, "&limit=1")
        if not ratios:
            return None
        r = ratios[0]
        return ValuationMultiples(
            pe_trailing=float(r["priceEarningsRatio"]) if r.get("priceEarningsRatio") else None,
            forward_pe=None,
            pb_ratio=float(r["priceToBookRatio"]) if r.get("priceToBookRatio") else None,
            ps_ratio=float(r["priceToSalesRatio"]) if r.get("priceToSalesRatio") else None,
            ev_ebitda=None,
            peg_ratio=float(r["pegRatio"]) if r.get("pegRatio") else None,
        )

    def _fmp_get_advanced(self, ticker: str) -> Optional[AdvancedMetricsData]:
        cf = self._fmp_get("cash-flow-statement", ticker, "&limit=1")
        growth = self._fmp_get("financial-growth", ticker, "&limit=1")
        profile = self._fmp_get("profile", ticker)

        capex = None
        buybacks = None
        if cf:
            capex = float(cf[0]["capitalExpenditure"]) if cf[0].get("capitalExpenditure") else None
            buybacks = float(abs(cf[0]["commonStockRepurchased"])) if cf[0].get("commonStockRepurchased") else None

        beta = None
        dividend_yield = 0.0
        if profile:
            beta = float(profile[0]["beta"]) if profile[0].get("beta") else None
            dividend_yield = float(profile[0]["lastDivDividendYield"]) if profile[0].get("lastDivDividendYield") and profile[0]["lastDivDividendYield"] > 0 else 0.0

        stock_return = None
        spy_return = None
        alpha = None
        if growth:
            for g in growth:
                if g.get("symbol") == ticker:
                    stock_return = float(g["stockPriceChange1Y"]) if g.get("stockPriceChange1Y") else None
                    break

        return AdvancedMetricsData(
            capex=capex,
            stock_buybacks=buybacks,
            dividend_yield=dividend_yield,
            stock_1y_return=stock_return,
            spy_1y_return=spy_return,
            alpha_vs_spy=alpha,
            beta=beta,
        )

    def _fmp_get_assumptions(self, ticker: str) -> Optional[ValuationAssumptions]:
        growth = self._fmp_get("financial-growth", ticker, "&limit=5")
        estimates = self._fmp_get("analyst-estimates", ticker, "&period=annual&page=0&limit=10")
        profile = self._fmp_get("profile", ticker)
        dcf_data = self._fmp_get("discounted-cash-flow", ticker)

        historic_cagr = None
        if growth and len(growth) >= 2:
            revs = [float(g.get("revenueGrowth", 0)) for g in growth if g.get("revenueGrowth")]
            if revs:
                historic_cagr = float(np.mean(revs))

        analyst_growth_ny = None
        analyst_growth_5y = None
        if estimates:
            # 如果有至少2期（当前FY + 下FY），用 revenueAvg 计算隐含增长率
            revenue_avgs = [e.get("revenueAvg") for e in estimates if e.get("revenueAvg")]
            if len(revenue_avgs) >= 2:
                analyst_growth_ny = (revenue_avgs[0] - revenue_avgs[1]) / revenue_avgs[1]
            elif revenue_avgs:
                analyst_growth_ny = revenue_avgs[0]

        beta = None
        if profile:
            beta = float(profile[0]["beta"]) if profile[0].get("beta") else None

        fmp_dcf = None
        if dcf_data:
            fmp_dcf = float(dcf_data[0]["dcf"]) if dcf_data[0].get("dcf") else None

        rf = self._get_risk_free_rate()

        erp = self._get_equity_risk_premium()
        cost_of_equity = (rf + beta * erp) if beta is not None else None
        wacc = cost_of_equity

        return ValuationAssumptions(
            historic_revenue_cagr_5y=historic_cagr,
            analyst_growth_next_year=analyst_growth_ny,
            analyst_growth_next_5y=analyst_growth_5y,
            risk_free_rate=rf,
            beta=beta,
            equity_risk_premium=erp,
            cost_of_equity=round(cost_of_equity, 4) if cost_of_equity else None,
            wacc=round(wacc, 4) if wacc else None,
            fmp_dcf_value=fmp_dcf,
        )

    # ========== yFinance 兜底 ==========

    def _yf_get_financials(self, ticker: str) -> Optional[FinancialData]:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = float(info.get("currentPrice") or info.get("previousClose") or 0)
            shares = int(info.get("sharesOutstanding", 1))
            total_revenue = float(info.get("totalRevenue", 0) or 0)
            ebitda = float(info.get("ebitda", 0) or 0)
            fcf = float(info.get("freeCashflow", 0) or 0)
            total_cash = float(info.get("totalCash", 0) or 0)
            total_debt = float(info.get("totalDebt", 0) or 0)
            ev = float(info.get("enterpriseValue", 0) or 0)
            roe = float(info["returnOnEquity"]) if info.get("returnOnEquity") else None
            dte = float(info["debtToEquity"]) if info.get("debtToEquity") else None
            margin = float(info["profitMargins"]) if info.get("profitMargins") else None
            rev_growth = float(info["revenueGrowth"]) if info.get("revenueGrowth") else None
            return FinancialData(
                price=price, shares_outstanding=shares,
                total_revenue=total_revenue, ebitda=ebitda,
                free_cashflow=fcf, total_cash=total_cash, total_debt=total_debt,
                net_debt=total_debt - total_cash, enterprise_value=ev,
                roe=roe, debt_to_equity=dte, profit_margin=margin,
                revenue_growth=rev_growth,
            )
        except Exception as e:
            print(f"[YF] 财务数据获取失败: {e}")
            return None

    def _yf_get_multiples(self, ticker: str) -> Optional[ValuationMultiples]:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            ev = float(info.get("enterpriseValue", 0) or 0)
            ebitda = float(info.get("ebitda", 0) or 0)
            price = float(info.get("currentPrice") or info.get("previousClose") or 1)
            shares = int(info.get("sharesOutstanding", 1))
            revenue = float(info.get("totalRevenue", 0) or 0)
            market_cap = price * shares

            return ValuationMultiples(
                pe_trailing=float(info["trailingPE"]) if info.get("trailingPE") else None,
                forward_pe=float(info["forwardPE"]) if info.get("forwardPE") else None,
                pb_ratio=float(info["priceToBook"]) if info.get("priceToBook") else None,
                ps_ratio=round(market_cap / revenue, 2) if revenue > 0 else None,
                ev_ebitda=round(ev / ebitda, 2) if ebitda > 0 else None,
                peg_ratio=float(info["pegRatio"]) if info.get("pegRatio") else None,
            )
        except Exception as e:
            print(f"[YF] 倍数数据获取失败: {e}")
            return None

    def _yf_get_advanced(self, ticker: str) -> Optional[AdvancedMetricsData]:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            cashflow = stock.cashflow
            capex = None
            buybacks = None
            if not cashflow.empty:
                if "Capital Expenditure" in cashflow.index:
                    val = cashflow.loc["Capital Expenditure"].iloc[0]
                    if pd.notna(val): capex = float(val)
                if "Repurchase Of Capital Stock" in cashflow.index:
                    val = cashflow.loc["Repurchase Of Capital Stock"].iloc[0]
                    if pd.notna(val): buybacks = float(abs(val))
            dividend_yield = float(info.get("dividendYield", 0) or 0)

            hist = stock.history(period="1y")
            spy = yf.Ticker("SPY").history(period="1y")
            stock_return = None; spy_return = None; alpha = None
            if not hist.empty and not spy.empty:
                stock_return = float((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0])
                spy_return = float((spy['Close'].iloc[-1] - spy['Close'].iloc[0]) / spy['Close'].iloc[0])
                alpha = round(stock_return - spy_return, 4)

            beta = float(info.get("beta", 0)) if info.get("beta") else None

            return AdvancedMetricsData(
                capex=capex, stock_buybacks=buybacks,
                dividend_yield=round(dividend_yield, 4),
                stock_1y_return=round(stock_return, 4) if stock_return else None,
                spy_1y_return=round(spy_return, 4) if spy_return else None,
                alpha_vs_spy=alpha, beta=beta,
            )
        except Exception as e:
            print(f"[YF] 高级指标获取失败: {e}")
            return None

    def _yf_get_assumptions(self, ticker: str) -> Optional[ValuationAssumptions]:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            beta = float(info.get("beta", 0)) if info.get("beta") else None
            rf = self._get_risk_free_rate()
            erp = self._get_equity_risk_premium()
            cost_of_equity = (rf + beta * erp) if beta is not None else None
            return ValuationAssumptions(
                beta=beta, risk_free_rate=rf, equity_risk_premium=erp,
                cost_of_equity=round(cost_of_equity, 4) if cost_of_equity else None,
                wacc=round(cost_of_equity, 4) if cost_of_equity else None,
            )
        except Exception as e:
            print(f"[YF] 假设获取失败: {e}")
            return None

    def _yf_get_profile(self, ticker: str) -> Optional[CompanyProfile]:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return CompanyProfile(
                ticker=ticker,
                sector=info.get("sector", "Unknown"),
                industry=info.get("industry", "Unknown"),
                market_cap=float(info.get("marketCap", 0) or 0),
            )
        except Exception:
            return None

    # ========== 公共方法 ==========

    def _get_risk_free_rate(self) -> float:
        try:
            tnx = yf.Ticker("^TNX")
            price = float(tnx.history(period="5d")['Close'].iloc[-1])
            if not pd.isna(price) and price > 0:
                return round(price / 100, 4)
        except Exception:
            pass
        return 0.045

    def _get_equity_risk_premium(self) -> float:
        """通过 SP500 盈利收益率 - 无风险利率 推算隐含股权风险溢价 (ERP)"""
        try:
            spy = yf.Ticker("SPY")
            info = spy.info
            pe = info.get("trailingPE")
            rf = self._get_risk_free_rate()
            if pe and pe > 0 and rf > 0:
                earnings_yield = 1.0 / pe
                erp = earnings_yield - rf
                return round(max(min(erp, 0.10), 0.02), 4)
        except Exception:
            pass
        return 0.055

    def _merge_missing_from_fmp(self, ticker: str, fin: FinancialData, mult: ValuationMultiples) -> tuple[FinancialData, ValuationMultiples]:
        """用 FMP 补充 yFinance 中缺失的字段"""
        fmp_fin = self._fmp_get_financials(ticker)
        fmp_mult = self._fmp_get_multiples(ticker)
        fmp_assumptions = self._fmp_get_assumptions(ticker)

        if fmp_fin:
            if fin.roe is None: fin.roe = fmp_fin.roe
            if fin.debt_to_equity is None: fin.debt_to_equity = fmp_fin.debt_to_equity
            if fin.profit_margin is None: fin.profit_margin = fmp_fin.profit_margin
            if fin.revenue_growth is None: fin.revenue_growth = fmp_fin.revenue_growth
        if fmp_mult:
            if mult.pe_trailing is None: mult.pe_trailing = fmp_mult.pe_trailing
            if mult.ps_ratio is None: mult.ps_ratio = fmp_mult.ps_ratio
            if mult.pb_ratio is None: mult.pb_ratio = fmp_mult.pb_ratio
            if mult.ev_ebitda is None: mult.ev_ebitda = fmp_mult.ev_ebitda
        if fmp_assumptions:
            self._fmp_assumptions_cache = fmp_assumptions
        else:
            self._fmp_assumptions_cache = None
        return fin, mult

    def collect_all(self, ticker: str) -> CollectedData:
        """收集所有数据，自动降级: yFinance 优先 → FMP 补充缺失字段"""
        warnings = []
        profile = None; financials = None; multiples = None
        advanced = None; assumptions = None
        self._fmp_assumptions_cache = None
        source = "none"

        # 第1优先: yFinance
        try:
            yf_profile = self._yf_get_profile(ticker)
            yf_fin = self._yf_get_financials(ticker)
            if yf_fin:
                profile = yf_profile or CompanyProfile(ticker=ticker)
                financials = yf_fin
                multiples = self._yf_get_multiples(ticker) or ValuationMultiples()
                advanced = self._yf_get_advanced(ticker)
                assumptions = self._yf_get_assumptions(ticker)

                # 用 FMP 补充 yFinance 中缺失的字段（如 beta、roe、分析师预期等）
                if self.fmp_api_key:
                    financials, multiples = self._merge_missing_from_fmp(ticker, financials, multiples)
                    if assumptions and assumptions.beta is None:
                        fmp_a = self._fmp_get_assumptions(ticker)
                        if fmp_a:
                            assumptions.beta = fmp_a.beta
                            assumptions.cost_of_equity = fmp_a.cost_of_equity
                            assumptions.wacc = fmp_a.wacc
                            if assumptions.analyst_growth_next_year is None:
                                assumptions.analyst_growth_next_year = fmp_a.analyst_growth_next_year
                            if assumptions.historic_revenue_cagr_5y is None:
                                assumptions.historic_revenue_cagr_5y = fmp_a.historic_revenue_cagr_5y
                            if assumptions.fmp_dcf_value is None:
                                assumptions.fmp_dcf_value = fmp_a.fmp_dcf_value
                source = "yfinance"
            else:
                warnings.append("yFinance 数据为空")
        except Exception as e:
            warnings.append(f"yFinance 异常: {e}")

        # 第2优先: yFinance 失败时降级到 FMP
        if source == "none" and self.fmp_api_key:
            warnings.append("降级到 FMP")
            try:
                profile = CompanyProfile(ticker=ticker, sector="Unknown")
                fmp_profile = self._fmp_get("profile", ticker)
                if fmp_profile:
                    p = fmp_profile[0]
                    profile = CompanyProfile(
                        ticker=ticker, sector=p.get("sector", "Unknown"),
                        industry=p.get("industry", "Unknown"),
                        market_cap=float(p.get("marketCap", 0)),
                    )
                financials = self._fmp_get_financials(ticker)
                multiples = self._fmp_get_multiples(ticker)
                advanced = self._fmp_get_advanced(ticker)
                assumptions = self._fmp_get_assumptions(ticker)
                if financials:
                    source = "fmp"
                else:
                    warnings.append("FMP 也无数据")
                    source = "failed"
            except Exception as e:
                warnings.append(f"FMP 异常: {e}")
                source = "failed"

        if source == "none":
            source = "failed"

        # EV/EBITDA 兜底计算
        if multiples and financials and multiples.ev_ebitda is None:
            if financials.ebitda > 0 and financials.enterprise_value > 0:
                multiples.ev_ebitda = round(financials.enterprise_value / financials.ebitda, 2)

        score = self._calc_quality_score(financials, multiples, source)

        return CollectedData(
            profile=profile, financials=financials, multiples=multiples,
            advanced=advanced, assumptions=assumptions,
            data_quality=score, source=source, warnings=warnings,
        )

    def _calc_quality_score(self, financials: Optional[FinancialData], multiples: Optional[ValuationMultiples], source: str) -> float:
        if source == "failed":
            return 0.0
        if not financials:
            return 0.0

        present = 0
        total = 0

        critical = [
            financials.price > 0, financials.total_revenue > 0,
            financials.free_cashflow is not None,
            financials.shares_outstanding > 0,
        ]
        present += sum(1 for c in critical if c)
        total += len(critical)

        if multiples:
            important = [
                multiples.pe_trailing is not None,
                multiples.ps_ratio is not None,
                multiples.ev_ebitda is not None,
            ]
            present += sum(1 for c in important if c)
            total += len(important)

        score = present / total if total > 0 else 0.0
        if source == "fmp":
            score = min(score + 0.2, 1.0)

        return round(score, 2)
