# server.py (FastAPI)
import json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional

from src.agents.graph import build_graph

app = FastAPI(title="QuantFinance Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    prompt: str
    model_config: Optional[Dict[str, str]] = {}

# 白名单：我们前端 UI 上定义的所有有效节点
VALID_NODES = [
    "intent_analyzer", "macro", "fundamental", "valuation", 
    "bull_expert", "bear_expert", "chief"
]

@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    
    async def generate():
        initial_state = {
            "user_prompt": request.prompt,
            "model_config": request.model_config,
            "ticker": "", 
            "investment_horizon": "", 
            "user_concerns": "", 
            "sector": "", 
            "macro_data": None, 
            "fundamental_data": None, 
            "final_report": ""
        }
        
        app_graph = build_graph()
        
        try:
            async for event in app_graph.astream_events(initial_state, version="v2"):
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
                    if chunk and langgraph_node in ["bull_expert", "bear_expert", "chief"]:
                        payload = json.dumps({
                            "type": "token",
                            "node": langgraph_node,
                            "chunk": chunk
                        }, ensure_ascii=False)
                        yield f"data: {payload}\n\n"
                        
                # 2. 【节点完成状态拦截】(UI 图标点亮的核心)
                # 核心修复：只拦截我们白名单中的节点，并且确保是节点本体结束（name == node_name）
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
            yield f"data: {json.dumps({'node': 'DONE'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'node': 'ERROR', 'message': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=5000, reload=True)