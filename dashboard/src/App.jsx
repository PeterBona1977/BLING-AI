import React, { useState, useEffect } from 'react';
import {
  Zap,
  Cpu,
  ShieldAlert,
  RefreshCw
} from 'lucide-react';

export default function App() {
  const [statusData, setStatusData] = useState({ status: 'OFFLINE', active_modules_count: 0, modules: [] });
  const [pendingRequests, setPendingRequests] = useState([]);
  const [loading, setLoading] = useState(false);

  // URL do Backend (será atualizada quando o servidor Python estiver na nuvem)
  const API_URL = "http://localhost:8000";

  const fetchData = async () => {
    setLoading(true);
    try {
      const resStatus = await fetch(`${API_URL}/api/status`);
      if (resStatus.ok) {
        const data = await resStatus.json();
        setStatusData(data);
      }

      const resPending = await fetch(`${API_URL}/api/pending-inputs`);
      if (resPending.ok) {
        const pending = await resPending.json();
        setPendingRequests(pending.pending_requests || []);
      }
    } catch (err) {
      console.log("Erro a ligar à API:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-4 pb-20">
      {/* HEADER MOBILE */}
      <header className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Zap className="w-7 h-7 text-amber-400 fill-amber-400" />
          <h1 className="text-2xl font-black bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent">
            BLING AI
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchData}
            className="p-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-300 active:scale-95 transition-transform"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <span className={`px-3 py-1 rounded-full text-xs font-bold border ${statusData.status === 'ONLINE'
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
            }`}>
            {statusData.status}
          </span>
        </div>
      </header>

      {/* METRICAS */}
      <div className="grid grid-cols-2 gap-3 mb-6">
        <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-xl">
          <p className="text-[10px] text-slate-400 uppercase font-semibold">Módulos Ativos</p>
          <p className="text-xl font-bold text-white mt-1">{statusData.active_modules_count}</p>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-xl">
          <p className="text-[10px] text-slate-400 uppercase font-semibold">Pedidos Pendentes</p>
          <p className="text-xl font-bold text-amber-400 mt-1">{pendingRequests.length}</p>
        </div>
      </div>

      {/* PEDIDOS DE INPUTS */}
      {pendingRequests.length > 0 && (
        <div className="mb-6 bg-amber-950/20 border border-amber-500/30 rounded-2xl p-4">
          <div className="flex items-center gap-2 text-amber-400 mb-3 font-semibold text-xs uppercase tracking-wider">
            <ShieldAlert className="w-4 h-4" />
            <span>Ação Necessária (Credenciais / Inputs)</span>
          </div>

          {pendingRequests.map((req, idx) => (
            <div key={idx} className="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-3 mb-2">
              <p className="text-xs font-mono text-slate-300">{req.key}</p>
              <input
                type="text"
                placeholder="Inserir dados para o Vault..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white focus:outline-none focus:border-amber-500"
              />
              <button className="w-full bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold py-2 rounded-lg text-xs uppercase">
                Submeter para o Vault
              </button>
            </div>
          ))}
        </div>
      )}

      {/* MÓDULOS EM EXECUÇÃO */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-4">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-blue-400" />
          Módulos Autónomos (`modules/`)
        </h3>

        <div className="space-y-2">
          {statusData.modules.length > 0 ? (
            statusData.modules.map((mod, i) => (
              <div key={i} className="flex items-center justify-between p-2.5 bg-slate-900 rounded-lg border border-slate-800 text-xs">
                <span className="font-mono text-slate-200 truncate">{mod}.py</span>
                <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  RUNNING
                </span>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-500 py-2">Nenhum módulo detetado.</p>
          )}
        </div>
      </div>
    </div>
  );
}