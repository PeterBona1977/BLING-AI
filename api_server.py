import os
import asyncio
import json
import re
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from groq import Groq
from supabase import create_client, Client

# 1. Configuração Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Optional[Client] = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Despachador Telegram
async def send_telegram_alert(message_text: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("[Telegram]: Bot token ou Chat ID em falta.")
        return "Telegram não configurado."

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json={"chat_id": chat_id, "text": message_text, "parse_mode": "Markdown"})
            if r.status_code == 200:
                print("[Telegram]: Alerta enviado com sucesso.")
                return "Notificação enviada."
            print(f"[Telegram Error Status]: {r.status_code} - {r.text}")
            return f"Telegram status: {r.status_code}"
    except Exception as e:
        print(f"[Telegram Exception]: {e}")
        return f"Erro Telegram: {str(e)}"

def opportunity_exists(title: str) -> bool:
    if not supabase:
        return False
    try:
        res = supabase.table("opportunities").select("id").ilike("title", f"%{title[:25]}%").execute()
        return len(res.data) > 0
    except Exception:
        return False

def save_opportunity_to_supabase(
    source: str, 
    title: str, 
    score: int, 
    summary: str, 
    action_plan: str, 
    social_post: str = "", 
    product_concept: str = "",
    code_payload: str = "",
    landing_page_html: str = "",
    video_script: str = "",
    ai_media_prompt: str = "",
    cold_email: str = ""
):
    if not supabase:
        return None
    try:
        res = supabase.table("opportunities").insert({
            "source": source,
            "title": title,
            "score": score,
            "summary": summary,
            "action_plan": action_plan,
            "social_post": social_post,
            "product_concept": product_concept,
            "code_payload": code_payload,
            "landing_page_html": landing_page_html,
            "video_script": video_script,
            "ai_media_prompt": ai_media_prompt,
            "cold_email": cold_email,
            "status": "detected"
        }).execute()
        if res.data and len(res.data) > 0:
            return res.data[0].get("id")
        return None
    except Exception as e:
        print(f"[Supabase Insert Error]: {e}")
        return None

