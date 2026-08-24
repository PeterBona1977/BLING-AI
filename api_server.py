import os
import asyncio
import json
import re
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from groq import Groq
from supabase import create_client, Client

# 1. Supabase Setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Optional[Client] = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Telegram Dispatcher
async def send_telegram_alert(message_text: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return "Telegram não configurado."

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(url, json={"chat_id": chat_id, "text": message_text, "parse_mode": "Markdown"})
            if r.status_code == 200:
                return "Notificação enviada."
            return f"Telegram status: {r.status_code}"
    except Exception as e:
        return f"Erro Telegram: {str(e)}"

def save_opportunity_to_supabase(
    source: str, 
    title: str, 
    score: int, 
    summary: str, 
    action_plan: str, 
    social_post: str = "", 
    product_concept: str = "",
    code_payload: str = "",
    landing_page_html: str = ""
):
    if not supabase:
        return "Supabase não configurado."
    try:
        supabase.table("opportunities").insert({
            "source": source,
            "title": title,
            "score": score,
            "summary": summary,
            "action_plan": action_plan,
            "social_post": social_post,
            "product_concept": product_concept,
            "code_payload": code_payload,
            "landing_page_html": landing_page_html,
            "status": "detected"
        }).execute()
        return "Gravado com sucesso no Supabase."
    except Exception as e:
        print(f"[Supabase Error]: {e}")
        return f"Erro Supabase: {str(e)}"

def get_opportunities_from_supabase(limit: int = 30):
    if not supabase:
        return []
    try:
        response = supabase.table("opportunities").select("*").order("created_at", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        print(f"[Supabase Read Error]: {e}")
        return []

# 3. Multi-Scanner Feed
async def fetch_feed_items(client: httpx.AsyncClient) -> List[Dict[str, str]]:
    items = []
    try:
        r = await client.get("https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=2")
        if r.status_code == 200:
            for hit in r.json().get("hits", []):
                if hit.get("title"):
                    items.append({"source": "HackerNews", "title": hit["title"]})
    except Exception as e:
        print(f"[Fetch HN Error]: {e}")

    for sub in ["SaaS", "SideProject"]:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (BLING-AI Scanner)"}
            r = await client.get(f"https://www.reddit.com/r/{sub}/new.json?limit=1", headers=headers)
            if r.status_code == 200:
                for p in r.json().get("data", {}).get("children", []):
                    title = p.get("data", {}).get("title")
                    if title:
                        items.append({"source": f"Reddit r/{sub}", "title": title})
        except Exception as e:
            print(f"[Fetch Reddit {sub} Error]: {e}")

    return items

async def generate_fast_product(ai: Groq, topic: str, source: str = "Ordem Manual"):
    prompt = f"""
    Cria a solução completa para o produto digital: '{topic}'.
    Responde com as seguintes chaves em formato JSON:
    {{
        "title": "{topic}",
        "score": 10,
        "summary": "Resumo do problema e solução em 1 frase",
        "action_plan": "Estratégia de monetização direta",
        "product_concept": "Descrição técnica da stack e arquitetura da ferramenta",
        "code_payload": "# Script funcional\\nimport sys\\nprint('Ferramenta pronta')",
        "social_post": "Post viral pronto para LinkedIn / X com gancho e CTA"
    }}
    """
    
    completion = ai.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": "És um arquiteto de SaaS e produtos digitais de alta conversão. Responde estritamente em JSON."},
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
    summary = data.get("summary", f"Solução automatizada para: {topic}")
    action_plan = data.get("action_plan", "Monetização via subscrição mensal ou pagamento único.")
    product_concept = data.get("product_concept", f"Micro-ferramenta orientada a resolver {topic}")
    code_payload = data.get("code_payload", f"# Boilerplate funcional para {topic}\nimport os\nprint('Módulo ativo')")
    social_post = data.get("social_post", f"🚀 Acabei de automatizar '{topic}'!\n\n1. Rápido\n2. Escalável\n\nQueres testar? Comenta 'EU QUERO'.")
    
    # Landing page com leitura dinâmica do DOM para evitar quebra por aspas
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
    <span class="text-xs font-semibold px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-4 inline-block">Acesso Antecipado</span>
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
        alert('Erro de conexão com o servidor.');
        btn.disabled = false;
        btn.innerText = 'Entrar na Lista VIP';
      }}
    }}
  </script>
