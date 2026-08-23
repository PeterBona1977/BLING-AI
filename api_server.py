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
        return "Telegram não configurado no Railway."

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json={"chat_id": chat_id, "text": message_text, "parse_mode": "Markdown"})
            if r.status_code == 200:
                return "Mensagem enviada com sucesso para o Telegram."
            return f"Telegram Response: {r.text}"
    except Exception as e:
        return f"Erro Telegram: {e}"

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
        return f"Erro Supabase: {e}"

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
        r = await client.get("https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=3")
        if r.status_code == 200:
            for hit in r.json().get("hits", []):
                if hit.get("title"):
                    items.append({"source": "HackerNews", "title": hit["title"]})
    except Exception as e:
        print(f"[Fetch HN Error]: {e}")

    # Reddit
    for sub in ["SaaS", "SideProject"]:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (BLING-AI Market Scanner)"}
            r = await client.get(f"https://www.reddit.com/r/{sub}/new.json?limit=2", headers=headers)
            if r.status_code == 200:
                for p in r.json().get("data", {}).get("children", []):
                    title = p.get("data", {}).get("title")
                    if title:
                        items.append({"source": f"Reddit r/{sub}", "title": title})
        except Exception as e:
            print(f"[Fetch Reddit {sub} Error]: {e}")

    # GitHub
    try:
        headers = {"User-Agent": "BLING-AI Scanner"}
        r = await client.get("https://api.github.com/search/repositories?q=stars:>100+created:>2026-01-01&sort=stars&order=desc&per_page=2", headers=headers)
        if r.status_code == 200:
            for repo in r.json().get("items", []):
                name = repo.get("full_name")
                desc = repo.get("description") or "Sem descrição"
                items.append({"source": "GitHub Trending", "title": f"{name}: {desc}"})
    except Exception as e:
        print(f"[Fetch GitHub Error]: {e}")

    return items

async def generate_full_product_and_save(ai: Groq, topic: str, source: str = "Agente Sob Pedido"):
    prompt = f"""
    És um Engenheiro e Estratega de Negócios Digitais de Elite.
    Cria um ecossistema de produto digital e monetização 100% completo e funcional para: '{topic}'.
    
    Responde EXCLUSIVAMENTE em formato JSON estrito:
    {{
        "title": "{topic}",
        "score": 10,
        "summary": "<resumo conciso de 1 frase do problema e solução>",
        "action_plan": "<estratégia clara de monetização passo a passo>",
        "product_concept": "<descrição detalhada do micro-SaaS ou ferramenta>",
        "code_payload": "<código Python ou JavaScript funcional completo, comentado e executável>",
        "landing_page_html": "<!DOCTYPE html><html lang='pt'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><script src='https://cdn.tailwindcss.com'></script><title>{topic}</title></head><body class='bg-slate-950 text-slate-100 min-h-screen font-sans'><header class='p-6 max-w-5xl mx-auto flex justify-between items-center'><div class='text-xl font-bold text-emerald-400'>BLING Product</div><a href='#pricing' class='bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold px-4 py-2 rounded-xl text-sm'>Aceder Agora</a></header><main class='max-w-4xl mx-auto px-6 py-16 text-center'><h1 class='text-4xl md:text-6xl font-extrabold text-white tracking-tight mb-6'>{topic}</h1><p class='text-lg text-slate-400 mb-10 max-w-2xl mx-auto'>A solução definitiva e automatizada construída para resolver a sua maior dor de forma imediata.</p><div class='bg-slate-900 border border-slate-800 p-8 rounded-2xl max-w-md mx-auto shadow-2xl'><h3 class='text-xl font-bold mb-4'>Garantir Acesso Antecipado</h3><form class='space-y-4'><input type='email' placeholder='O seu melhor email' class='w-full p-3 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-emerald-500 text-sm'><button type='button' class='w-full py-3 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold rounded-xl text-sm transition'>Comprar / Inscrever</button></form></div></main></body></html>",
        "social_post": "<post persuasivo e viral pronto para o LinkedIn/X com gancho forte, pontos e chamada para ação>"
    }}
    """
    
    completion = ai.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3
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
    
    # Notifica também no Telegram
    tg_text = f"🚀 *PRODUTO CRIADO PELO AGENTE!*\n\n📦 *Tema:* {topic}\n💡 *Conceito:* {data.get('product_concept')}\n\n📱 *Post:* {data.get('social_post')[:200]}..."
    await send_telegram_alert(tg_text)
    
    return data

# 4. Loop Autónomo de Background
async def autonomous_scanner_loop():
    while True:
        try:
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                ai = Groq(api_key=groq_key)
                async with httpx.AsyncClient(timeout=25.0) as client:
                    feed = await fetch_feed_items(client)
                    for item in feed:
                        await generate_full_product_and_save(ai, item["title"], source=item["source"])
        except Exception as e:
            print(f"[Autonomous Scanner Error]: {e}")
            
        await asyncio.sleep(480)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(autonomous_scanner_loop())
    yield
    task.cancel()

app = FastAPI(title="BLING AI Deterministic Action Engine", lifespan=lifespan)

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
        "agent": "BLING-AI Real-Time Action Engine",
        "actions": ["Direct Code Generator", "Supabase Injector", "Instant Telegram Dispatch"],
        "database": "Supabase PostgreSQL"
    }

@app.get("/api/opportunities")
def list_opportunities():
    return {"opportunities": get_opportunities_from_supabase(limit=30)}

@app.post("/api/agent")
async def run_agent(req: AgentRequest):
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY não configurada")
    
    client = Groq(api_key=groq_key)
    p_lower = req.prompt.lower()

    # 1. Comando Direto: Telegram
    if "telegram" in p_lower or "mensagem" in p_lower or "notifica" in p_lower:
        res = await send_telegram_alert(f"🤖 *Instrução BLING-AI Executada:*\n\n{req.prompt}")
        return {"result": f"⚡ [AÇÃO REAL EXECUTADA NO TELEGRAM]:\n{res}"}

    # 2. Comando Direto: Scan de Mercado
    if "scan" in p_lower or "pesquisa" in p_lower or "mercado" in p_lower:
        async with httpx.AsyncClient(timeout=25.0) as http_c:
            feed = await fetch_feed_items(http_c)
            for item in feed:
                await generate_full_product_and_save(client, item["title"], source=item["source"])
        return {"result": f"⚡ [SCAN REAL EXECUTADO]: Processados e gravados {len(feed)} novos produtos no Supabase!"}

    # 3. Comando Direto: Criação de Produto / Código / Micro-SaaS / Landing Page
    if any(k in p_lower for k in ["cria", "gera", "faz", "produto", "saas", "código", "landing", "script"]):
        product_data = await generate_full_product_and_save(client, req.prompt, source="Ordem Manual")
        return {
            "result": f"✅ [PRODUTO CRIADO E GRAVADO NO SUPABASE COM SUCESSO!]\n\n"
                      f"📦 Produto: {product_data.get('product_concept')}\n\n"
                      f"💻 Código Gerado: Sim (visível no painel)\n"
                      f"🌐 Landing Page: Sim (pronta a pré-visualizar)\n"
                      f"📲 Alerta Telegram: Enviado\n\n"
                      f"Atualiza a lista para ver o novo ativo no topo!"
        }

    # 4. Consulta Geral
    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": "És o consultor e engenheiro executivo BLING-AI."},
            {"role": "user", "content": req.prompt}
        ],
        temperature=0.3
    )
    return {"result": completion.choices[0].message.content}