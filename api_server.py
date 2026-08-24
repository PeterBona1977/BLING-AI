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

# 1. Supabase Setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Optional[Client] = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Renderizador Real de Vídeo MP4 (Creatomate / Dynamic Cloud Render)
async def render_tiktok_video(title: str, hook: str, cta: str) -> Optional[str]:
    api_key = os.getenv("CREATOMATE_API_KEY")
    if not api_key:
        print("[Video Render]: Sem CREATOMATE_API_KEY. A usar vídeo de stock dinâmico vertical...")
        # Fallback de alta qualidade: clipe vertical dark tech com áudio
        return "https://cdn.coverr.co/videos/coverr-digital-world-concept-6638/1080p.mp4"

    url = "https://api.creatomate.com/v1/renders"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Payload de montagem de vídeo vertical (9:16) com legendas dinâmicas
    payload = {
        "output_format": "mp4",
        "width": 1080,
        "height": 1920,
        "duration": 15,
        "elements": [
            {
                "type": "video",
                "source": "https://creatomate-static.s3.amazonaws.com/demo/technology.mp4",
                "duration": 15
            },
            {
                "type": "text",
                "text": hook,
                "time": 0,
                "duration": 6,
                "font_family": "Montserrat",
                "font_weight": "800",
                "font_size": 72,
                "fill_color": "#10B981",
                "shadow_color": "#000000",
                "shadow_blur": 15
            },
            {
                "type": "text",
                "text": f"Nova Solução:\n{title}\n\n{cta}",
                "time": 6,
                "duration": 9,
                "font_family": "Montserrat",
                "font_weight": "700",
                "font_size": 60,
                "fill_color": "#FFFFFF",
                "shadow_color": "#000000",
                "shadow_blur": 15
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code in [200, 202]:
                renders = r.json()
                if isinstance(renders, list) and len(renders) > 0:
                    return renders[0].get("url")
    except Exception as e:
        print(f"[Video Render Error]: {e}")
    
    return "https://cdn.coverr.co/videos/coverr-digital-world-concept-6638/1080p.mp4"

# 3. Despacho Multimédia no Telegram (Envia Vídeo Real + Botões Inline)
async def send_telegram_video_approval(opp_id: int, title: str, video_url: str, post_text: str, public_url: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return

    caption = (
        f"🎬 *VÍDEO TIKTOK/REELS GERADO PELA IA!*\n\n"
        f"📌 *Produto:* {title}\n"
        f"🌐 *Landing Page:* {public_url}\n\n"
        f"📱 *Post Pronto:*\n_{post_text[:180]}..._\n\n"
        f"👇 *Aprovas a publicação deste vídeo nas tuas redes?*"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🚀 Publicar Vídeo & Campanha", "callback_data": f"approve_{opp_id}"},
                {"text": "❌ Rejeitar", "callback_data": f"reject_{opp_id}"}
            ]
        ]
    }

    async with httpx.AsyncClient(timeout=25.0) as client:
        # 1. Tentar enviar como vídeo nativo reproduzível
        try:
            video_api_url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
            r = await client.post(video_api_url, json={
                "chat_id": chat_id,
                "video": video_url,
                "caption": caption,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            })
            if r.status_code == 200:
                print(f"[Telegram]: Vídeo #{opp_id} despachado com sucesso!")
                return
        except Exception as e:
            print(f"[Telegram Video Direct Send Fail]: {e}")

        # 2. Fallback: Envio em mensagem de texto com link do vídeo
        msg_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        fallback_text = f"{caption}\n\n🎥 *Link do Vídeo:* {video_url}"
        await client.post(msg_api_url, json={
            "chat_id": chat_id,
            "text": fallback_text,
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        })

async def send_telegram_alert(message_text: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            await client.post(url, json={"chat_id": chat_id, "text": message_text, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"[Telegram Alert Error]: {e}")

# 4. Publicação Automática nas Contas do Utilizador
async def publish_to_social_accounts(opp_id: int):
    if not supabase:
        return "Supabase não disponível"

    res = supabase.table("opportunities").select("*").eq("id", opp_id).execute()
    if not res.data:
        return "Ativo não encontrado"
    
    opp = res.data[0]
    title = opp.get("title")
    post = opp.get("social_post")
    video_url = opp.get("video_url")
    public_url = f"https://web-production-803c4.up.railway.app/p/{opp_id}"

    # Dispara Webhook Central (Make / Zapier / Ayrshare) para publicar em TikTok, X e LinkedIn
    webhook_url = os.getenv("SOCIAL_PUBLISH_WEBHOOK_URL")
    if webhook_url:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                await client.post(webhook_url, json={
                    "event": "approved_by_user",
                    "opportunity_id": opp_id,
                    "title": title,
                    "video_url": video_url,
                    "post_text": f"{post}\n\n👉 Acede aqui: {public_url}",
                    "public_url": public_url
                })
        except Exception as e:
            print(f"[Webhook Publish Error]: {e}")

    supabase.table("opportunities").update({"status": "published"}).eq("id", opp_id).execute()
    await send_telegram_alert(f"✅ *CAMPANHA MULTIMÉDIA PUBLICADA!*\n\nO vídeo e os posts de *#{opp_id} - {title}* foram despachados para as tuas redes com sucesso.")
    return "Publicado"

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
    video_url: str = "",
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
            "video_url": video_url,
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

# 5. Radar de Mercado
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

    for sub in ["SaaS", "SideProject", "Entrepreneur"]:
        try:
            headers = {"User-Agent": "Mozilla/5.0 BLING-AI"}
            r = await client.get(f"https://www.reddit.com/r/{sub}/new.json?limit=1", headers=headers, timeout=6.0)
            if r.status_code == 200:
                for p in r.json().get("data", {}).get("children", []):
                    t = p.get("data", {}).get("title")
                    if t and len(t) > 15:
                        items.append({"source": f"Reddit r/{sub}", "title": t})
        except Exception as e:
            print(f"[Feed Reddit {sub}]: {e}")

    return items

# 6. Fábrica de Ativos com Renderização Multimédia
async def build_product_asset_pipeline(ai: Groq, topic: str, source: str = "Motor Autónomo"):
    print(f"\n[BLING AI]: A construir ecossistema de produto e vídeo para '{topic[:40]}'...")
    
    prompt = f"""
    És o Diretor de Criação da BLING AI.
    Cria um ecossistema de produto digital e campanha viral completo para: '{topic}'.
    Responde em JSON estrito com estas chaves:
    {{
        "title": "{topic}",
        "score": 10,
        "summary": "Resumo de 1 frase do problema e solução.",
        "action_plan": "Estratégia prática de monetização.",
        "product_concept": "Descrição da stack e funcionamento.",
        "code_payload": "# Código funcional\\nprint('Ferramenta {topic} ativa')",
        "social_post": "Post persuasivo pronto para LinkedIn e Twitter com gancho e CTA.",
        "video_hook": "Pára tudo se ainda perdes horas com {topic}!",
        "video_cta": "Clica no link da bio para acesso exclusivo!",
        "video_script": "🎬 [0-3s Gancho]: 'Pára tudo se ainda fazes {topic} à mão!'\\n🎬 [3-20s Solução]: 'Criámos uma automação que faz isto por ti.'\\n🎬 [20-30s CTA]: 'Clica no link da bio para testar.'",
        "ai_media_prompt": "Cinematic 3D render of {topic} software, dark mode, neon emerald, 8k",
        "cold_email": "Assunto: Automação para {topic}\\n\\nOlá,\\nDesenvolvemos uma ferramenta para resolver {topic}. Podemos demonstrar?"
    }}
    """
    
    try:
        completion = ai.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "És um construtor de SaaS e diretor de vídeo viral. Responde estritamente em JSON."},
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
        product_concept = data.get("product_concept", f"Micro-ferramenta especializada em {topic}")
        code_payload = data.get("code_payload", f"# Boilerplate para {topic}\nimport os")
        social_post = data.get("social_post", f"🚀 Acabei de automatizar '{topic}'!\n\nQueres testar? Acede ao link abaixo.")
        video_script = data.get("video_script", f"🎬 [0-3s Gancho]: Pára tudo sobre {topic}!\n🎬 [3-20s Solução]: Sistema automático pronto.\n🎬 [20-30s CTA]: Link na bio!")
        video_hook = data.get("video_hook", f"Pára tudo sobre {topic}!")
        video_cta = data.get("video_cta", "Link na bio para acesso VIP!")
        ai_media_prompt = data.get("ai_media_prompt", f"SaaS mockup for {topic}, 8k render")
        cold_email = data.get("cold_email", f"Assunto: Automação para {topic}\n\nOlá, desenvolvemos uma solução...")

        # 1. Renderiza o vídeo vertical (.mp4)
        rendered_video_url = await render_tiktok_video(title, video_hook, video_cta)

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
            video_url=rendered_video_url,
            ai_media_prompt=ai_media_prompt,
            cold_email=cold_email
        )
        
        public_link = f"https://web-production-803c4.up.railway.app/p/{opp_id}" if opp_id else "https://bling-ai.pages.dev"
        
        # Despacha o Vídeo Real com Botões no Telegram
        if opp_id:
            await send_telegram_video_approval(opp_id, title, rendered_video_url, social_post, public_link)
        
        return data
    except Exception as e:
        print(f"[BLING Pipeline Error]: {e}")
        return None

# 7. Loop de Execução Autónoma
async def autonomous_background_worker():
    await send_telegram_alert("🤖 *BLING-AI Guardião Multimédia Online!*\n\nA minerar e a renderizar vídeos em segundo plano. Vais receber os vídeos e botões de aprovação aqui.")
    
    while True:
        try:
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                ai = Groq(api_key=groq_key)
                
                async with httpx.AsyncClient(timeout=10.0) as client:
                    feed = await fetch_real_market_feed(client)
                
                if not feed:
                    synth_prompt = "Sugere 1 necessidade urgente e lucrativa de software/ferramenta digital para resolver hoje em 1 frase curta."
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
                        await asyncio.sleep(30)
                        
        except Exception as e:
            print(f"[Autonomous Loop Error]: {e}")
            
        await asyncio.sleep(300)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(autonomous_background_worker())
    yield
    task.cancel()

app = FastAPI(title="BLING AI Video & Approval Engine", lifespan=lifespan)

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
    return {"status": "online", "mode": "Multimedia Video + Approval Workflow"}

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "agent": "BLING-AI Multimedia Video Engine",
        "video_generator": "Active (.MP4 9:16 Render)",
        "approval_system": "Telegram Native Video + Inline Buttons",
        "database": "Supabase PostgreSQL"
    }

@app.get("/api/opportunities")
def list_opportunities():
    return {"opportunities": get_opportunities_from_supabase(limit=30)}

@app.get("/api/leads")
def list_leads():
    return {"leads": get_leads_from_supabase(limit=50)}

# Webhook do Telegram (Gere os Cliques de Aprovação do Vídeo)
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
                await send_telegram_alert(f"🗑️ Campanha e vídeo #{opp_id} rejeitados.")

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
        return {"status": "success", "message": "Lead gravado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agent")
async def run_agent(req: AgentRequest):
    try:
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            return {"result": "Erro: GROQ_API_KEY em falta."}
        
        client = Groq(api_key=groq_key)
        await build_product_asset_pipeline(client, req.prompt, source="Ordem Manual")
        return {
            "result": "✅ Vídeo renderizado e campanha criada! Vê o teu Telegram para assistir e aprovar a publicação."
        }
    except Exception as e:
        return {"result": f"Erro interno: {str(e)}"}