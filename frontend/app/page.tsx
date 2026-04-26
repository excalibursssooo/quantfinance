'use client';

import React, { useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  Search, TrendingUp, TrendingDown, Activity, 
  Briefcase, Scale, BrainCircuit, Loader2, AlertCircle,
  SlidersHorizontal, DollarSign, Download // 确保有 DollarSign
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// --- 类型定义 ---
interface ValuationData {
  selected_method?: string;
  reasoning?: string;
  intrinsic_value?: number;
  current_price?: number;
  verdict?: string;
  key_metrics?: Record<string, any>;
  sensitivity?: Record<string, number>;
}

interface AgentState {
  ticker?: string;
  investment_horizon?: string;
  user_concerns?: string;
  sector?: string;
  valuation_data?: ValuationData;
  var_data?: Record<string, any>; 
  bull_thesis?: string;
  bear_thesis?: string;
  audit_report?: string; 
  final_report?: string;
}

const STAGE_GROUPS = [
  [{ id: 'intent_analyzer', label: '意图解析', icon: BrainCircuit }], 
  [ 
    { id: 'macro', label: '宏观调研', icon: Activity },
    { id: 'fundamental', label: '基本面分析', icon: Briefcase }
  ],
  [{ id: 'valuation', label: '估值建模', icon: SlidersHorizontal }],
  [
    { id: 'bull_expert', label: '多头逻辑', icon: TrendingUp },
    { id: 'bear_expert', label: '空头逻辑', icon: TrendingDown },
  ],
  [{ id: 'auditor', label: '风控审计', icon: AlertCircle }],
  [{ id: 'chief', label: '终审决策', icon: Scale }]
];

// --- 交互式估值微调组件 (动态适配不同估值方法) ---
const InteractiveValuation = ({ 
  initialData, 
  threadId, 
  onConfirm 
}: { 
  initialData: ValuationData, 
  threadId: string, 
  onConfirm: () => void 
}) => {
  const method = initialData?.selected_method || 'calculate_dcf';
  const metrics = initialData?.key_metrics || {};

  // 1. DCF 参数状态
  const [wacc, setWacc] = useState<number>(Number(metrics.wacc || 0.1));
  const [tg, setTg] = useState<number>(Number(metrics.tg || 0.02));
  
  // 2. P/S 参数状态
  const [targetPs, setTargetPs] = useState<number>(Number(metrics.target_ps || 5.0));
  
  // 3. EV/EBITDA 参数状态
  const [targetEvEbitda, setTargetEvEbitda] = useState<number>(Number(metrics.target_ev_ebitda || 15.0));

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleConfirm = async () => {
    setIsSubmitting(true);
    let feedbackPayload = {};

    // 动态构造后端需要的 Payload
    if (method === 'calculate_dcf') {
      feedbackPayload = { wacc, tg };
    } else if (method === 'calculate_ps_valuation') {
      feedbackPayload = { target_ps: targetPs };
    } else if (method === 'calculate_ev_ebitda') {
      feedbackPayload = { target_ev_ebitda: targetEvEbitda };
    }

    try {
      await fetch(`http://localhost:8000/api/feedback?thread_id=${threadId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedbackPayload)
      });
      onConfirm(); 
    } catch (e) {
      console.error("提交参数微调失败", e);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mt-8 p-6 bg-slate-800/80 border border-blue-500/40 rounded-xl shadow-lg">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500/20 rounded-lg"><SlidersHorizontal className="w-5 h-5 text-blue-400" /></div>
          <h3 className="text-xl font-bold text-white">
            CIO 审查与参数微调
            <span className="ml-3 text-sm font-normal text-slate-400">
              ({method === 'calculate_dcf' ? 'DCF 贴现模型' : method === 'calculate_ps_valuation' ? 'P/S 乘数模型' : 'EV/EBITDA 估值'})
            </span>
          </h3>
        </div>
        <span className="px-3 py-1 bg-yellow-500/20 text-yellow-400 text-xs rounded-full border border-yellow-500/30">
          Agent 已挂起等待指示
        </span>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* --- DCF 专属输入框 --- */}
        {method === 'calculate_dcf' && (
          <>
            <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700">
              <label className="flex justify-between text-sm text-slate-300 mb-2 font-medium">
                <span>贴现率 (WACC)</span>
                <span className="font-mono text-blue-400">{(wacc * 100).toFixed(1)}%</span>
              </label>
              <input 
                type="number" step="0.005" 
                value={wacc} onChange={(e) => setWacc(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
              />
            </div>
            
            <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700">
              <label className="flex justify-between text-sm text-slate-300 mb-2 font-medium">
                <span>永续增长率 (Terminal Growth)</span>
                <span className="font-mono text-blue-400">{(tg * 100).toFixed(1)}%</span>
              </label>
              <input 
                type="number" step="0.001" 
                value={tg} onChange={(e) => setTg(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
              />
            </div>
          </>
        )}

        {/* --- P/S 专属输入框 --- */}
        {method === 'calculate_ps_valuation' && (
          <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700">
            <label className="flex justify-between text-sm text-slate-300 mb-2 font-medium">
              <span>目标市销率 (Target P/S 倍数)</span>
              <span className="font-mono text-blue-400">{targetPs.toFixed(1)}x</span>
            </label>
            <input 
              type="number" step="0.1" 
              value={targetPs} onChange={(e) => setTargetPs(Number(e.target.value))}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
            />
          </div>
        )}

        {/* --- EV/EBITDA 专属输入框 --- */}
        {method === 'calculate_ev_ebitda' && (
          <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700">
            <label className="flex justify-between text-sm text-slate-300 mb-2 font-medium">
              <span>目标 EV/EBITDA 倍数</span>
              <span className="font-mono text-blue-400">{targetEvEbitda.toFixed(1)}x</span>
            </label>
            <input 
              type="number" step="0.1" 
              value={targetEvEbitda} onChange={(e) => setTargetEvEbitda(Number(e.target.value))}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
            />
          </div>
        )}
      </div>

      <div className="mt-6 flex flex-col sm:flex-row items-center justify-end">
        <button 
          onClick={handleConfirm}
          disabled={isSubmitting}
          className="px-8 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-bold transition-all disabled:opacity-50 flex items-center gap-2"
        >
          {isSubmitting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Scale className="w-5 h-5" />}
          {isSubmitting ? '正在计算并生成研报...' : '确认参数并生成终版研报'}
        </button>
      </div>
    </div>
  );
};


export default function QuantAgentPage() {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [agentData, setAgentData] = useState<AgentState>({});
  const [completedNodes, setCompletedNodes] = useState<Set<string>>(new Set());
  
  const [threadId, setThreadId] = useState<string>('');
  const [isWaitingFeedback, setIsWaitingFeedback] = useState<boolean>(false);
  const reportRef = useRef<HTMLDivElement>(null);

  const exportToPDF = async () => {
    if (!reportRef.current) return;
    
    // 增加一个简单的加载提示反馈
    const originalText = reportRef.current.style.opacity;
    reportRef.current.style.opacity = '0.7'; 
    
    try {
      // 动态导入，避免 Next.js 服务端渲染报错
      const { toPng } = await import('html-to-image');
      const { jsPDF } = await import('jspdf');

      const element = reportRef.current;

      // 1. 将 DOM 转换为高清 PNG 图片 (原生支持所有现代 CSS)
      const dataUrl = await toPng(element, { 
        quality: 1.0,
        pixelRatio: 2, // 提高 PDF 清晰度
        backgroundColor: '#141416' // 强制填充暗色背景，防止透明
      });

      // 2. 实例化 PDF (A4 纸张)
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'px',
        format: 'a4'
      });

      // 3. 计算图片在 A4 纸上的比例
      const pdfWidth = pdf.internal.pageSize.getWidth();
      // 根据 DOM 实际宽高比算出 PDF 里的高度
      const pdfHeight = (element.offsetHeight * pdfWidth) / element.offsetWidth;

      // 4. 将图片写入 PDF 并保存
      pdf.addImage(dataUrl, 'PNG', 0, 0, pdfWidth, pdfHeight);
      pdf.save(`Quant_Research_${agentData.ticker || 'Report'}.pdf`);
      
    } catch (error) {
      console.error("PDF 导出失败", error);
      alert("PDF 导出失败，请检查控制台。");
    } finally {
      // 恢复 UI 状态
      if (reportRef.current) {
        reportRef.current.style.opacity = originalText;
      }
    }
  };

  const [nodeModels, setNodeModels] = useState({
    intent: 'qwen3.5-flash',      
    valuation: 'qwen3.6-flash',          
    debate_model: 'qwen3.6-flash',   
    chief_model: 'qwen3.6-flash' 
  });
  const [showModelSettings, setShowModelSettings] = useState(false);

  const AVAILABLE_MODELS = [
    { value: 'qwen3.5-flash', label: 'Qwen 3.5 Flash (快速/便宜)' },
    { value: 'qwen3.6-flash', label: 'Qwen 3.6 Flash (全能/逻辑强)' },
    { value: 'claude-3-5-sonnet-20240620', label: 'Claude 3.5 (排版/深度思考)' },
    { value: 'deepseek-v4-flash', label: 'DeepSeek V4 (高性价比)' }
  ];

  const handleAnalyze = async (existingThreadId?: string) => {
    if (!input.trim() && !existingThreadId) return;
    setIsLoading(true);
    setIsWaitingFeedback(false);

    if (!existingThreadId) {
      setAgentData({});
      setCompletedNodes(new Set());
      setActiveNode('intent_analyzer');
    }

    const currentThreadId = existingThreadId || `thread_${Date.now()}`;
    setThreadId(currentThreadId);

    try {
      const response = await fetch('http://localhost:8000/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          prompt: input,
          thread_id: currentThreadId,
          expert_configs: nodeModels,
        }),
      });

      if (!response.body) throw new Error("No response body");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (!dataStr) continue;

            try {
              const eventData = JSON.parse(dataStr);

              if (eventData.type === 'node_start') {
                setActiveNode(eventData.node);
              } 
              else if (eventData.type === 'token') {
                setAgentData((prevData) => {
                  const newData = { ...prevData };
                  if (eventData.node === 'bull_expert') {
                    newData.bull_thesis = (newData.bull_thesis || '') + eventData.chunk;
                  } else if (eventData.node === 'bear_expert') {
                    newData.bear_thesis = (newData.bear_thesis || '') + eventData.chunk;
                  } else if (eventData.node === 'chief') {
                    newData.final_report = (newData.final_report || '') + eventData.chunk;
                  }
                  return newData;
                });
              } 
              else if (eventData.type === 'state') {
                setAgentData((prevData) => ({
                  ...prevData,
                  ...eventData.state 
                }));
                setCompletedNodes(prev => new Set(prev).add(eventData.node));
              }
              else if (eventData.type === 'pause' || eventData.node === 'PAUSED') {
                setIsWaitingFeedback(true); 
                setIsLoading(false);        
                setActiveNode(null);        
              } 
              else if (eventData.node === 'DONE') {
                setIsLoading(false);
                setActiveNode(null);
              } else if (eventData.type === 'error') {
                console.error("Agent Error:", eventData.message);
                setIsLoading(false);
                setActiveNode(null);
              }

            } catch (err) {
              console.error("解析 SSE 数据失败:", err, dataStr);
            }
          }
        }
      }
    } catch (error) {
      console.error("Failed to analyze:", error);
      setIsLoading(false);
      setActiveNode(null);
    }
  };

  const handleResumeAfterFeedback = () => {
    handleAnalyze(threadId);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-blue-500/30">
      
      {/* 头部区域 */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-2 rounded-lg">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">QuantFinance AI</h1>
              <p className="text-xs text-slate-400">Professional Agentic Workflow</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="mb-4">
          <button 
            onClick={() => setShowModelSettings(!showModelSettings)}
            className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors"
          >
            <SlidersHorizontal className="w-4 h-4" /> 
            专家模型分配策略 {showModelSettings ? '▲' : '▼'}
          </button>
          
          <AnimatePresence>
            {showModelSettings && (
              <motion.div 
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-4 bg-slate-800/50 p-4 rounded-xl border border-slate-700"
              >
                {Object.entries({
                  intent: '意图解析 (前台)',
                  valuation: '估值专家 (量化)',
                  debate_model: '多空分析师 (辩论)',
                  chief_model: '首席投委会 (终审)'
                }).map(([key, label]) => (
                  <div key={key} className="flex flex-col gap-1">
                    <label className="text-xs text-slate-400">{label}</label>
                    <select
                      value={nodeModels[key as keyof typeof nodeModels]}
                      onChange={(e) => setNodeModels({...nodeModels, [key]: e.target.value})}
                      className="bg-slate-900 text-sm text-white border border-slate-600 rounded px-2 py-1 outline-none focus:border-blue-500"
                    >
                      {AVAILABLE_MODELS.map(m => (
                        <option key={m.value} value={m.value}>{m.label}</option>
                      ))}
                    </select>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        
        {/* 输入区域 */}
        <div className="bg-slate-900 rounded-2xl p-2 border border-slate-800 shadow-xl flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input 
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !isLoading && !isWaitingFeedback && handleAnalyze()}
              placeholder="e.g. 帮我深度调研特斯拉 (TSLA)，我担心它的利润率下滑，打算长线持有..."
              className="w-full bg-transparent border-none py-4 pl-12 pr-4 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-0 text-lg"
              disabled={isLoading || isWaitingFeedback}
            />
          </div>
          <button 
            onClick={() => handleAnalyze()}
            disabled={isLoading || !input.trim() || isWaitingFeedback}
            className="px-8 py-4 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : '启动调研'}
          </button>
        </div>

        {/* Agent 工作流展示 */}
        <AnimatePresence>
          {(isLoading || completedNodes.size > 0 || isWaitingFeedback) && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              className="mt-12 bg-slate-900/50 border border-slate-800 rounded-2xl p-8"
            >
              <h3 className="text-sm font-medium text-slate-400 mb-8 uppercase tracking-wider flex items-center gap-2">
                <BrainCircuit className="w-4 h-4" /> Agentic Reasoning Process
              </h3>
              
              <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                {STAGE_GROUPS.map((group, groupIdx) => (
                  <React.Fragment key={groupIdx}>
                    <div className="flex flex-col gap-3 w-full md:w-auto">
                      {group.map(stage => {
                        const Icon = stage.icon;
                        const isCompleted = completedNodes.has(stage.id);
                        const isActive = activeNode === stage.id;

                        return (
                          <div 
                            key={stage.id}
                            className={`flex items-center gap-3 p-3 rounded-xl transition-all duration-300 ${
                              isActive ? 'bg-blue-500/10 border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.15)]' : 
                              isCompleted ? 'bg-emerald-500/10 border border-emerald-500/20' : 
                              'bg-slate-800/50 border border-slate-700/50 opacity-50'
                            }`}
                          >
                            <div className={`p-2 rounded-lg ${
                              isActive ? 'bg-blue-500 text-white animate-pulse' : 
                              isCompleted ? 'bg-emerald-500 text-white' : 
                              'bg-slate-700 text-slate-400'
                            }`}>
                              {isActive ? <Loader2 className="w-4 h-4 animate-spin" /> : <Icon className="w-4 h-4" />}
                            </div>
                            <span className={`font-medium text-sm ${
                              isActive ? 'text-blue-400' : isCompleted ? 'text-emerald-400' : 'text-slate-400'
                            }`}>
                              {stage.label}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                    {groupIdx < STAGE_GROUPS.length - 1 && (
                      <div className="hidden md:block w-8 h-px bg-slate-700" />
                    )}
                  </React.Fragment>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 动态内容展示区 */}
        <div className="mt-8 space-y-6">
          
          {/* 基本信息 */}
          {agentData.ticker && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-4 mb-8">
              <div className="px-4 py-2 bg-slate-800 rounded-lg border border-slate-700 font-mono text-blue-400 font-bold">
                {agentData.ticker}
              </div>
              <div className="px-4 py-2 bg-slate-800 rounded-lg border border-slate-700 text-slate-300 text-sm flex items-center">
                板块: {agentData.sector} | 周期: {agentData.investment_horizon}
              </div>
            </motion.div>
          )}

          {/*估值结果看板 (修复卡片消失与数据刷新动画) */}
          {(agentData.valuation_data?.selected_method || activeNode === 'valuation') && (
            <motion.div 
              // 🌟 核心修复 1：绑定 key，一旦价值改变，强制触发一次 React 的出现动画
              key={agentData.valuation_data?.intrinsic_value || 'loading_card'} 
              initial={{ opacity: 0, y: 20 }} 
              animate={{ opacity: 1, y: 0 }} 
              className="mb-8 bg-slate-800/60 border border-slate-700/80 rounded-xl p-6 shadow-lg backdrop-blur-sm"
            >
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-emerald-500/20 rounded-lg">
                  <DollarSign className="w-5 h-5 text-emerald-400" />
                </div>
                <h3 className="text-xl font-bold text-white flex items-center gap-3">
                  量化估值模型 (Valuation Dashboard)
                  {agentData.valuation_data?.selected_method && (
                    <span className="px-2 py-1 bg-slate-700 text-slate-300 text-xs rounded border border-slate-600 font-normal">
                      {agentData.valuation_data.selected_method === 'calculate_dcf' ? 'DCF 绝对估值法' : 
                       agentData.valuation_data.selected_method === 'calculate_ps_valuation' ? 'P/S 相对估值法' : 
                       agentData.valuation_data.selected_method === 'calculate_ev_ebitda' ? 'EV/EBITDA 乘数法' : '自定义模型'}
                    </span>
                  )}
                </h3>
              </div>
              
              {/* 🌟 核心修复 2：严格判断 !== undefined，防止数字 0 被判定为 false */}
              {agentData.valuation_data?.intrinsic_value !== undefined ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* 当前价格 */}
                  <div className="bg-slate-900/50 p-5 rounded-xl border border-slate-700/50 relative overflow-hidden">
                    <p className="text-sm text-slate-400 mb-2">当前股价 (Current Price)</p>
                    <p className="text-3xl font-mono text-white flex items-baseline gap-1">
                      <span className="text-lg text-slate-500">$</span>
                      {agentData.valuation_data.current_price?.toFixed(2) || 'N/A'}
                    </p>
                  </div>

                  {/* 内在价值 */}
                  <div className="bg-slate-900/50 p-5 rounded-xl border border-blue-900/50 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-16 h-16 bg-blue-500/10 rounded-bl-full blur-xl"></div>
                    <p className="text-sm text-blue-300/80 mb-2">模型测算内在价值 (Intrinsic Value)</p>
                    <p className="text-3xl font-mono text-blue-400 flex items-baseline gap-1">
                      <span className="text-lg text-blue-500/50">$</span>
                      {/* 如果算出 0，直接显示 0.00 */}
                      {agentData.valuation_data.intrinsic_value.toFixed(2)}
                    </p>
                  </div>

                  {/* 估值结论 (动态颜色) */}
                  <div className={`p-5 rounded-xl border relative overflow-hidden ${
                    agentData.valuation_data.verdict?.includes('低估') || agentData.valuation_data.verdict?.includes('看多') 
                      ? 'bg-emerald-900/20 border-emerald-500/30 text-emerald-400' 
                      : agentData.valuation_data.verdict?.includes('高估') || agentData.valuation_data.verdict?.includes('泡沫') || agentData.valuation_data.verdict?.includes('看空') 
                      ? 'bg-rose-900/20 border-rose-500/30 text-rose-400' 
                      : 'bg-yellow-900/20 border-yellow-500/30 text-yellow-400'
                  }`}>
                    <p className="text-sm opacity-80 mb-2">系统初筛结论 (System Verdict)</p>
                    <p className="text-2xl font-bold tracking-wide">
                      {agentData.valuation_data.verdict || '需要人工复核'}
                    </p>
                  </div>
                </div>
              ) : (
                // 加载中状态
                <div className="flex items-center gap-3 text-slate-400 p-4 bg-slate-900/50 rounded-lg border border-slate-800">
                  <Loader2 className="w-5 h-5 animate-spin text-blue-500" /> 
                  <span className="animate-pulse">正在提取财务数据并构建估值模型...</span>
                </div>
              )}
            </motion.div>
          )}
          {/* 两侧辩论区 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 多头观点 */}
            {(agentData.bull_thesis || activeNode === 'bull_expert') && (
              <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="bg-emerald-950/20 border border-emerald-900/50 rounded-xl p-6">
                <h3 className="text-emerald-400 font-bold flex items-center gap-2 mb-4">
                  <TrendingUp className="w-5 h-5" /> Bull Thesis (多头逻辑)
                </h3>
                {agentData.bull_thesis ? (
                  <div className="prose prose-invert prose-sm prose-emerald"><ReactMarkdown>{agentData.bull_thesis}</ReactMarkdown></div>
                ) : (
                  <div className="flex items-center gap-2 text-emerald-600/50"><Loader2 className="w-4 h-4 animate-spin" /> 多头专家正在撰写报告...</div>
                )}
              </motion.div>
            )}

            {/* 空头观点 */}
            {(agentData.bear_thesis || activeNode === 'bear_expert') && (
              <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="bg-rose-950/20 border border-rose-900/50 rounded-xl p-6">
                <h3 className="text-rose-400 font-bold flex items-center gap-2 mb-4">
                  <TrendingDown className="w-5 h-5" /> Bear Thesis (空头逻辑)
                </h3>
                {agentData.bear_thesis ? (
                  <div className="prose prose-invert prose-sm prose-rose"><ReactMarkdown>{agentData.bear_thesis}</ReactMarkdown></div>
                ) : (
                  <div className="flex items-center gap-2 text-rose-600/50"><Loader2 className="w-4 h-4 animate-spin" /> 空头专家正在寻找破绽...</div>
                )}
              </motion.div>
            )}
          </div>

          {/* 🌟 CIO 交互看板 (动态适配模型) */}
          {isWaitingFeedback && (
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
              <InteractiveValuation 
                initialData={agentData.valuation_data || {}} 
                threadId={threadId}
                onConfirm={handleResumeAfterFeedback} 
              />
            </motion.div>
          )}

          {/* 终版报告 */}
          {agentData.final_report && (
            <motion.div 
              ref={reportRef} 
              initial={{ opacity: 0, y: 20 }} 
              animate={{ opacity: 1, y: 0 }} 
              transition={{ delay: 0.2 }}
              className="mt-12 bg-[#141416] border border-blue-900/50 rounded-2xl shadow-2xl overflow-hidden relative group"
            >
              <button 
                onClick={exportToPDF}
                className="absolute top-5 right-6 px-4 py-2 bg-slate-800/80 hover:bg-slate-700 border border-slate-600 rounded-lg flex items-center gap-2 text-sm text-slate-200 transition-all z-10 opacity-70 group-hover:opacity-100"
              >
                <Download className="w-4 h-4" /> 导出 PDF
              </button>

              <div className="bg-gradient-to-r from-blue-900/40 via-slate-900 to-[#141416] px-8 py-6 border-b border-blue-900/30 flex items-center gap-4">
                <div className="p-3 bg-blue-500/20 rounded-xl"><Scale className="w-6 h-6 text-blue-400" /></div>
                <div>
                  <h2 className="text-2xl font-bold text-white tracking-wide">首席投委会最终裁决 (IC Report)</h2>
                  <p className="text-blue-400/80 text-sm mt-1">Chief Investment Officer Synthesis & Final Verdict</p>
                </div>
              </div>
              
              <div className="p-8 md:p-10 prose prose-invert prose-lg max-w-none prose-headings:text-white prose-a:text-blue-400 prose-strong:text-blue-300">
                <ReactMarkdown>{agentData.final_report}</ReactMarkdown>
              </div>

              <div className="py-4 text-center text-xs text-slate-600 border-t border-slate-800/50 bg-[#101012]">
                Generated by QuantFinance AI Agent • Engine: LangGraph & qwen3.5-flash • {new Date().toLocaleDateString()}
              </div>
            </motion.div>
          )}

        </div>
      </main>
    </div>
  );
}