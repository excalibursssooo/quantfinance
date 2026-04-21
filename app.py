# app.py
import streamlit as st
import time
from agents.graph import build_graph

st.set_page_config(page_title="WallStreet Oracle", page_icon="🤖", layout="wide")

# ================= 侧边栏：配置与控制 =================
with st.sidebar:
    st.header("⚙️ 系统引擎配置")
    st.markdown("为不同的 Agent 分配最合适的模型以优化成本与性能。")
    
    if "model_config" not in st.session_state:
        st.session_state.model_config = {}

    st.session_state.model_config["intent_model"] = st.selectbox(
        "🧠 意图解析 & 数据汇总", 
        ["qwen3.6-flash", "qwen3.5-35b-a3b", "deepseek-v3.2", "qwen3.5-flash"], index=0
    )
    
    st.session_state.model_config["debate_model"] = st.selectbox(
        "⚔️ 多空辩论专家", 
        ["qwen3.6-flash", "qwen3.5-35b-a3b", "deepseek-v3.2", "qwen3.5-flash"], index=0
    )
    
    st.session_state.model_config["chief_model"] = st.selectbox(
        "👑 首席分析师", 
        ["qwen3.6-flash", "qwen3.5-35b-a3b", "deepseek-v3.2", "qwen3.5-flash"], index=0
    )
    
    st.markdown("---")
    st.header("🛑 系统控制")
    # 随时可以点击的紧急停止/重置按钮
    if st.button("⏹️ 紧急停止 / 重置系统", type="primary", use_container_width=True):
        st.toast("已强制终止当前工作流并重置系统！", icon="🛑")
        time.sleep(0.5)
        st.rerun() # 强制刷新页面，打断所有正在运行的后端 Python 进程

# ================= 主界面 =================
st.title("📈 WallStreet-Oracle 智能投研系统")

user_prompt = st.text_area(
    "告诉分析师你想看什么 (支持自然语言):", 
    value="帮我看看特斯拉(TSLA)还能买吗？打算拿一年，主要担心它的降价伤利润，以及FSD到底行不行。",
    height=80
)

if st.button("🚀 下达调研指令", use_container_width=True):
    if not user_prompt.strip():
        st.warning("⚠️ 请输入调研指令！")
        st.stop()

    initial_state = {
        "user_prompt": user_prompt,
        "ticker": "", "investment_horizon": "", "user_concerns": "", "sector": "",
        "macro_data": None, "fundamental_data": None, "final_report": ""
    }

    # ================= 动态可视化指挥室 =================
    st.markdown("### 📊 投研指挥室实时监控")
    
    intent_box = st.empty()
    progress_bar = st.progress(0, text="等待指令下达...")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🟢 多头阵地 (Bull)")
        bull_box = st.empty()
    with col2:
        st.markdown("#### 🔴 空头阵地 (Bear)")
        bear_box = st.empty()
        
    st.markdown("---")
    st.markdown("#### 👑 首席分析师决断")
    chief_box = st.empty()

    app_graph = build_graph()

    # ================= 核心：加入全局错误熔断 =================
    try:
        # LangGraph 的 stream 方法如果在任何 Node 内部抛出 Exception，都会中断并抛到这里
        for event in app_graph.stream(initial_state):
            for node_name, node_state in event.items():
                
                if node_name == "intent_analyzer":
                    ticker = node_state.get('ticker', 'UNKNOWN')
                    if ticker == 'UNKNOWN' or not ticker:
                        # 主动抛错，触发你在 app.py 中写的 try...except 熔断
                        raise ValueError("意图解析失败：未能从您的输入中识别到有效的股票代码。")
                    progress_bar.progress(10, text="🧠 意图解析完成，正在分发指令...")
                    with intent_box.container():
                        st.success(f"**🎯 锁定标的:** {node_state.get('ticker', '未知')} | **⏱️ 周期:** {node_state.get('investment_horizon', '未知')} \n\n **🔍 核心关切:** {node_state.get('user_concerns', '无')}")
                
                elif node_name in ["macro", "fundamental", "sentiment", "valuation"]:
                    progress_bar.progress(40, text="📡 正在并联拉取财报数据与进行估值推演...")
                    
                elif node_name == "bull_expert":
                    progress_bar.progress(70, text="🟢 多头分析师已提交报告...")
                    with bull_box.container():
                        st.info(node_state.get("bull_thesis", "多头分析中..."))
                        
                elif node_name == "bear_expert":
                    progress_bar.progress(70, text="🔴 空头分析师已提交报告...")
                    with bear_box.container():
                        st.error(node_state.get("bear_thesis", "空头分析中..."))
                        
                elif node_name == "chief":
                    progress_bar.progress(100, text="✅ 首席分析师审阅完毕，报告生成！")
                    with chief_box.container():
                        st.markdown(node_state.get("final_report", ""))

    except Exception as e:
        # 熔断机制触发：捕获任何图谱节点中的错误并优雅展示
        progress_bar.progress(100, text="❌ 任务因异常终止")
        st.error(f"**系统触发熔断保护。**\n\n在执行调研时发生错误：`{str(e)}`")
        st.warning("建议检查：1. 股票代码是否有效；2. 大模型 API 余额/网络是否正常；3. 点击侧边栏【紧急停止】后重试。")