import streamlit as st
import time
from agents.graph import build_graph

# 1. 页面基本配置
st.set_page_config(
    page_title="WallStreet Oracle | AI投研分析师",
    page_icon="🤖",
    layout="wide"
)

# 2. 侧边栏配置
with st.sidebar:
    st.title("⚙️ 控制面板")
    st.markdown("欢迎使用 **WallStreet-Oracle** 多智能体投研系统。")
    st.info("本系统将并行调度四个专家 Agent（宏观、基本面、估值、情绪）对标的进行深度剖析，并根据真实财务数据动态进行 DCF 估值推演。")
    st.markdown("---")
    st.caption("AI 生成内容，仅供参考，不构成投资建议。")

# 3. 主界面
st.title("📈 WallStreet-Oracle 智能投研系统")

# 用户输入区域
col1, col2 = st.columns([3, 1])
with col1:
    ticker_input = st.text_input("请输入美股代码 (如 AAPL, TSLA, NVDA):", value="AAPL")
with col2:
    st.write("") # 占位对齐
    st.write("")
    run_button = st.button("🚀 开始生成深度研报", use_container_width=True)

# 4. 触发运行逻辑
if run_button:
    ticker = ticker_input.strip().upper()
    if not ticker:
        st.warning("⚠️ 股票代码不能为空！")
    else:
        # 使用 Streamlit 的状态提示
        with st.status(f"正在调遣专家团队全方位调研 {ticker} ...", expanded=True) as status:
            st.write("🕵️‍♂️ 宏观专家、基本面专家、估值专家、情绪专家已就位...")
            st.write("📊 正在连接源数据并拉取 10 年期美债收益率...")
            
            # 初始化图
            app = build_graph()
            initial_state = {
                "ticker": ticker,
                "macro_data": None,
                "fundamental_data": None,
                "valuation_data": None,
                "sentiment_data": None,
                "cleaned_context": None,
                "final_report": ""
            }
            
            # 执行图流转
            start_time = time.time()
            try:
                result = app.invoke(initial_state)
                elapsed_time = round(time.time() - start_time, 2)
                status.update(label=f"✅ 研报生成完毕！(耗时 {elapsed_time} 秒)", state="complete", expanded=False)
                
                # 5. 展示结果
                st.divider()
                st.markdown(result["final_report"])
                
            except Exception as e:
                status.update(label="❌ 生成过程中发生错误", state="error")
                st.error(f"系统报错: {str(e)}")