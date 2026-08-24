import os
import asyncio
import json
import re
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
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
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"[Supabase Init Error]: {e}")

# 2. Despacho Telegram com Botões Interativos
async def send_telegram_alert(message_text: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("[Telegram]: Bot token ou Chat ID não configurados.")
        return "Telegram não configurado."

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(url, json={"chat_id": chat_id, "text": message_text, "parse_mode": "Markdown"})
            return "Mensagem enviada para o Telegram."
    except Exception as e:
        print(f"[Telegram Alert Error]: {e}")
        return f"Erro Telegram: {str(e)}"

async def send_telegram_approval_request(opp_id: int, title: str, concept: str, video_script: str, public_url: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    text = (
        f"🎯 *NOVO ATIVO GERADO PELA IA*\n\n"
        f"📌 *Tema:* {title}\n"
        f"💡 *Produto:* {concept}\n"
        f"🌐 *Landing Page:* {public_url}\n\n"
        f"🎬 *TikTok Script:*\n_{video_script[:220]}..._\n\n"
        f"👇 *Aprovas a publicação automática nas tuas contas?*"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🚀 Aprovar & Publicar", "callback_data": f"approve_{opp_id}"},
                {"text": "❌ Rejeitar", "callback_data": f"reject_{opp_id}"}
            ]
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            })
    except Exception as e:
        print(f"[Telegram Approval Error]: {e}")

# 3. Gestor de Base de Dados
def opportunity_exists(title: str) -> bool:
    if not supabase:
        return False
    try:
        res = supabase.table("opportunities").select("id").ilike("title", f"%{title[:20]}%").execute()
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
            "status": "pending_approval"
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

# 4. Meta-Programação e Auto-Evolução
def register_new_skill(name: str, description: str, code: str):
    if not supabase:
        return False
    try:
        supabase.table("agent_skills").upsert({
            "name": name,
            "description": description,
            "code": code,
            "status": "active"
        }, on_conflict="name").execute()
        return True
    except Exception as e:
        print(f"[Skill Save Error]: {e}")
        return False

async def self_evolve_create_skill(ai: Groq, required_task: str):
    prompt = f"""
    Cria uma função Python pura e executável para a seguinte tarefa: '{required_task}'.
    A função principal deve chamar-se `execute(params: dict) -> dict`.
    Responde estritamente em JSON:
    {{
        "skill_name": "<nome_snake_case>",
        "description": "<resumo da capacidade>",
        "python_code": "def execute(params: dict) -> dict:\\n    return {{'status': 'ok'}}"
    }}
    """
    try:
        comp = ai.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        raw = comp.choices[0].message.content
        data = {}
        try:
            data = json.loads(raw)
        except Exception:
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
        
        name = data.get("skill_name", "nova_ferramenta")
        desc = data.get("description", "Ferramenta auto-gerada")
        code = data.get("python_code", "")
        
        register_new_skill(name, desc, code)
        await send_telegram_alert(f"🧠 *[AUTO-EVOLUÇÃO]:* Nova ferramenta criada: `{name}` - {desc}")
        return {"status": "success", "skill_name": name}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# 5. Radar de Mercado e Criação Completa de Produto
async def fetch_real_market_feed(client: httpx.AsyncClient) -> List[Dict[str, str]]:
    items = []
    try:
        r = await client.get("https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=3", timeout=6.0)
        if r.status_code == 200:
            for hit in r.json().get("hits", []):
                t = hit.get("title")
                if t and len(t) > 12:
                    items.append({"source": "HackerNews Radar", "title": t})
    except Exception as e:
        print(f"[Feed HN]: {e}")

    for sub in ["SaaS", "Entrepreneur", "SideProject"]:
        try:
            headers = {"User-Agent": "Mozilla/5.0 BLING-AI/3.0"}
            r = await client.get(f"https://www.reddit.com/r/{sub}/new.json?limit=1", headers=headers, timeout=6.0)
            if r.status_code == 200:
                for p in r.json().get("data", {}).get("children", []):
                    t = p.get("data", {}).get("title")
                    if t and len(t) > 15:
                        items.append({"source": f"Reddit r/{sub}", "title": t})
        except Exception as e:
            print(f"[Feed Reddit {sub}]: {e}")

    return items

