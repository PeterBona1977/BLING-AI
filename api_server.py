import os
import asyncio
import json
import re
import urllib.parse
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from groq import Groq
from supabase import create_client, Client

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

# 1. Supabase Setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Optional[Client] = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"[Supabase Init Error]: {e}")

# 2. Geradores Cloud Seguros
def generate_ai_banner_image(topic: str) -> str:
    clean_prompt = f"Futuristic dark mode 3D SaaS application UI dashboard for {topic}, neon emerald lights, photorealistic, 8k render"
    encoded = urllib.parse.quote(clean_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1080&nologo=true&model=flux"

def generate_cloud_neural_voice(script_text: str) -> str:
    clean_text = re.sub(r'🎬 \[.*?\]: ', '', script_text).replace("'", "").replace('"', '')
    encoded_text = urllib.parse.quote(clean_text)
    return f"https://web-production-803c4.up.railway.app/api/tts?text={encoded_text}"

FALLBACK_VIDEO_URL = "https://cdn.coverr.co/videos/coverr-digital-world-concept-6638/1080p.mp4"

# 3. Despacho no Telegram
async def send_telegram_alert(message_text: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            await client.post(url, json={"chat_id": chat_id, "text": message_text, "parse_mode": "Markdown"})
    except Exception:
        pass

# 4. BD
def save_opportunity_to_supabase(
    source: str, title: str, score: int, summary: str, action_plan: str, 
    social_post: str = "", product_concept: str = "", code_payload: str = "", 
    landing_page_html: str = "", video_script: str = "", video_url: str = "", 
    image_url: str = "", audio_url: str = "", cold_email: str = ""
):
    if not supabase: return None
    try:
        res = supabase.table("opportunities").insert({
            "source": source, "title": title, "score": score, "summary": summary,
            "action_plan": action_plan, "social_post": social_post, 
            "product_concept": product_concept, "code_payload": code_payload,
            "landing_page_html": landing_page_html, "video_script": video_script,
            "video_url": video_url, "image_url": image_url, "audio_url": audio_url,
            "cold_email": cold_email, "status": "pending_approval"
        }).execute()
        if res.data and len(res.data) > 0:
            return res.data[0].get("id")
        return None
    except Exception as e:
        print(f"[DB Error]: {e}")
        return None

# 5. Motor de Criação (CORRIGIDO)
async def build_product_asset_pipeline(ai: Groq, topic: str, source: str = "Ordem Manual"):
    # A ORDEM FOI CORRIGIDA AQUI: Pedimos um "nome curto de marca" para o título.
    prompt = f"""
    Cria um plano de produto digital e campanha viral completa para: '{topic}'.
    Responde em JSON estrito com estas chaves:
    {{
        "title": "Nome comercial curto e catita para a marca (máximo 3 palavras, ex: ViralCaps AI)",
        "score": 10,
        "summary": "Resumo de 1 frase do problema e solução.",
        "action_plan": "Estratégia de monetização.",
        "product_concept": "Descrição técnica.",
        "code_payload": "# Código funcional\\nprint('Pronto!')",
        "social_post": "Post para redes.",
        "video_script": "🎬 [0-3s Gancho]: 'Chega de perder tempo!'\\n🎬 [3-20s Solução]: 'Usa esta automação rápida e simples.'\\n🎬 [20-30s CTA]: 'Clica no link na bio!'",
        "cold_email": "Assunto: Automação\\n\\nOlá..."
    }}
    """
    
    try:
        completion = ai.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "És um diretor criativo focado em conversão. Responde apenas em JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        raw_content = completion.choices[0].message.content
        data = {}
        try:
            data = json.loads(raw_content)
        except:
            json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))

        # Se a IA por acaso falhar, cortamos o título para não quebrar a página
        raw_title = data.get("title", "BLING Product")
        title = raw_title if len(raw_title) < 40 else "BLING Product"
        
        summary = data.get("summary", "A tua nova solução automatizada.")
        product_concept = data.get("product_concept", "Micro-ferramenta SaaS.")
        social_post = data.get("social_post", f"🚀 Acabei de lançar o {title}!")
        video_script = data.get("video_script", f"🎬 [0-3s Gancho]: Pára tudo!\n🎬 [3-20s Solução]: Sistema pronto.\n🎬 [20-30s CTA]: Link na bio!")
        
        image_url = generate_ai_banner_image(title)
        audio_url = generate_cloud_neural_voice(video_script)
        video_url = FALLBACK_VIDEO_URL
        
        landing_page_html = f"""<!DOCTYPE html><html lang="pt"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><script src="https://cdn.tailwindcss.com"></script><title>{title}</title></head><body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col items-center justify-center p-6"><div class="absolute top-6 left-6 text-xl font-bold text-emerald-400 tracking-tighter">{title}</div><h1 class="text-5xl md:text-6xl font-extrabold text-white mb-6 text-center tracking-tight max-w-4xl">{title}</h1><p class="text-slate-400 text-lg md:text-xl text-center mb-12 max-w-2xl">{summary}</p><div class="bg-slate-900 p-8 md:p-10 rounded-3xl w-full max-w-md border border-slate-800 shadow-2xl shadow-emerald-900/10"><h3 class="text-xl font-bold mb-6 text-center">Garantir Acesso Antecipado</h3><input type="email" id="leadEmail" placeholder="O teu melhor email..." class="w-full p-4 rounded-xl bg-slate-950 border border-slate-800 text-white mb-4 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition"><button class="w-full py-4 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl transition shadow-lg shadow-emerald-500/20 text-lg" onclick="sendLead()">Quero Aceder</button><div id="successMsg" class="hidden text-emerald-400 font-semibold text-center pt-6">✅ Inscrição confirmada com sucesso!</div></div><script>async function sendLead() {{ const email = document.getElementById('leadEmail').value; if (!email) return; try {{ await fetch('https://web-production-803c4.up.railway.app/api/leads', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ product_name: '{title}', email: email }}) }}); document.getElementById('successMsg').classList.remove('hidden'); }} catch(e) {{}} }}</script></body></html>"""

        save_opportunity_to_supabase(
            source=source, title=title, score=10, summary=summary,
            action_plan=data.get("action_plan", ""), social_post=social_post,
            product_concept=product_concept, code_payload=data.get("code_payload", ""),
            landing_page_html=landing_page_html, video_script=video_script,
            video_url=video_url, image_url=image_url, audio_url=audio_url,
            cold_email=data.get("cold_email", "")
        )
        
        return data
    except Exception as e:
        print(f"[Pipeline Error]: {e}")
        return None

