# main.py
import sys
from agents.graph import build_graph

def main():
    print("🤖 WallStreet-Oracle 系统初始化中...")
    
    # 允许通过命令行参数传入 Ticker，例如：python main.py TSLA
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "NVDA"
    
    print(f"🎯 目标标的: {ticker}\n")
    
    app = build_graph()
    
    initial_state = {
        "ticker": ticker,
        "stock_data": {},
        "news_summary": "",
        "final_report": ""
    }
    
    # 执行流
    result = app.invoke(initial_state)
    
    # 打印最终结果
    print("\n" + "="*50)
    print(result["final_report"])
    print("="*50)

if __name__ == "__main__":
    main()