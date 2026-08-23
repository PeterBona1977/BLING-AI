import React, { useState, useEffect } from 'react';
import {
  Bot,
  Activity,
  Zap,
  Send,
  Database,
  ShieldCheck,
  TrendingUp,
  Sparkles,
  RefreshCw
} from 'lucide-react';

const BACKEND_URL = "https://web-production-803c4.up.railway.app";

export default function App() {
  const [status, setStatus] = useState(null);
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [prompt, setPrompt] = useState("");
  const [agentResponse, setAgentResponse] = useState("");
  const [agentLoading, setAgentLoading] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statusRes, oppsRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/status`).then(res => res.json()).catch(() => null),
        fetch(`${BACKEND_URL}/api/opportunities`).then(res => res.json()).catch(() => ({ opportunities: [] }))
      ]);
      setStatus(statusRes);
      if (oppsRes && oppsRes.opportunities) {
        setOpportunities(oppsRes.opportunities);
      }
    } catch (e) {
      console.error("Erro ao carregar dados:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleAskAgent = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setAgentLoading(true);
    setAgentResponse("");

    try {
      const res = await fetch(`${BACKEND_URL}/api/agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt })
      });
      const data = await res.json();
      setAgentResponse(data.result || "Sem resposta do agente.");
    } catch (err) {
      setAgentResponse("Erro ao contactar o agente.");
    } finally {
      setAgentLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8 font-sans">
      <header className="max-w-6xl mx-auto flex flex-col sm:flex-row justify-between items-center pb-6 border-b border-slate-800 gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400">
            <Zap className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">BLING AI Autonomous Engine</h1>
            <p className="text-xs text-slate-400">Agente de Inteligência e Automação de Mercado</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 transition"
            title="Atualizar dados"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs">
            <span className={`w-2 h-2 rounded-full ${status ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`}></span>
            <span className="text-slate-300">{status ? 'Autonomous Loop Ativo' : 'Offline'}</span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto mt-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                <TrendingUp className="w-4 h-4" />
                <span>Oportunidades Detetadas em Tempo Real (Supabase)</span>
              </div>
              <span className="text-xs bg-slate-800 text-slate-400 px-2.5 py-1 rounded-full">
                {opportunities.length} registos
              </span>
            </div>

            {opportunities.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-sm">
                Nenhuma oportunidade detetada de momento. O scanner corre a cada 10 minutos.
              </div>
            ) : (
              <div className="space-y-3">
                {opportunities.map((opp) => (
                  <div key={opp.id} className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-xl hover:border-slate-700 transition">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                            {opp.source}
                          </span>
                          <span className="text-xs text-slate-500">
                            {new Date(opp.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <h3 className="font-medium text-slate-200 mt-1.5 text-sm md:text-base">{opp.title}</h3>
                      </div>
                      <div className="flex flex-col items-end">
                        <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          Score: {opp.score}/10
                        </span>
                      </div>
                    </div>

                    {opp.summary && (
                      <p className="text-xs text-slate-400 mt-2 line-clamp-2">
                        {opp.summary}
                      </p>
                    )}

                    {opp.action_plan && (
                      <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex items-start gap-2">
                        <Sparkles className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                        <p className="text-xs text-amber-200/90 leading-relaxed font-mono">
                          {opp.action_plan}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
            <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm mb-4">
              <Bot className="w-4 h-4 text-emerald-400" />
              <span>Prompt Manual com o Agente</span>
            </div>

            <form onSubmit={handleAskAgent} className="space-y-3">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Pede uma análise ou instrução direta ao agente..."
                rows={4}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 resize-none"
              />
              <button
                type="submit"
                disabled={agentLoading || !prompt.trim()}
                className="w-full bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-slate-950 font-semibold text-sm py-2.5 px-4 rounded-xl flex items-center justify-center gap-2 transition"
              >
                {agentLoading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Executar Agente</span>
                  </>
                )}
              </button>
            </form>

            {agentResponse && (
              <div className="mt-4 p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
                {agentResponse}
              </div>
            )}
          </div>

          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-4 text-xs space-y-2.5 text-slate-400">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5"><Database className="w-3.5 h-3.5" /> Base de Dados</span>
              <span className="text-emerald-400">PostgreSQL (Supabase)</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5"><ShieldCheck className="w-3.5 h-3.5" /> Motor LLM</span>
              <span className="text-slate-200">Groq High-Speed</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5"><Activity className="w-3.5 h-3.5" /> Frequência de Scan</span>
              <span className="text-slate-200">10 Minutos</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}