# 6. Aplicação Web
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="BLING AI Media Studio", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class AgentRequest(BaseModel):
    prompt: str

class LeadRequest(BaseModel):
    product_name: str
    email: str

@app.get("/api/status")
def get_status(): return {"status": "online"}

@app.get("/api/opportunities")
def list_opportunities():
    if not supabase: return {"opportunities": []}
    try:
        res = supabase.table("opportunities").select("*").order("created_at", desc=True).limit(30).execute()
        return {"opportunities": res.data}
    except Exception:
        return {"opportunities": []}

@app.get("/api/leads")
def list_leads():
    if not supabase: return {"leads": []}
    try:
        res = supabase.table("leads").select("*").order("created_at", desc=True).limit(50).execute()
        return {"leads": res.data}
    except Exception:
        return {"leads": []}

@app.post("/api/leads")
async def capture_lead(lead: LeadRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase não configurado")
    try:
        supabase.table("leads").insert({"product_name": lead.product_name, "email": lead.email}).execute()
        await send_telegram_alert(f"🎉 *NOVO LEAD CAPTURADO!*\n\n📦 *Produto:* {lead.product_name}\n📧 *Email:* `{lead.email}`")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tts")
async def proxy_tts(text: str):
    clean_text = urllib.parse.unquote(text)[:600]
    
    if EDGE_TTS_AVAILABLE:
        try:
            communicate = edge_tts.Communicate(clean_text, "pt-PT-DuarteNeural")
            audio_data = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])
            return Response(content=bytes(audio_data), media_type="audio/mpeg")
        except Exception as e:
            print(f"[Neural TTS Error]: {e}")

    url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=pt-PT&client=tw-ob&q={urllib.parse.quote(clean_text[:200])}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                return Response(content=r.content, media_type="audio/mpeg")
    except Exception:
        pass
    return Response(status_code=404)

@app.post("/api/agent")
async def run_agent(req: AgentRequest):
    try:
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key: return {"result": "Erro: GROQ_API_KEY em falta."}
        
        client = Groq(api_key=groq_key)
        await build_product_asset_pipeline(client, req.prompt, source="Ordem Manual")
        return {"result": f"✅ [SUCESSO!]\n\nAtivo criado! Testa agora a nova Landing Page limpa e organizada."}
    except Exception as e:
        return {"result": f"Erro interno: {str(e)}"}

@app.get("/p/{opp_id}", response_class=HTMLResponse)
def serve_landing_page(opp_id: int):
    if not supabase: raise HTTPException(status_code=500)
    res = supabase.table("opportunities").select("landing_page_html").eq("id", opp_id).execute()
    if res.data and len(res.data) > 0: return res.data[0]["landing_page_html"]
    raise HTTPException(status_code=404)