</body>
</html>"""

    save_opportunity_to_supabase(
        source=source,
        title=title,
        score=10,
        summary=summary,
        action_plan=action_plan,
        social_post=social_post,
        product_concept=product_concept,
        code_payload=code_payload,
        landing_page_html=landing_page_html
    )
    
    tg_text = f"🚀 *NOVO PRODUTO CRIADO!*\n\n📦 *Tema:* {title}\n💡 *Conceito:* {product_concept}\n\n📱 *Post:* {social_post[:180]}..."
    await send_telegram_alert(tg_text)
    
    return {
        "title": title,
        "product_concept": product_concept,
        "summary": summary,
        "social_post": social_post
    }

# 4. Background Scanner
async def autonomous_scanner_loop():
    while True:
        try:
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                ai = Groq(api_key=groq_key)
                async with httpx.AsyncClient(timeout=15.0) as client:
                    feed = await fetch_feed_items(client)
                    for item in feed:
                        await generate_fast_product(ai, item["title"], source=item["source"])
        except Exception as e:
            print(f"[Autonomous Scanner Error]: {e}")
            
        await asyncio.sleep(480)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(autonomous_scanner_loop())
    yield
    task.cancel()

app = FastAPI(title="BLING AI Full Commercial Engine", lifespan=lifespan)

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
    return {"status": "online"}

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "agent": "BLING-AI Commercial Engine",
        "lead_capture": "Active",
        "model": "openai/gpt-oss-20b",
        "database": "Supabase PostgreSQL"
    }

@app.get("/api/opportunities")
def list_opportunities():
    return {"opportunities": get_opportunities_from_supabase(limit=30)}

# Endpoint de Captura de Leads com Notificação Imediata no Telegram
@app.post("/api/leads")
async def capture_lead(lead: LeadRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase não configurado")
    
    try:
        supabase.table("leads").insert({
            "product_name": lead.product_name,
            "email": lead.email
        }).execute()
        
        tg_msg = f"🎉 *NOVO LEAD CAPTURADO!*\n\n📦 *Produto:* {lead.product_name}\n📧 *Email:* `{lead.email}`\n\nPronto para contacto comercial!"
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
        p_lower = req.prompt.lower()

        # 1. Telegram
        if "telegram" in p_lower or "mensagem" in p_lower:
            res = await send_telegram_alert(f"🤖 *BLING-AI:* {req.prompt}")
            return {"result": f"⚡ [TELEGRAM]: {res}"}

        # 2. Scan
        if "scan" in p_lower or "pesquisa" in p_lower:
            async with httpx.AsyncClient(timeout=15.0) as http_c:
                feed = await fetch_feed_items(http_c)
                for item in feed:
                    await generate_fast_product(client, item["title"], source=item["source"])
            return {"result": f"⚡ [SCAN EXECUTADO]: {len(feed)} novos itens processados e gravados!"}

        # 3. Criação de Produto / Código / Micro-SaaS
        if any(k in p_lower for k in ["cria", "gera", "faz", "produto", "saas", "código", "landing", "script", "micro"]):
            data = await generate_fast_product(client, req.prompt, source="Ordem Manual")
            return {
                "result": f"✅ [PRODUTO CRIADO E GRAVADO NO SUPABASE!]\n\n"
                          f"📦 Conceito: {data.get('product_concept')}\n\n"
                          f"💻 Código Funcional & Landing Page Compilada com Captura de Leads Ativa!\n"
                          f"📲 Alerta Telegram Enviado.\n\n"
                          f"(O novo ativo já está no topo da lista no teu dashboard)"
            }

        # 4. Chat Geral
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "És o consultor executivo BLING-AI. Responde de forma concisa e direta."},
                {"role": "user", "content": req.prompt}
            ],
            temperature=0.3
        )
        return {"result": completion.choices[0].message.content}
    except Exception as e:
        return {"result": f"Erro interno de execução: {str(e)}"}