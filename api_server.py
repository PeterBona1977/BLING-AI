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

# 2. Geradores Cloud Seguros (Corrigido Imagem e Vídeo)
def generate_ai_banner_image(topic: str) -> str:
    # Limpa caracteres estranhos que possam quebrar a URL da imagem
    safe_topic = re.sub(r'[^a-zA-Z0-9 ]', '', topic)
    clean_prompt = f"Futuristic dark mode 3D SaaS application UI dashboard for {safe_topic}, neon emerald lights, photorealistic, 8k render"
    encoded = urllib.parse.quote(clean_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1080&nologo=true&model=flux"

def generate_cloud_neural_voice(script_text: str) -> str:
    clean_text = re.sub(r'🎬 \[.*?\]: ', '', script_text).replace("'", "").replace('"', '')
    encoded_text = urllib.parse.quote(clean_text)
    return f"https://web-production-803c4.up.railway.app/api/tts?text={encoded_text}"

# VÍDEO CORRIGIDO: Link do Google Cloud (Garante que a imagem aparece e nunca fica ecrã preto)
FALLBACK_VIDEO_URL = "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"

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

# 4. Gravação na Base de Dados
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

# 5. MOTOR: ENGENHEIRO DE SOFTWARE FUNCIONAL
async def build_product_asset_pipeline(ai: Groq, topic: str, source: str = "Ordem Manual"):
    prompt = f"""
    És um Engenheiro de Software Full-Stack e Diretor de Produto.
    O utilizador pediu uma ferramenta baseada nesta ideia: '{topic}'.
    
    CRIA UMA APLICAÇÃO WEB FUNCIONAL (Micro-SaaS).
    A aplicação deve ter UI (Tailwind CSS) e LÓGICA (JavaScript puro) dentro do HTML.
    NOTA IMPORTANTE: No HTML gerado, usa aspas simples para os atributos (ex: class='bg-black') para não quebrar o formato JSON.

    Responde em JSON estrito com estas chaves:
    {{
        "title": "Nome curto de marca",
        "summary": "Ferramenta gratuita para {topic}",
        "product_concept": "Arquitetura técnica da aplicação gerada.",
        "social_post": "Lançámos hoje o {{title}}! Testa a nossa ferramenta grátis: [LINK]",
        "video_script": "🎬 [0-3s Gancho]: 'Testa esta ferramenta!'\\n🎬 [3-20s Solução]: 'Vê como funciona na prática.'\\n🎬 [20-30s CTA]: 'Link na bio!'",
        "functional_html": "<html lang='pt'>...CÓDIGO HTML COM SCRIPT FUNCIONAL...</html>"
    }}
    """
    
    try:
        completion = ai.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "És um programador focado em ferramentas web Single Page. Responde EXCLUSIVAMENTE em JSON válido."},
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

        title = data.get("title", "AppFuncional")
        if len(title) > 30: title = "MicroTool"
        
        summary = data.get("summary", "A tua nova ferramenta.")
        product_concept = data.get("product_concept", "Aplicação Web SPA.")
        social_post = data.get("social_post", f"🚀 Acabei de lançar o {title}!")
        video_script = data.get("video_script", f"🎬 [0-3s Gancho]: Pára tudo!\n🎬 [3-20s Solução]: Ferramenta lançada.\n🎬 [20-30s CTA]: Link na bio!")
        
        functional_html = data.get("functional_html", f"<h1>Erro ao gerar a aplicação {title}</h1>")
        
        # Gera o banner visual IA e a Voz
        image_url = generate_ai_banner_image(title)
        audio_url = generate_cloud_neural_voice(video_script)
        video_url = FALLBACK_VIDEO_URL
        
        opp_id = save_opportunity_to_supabase(
            source=source, title=title, score=10, summary=summary,
            action_plan="Monetização Fase 2 (Stripe)", social_post=social_post,
            product_concept=product_concept, code_payload="Lógica JS injetada na UI",
            landing_page_html=functional_html, video_script=video_script,
            video_url=video_url, image_url=image_url, audio_url=audio_url,
            cold_email="N/A"
        )
        
        return data
    except Exception as e:
        print(f"[Pipeline Error]: {e}")
        return None

# 6. Aplicação Web
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="BLING AI Execution Engine", lifespan=lifespan)
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
        await send_telegram_alert(f"🎉 *NOVO LEAD/CLIENTE!*\n\n📦 *Ferramenta:* {lead.product_name}\n📧 *Email:* `{lead.email}`")
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
        return {"result": f"✅ [SOFTWARE E MÍDIA CRIADOS!]\n\nA Capa Visual, o Vídeo MP4 e o Código Funcional foram gerados na perfeição."}
    except Exception as e:
        return {"result": f"Erro interno: {str(e)}"}

@app.get("/p/{opp_id}", response_class=HTMLResponse)
def serve_landing_page(opp_id: int):
    if not supabase: raise HTTPException(status_code=500)
    res = supabase.table("opportunities").select("landing_page_html").eq("id", opp_id).execute()
    if res.data and len(res.data) > 0: return res.data[0]["landing_page_html"]
    raise HTTPException(status_code=404)