'use client';

import React, { useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  Search, TrendingUp, TrendingDown, Activity, 
  Briefcase, Scale, BrainCircuit, Loader2, AlertCircle,
  SlidersHorizontal, DollarSign
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// --- 类型定义 ---
interface ValuationData {
  selected_method?: string;   // 路由选择的模型名称
  reasoning?: string;         // 模型选择逻辑
  intrinsic_value?: number;   // 估算出来的合理价格
  current_price?: number;     // 现价（由后端或前端补齐）
  verdict?: string;           // 结论：高估/合理/低估
  key_metrics?: Record<string, any>; // 动态参数对，如 {"G": "15%", "WACC": "8%"}
}

interface AgentState {
  ticker?: string;
  investment_horizon?: string;
  user_concerns?: string;
  sector?: string;
  valuation_data?: ValuationData;
  bull_thesis?: string;
  bear_thesis?: string;
  final_report?: string;
}

const STAGE_GROUPS = [
  [{ id: 'intent_analyzer', label: '意图解析', icon: BrainCircuit }], 
  
  [ 
    { id: 'macro', label: '宏观调研', icon: Activity },
    { id: 'fundamental', label: '基本面分析', icon: Briefcase }
  ],
  
  [{ id: 'valuation', label: '智能估值', icon: DollarSign, color: 'text-amber-400' }],
  
  [ 
    { id: 'bull_expert', label: '多头建构', icon: TrendingUp, color: 'text-emerald-500' },
    { id: 'bear_expert', label: '空头建构', icon: TrendingDown, color: 'text-rose-500' }
  ],
  
  [{ id: 'chief', label: '首席总管', icon: Scale, color: 'text-blue-400' }] 
];

// 可选的模型列表
const AVAILABLE_MODELS = [
  { id: 'qwen3.5-flash', name: 'Qwen 3.5 Flash (默认/高速)' },
  { id: 'qwen3.6-flash', name: 'Qwen 3.6 Flash (深度推理)' },
  { id: 'deepseek-v3.2', name: 'DeepSeek V3.2 (高性价比)' }
];

export default function FinanceTerminal() {
  const [prompt, setPrompt] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // --- 新增：模型配置状态 ---
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [currentNode, setCurrentNode] = useState<string>('');
  const [showConfig, setShowConfig] = useState(false);
  const [debateModel, setDebateModel] = useState('qwen3.5-flash');
  const [chiefModel, setChiefModel] = useState('qwen3.5-flash');
  
  // 状态流转追踪
  const [activeNodes, setActiveNodes] = useState<string[]>([]);
  const [completedNodes, setCompletedNodes] = useState<string[]>([]);
  const [agentData, setAgentData] = useState<AgentState>({});

  // 滚动锚点
  const resultsRef = useRef<HTMLDivElement>(null);

const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setIsAnalyzing(true);
    setError(null);
    setActiveNodes([]);
    setCompletedNodes([]);
    setAgentData({});

    try {
      const response = await fetch('http://localhost:5000/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          prompt, 
          // --- 新增：将前端的配置注入到 payload 中 ---
          model_config: { 
            debate_model: debateModel, 
            chief_model: chiefModel 
          } 
        }),
      });

      if (!response.body) throw new Error('流获取失败');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      
      // 🛡️ 引入 buffer 解决流式截断问题
      let buffer = '';

      while (true) {
        // stream: true 保证多字节字符不会乱码
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let boundary = buffer.indexOf('\n\n');
        while (boundary !== -1) {
          const message = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2); // 移除已处理的消息

          if (message.startsWith('data: ')) {
            const jsonStr = message.replace('data: ', '');
            try {
              const data = JSON.parse(jsonStr);

              if (data.node === 'DONE') {
                setIsLoading(false);
                setCurrentNode('');
              } else if (data.node === 'ERROR') {
                setError(data.message);
                setIsLoading(false);
              } else if (data.type === 'node_start') {
                setActiveNodes(prev => Array.from(new Set([...prev, data.node])));
              } else if (data.type === 'token') {
                setAgentData(prev => {
                  const keyMap: Record<string, keyof AgentState> = {
                    'bull_expert': 'bull_thesis',
                    'bear_expert': 'bear_thesis',
                    'chief': 'final_report'
                  };
                  const stateKey = keyMap[data.node];
                  if (!stateKey) return prev;
                  
                  return {
                    ...prev,
                    [stateKey]: (prev[stateKey] || '') + data.chunk
                  };
                });
                setCurrentNode(data.node);
              } else if (data.type === 'state') {
                // 📦 节点跑完的完整状态更新
                if (data.state) {
                  setAgentData(prev => ({ ...prev, ...data.state }));
                  setCompletedNodes(prev => Array.from(new Set([...prev, data.node])));
                  setActiveNodes(prev => prev.filter(n => n !== data.node));
                }
              }
            } catch (e) {
              // 吞掉由于极端截断导致的临时 JSON 错误，等待下一次 buffer 拼接
              console.warn("JSON Parse skipped temporarily:", jsonStr);
            }
          }
          // 检查是否还有完整的消息
          boundary = buffer.indexOf('\n\n');
        }
      }
    } catch (err: any) {
      setError(err.message || '分析过程中发生未知错误');
      setIsAnalyzing(false);
      setActiveNodes([]);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-slate-300 font-sans selection:bg-blue-500/30">
      {/* 顶部导航 */}
      <header className="border-b border-white/10 bg-[#121214] px-6 py-4 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-600/20 rounded-lg border border-blue-500/30">
              <Scale className="w-6 h-6 text-blue-400" />
            </div>
            <h1 className="text-xl font-bold tracking-wider text-white">
              AI QUANT <span className="text-blue-500">TERMINAL</span>
            </h1>
          </div>
          <div className="text-xs text-slate-500 uppercase tracking-widest font-mono">
            Multi-Agent Analysis Engine v2.0
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-12">
        {/* 搜索输入区 */}
        <div className="max-w-3xl mx-auto mb-16">
          <form onSubmit={handleAnalyze} className="relative group z-20">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-2xl blur-xl transition-all group-hover:blur-2xl opacity-50"></div>
            <div className="relative flex items-center bg-[#18181b] border border-white/10 rounded-2xl p-2 shadow-2xl focus-within:border-blue-500/50 transition-colors">
              <Search className="w-6 h-6 text-slate-400 ml-4" />
              <input
                type="text"
                className="w-full bg-transparent border-none outline-none px-4 py-4 text-lg text-white placeholder-slate-600"
                placeholder="输入你想分析的股票及关切... (例：深度分析 NVDA)"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={isAnalyzing}
              />
              
              {/* 设置按钮 */}
              <button
                type="button"
                onClick={() => setShowConfig(!showConfig)}
                className={`p-3 mr-2 rounded-xl transition-colors ${showConfig ? 'bg-blue-500/20 text-blue-400' : 'text-slate-400 hover:bg-slate-800'}`}
                title="配置模型"
              >
                <SlidersHorizontal className="w-5 h-5" />
              </button>

              <button
                type="submit"
                disabled={isAnalyzing || !prompt.trim()}
                className="bg-white text-black px-8 py-3 rounded-xl font-semibold hover:bg-slate-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isAnalyzing ? (
                  <><Loader2 className="w-5 h-5 animate-spin" /> 调度中</>
                ) : (
                  '深度投研'
                )}
              </button>
            </div>
          </form>

          {/* 模型配置面板 (下拉动画) */}
          <AnimatePresence>
            {showConfig && (
              <motion.div
                initial={{ opacity: 0, height: 0, y: -20 }}
                animate={{ opacity: 1, height: 'auto', y: 0 }}
                exit={{ opacity: 0, height: 0, y: -20 }}
                className="overflow-hidden mt-2 relative z-10"
              >
                <div className="bg-[#121214] border border-white/10 rounded-2xl p-6 shadow-xl grid md:grid-cols-2 gap-6">
                  {/* 多空博弈模型选择 */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-400 flex items-center gap-2">
                      <BrainCircuit className="w-4 h-4" />
                      多空博弈辩论模型 (Debate Agent)
                    </label>
                    <select
                      value={debateModel}
                      onChange={(e) => setDebateModel(e.target.value)}
                      disabled={isAnalyzing}
                      className="w-full bg-[#0a0a0b] border border-slate-700 rounded-lg px-4 py-3 text-slate-200 focus:outline-none focus:border-blue-500/50 appearance-none cursor-pointer"
                    >
                      {AVAILABLE_MODELS.map(model => (
                        <option key={model.id} value={model.id}>{model.name}</option>
                      ))}
                    </select>
                    <p className="text-xs text-slate-500">负责生成红蓝两方的对抗性策略分析。推荐使用推理速度快、逻辑发散的模型。</p>
                  </div>

                  {/* 首席分析师模型选择 */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-400 flex items-center gap-2">
                      <Scale className="w-4 h-4" />
                      首席总管决策模型 (Chief Agent)
                    </label>
                    <select
                      value={chiefModel}
                      onChange={(e) => setChiefModel(e.target.value)}
                      disabled={isAnalyzing}
                      className="w-full bg-[#0a0a0b] border border-slate-700 rounded-lg px-4 py-3 text-slate-200 focus:outline-none focus:border-blue-500/50 appearance-none cursor-pointer"
                    >
                      {AVAILABLE_MODELS.map(model => (
                        <option key={model.id} value={model.id}>{model.name}</option>
                      ))}
                    </select>
                    <p className="text-xs text-slate-500">负责最终研报的拍板与合成。推荐使用逻辑严密、长文本生成能力极强的旗舰模型（如 GPT-4o）。</p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {error && (
            <div className="mt-4 p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-center gap-3 text-rose-400">
              <AlertCircle className="w-5 h-5" />
              <p>{error}</p>
            </div>
          )}
        </div>

        {(isAnalyzing || completedNodes.length > 0) && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            className="mb-12 bg-[#121214] border border-white/5 rounded-2xl p-6 shadow-xl overflow-x-auto"
          >
            {/* 使用 Graph 拓扑布局体现并行 */}
            <div className="flex justify-between items-center relative min-w-[600px] py-4">
              {/* 贯穿全局的背景连线 */}
              <div className="absolute left-8 right-8 top-1/2 -translate-y-1/2 h-0.5 bg-slate-800 -z-10" />
              
              {STAGE_GROUPS.map((group, groupIdx) => (
                <div key={groupIdx} className="flex flex-col gap-6 relative z-10 bg-[#121214] py-2 px-1">
                  {group.map(step => {
                    const isCompleted = completedNodes.includes(step.id);
                    const isActive = activeNodes.includes(step.id);
                    
                    return (
                      <div key={step.id} className="flex flex-col items-center gap-2">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${
                          isCompleted 
                            ? 'bg-blue-500/20 border-blue-500 text-blue-400' 
                            : isActive 
                            ? 'bg-slate-800 border-blue-400 text-white shadow-[0_0_15px_rgba(59,130,246,0.5)] scale-110' 
                            : 'bg-slate-900 border-slate-800 text-slate-600'
                        }`}>
                          {isActive ? (
                            <Loader2 className="w-5 h-5 animate-spin text-blue-400" />
                          ) : (
                            <step.icon className={`w-5 h-5 ${isCompleted ? step.color : ''}`} />
                          )}
                        </div>
                        <span className={`text-[11px] font-medium tracking-wide whitespace-nowrap ${isCompleted || isActive ? 'text-slate-300' : 'text-slate-600'}`}>
                          {step.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </motion.div>
        )}

        <AnimatePresence>
          {agentData.ticker && (
             <motion.div 
             ref={resultsRef}
             initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }}
             className="space-y-6"
           >
             {/* 标的概览 */}
             <div className="flex flex-wrap items-center gap-4 mb-8">
               <div className="text-4xl font-black text-white tracking-tight px-6 py-2 bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700 rounded-xl shadow-lg">
                 {agentData.ticker}
               </div>
               {agentData.sector && (
                 <span className="px-4 py-2 bg-blue-900/30 text-blue-400 border border-blue-800/50 rounded-lg text-sm font-medium">
                   Sector: {agentData.sector}
                 </span>
               )}
               {agentData.investment_horizon && (
                 <span className="px-4 py-2 bg-slate-800 text-slate-300 border border-slate-700 rounded-lg text-sm font-medium">
                   Horizon: {agentData.investment_horizon}
                 </span>
               )}
             </div>

              {/* 智能估值卡片 */}
              {agentData.valuation_data && (
                <motion.div 
                  initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                  className="bg-[#18181b] border border-amber-900/30 rounded-2xl overflow-hidden shadow-xl"
                >
                  <div className="bg-amber-900/20 px-6 py-4 border-b border-amber-900/30 flex justify-between items-center">
                    <div className="flex items-center gap-2">
                      <DollarSign className="w-5 h-5 text-amber-400" />
                      <h3 className="text-lg font-semibold text-white">
                        智能估值分析 <span className="text-sm font-normal text-amber-400/60 ml-2">[{agentData.valuation_data.selected_method}]</span>
                      </h3>
                    </div>
                    {/* 结论勋章 */}
                    <div className={`px-3 py-1 rounded-full text-xs font-bold border ${
                      agentData.valuation_data.verdict?.includes('低估') ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400' :
                      agentData.valuation_data.verdict?.includes('高估') ? 'bg-rose-500/10 border-rose-500/50 text-rose-400' :
                      'bg-blue-500/10 border-blue-500/50 text-blue-400'
                    }`}>
                      {agentData.valuation_data.verdict}
                    </div>
                  </div>

                  <div className="p-6">
                    {/* 模型选择理由 */}
                    <div className="mb-6 p-4 bg-amber-900/10 border-l-4 border-amber-500/50 rounded-r-lg">
                      <p className="text-sm text-amber-100/80 italic">
                        <span className="font-bold text-amber-400">路由决策：</span>
                        {agentData.valuation_data.reasoning}
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                      {/* 左侧：核心指标动态列表 */}
                      <div>
                        <h4 className="text-sm font-medium text-slate-400 mb-4 uppercase tracking-wider">关键估值参数</h4>
                        <div className="space-y-3">
                          {Object.entries(agentData.valuation_data.key_metrics || {}).map(([key, value]) => (
                            <div key={key} className="flex justify-between items-center border-b border-slate-800 pb-2">
                              <span className="text-slate-400 text-sm">{key}</span>
                              <span className="text-white font-mono font-medium">{String(value)}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* 右侧：价格对比可视化 */}
                      <div className="flex flex-col justify-center items-center p-6 bg-slate-900/50 rounded-xl border border-slate-800">
                        <div className="text-sm text-slate-400 mb-2">估算内在价值 (Intrinsic Value)</div>
                        <div className="text-4xl font-bold text-amber-400 mb-4">
                          ${agentData.valuation_data.intrinsic_value?.toFixed(2)}
                        </div>
                        
                        <div className="w-full space-y-2">
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-500">当前价: ${agentData.valuation_data.current_price || '--'}</span>
                            <span className={agentData.valuation_data.intrinsic_value! > (agentData.valuation_data.current_price || 0) ? 'text-emerald-400' : 'text-rose-400'}>
                              空间: {(((agentData.valuation_data.intrinsic_value! / (agentData.valuation_data.current_price || 1)) - 1) * 100).toFixed(1)}%
                            </span>
                          </div>
                          {/* 简易进度条模拟溢价/折价 */}
                          <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                            <motion.div 
                              initial={{ width: 0 }}
                              animate={{ width: '70%' }} // 这里可以根据现价和估价的比例动态计算
                              className={`h-full ${agentData.valuation_data.intrinsic_value! > (agentData.valuation_data.current_price || 0) ? 'bg-emerald-500' : 'bg-rose-500'}`}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
             {(agentData.bull_thesis || agentData.bear_thesis) && (
               <div className="grid md:grid-cols-2 gap-6">
                 {/* 多头报告 */}
                 <div className="bg-gradient-to-b from-emerald-950/20 to-[#121214] border border-emerald-900/30 rounded-2xl p-6 relative overflow-hidden">
                   <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-3xl" />
                   <div className="flex items-center gap-3 mb-6 border-b border-emerald-900/30 pb-4">
                     <div className="p-2 bg-emerald-500/10 rounded-lg"><TrendingUp className="w-6 h-6 text-emerald-400" /></div>
                     <h3 className="text-xl font-bold text-emerald-400">多头策略 (Bull Thesis)</h3>
                   </div>
                   <div className="prose prose-invert prose-emerald max-w-none prose-sm">
                     {agentData.bull_thesis ? (
                       <ReactMarkdown>{agentData.bull_thesis}</ReactMarkdown>
                     ) : (
                       <div className="flex items-center gap-2 text-emerald-600"><Loader2 className="w-4 h-4 animate-spin" /> 多头专家正在建构逻辑...</div>
                     )}
                   </div>
                 </div>

                 {/* 空头报告 */}
                 <div className="bg-gradient-to-b from-rose-950/20 to-[#121214] border border-rose-900/30 rounded-2xl p-6 relative overflow-hidden">
                   <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/5 rounded-full blur-3xl" />
                   <div className="flex items-center gap-3 mb-6 border-b border-rose-900/30 pb-4">
                     <div className="p-2 bg-rose-500/10 rounded-lg"><TrendingDown className="w-6 h-6 text-rose-400" /></div>
                     <h3 className="text-xl font-bold text-rose-400">空头策略 (Bear Thesis)</h3>
                   </div>
                   <div className="prose prose-invert prose-rose max-w-none prose-sm">
                     {agentData.bear_thesis ? (
                       <ReactMarkdown>{agentData.bear_thesis}</ReactMarkdown>
                     ) : (
                       <div className="flex items-center gap-2 text-rose-600"><Loader2 className="w-4 h-4 animate-spin" /> 空头专家正在寻找破绽...</div>
                     )}
                   </div>
                 </div>
               </div>
             )}

             {/* 首席投资官最终决断 */}
             {agentData.final_report && (
               <motion.div 
                 initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 }}
                 className="mt-8 bg-[#18181b] border-2 border-blue-900/50 rounded-2xl shadow-2xl overflow-hidden"
               >
                 <div className="bg-gradient-to-r from-blue-900/40 to-slate-900 px-8 py-5 border-b border-blue-900/50 flex items-center gap-4">
                   <div className="p-2 bg-blue-500/20 rounded-lg"><Scale className="w-6 h-6 text-blue-400" /></div>
                   <div>
                     <h2 className="text-2xl font-bold text-white tracking-wide">首席投委会最终裁决 (IC Report)</h2>
                     <p className="text-blue-400/80 text-sm mt-1">Chief Investment Officer Synthesis</p>
                   </div>
                 </div>
                 <div className="p-8 prose prose-invert prose-lg max-w-none prose-headings:text-white prose-a:text-blue-400 prose-strong:text-blue-300">
                   <ReactMarkdown>{agentData.final_report}</ReactMarkdown>
                 </div>
               </motion.div>
             )}
           </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}