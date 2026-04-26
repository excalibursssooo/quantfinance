# server.py (FastAPI)
import json
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
from src.tools.finance_tool import calculate_dcf, calculate_ps_valuation, calculate_ev_ebitda
# 核心：引入异步 Postgres 检查点
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.agents.graph import build_graph
from src.core.config import Config


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 启动时：此时 Uvicorn 的 event loop 已经启动，可以安全创建异步连接池
    async with AsyncConnectionPool(
        conninfo=Config.DATABASE_URL,
        max_size=20,
        kwargs={"autocommit": True}
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        # 自动创建 LangGraph 所需的系统表
        await checkpointer.setup()
        
        # 将 checkpointer 挂载到 app.state 上供全局路由使用
        app.state.checkpointer = checkpointer
        
        print("✅ 数据库连接池与 LangGraph 持久化记忆初始化成功！")
        yield
        
    # 2. 关闭时：随着 yield 结束退出 async with，连接池会自动优雅关闭

app = FastAPI(title="QuantFinance Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 建议开发阶段改为 "*" 防止跨域报错，或填入 "http://localhost:3000"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    prompt: str
    thread_id: str = "default_user" # 允许前端传入 thread_id 以恢复记忆
    expert_configs: Optional[Dict[str, str]] = {}

# 白名单：所有有效的 Agent 节点（包括对抗辩论）
VALID_NODES = [
    "intent_analyzer", "macro", "fundamental", "valuation",
    "context_cleaner", "error_handler",
    "bull_expert", "bear_counter", "bull_rebuttal",
    "auditor", "chief"
]


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    
    async def generate():
        # 给每个请求生成一个唯一的 thread_id，用于长效记忆和中断恢复
        config = {"configurable": {"thread_id": request.thread_id}}        
        initial_state = {
            "user_prompt": request.prompt,
            "model_config": request.expert_configs,
            "ticker": "", 
            "investment_horizon": "", 
            "user_concerns": "", 
            "sector": "", 
            "macro_data": None, 
            "fundamental_data": None, 
            "final_report": ""
        }
        checkpointer = app.state.checkpointer
        workflow = build_graph()        
        app_graph = workflow.compile(
            checkpointer=checkpointer,
            interrupt_before=["chief"] 
        )

        try:
            current_state = await app_graph.aget_state(config)
            
            # 👇 核心修复区：判断是【新对话】还是【微调后的恢复】
            if current_state.next:
                # 如果状态里的 next 不为空，说明目前图是被 interrupt_before 拦截住了（比如停在 chief 前）
                # 这时候我们是在恢复执行（Resume），因此传入 None 即可，不要传 initial_state！
                inputs = None
                print(f"🔄 检测到中断点，从 {current_state.next} 恢复执行...")

                # 在流开始前，主动把数据库里最新的估值数据提取出来，发给前端强制同步
                sync_payload = json.dumps({
                    "type": "state",
                    "node": "VALUATION_SYNC", # 伪造一个节点名，只要前端能匹配 type='state' 即可
                    "state": {
                        "valuation_data": current_state.values.get("valuation_data", {})
                    }
                }, ensure_ascii=False)
                yield f"data: {sync_payload}\n\n"
                
            else:
                # 如果 next 为空，说明这是一次全新的分析任务
                inputs = initial_state
                print(f"🚀 开启全新图执行...")
                
            # 将原来硬编码的 initial_state 改为上面判断好的 inputs
            async for event in app_graph.astream_events(inputs, version="v2", config=config):
                kind = event["event"]
                # 安全获取当前所属的节点名称
                langgraph_node = event.get("metadata", {}).get("langgraph_node", "")
                
                if kind == "on_chain_start" and langgraph_node in VALID_NODES and event["name"] == langgraph_node:
                    payload = json.dumps({
                        "type": "node_start",
                        "node": langgraph_node
                    }, ensure_ascii=False)
                    yield f"data: {payload}\n\n"

                # 1. 【流式 Token 拦截】(打字机效果)
                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    if chunk and langgraph_node in ["bull_expert", "bear_counter", "bull_rebuttal", "chief"]:
                        payload = json.dumps({
                            "type": "token",
                            "node": langgraph_node,
                            "chunk": chunk
                        }, ensure_ascii=False)
                        yield f"data: {payload}\n\n"
                        
                # 2. 【节点完成状态拦截】(UI 图标点亮的核心)
                elif kind == "on_chain_end" and langgraph_node in VALID_NODES and event["name"] == langgraph_node:
                    node_state = event["data"].get("output")
                    
                    if langgraph_node == "intent_analyzer" and isinstance(node_state, dict):
                        ticker = node_state.get('ticker', 'UNKNOWN')
                        if ticker == 'UNKNOWN' or not ticker:
                            raise ValueError("无法识别股票代码，请检查输入。")

                    # 如果节点有输出，推给前端点亮图标并更新数据
                    if node_state and isinstance(node_state, dict):
                        payload = json.dumps({
                            "type": "state", 
                            "node": langgraph_node, 
                            "state": node_state
                        }, ensure_ascii=False)
                        yield f"data: {payload}\n\n"

            # 3. 整体流程执行完毕
            final_state = await app_graph.aget_state(config)
            if final_state.next:
                # 如果 next 里有值（比如 'chief'），说明被 interrupt_before 拦截了
                yield f"data: {json.dumps({'type': 'pause', 'node': 'PAUSED'})}\n\n"
            else:
                # 真正全部执行完毕
                yield f"data: {json.dumps({'type': 'done', 'node': 'DONE'})}\n\n"
            
        except asyncio.exceptions.CancelledError:
            # 捕获由于前端断开连接引发的 CancelledError（也就是我们之前提到的背锅侠）
            print("⚠️ 前端连接已断开，正常取消流式传输。")
        except Exception as e:
            # 捕获未知异常，传给前端后立刻退出协程
            print(f"❌ 运行报错: {e}")
            yield f"data: {json.dumps({'type': 'error', 'node': 'ERROR', 'message': str(e)})}\n\n"
            return

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/api/feedback")
async def give_feedback(thread_id: str, feedback: dict):
    """
    根据用户微调的参数重新计算估值，并更新图状态。
    """
    checkpointer = app.state.checkpointer
    workflow = build_graph()
    app_graph = workflow.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    
    # 1. 获取当前状态和旧的估值数据
    current_state = await app_graph.aget_state(config)
    old_val_data = current_state.values.get("valuation_data", {})
    method = old_val_data.get("selected_method") # 判定是哪个工具算出来的
    
    # 2. 准备计算参数：将大模型原始生成的 key_metrics 与用户微调的反馈合并
    calc_args = old_val_data.get("key_metrics", {}).copy()
    calc_args.update(feedback) 
    
    new_intrinsic_value = 0.0
    sensitivity = {}

    # 3. 根据方法名动态调用对应的工具重新计算
    try:
        if method == "calculate_dcf":
            # DCF 返回结构包含基础值和矩阵
            res = calculate_dcf.invoke(calc_args)
            new_intrinsic_value = res.get("base_intrinsic_value", 0.0)
            sensitivity = res.get("sensitivity_matrix", {})
        elif method == "calculate_ps_valuation":
            new_intrinsic_value = calculate_ps_valuation.invoke(calc_args)
        elif method == "calculate_ev_ebitda":
            new_intrinsic_value = calculate_ev_ebitda.invoke(calc_args)
    except Exception as e:
        print(f"重新计算失败: {e}")

    # 4. 更新结论 (Verdict)
    current_price = old_val_data.get("current_price", 0.0)
    verdict = "估值合理"
    if current_price > 0:
        if new_intrinsic_value > current_price * 1.15:
            verdict = "严重低估 (强烈看多)"
        elif new_intrinsic_value < current_price * 0.85:
            verdict = "存在泡沫 (估值偏高)"

    # 5. 构造全新的 valuation_data
    new_valuation_data = {
        **old_val_data,
        "key_metrics": calc_args,
        "intrinsic_value": new_intrinsic_value,
        "verdict": verdict,
        "sensitivity": sensitivity if method == "calculate_dcf" else {}
    }

    # 6. 写入状态。关键点：as_node="auditor" 确保图从 chief 开始恢复
    await app_graph.aupdate_state(
        config, 
        {"valuation_data": new_valuation_data}, 
        as_node="auditor" 
    )
    
    return {"status": "resumed"}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)