# server.py (Flask)
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import json
from src.agents.graph import build_graph

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    user_prompt = data.get("prompt", "")
    model_config = data.get("model_config", {})

    def generate():
        initial_state = {
            "user_prompt": user_prompt,
            "model_config": model_config,
            "ticker": "", "investment_horizon": "", "user_concerns": "", 
            "sector": "", "macro_data": None, "fundamental_data": None, "final_report": ""
        }
        app_graph = build_graph()
        try:
            for event in app_graph.stream(initial_state):
                for node_name, node_state in event.items():
                    # 业务逻辑：如果意图解析失败则中断
                    if node_name == "intent_analyzer":
                        ticker = node_state.get('ticker', 'UNKNOWN')
                        if ticker == 'UNKNOWN' or not ticker:
                            raise ValueError("无法识别股票代码，请检查输入。")

                    payload = json.dumps({"node": node_name, "state": node_state}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
            yield f"data: {json.dumps({'node': 'DONE'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'node': 'ERROR', 'message': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(port=5000, debug=True)