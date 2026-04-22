'use client';

import React, { useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  Search, TrendingUp, TrendingDown, Activity, 
  Briefcase, Scale, BrainCircuit, Loader2, AlertCircle,
  SlidersHorizontal
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// --- 类型定义 ---
interface AgentState {
  ticker?: string;
  investment_horizon?: string;
  user_concerns?: string;
  sector?: string;
  bull_thesis?: string;
  bear_thesis?: string;
  final_report?: string;
}

const AGENT_STEPS = [
  { id: 'intent_analyzer', label: '意图解析', icon: BrainCircuit },
  { id: 'macro', label: '宏观调研', icon: Activity },
  { id: 'fundamental', label: '基本面分析', icon: Briefcase },
  { id: 'bull_expert', label: '多头建构', icon: TrendingUp, color: 'text-emerald-500' },
  { id: 'bear_expert', label: '空头建构', icon: TrendingDown, color: 'text-rose-500' },
  { id: 'chief', label: '首席总管综合', icon: Scale, color: 'text-blue-400' }
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

    // 重置状态
    setIsAnalyzing(true);
    setError(null);
    setActiveNodes(['intent_analyzer']);
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
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            try {
              const payload = JSON.parse(jsonStr);

              if (payload.node === 'ERROR') {
                throw new Error(payload.message);
              }

              if (payload.node === 'DONE') {
                setIsAnalyzing(false);
                setActiveNodes([]);
                setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth' }), 500);
                continue;
              }

              setCompletedNodes(prev => [...new Set([...prev, payload.node])]);
              
              if (payload.state) {
                setAgentData(prev => ({ ...prev, ...payload.state }));
              }
              
            } catch (err) {
              console.error('解析流数据失败:', err, jsonStr);
            }
          }
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

        {/* --- 下方的进度条与 Markdown 渲染区保持不变 --- */}
        {/* 为了简洁，此处省略下方动态进度条与报告渲染的代码，保留上个版本的逻辑即可 */}
        {(isAnalyzing || completedNodes.length > 0) && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            className="mb-12 bg-[#121214] border border-white/5 rounded-2xl p-6 shadow-xl"
          >
            <div className="flex justify-between items-center relative">
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-0.5 bg-slate-800 -z-10" />
              {AGENT_STEPS.map((step, index) => {
                const isCompleted = completedNodes.includes(step.id);
                const isActive = activeNodes.includes(step.id) || (isAnalyzing && !isCompleted && completedNodes.length === index);
                
                return (
                  <div key={step.id} className="flex flex-col items-center gap-3 bg-[#121214] px-4">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center border-2 transition-all duration-500 ${
                      isCompleted 
                        ? 'bg-blue-500/20 border-blue-500 text-blue-400' 
                        : isActive 
                        ? 'bg-slate-800 border-slate-500 text-white shadow-[0_0_15px_rgba(255,255,255,0.2)]' 
                        : 'bg-slate-900 border-slate-800 text-slate-600'
                    }`}>
                      {isActive ? <Loader2 className="w-5 h-5 animate-spin" /> : <step.icon className={`w-5 h-5 ${isCompleted ? step.color : ''}`} />}
                    </div>
                    <span className={`text-xs font-medium tracking-wide ${isCompleted || isActive ? 'text-slate-300' : 'text-slate-600'}`}>
                      {step.label}
                    </span>
                  </div>
                );
              })}
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

             {/* 多空博弈区 (仅当双方都有数据时显示) */}
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