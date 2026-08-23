import React, { useState, useEffect } from 'react';
import {
  Bot,
  Send,
  Activity,
  Search,
  Terminal,
  DollarSign,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Zap,
  Globe,
  Database
} from 'lucide-react';

const API_URL = "https://web-production-803c4.up.railway.app";

function App() {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const [apiStatus, setApiStatus] = useState('checking');
  const [history, setHistory] = useState([]);

  // Verificar estado da API
  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_URL}/health`);
      if (res.ok) {
        setApiStatus('online');
      } else {
        setApiStatus('offline');
      }
    } catch (err) {
      setApiStatus('offline');
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || loading) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch(`${API_URL}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt }),
      });

      const data = await res.json();

      if (res.ok) {
        setResponse(data);
        setHistory(prev => [{ prompt, timestamp: new Date().toLocaleTimeString(), status: 'success' }, ...prev]);
      } else {
        setError(data.detail || 'Erro ao processar pedido.');
        setHistory(prev => [{ prompt, timestamp: new Date().toLocaleTimeString(), status: 'error' }, ...prev]);
      }
    } catch (err) {
      setError('Não foi possível ligar ao servidor do BLING AI.');
      setHistory(prev => [{ prompt, timestamp: new Date().toLocaleTimeString(), status: 'error' }, ...prev]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-indigo-600 rounded-lg shadow-lg shadow-indigo-500/30">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-xl tracking-wide bg-gradient-to-r from-white via-slate-200 to-indigo-400 bg-clip-text text-transparent">
              BLING AI
            </h1>
            <p className="text-xs text-slate-400">Autonomous Opportunity Scanner</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-xs bg-slate-800/80 px-3 py-1.5 rounded-full border border-slate-700">
            <span className={`w-2 h-2 rounded-full ${apiStatus === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`}></span>
            <span className="capitalize text-slate-300">Backend: {apiStatus}</span>
          </div>
          <button
            onClick={checkHealth}
            className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors"
            title="Atualizar Estado"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Left Column: Command & Input Panel */}
        <div className="lg:col-span-2 space-y-6">

          {/* Executive Input Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <div className="flex items-center space-x-2 mb-4 text-indigo-400 font-semibold text-sm">
              <Zap className="w-4 h-4" />
              <span>INSTRUÇÕES DO AGENTE</span>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Ex: Procura oportunidades de afiliados iGaming ou analisa novos tokens Solana em tendência..."
                  className="w-full h-32 bg-slate-950 border border-slate-800 rounded-lg p-4 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                />
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500">
                  Pressiona Executar para acionar a varredura autónoma
                </span>
                <button
                  type="submit"
                  disabled={loading || !prompt.trim()}
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-lg text-sm font-medium transition-all flex items-center space-x-2 shadow-lg shadow-indigo-600/20"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>A processar...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      <span>Executar Agente</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Results Display Window */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl min-h-[300px]">
            <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2 text-slate-300 font-semibold text-sm">
                <Terminal className="w-4 h-4 text-emerald-400" />
                <span>SAÍDA DA EXECUÇÃO</span>
              </div>
            </div>

            {loading && (
              <div className="flex flex-col items-center justify-center py-16 space-y-3 text-slate-400">
                <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
                <p className="text-sm">O agente está a analisar o pedido e a recolher dados...</p>
              </div>
            )}

            {error && (
              <div className="p-4 bg-rose-950/30 border border-rose-800/50 rounded-lg flex items-start space-x-3 text-rose-300">
                <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400 mt-0.5" />
                <div className="text-sm">
                  <p className="font-semibold">Erro na Execução</p>
                  <p className="text-xs text-rose-400/80 mt-1">{error}</p>
                </div>
              </div>
            )}

            {response && !loading && (
              <div className="space-y-4">
                <div className="p-4 bg-emerald-950/20 border border-emerald-800/40 rounded-lg flex items-center space-x-3 text-emerald-300 text-sm">
                  <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                  <span>Análise concluída com sucesso!</span>
                </div>

                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 overflow-x-auto">
                  <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
                    {typeof response === 'object' ? JSON.stringify(response, null, 2) : response}
                  </pre>
                </div>
              </div>
            )}

            {!response && !loading && !error && (
              <div className="text-center py-16 text-slate-600 text-sm">
                Aguardando execução. Introduz um comando para visualizar os resultados aqui.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: System Analytics & Quick Actions */}
        <div className="space-y-6">
          {/* Status Metrics */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
            <h3 className="text-xs font-bold text-slate-400 tracking-wider uppercase">Métricas do Sistema</h3>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                <div className="flex items-center space-x-2 text-slate-400 text-xs mb-1">
                  <Globe className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Ambiente</span>
                </div>
                <p className="text-sm font-semibold text-slate-200">Railway API</p>
              </div>

              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                <div className="flex items-center space-x-2 text-slate-400 text-xs mb-1">
                  <Database className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Modelo AI</span>
                </div>
                <p className="text-sm font-semibold text-slate-200">Groq LLM</p>
              </div>
            </div>
          </div>

          {/* Activity Log */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
            <h3 className="text-xs font-bold text-slate-400 tracking-wider uppercase mb-3">Histórico Recente</h3>

            {history.length === 0 ? (
              <p className="text-xs text-slate-600">Nenhuma atividade registada nesta sessão.</p>
            ) : (
              <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
                {history.map((item, idx) => (
                  <div key={idx} className="bg-slate-950 p-2.5 rounded border border-slate-800/60 text-xs space-y-1">
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="font-mono text-[10px]">{item.timestamp}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${item.status === 'success' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50' : 'bg-rose-950 text-rose-400 border border-rose-800/50'}`}>
                        {item.status}
                      </span>
                    </div>
                    <p className="text-slate-300 truncate">{item.prompt}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </main>
    </div>
  );
}

export default App;