async def build_product_asset_pipeline(ai: Groq, topic: str, source: str = "Motor Autónomo"):
    print(f"\n[BLING Engine]: A gerar pipeline para: '{topic[:40]}'...")
    
    prompt = f"""
    Cria um plano de produto digital e campanha viral completo para: '{topic}'.
    Responde em JSON com estas chaves:
    {{
        "title": "{topic}",
        "score": 10,
        "summary": "Resumo de 1 frase do problema e da solução automatizada.",
        "action_plan": "Estratégia de monetização direta.",
        "product_concept": "Descrição técnica e arquitetura da ferramenta.",
        "code_payload": "# Código funcional\\nprint('Ferramenta {topic} pronta!')",
        "social_post": "Post persuasivo para LinkedIn e X com gancho e CTA.",
        "video_script": "🎬 [0-3s Gancho]: 'Pára tudo se fazes {topic} à mão!'\\n🎬 [3-20s Solução]: 'Criámos uma automação que faz isto por ti.'\\n🎬 [20-30s CTA]: 'Link na bio para acesso VIP!'",
        "ai_media_prompt": "Cinematic 3D UI render of {topic} software, dark mode, neon emerald, 8k",
        "cold_email": "Assunto: Automação para {topic}\\n\\nOlá,\\nDesenvolvemos uma ferramenta para {topic}. Gostaria de testar?"
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
        summary = data.get("summary", f"Solução automatizada para: {topic}")
        action_plan = data.get("action_plan", "Monetização via subscrição.")
        product_concept = data.get("product_concept", f"Micro-ferramenta orientada a {topic}")
        code_payload = data.get("code_payload", f"# Boilerplate para {topic}\nimport os")
        social_post = data.get("social_post", f"🚀 Acabei de automatizar '{topic}'!\n\nQueres testar? Link abaixo.")
        video_script = data.get("video_script", f"🎬 [0-3s Gancho]: Pára tudo sobre {topic}!\n🎬 [3-20s Solução]: Sistema automático pronto.\n🎬 [20-30s CTA]: Link na bio!")
        ai_media_prompt = data.get("ai_media_prompt", f"SaaS mockup for {topic}, 8k render")
        cold_email = data.get("cold_email", f"Assunto: Automação para {topic}\n\nOlá, desenvolvemos uma solução...")

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
      <div id="successMsg" class="hidden text-emerald-400 font-semibold text-sm pt-4">✅ Inscrição confirmada!</div>
    </div>
  </main>
  
  <footer class="p-6 text-center text-xs text-slate-600">
    © 2026 BLING AI Engine.
  </footer>

  <script>
    async function sendLead() {{
      const emailInput = document.getElementById('leadEmail');
      const email = emailInput ? emailInput.value : '';
      const titleElem = document.getElementById('productTitle');
      const productName = titleElem ? titleElem.innerText : 'Produto BLING';
      const btn = document.getElementById('submitBtn');

      if (!email || !email.includes('@')) {{
        alert('Insere um email válido.');
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
          btn.disabled = false;
          btn.innerText = 'Entrar na Lista VIP';
        }}
      }} catch(e) {{
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
        
        if opp_id:
            await send_telegram_approval_request(opp_id, title, product_concept, video_script, public_link)
        
        return data
    except Exception as e:
        print(f"[BLING Pipeline Error]: {e}")
        return None

# 6. Publicação Automática após Aprovação
async def publish_to_social_accounts(opp_id: int):
    if not supabase:
        return "Supabase não disponível"

    res = supabase.table("opportunities").select("*").eq("id", opp_id).execute()
    if not res.data:
        return "Oportunidade não encontrada"
    
    opp = res.data[0]
    title = opp.get("title")
    post = opp.get("social_post")
    public_url = f"https://web-production-803c4.up.railway.app/p/{opp_id}"

    webhook_url = os.getenv("SOCIAL_PUBLISH_WEBHOOK_URL")
    if webhook_url:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                await client.post(webhook_url, json={
                    "event": "approved_by_user",
                    "opportunity_id": opp_id,
                    "title": title,
                    "post_text": f"{post}\n\n👉 Acede aqui: {public_url}",
                    "public_url": public_url
                })
        except Exception as e:
            print(f"[Webhook Publish Error]: {e}")

    supabase.table("opportunities").update({"status": "published"}).eq("id", opp_id).execute()
    await send_telegram_alert(f"✅ *PUBLICADO COM SUCESSO!*\n\nO ativo *#{opp_id} - {title}* foi despachado para as tuas redes.")
    return "Publicado"

# 7. Loop de Fundo Autónomo
async def autonomous_background_worker():
    print("[BLING Engine]: Loop autónomo a iniciar...")
    await send_telegram_alert("🤖 *BLING-AI Motor Autónomo Online!*\n\nA minerar e a criar produtos em segundo plano.")
    
    while True:
        try:
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                ai = Groq(api_key=groq_key)
                
                async with httpx.AsyncClient(timeout=10.0) as client:
                    feed = await fetch_real_market_feed(client)
                
                if not feed:
                    synth_prompt = "Sugere 1 necessidade urgente de SaaS/Micro-negócios digitais hoje em 1 frase curta."
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
                        await asyncio.sleep(25)
                        
        except Exception as e:
            print(f"[Autonomous Loop Error]: {e}")
            
        await asyncio.sleep(300)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(autonomous_background_worker())
    yield
    task.cancel()

app = FastAPI(title="BLING AI Full Unified Engine", lifespan=lifespan)

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

class ApprovalActionRequest(BaseModel):
    opportunity_id: int
    action: str

@app.get("/")
@app.get("/health")
def health():
    return {"status": "online"}

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "agent": "BLING-AI Unified Engine",
        "mode": "Autonomous + Human-in-the-loop",
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
        
        tg_msg = f"🎉 *NOVO LEAD CAPTURADO!*\n\n📦 *Produto:* {lead.product_name}\n📧 *Email:* `{lead.email}`"
        await send_telegram_alert(tg_msg)
        return {"status": "success", "message": "Lead gravado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/telegram-webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        if "callback_query" in data:
            cq = data["callback_query"]
            cb_data = cq.get("data", "")
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
                    json={"callback_query_id": cq["id"], "text": "Ordem recebida! A processar..."}
                )

            if cb_data.startswith("approve_"):
                opp_id = int(cb_data.replace("approve_", ""))
                await publish_to_social_accounts(opp_id)
            elif cb_data.startswith("reject_"):
                opp_id = int(cb_data.replace("reject_", ""))
                if supabase:
                    supabase.table("opportunities").update({"status": "rejected"}).eq("id", opp_id).execute()
                await send_telegram_alert(f"🗑️ Oportunidade #{opp_id} descartada.")

        return {"ok": True}
    except Exception as e:
        print(f"[Telegram Webhook Error]: {e}")
        return {"ok": False}

@app.post("/api/approve")
async def handle_manual_approval(req: ApprovalActionRequest):
    if req.action == "approve":
        res = await publish_to_social_accounts(req.opportunity_id)
        return {"status": "success", "message": res}
    else:
        if supabase:
            supabase.table("opportunities").update({"status": "rejected"}).eq("id", req.opportunity_id).execute()
        return {"status": "success", "message": "Rejeitado"}

# Endpoint do Prompt Interativo
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

        # 2. Scan / Pesquisa Imediata
        if "scan" in p_lower or "pesquisa" in p_lower:
            async with httpx.AsyncClient(timeout=12.0) as http_c:
                feed = await fetch_real_market_feed(http_c)
            
            if not feed:
                feed = [{"source": "Auto-AI Synthesizer", "title": "Micro-SaaS de automação de faturas com IA"}]
                
            for item in feed:
                await build_product_asset_pipeline(client, item["title"], source=item["source"])
            return {"result": f"⚡ [SCAN EXECUTADO]: {len(feed)} oportunidades mineradas, criadas e enviadas para o Telegram!"}

        # 3. Criação de Produto / Código / Micro-SaaS
        data = await build_product_asset_pipeline(client, req.prompt, source="Ordem Manual")
        return {
            "result": f"✅ [PRODUTO CRIADO E GRAVADO NO SUPABASE!]\n\n"
                      f"📦 Conceito: {data.get('product_concept') if data else 'Criado'}\n\n"
                      f"🎬 Guião TikTok + Landing Page Pronta!\n"
                      f"📲 Enviámos a mensagem de aprovação com botões para o teu Telegram."
        }
    except Exception as e:
        return {"result": f"Erro interno de execução: {str(e)}"}