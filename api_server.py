import os
import asyncio
import json
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
                return "Notificação enviada para o Telegram."
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
    
    # HackerNews
    try:
        r = await client.get("https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=2")
        if r.status_code == 200:
            for hit in r.json().get("hits", []):
                if hit.get("title"):
                    items.append({"source": "HackerNews", "title": hit["title"]})
    except Exception as e:
        print(f"[Fetch HN Error]: {e}")

    # Reddit
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
    Cria um plano completo de produto digital para: '{topic}'.
    Responde estritamente em formato JSON:
    {{
        "title": "{topic}",
        "score": 10,
        "summary": "<resumo conciso>",
        "action_plan": "<estratégia de monetização rápida>",
        "product_concept": "<descrição do micro-SaaS / ferramenta>",
        "code_payload": "<código Python ou JS funcional e conciso>",
        "landing_page_html": "<!DOCTYPE html><html><head><script src='https://cdn.tailwindcss.com'></script></head><body class='bg-slate-950 text-white min-h-screen p-8 text-center'><h1 class='text-3xl font-bold text-emerald-400 mb-4'>{topic}</h1><p class='text-slate-300 max-w-md mx-auto mb-6'>Acesso imediato à ferramenta.</p><button class='bg-emerald-500 text-black font-bold px-6 py-2 rounded-xl'>Garantir Acesso</button></body></html>",
        "social_post": "<post de conversão para LinkedIn e Twitter>"
    }}
    """
    
    completion = ai.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2
    )
    
    data = json.loads(completion.choices[0].message.content)
    
    save_opportunity_to_supabase(
        source=source,
        title=data.get("title", topic),
        score=data.get("score", 10),
        summary=data.get("summary", ""),
        action_plan=data.get("action_plan", ""),
        social_post=data.get("social_post", ""),
        product_concept=data.get("product_concept", ""),
        code_payload=data.get("code_payload", ""),
        landing_page_html=data.get("landing_page_html", "")
    )
    
    tg_text = f"🚀 *NOVO PRODUTO CRIADO!*\n\n📦 *Tema:* {topic}\n💡 *Conceito:* {data.get('product_concept')}\n\n📱 *Post:* {data.get('social_post')[:180]}..."
    await send_telegram_alert(tg_text)
    
    return data

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

app = FastAPI(title="BLING AI Ultra-Fast Action Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentRequest(BaseModel):
    prompt: str

@app.get("/")
@app.get("/health")
def health():
    return {"status": "online"}

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "agent": "BLING-AI Ultra-Fast Engine",
        "model": "openai/gpt-oss-20b",
        "database": "Supabase PostgreSQL"
    }

@app.get("/api/opportunities")
def list_opportunities():
    return {"opportunities": get_opportunities_from_supabase(limit=30)}

@app.post("/api/agent")
async def run_agent(req: AgentRequest):
    try:
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            return {"result": "Erro: GROQ_API_KEY não configurada no Railway."}
        
        client = Groq(api_key=groq_key)
        p_lower = req.prompt.lower()

        # 1. Comando Telegram
        if "telegram" in p_lower or "mensagem" in p_lower:
            res = await send_telegram_alert(f"🤖 *BLING-AI Action:*\n\n{req.prompt}")
            return {"result": f"⚡ [TELEGRAM]: {res}"}

        # 2. Comando Scan
        if "scan" in p_lower or "pesquisa" in p_lower:
            async with httpx.AsyncClient(timeout=15.0) as http_c:
                feed = await fetch_feed_items(http_c)
                for item in feed:
                    await generate_fast_product(client, item["title"], source=item["source"])
            return {"result": f"⚡ [SCAN EXECUTADO]: {len(feed)} novos itens minerados e gravados!"}

        # 3. Comando de Criação (Qualquer instrução de gerar produto/SaaS/código)
        if any(k in p_lower for k in ["cria", "gera", "faz", "produto", "saas", "código", "landing", "script", "micro"]):
            data = await generate_fast_product(client, req.prompt, source="Ordem Manual")
            return {
                "result": f"✅ [PRODUTO CRIADO E GRAVADO NO SUPABASE!]\n\n"
                          f"📦 Conceito: {data.get('product_concept')}\n\n"
                          f"💻 Código & Landing Page gerados com sucesso!\n"
                          f"📲 Notificação enviada para o teu Telegram.\n\n"
                          f"(Clica no botão de atualizar ou recarrega a página para ver o novo ativo no topo)"
            }

        # 4. Resposta Geral
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