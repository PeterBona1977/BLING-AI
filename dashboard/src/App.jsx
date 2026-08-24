import React, { useState, useEffect } from 'react';
import {
  Bot,
  Zap,
  Send,
  TrendingUp,
  RefreshCw,
  Share2,
  Package,
  Copy,
  Check,
  Code2,
  Globe,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Users,
  Link,
  Video,
  Image as ImageIcon,
  Mail
} from 'lucide-react';

const BACKEND_URL = "https://web-production-803c4.up.railway.app";

export default function App() {
  const [status, setStatus] = useState(null);
  const [opportunities, setOpportunities] = useState([]);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [prompt, setPrompt] = useState("");
  const [agentResponse, setAgentResponse] = useState("");
  const [agentLoading, setAgentLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [openCodeId, setOpenCodeId] = useState(null);
  const [activeTab, setActiveTab] = useState("opportunities");

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statusRes, oppsRes, leadsRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/status`).then(res => res.json()).catch(() => null),
        fetch(`${BACKEND_URL}/api/opportunities`).then(res => res.json()).catch(() => ({ opportunities: [] })),
        fetch(`${BACKEND_URL}/api/leads`).then(res => res.json()).catch(() => ({ leads: [] }))
      ]);
      setStatus(statusRes);
      if (oppsRes && oppsRes.opportunities) setOpportunities(oppsRes.opportunities);
      if (leadsRes && leadsRes.leads) setLeads(leadsRes.leads);
    } catch (e) {
      console.error("Erro:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleCopy = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

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
      setAgentResponse(data.result || "Sem resposta.");
      fetchData();
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
            <h1 className="text-xl font-bold tracking-tight">BLING AI Viral Marketing & Product Engine</h1>
            <p className="text-xs text-slate-400">Produtos Digitais + Vídeos TikTok/Reels + CRM</p>
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
            <span className="text-slate-300">{status ? 'Autonomia 100%' : 'Offline'}</span>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="max-w-6xl mx-auto mt-6 flex gap-3 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab("opportunities")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${activeTab === "opportunities"
              ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
              : "text-slate-400 hover:text-slate-200"
            }`}
        >
          <TrendingUp className="w-4 h-4" />
          <span>Oportunidades & Campanhas ({opportunities.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("leads")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${activeTab === "leads"
              ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
              : "text-slate-400 hover:text-slate-200"
            }`}
        >
          <Users className="w-4 h-4" />
          <span>CRM de Leads ({leads.length})</span>
        </button>
      </div>

      <main className="max-w-6xl mx-auto mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {activeTab === "opportunities" ? (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                  <TrendingUp className="w-4 h-4" />
                  <span>Produtos, Páginas e Guiões Multimédia</span>
                </div>
              </div>

              {opportunities.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-sm">
                  A carregar dados do Supabase...
                </div>
              ) : (
                <div className="space-y-4">
                  {opportunities.map((opp) => {
                    const publicUrl = `${BACKEND_URL}/p/${opp.id}`;
                    return (
                      <div key={opp.id} className="p-4 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-3">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-slate-800 text-emerald-400">
                                {opp.source}
                              </span>
                              <span className="text-xs text-slate-500">
                                {new Date(opp.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                            <h3 className="font-semibold text-slate-200 mt-1 text-sm md:text-base">{opp.title}</h3>
                          </div>
                          <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
                            Score: {opp.score}/10
                          </span>
                        </div>

                        {opp.summary && (
                          <p className="text-xs text-slate-400 leading-relaxed">
                            {opp.summary}
                          </p>
                        )}

                        {opp.product_concept && (
                          <div className="p-2.5 bg-indigo-950/30 border border-indigo-500/20 rounded-lg flex items-start gap-2">
                            <Package className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" />
                            <div className="text-xs text-indigo-200 leading-relaxed">
                              <span className="font-semibold text-indigo-300">Produto: </span>
                              {opp.product_concept}
                            </div>
                          </div>
                        )}

                        {/* Landing Page Pública */}
                        {opp.landing_page_html && (
                          <div className="p-2.5 bg-slate-900 border border-slate-800 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                            <div className="flex items-center gap-2 text-xs font-medium text-cyan-400">
                              <Globe className="w-3.5 h-3.5" />
                              <span>Landing Page Pública</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <a
                                href={publicUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs text-cyan-300 hover:text-cyan-100 flex items-center gap-1 bg-cyan-950/60 border border-cyan-500/30 px-2.5 py-1 rounded transition"
                              >
                                <ExternalLink className="w-3 h-3" />
                                <span>Abrir URL Pública</span>
                              </a>
                              <button
                                onClick={() => handleCopy(publicUrl, `link-${opp.id}`)}
                                className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 bg-slate-800 px-2 py-1 rounded transition"
                              >
                                {copiedId === `link-${opp.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Link className="w-3 h-3" />}
                                <span>{copiedId === `link-${opp.id}` ? "Link Copiado!" : "Copiar Link"}</span>
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Guião TikTok / Reels */}
                        {opp.video_script && (
                          <div className="p-3 bg-rose-950/20 border border-rose-500/20 rounded-lg space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="flex items-center gap-1.5 text-[11px] font-semibold text-rose-400">
                                <Video className="w-3.5 h-3.5" /> Guião TikTok / Reels / Shorts (30s)
                              </span>
                              <button
                                onClick={() => handleCopy(opp.video_script, `video-${opp.id}`)}
                                className="text-xs text-rose-300 hover:text-white flex items-center gap-1 bg-rose-950/60 border border-rose-500/30 px-2 py-0.5 rounded transition"
                              >
                                {copiedId === `video-${opp.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                                <span>{copiedId === `video-${opp.id}` ? "Guião Copiado!" : "Copiar Guião"}</span>
                              </button>
                            </div>
                            <p className="text-xs text-rose-200/90 whitespace-pre-wrap font-sans bg-slate-950 p-2.5 rounded border border-rose-950/40 leading-relaxed">
                              {opp.video_script}
                            </p>
                          </div>
                        )}

                        {/* Prompt de Imagem/Vídeo IA */}
                        {opp.ai_media_prompt && (
                          <div className="p-2.5 bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2 text-xs font-medium text-amber-400">
                              <ImageIcon className="w-3.5 h-3.5 shrink-0" />
                              <span className="truncate max-w-[280px] sm:max-w-md text-amber-200/80 font-mono text-[11px]">Prompt Midjourney: {opp.ai_media_prompt}</span>
                            </div>
                            <button
                              onClick={() => handleCopy(opp.ai_media_prompt, `media-${opp.id}`)}
                              className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 bg-slate-800 px-2 py-0.5 rounded transition shrink-0"
                            >
                              {copiedId === `media-${opp.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                              <span>{copiedId === `media-${opp.id}` ? "Copiado!" : "Copiar Prompt"}</span>
                            </button>
                          </div>
                        )}

                        {/* Cold Email B2B */}
                        {opp.cold_email && (
                          <div className="p-2.5 bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
                              <Mail className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                              <span className="truncate max-w-[280px] sm:max-w-md text-slate-400 text-[11px]">Email Outreach B2B</span>
                            </div>
                            <button
                              onClick={() => handleCopy(opp.cold_email, `email-${opp.id}`)}
                              className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 bg-slate-800 px-2 py-0.5 rounded transition shrink-0"
                            >
                              {copiedId === `email-${opp.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                              <span>{copiedId === `email-${opp.id}` ? "Copiado!" : "Copiar Email"}</span>
                            </button>
                          </div>
                        )}

                        {/* Código Fonte */}
                        {opp.code_payload && (
                          <div className="p-2.5 bg-slate-900 border border-slate-800 rounded-lg">
                            <div className="flex items-center justify-between">
                              <button
                                onClick={() => setOpenCodeId(openCodeId === opp.id ? null : opp.id)}
                                className="text-xs font-medium text-emerald-400 flex items-center gap-1.5 hover:underline"
                              >
                                <Code2 className="w-3.5 h-3.5" />
                                <span>{openCodeId === opp.id ? "Ocultar Código" : "Ver Código do Produto"}</span>
                                {openCodeId === opp.id ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                              </button>
                              <button
                                onClick={() => handleCopy(opp.code_payload, `code-${opp.id}`)}
                                className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 bg-slate-800 px-2 py-0.5 rounded transition"
                              >
                                {copiedId === `code-${opp.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                                <span>{copiedId === `code-${opp.id}` ? "Copiado!" : "Copiar Código"}</span>
                              </button>
                            </div>
                            {openCodeId === opp.id && (
                              <pre className="mt-2 p-3 bg-slate-950 text-emerald-300 text-[11px] font-mono rounded overflow-x-auto border border-slate-900 whitespace-pre-wrap">
                                {opp.code_payload}
                              </pre>
                            )}
                          </div>
                        )}

                        {/* Post para Redes Sociais */}
                        {opp.social_post && (
                          <div className="p-3 bg-slate-900/90 border border-slate-800 rounded-lg space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="flex items-center gap-1.5 text-[11px] font-medium text-slate-400">
                                <Share2 className="w-3 h-3 text-cyan-400" /> Post Pronto (LinkedIn / X)
                              </span>
                              <button
                                onClick={() => handleCopy(`${opp.social_post}\n\n👉 Acede aqui: ${publicUrl}`, `post-${opp.id}`)}
                                className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 bg-slate-800/80 px-2 py-0.5 rounded transition"
                              >
                                {copiedId === `post-${opp.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                                <span>{copiedId === `post-${opp.id}` ? "Copiado com Link!" : "Copiar Post + Link"}</span>
                              </button>
                            </div>
                            <p className="text-xs text-slate-300 whitespace-pre-wrap font-sans bg-slate-950 p-2.5 rounded border border-slate-900">
                              {opp.social_post}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            /* CRM de Leads */
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                  <Users className="w-4 h-4" />
                  <span>Leads & Inscrições Recebidas ({leads.length})</span>
                </div>
              </div>

              {leads.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-sm">
                  Nenhum lead capturado ainda. Partilha os vídeos do TikTok e os posts com o link público para começar a receber inscrições!
                </div>
              ) : (
                <div className="space-y-3">
                  {leads.map((l) => (
                    <div key={l.id} className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl flex items-center justify-between">
                      <div>
                        <div className="text-xs font-semibold text-emerald-400">{l.email}</div>
                        <div className="text-[11px] text-slate-400 mt-0.5">Interesse: {l.product_name}</div>
                      </div>
                      <div className="text-[10px] text-slate-500">
                        {new Date(l.created_at).toLocaleDateString()} {new Date(l.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Prompt Lateral */}
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
            <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm mb-4">
              <Bot className="w-4 h-4 text-emerald-400" />
              <span>Prompt Estratégico Multimédia</span>
            </div>

            <form onSubmit={handleAskAgent} className="space-y-3">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ex: Cria um vídeo viral para o TikTok sobre uma ferramenta de transcrição..."
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
        </div>
      </main>
    </div>
  );
}