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

# 2. Telegram Notifier
async def send_telegram_alert(source: str, title: str, score: int, post: str, product: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return

    message = (
        f"🚨 *NOVA OPORTUNIDADE (Score: {score}/10)*\n\n"
        f"📌 *Fonte:* {source}\n"
        f"💡 *Tópico:* {title}\n\n"
        f"📦 *Produto:* {product}\n\n"
        f"📱 *Post de Conversão:*\n{post}"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            await client.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
            print(f"[Telegram]: Alerta enviado com sucesso.")
    except Exception as e:
        print(f"[Telegram Error]: {e}")

def save_opportunity_to_supabase(
    source: str, 
    title: str, 
    score: int, 
    summary: str, 
    action_plan: str, 
    social_post: str = "", 
    product_concept: str = "",
    code_payload: str = ""
):
    if not supabase:
        return
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
            "status": "detected"
        }).execute()
        print(f"[Supabase]: Ativo gravado [{source}] - {title[:35]}... (Score: {score})")
    except Exception as e:
        print(f"[Supabase Error]: {e}")

def get_opportunities_from_supabase(limit: int = 25):
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

# 4. Loop Autónomo com Geração de Código/Boilerplate
async def autonomous_scanner_loop():
    while True:
        try:
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                ai = Groq(api_key=groq_key)
                async with httpx.AsyncClient(timeout=20.0) as client:
                    feed = await fetch_feed_items(client)
                    
                    for item in feed:
                        prompt = f"""
                        Analisa esta necessidade de mercado / tendência recente: '{item['title']}'.
                        Fonte: {item['source']}.
                        Identifica o valor comercial, potencial de monetização e crie o produto digital completo (código, post, conceito).
                        
                        Responde EXCLUSIVAMENTE em formato JSON estrito:
                        {{
                            "score": <inteiro de 1 a 10>,
                            "summary": "<resumo conciso de 1 frase>",
                            "action_plan": "<estratégia de monetização>",
                            "social_post": "<post viral formatado com gancho, 2 pontos-chave e CTA>",
                            "product_concept": "<ideia de micro-SaaS ou ferramenta>",
                            "code_payload": "<código Python ou JavaScript funcional completo e executável que resolve este problema ou serve de boilerplate pronto>"
                        }}
                        """
                        
                        completion = ai.chat.completions.create(
                            model="openai/gpt-oss-20b",
                            messages=[{"role": "user", "content": prompt}],
                            response_format={"type": "json_object"},
                            temperature=0.3
                        )
                        
                        data = json.loads(completion.choices[0].message.content)
                        score = data.get("score", 0)
                        
                        if score >= 6:
                            save_opportunity_to_supabase(
                                source=item["source"],
                                title=item["title"],
                                score=score,
                                summary=data.get("summary", ""),
                                action_plan=data.get("action_plan", ""),
                                social_post=data.get("social_post", ""),
                                product_concept=data.get("product_concept", ""),
                                code_payload=data.get("code_payload", "")
                            )
                            
                            if score >= 8:
                                await send_telegram_alert(
                                    source=item["source"],
                                    title=item["title"],
                                    score=score,
                                    post=data.get("social_post", ""),
                                    product=data.get("product_concept", "")
                                )
        except Exception as e:
            print(f"[Autonomous Scanner Error]: {e}")
            
        await asyncio.sleep(480)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(autonomous_scanner_loop())
    yield
    task.cancel()

app = FastAPI(title="BLING AI Autonomous Engine", lifespan=lifespan)

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
        "agent": "BLING-AI Autonomous Product Engine",
        "sources": ["HackerNews", "Reddit SaaS/SideProject", "GitHub"],
        "notifications": "Telegram Active",
        "code_generator": "Active",
        "database": "Supabase PostgreSQL"
    }

@app.get("/api/opportunities")
def list_opportunities():
    return {"opportunities": get_opportunities_from_supabase(limit=25)}

@app.post("/api/agent")
def run_agent(req: AgentRequest):
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY não configurada")
    
    client = Groq(api_key=groq_key)
    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": "És o engenheiro e estratega de monetização BLING-AI."},
            {"role": "user", "content": req.prompt}
        ],
        temperature=0.3
    )
    return {"result": completion.choices[0].message.content}