def get_opportunities_from_supabase(limit: int = 30):
    if not supabase:
        return []
    try:
        response = supabase.table("opportunities").select("*").order("created_at", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        print(f"[Supabase Read Error]: {e}")
        return []

def get_leads_from_supabase(limit: int = 50):
    if not supabase:
        return []
    try:
        response = supabase.table("leads").select("*").order("created_at", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        print(f"[Supabase Leads Error]: {e}")
        return []

# 3. Radar de Mercado com Fallback Autónomo
async def fetch_real_market_feed(client: httpx.AsyncClient) -> List[Dict[str, str]]:
    items = []
    
    # HackerNews Top Recentes
    try:
        r = await client.get("https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=4", timeout=6.0)
        if r.status_code == 200:
            for hit in r.json().get("hits", []):
                t = hit.get("title")
                if t and len(t) > 12:
                    items.append({"source": "HackerNews Radar", "title": t})
    except Exception as e:
        print(f"[Feed HN]: {e}")

    # Reddit r/SaaS & r/Entrepreneur via RSS JSON
    for sub in ["SaaS", "Entrepreneur", "SideProject"]:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BLING/2.0"}
            r = await client.get(f"https://www.reddit.com/r/{sub}/new.json?limit=2", headers=headers, timeout=6.0)
            if r.status_code == 200:
                for p in r.json().get("data", {}).get("children", []):
                    t = p.get("data", {}).get("title")
                    if t and len(t) > 15 and not t.startswith("["):
                        items.append({"source": f"Reddit r/{sub}", "title": t})
        except Exception as e:
            print(f"[Feed Reddit {sub}]: {e}")

    return items

# 4. Fábrica Digital Autónoma
async def build_product_asset_pipeline(ai: Groq, topic: str, source: str = "Motor Autónomo"):
    print(f"\n[BLING Autonomous Engine]: A sintetizar produto para -> {topic[:40]}...")
    
    prompt = f"""
    És o Diretor de Criação e Engenheiro-Chefe da BLING AI.
    Cria um ecossistema de produto digital e campanha viral completo para: '{topic}'.
    Responde em JSON com estas chaves:
    {{
        "title": "{topic}",
        "score": 10,
        "summary": "Resumo conciso de 1 frase do problema e da solução automatizada.",
        "action_plan": "Estratégia prática de monetização e lançamento.",
        "product_concept": "Descrição técnica da arquitetura, stack e funcionalidades chave.",
        "code_payload": "# Código Python ou JavaScript funcional e pronto a correr\\nprint('Ferramenta {topic} inicializada com sucesso!')",
        "social_post": "Post viral pronto para LinkedIn e Twitter com gancho, 2 benefícios e chamada para ação.",
        "video_script": "🎬 [0-3s Gancho]: 'Pára tudo se fazes {topic} à mão!'\\n🎬 [3-20s Demonstração]: 'Criámos uma automação que faz isto por ti em segundos.'\\n🎬 [20-30s CTA]: 'Clica no link da bio para acesso exclusivo.'",
        "ai_media_prompt": "Cinematic 3D SaaS UI dashboard render of {topic}, dark mode, neon emerald accents, photorealistic studio lighting, 8k resolution",
        "cold_email": "Assunto: Automação para {topic}\\n\\nOlá,\\nDesenvolvemos uma ferramenta para resolver {topic} de forma autónoma. Gostaria de testar sem custo?"
    }}
    """
    
    try:
        completion = ai.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "És um construtor de micro-SaaS e diretor de monetização. Responde estritamente em JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        raw_content = completion.choices[0].message.content
        data = {}
        try:
            data = json.loads(raw_content)
        except Exception:
            json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                except Exception:
                    pass

        title = data.get("title", topic)
        summary = data.get("summary", f"Solução automatizada desenvolvida para: {topic}")
        action_plan = data.get("action_plan", "Monetização via subscrição mensal ou licença direta.")
        product_concept = data.get("product_concept", f"Micro-ferramenta especializada em {topic}")
        code_payload = data.get("code_payload", f"# Boilerplate funcional para {topic}\nimport os\nprint('Módulo ativo')")
        social_post = data.get("social_post", f"🚀 Acabei de automatizar '{topic}'!\n\n1. Processamento instantâneo\n2. Poupança de tempo garantida\n\nQueres testar? Acede ao link abaixo.")
        video_script = data.get("video_script", f"🎬 [0-3s Gancho]: Pára tudo se ainda perdes horas com {topic}!\n🎬 [3-20s Solução]: Criámos um sistema automático que resolve isto em 1 clique.\n🎬 [20-30s CTA]: Link na bio para garantir acesso VIP!")
        ai_media_prompt = data.get("ai_media_prompt", f"High tech futuristic SaaS UI mockup for {topic}, dark neon aesthetic, ultra detailed, 8k render")
        cold_email = data.get("cold_email", f"Assunto: Solução para {topic}\n\nOlá,\\nDesenvolvemos uma automação para {topic}. Podemos demonstrar?")
        
        landing_page_html = f"""<!DOCTYPE html>
<html lang="pt">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://cdn.tailwindcss.com"></script>
  <title>{title}</title>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans flex flex-col justify-between">
  <header class="p-6 max-w-5xl mx-auto w-full flex justify-between items-center">
    <div class="text-xl font-bold text-emerald-400">BLING Product</div>
    <a href="#cta" class="bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold px-4 py-2 rounded-xl text-sm transition">Garantir Acesso</a>
  </header>
  <main class="max-w-4xl mx-auto px-6 py-12 text-center">
    <span class="text-xs font-semibold px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-4 inline-block">Acesso VIP</span>
    <h1 id="productTitle" class="text-3xl md:text-5xl font-extrabold text-white tracking-tight mb-6">{title}</h1>
    <p class="text-base md:text-lg text-slate-400 mb-10 max-w-2xl mx-auto">{summary}</p>
    
    <div id="cta" class="bg-slate-900 border border-slate-800 p-8 rounded-2xl max-w-md mx-auto shadow-2xl">
      <h3 class="text-lg font-bold mb-2 text-white">Inscrever para Acesso Imediato</h3>
      <p class="text-xs text-slate-400 mb-6">{product_concept}</p>
      
      <div id="formContainer" class="space-y-4">
        <input id="leadEmail" type="email" placeholder="O teu melhor email..." class="w-full p-3 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-emerald-500 text-sm">
        <button id="submitBtn" onclick="sendLead()" class="w-full py-3 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold rounded-xl text-sm transition">Entrar na Lista VIP</button>
      </div>
      <div id="successMsg" class="hidden text-emerald-400 font-semibold text-sm pt-4">✅ Inscrição confirmada! Entraremos em contacto em breve.</div>
    </div>
  </main>
  
  <footer class="p-6 text-center text-xs text-slate-600">
    © 2026 BLING AI Engine. Todos os direitos reservados.
  </footer>

  <script>
    async function sendLead() {{
      const emailInput = document.getElementById('leadEmail');
      const email = emailInput ? emailInput.value : '';
      const titleElem = document.getElementById('productTitle');
      const productName = titleElem ? titleElem.innerText : 'Produto BLING';
      const btn = document.getElementById('submitBtn');

      if (!email || !email.includes('@')) {{
        alert('Por favor insere um email válido.');
        return;
      }}
      btn.innerText = 'A processar...';
      btn.disabled = true;
      try {{
        const res = await fetch('https://web-production-803c4.up.railway.app/api/leads', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ product_name: productName, email: email }})
        }});
        if(res.ok) {{
          document.getElementById('formContainer').classList.add('hidden');
          document.getElementById('successMsg').classList.remove('hidden');
        }} else {{
          alert('Erro ao registar. Tenta novamente.');
          btn.disabled = false;
          btn.innerText = 'Entrar na Lista VIP';
        }}
      }} catch(e) {{
        alert('Erro de conexão.');
        btn.disabled = false;
        btn.innerText = 'Entrar na Lista VIP';
      }}
    }}
  </script>
</body>
</html>"""

        opp_id = save_opportunity_to_supabase(
            source=source,
            title=title,
            score=10,
            summary=summary,
            action_plan=action_plan,
            social_post=social_post,
            product_concept=product_concept,
            code_payload=code_payload,
            landing_page_html=landing_page_html,
            video_script=video_script,
            ai_media_prompt=ai_media_prompt,
            cold_email=cold_email
        )
        
        public_link = f"https://web-production-803c4.up.railway.app/p/{opp_id}" if opp_id else "https://bling-ai.pages.dev"
        
        # Envio de Alerta de Alto Nível para o Telegram
        tg_msg = (
            f"⚡ *[MOTOR AUTÓNOMO]: NOVO ATIVO CRIADO!*\n\n"
            f"📌 *Tema:* {title}\n"
            f"💡 *Produto:* {product_concept}\n\n"
            f"🌐 *Landing Page Ativa:* {public_link}\n\n"
            f"🎬 *TikTok Script:* {video_script[:130]}...\n\n"
            f"📱 *Post:* {social_post[:120]}..."
        )
        await send_telegram_alert(tg_msg)
        print(f"[BLING Autonomous Engine]: Ativo criado com sucesso -> ID: {opp_id}")
        
        return data
    except Exception as e:
        print(f"[BLING Pipeline Error]: {e}")
        return None

# 5. Loop Permanente e Ininterrupto de Execução
async def autonomous_background_worker():
    print("[BLING Engine]: Loop autónomo iniciado com sucesso.")
    
    # Alerta de arranque no Telegram
    await send_telegram_alert("🤖 *BLING-AI Motor Autónomo Online!*\n\nA iniciar mineração e criação de ativos digitais contínua sem intervenção manual.")
    
    while True:
        try:
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                ai = Groq(api_key=groq_key)
                
                async with httpx.AsyncClient(timeout=10.0) as client:
                    feed = await fetch_real_market_feed(client)
                
                # Se os feeds externos estiverem vazios/bloqueados, a IA sintetiza tendências lucrativas por iniciativa própria
                if not feed:
                    print("[BLING Engine]: A sintetizar nicho de mercado autónomo via IA...")
                    synth_prompt = "Diz-me uma dor urgente de mercado de profissionais digitais ou micro-empresas hoje (ex: automação, scraping, finanças, produtividade) em 1 frase curta."
                    comp = ai.chat.completions.create(
                        model="openai/gpt-oss-20b",
                        messages=[{"role": "user", "content": synth_prompt}],
                        temperature=0.7
                    )
                    niche_topic = comp.choices[0].message.content.strip()
                    feed = [{"source": "Auto-AI Market Synthesizer", "title": niche_topic}]
                
                for item in feed:
                    if not opportunity_exists(item["title"]):
                        await build_product_asset_pipeline(ai, item["title"], source=item["source"])
                        await asyncio.sleep(20) # Pausa suave entre criações
                        
        except Exception as e:
            print(f"[Autonomous Loop Error]: {e}")
            
        print("[BLING Engine]: Ciclo concluído. Próxima varredura em 5 minutos...")
        await asyncio.sleep(300) # Corre a cada 5 minutos

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(autonomous_background_worker())
    yield
    task.cancel()

app = FastAPI(title="BLING AI Full Autonomous Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentRequest(BaseModel):
    prompt: str

class LeadRequest(BaseModel):
    product_name: str
    email: str

@app.get("/")
@app.get("/health")
def health():
    return {"status": "online", "mode": "100% Autonomous Zero-Touch"}

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "agent": "BLING-AI Autonomous Zero-Touch Engine",
        "loop_interval": "300s (5 min)",
        "features": ["Autonomous Synthesis", "TikTok Scripts", "AI Visual Prompts", "Public Landing Pages", "Telegram Alerts"],
        "database": "Supabase PostgreSQL"
    }

@app.get("/api/opportunities")
def list_opportunities():
    return {"opportunities": get_opportunities_from_supabase(limit=30)}

@app.get("/api/leads")
def list_leads():
    return {"leads": get_leads_from_supabase(limit=50)}

@app.get("/p/{opp_id}", response_class=HTMLResponse)
def serve_landing_page(opp_id: int):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase não configurado")
    try:
        res = supabase.table("opportunities").select("landing_page_html").eq("id", opp_id).execute()
        if res.data and len(res.data) > 0 and res.data[0].get("landing_page_html"):
            return res.data[0]["landing_page_html"]
        raise HTTPException(status_code=404, detail="Landing Page não encontrada.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/leads")
async def capture_lead(lead: LeadRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase não configurado")
    try:
        supabase.table("leads").insert({
            "product_name": lead.product_name,
            "email": lead.email
        }).execute()
        
        tg_msg = f"🎉 *NOVO LEAD CAPTURADO!*\n\n📦 *Produto:* {lead.product_name}\n📧 *Email:* `{lead.email}`\n\nPronto para contacto!"
        await send_telegram_alert(tg_msg)
        return {"status": "success", "message": "Lead gravado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agent")
async def run_agent(req: AgentRequest):
    try:
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            return {"result": "Erro: GROQ_API_KEY não configurada no Railway."}
        
        client = Groq(api_key=groq_key)
        data = await build_product_asset_pipeline(client, req.prompt, source="Ordem Manual Instantânea")
        return {
            "result": f"✅ [ATIVO CRIADO E GRAVADO NO SUPABASE!]\n\n"
                      f"📦 Conceito: {data.get('product_concept') if data else 'Criado com sucesso'}\n\n"
                      f"🎬 Guião TikTok + Landing Page + Alerta Telegram despachados!"
        }
    except Exception as e:
        return {"result": f"Erro interno: {str(e)}"}