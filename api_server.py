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

def save_opportunity_to_supabase(source: str, title: str, score: int, summary: str, action_plan: str):
    if not supabase:
        return
    try:
        supabase.table("opportunities").insert({
            "source": source,
            "title": title,
            "score": score,
            "summary": summary,
            "action_plan": action_plan,
            "status": "detected"
        }).execute()
        print(f"[Supabase]: Gravado [{source}] - {title[:40]}...")
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

# 2. Coletor Multi-Fontes
async def fetch_feed_items(client: httpx.AsyncClient) -> List[Dict[str, str]]:
    items = []
    
    # Fonte 1: Hacker News
    try:
        r = await client.get("https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=3")
        if r.status_code == 200:
            for hit in r.json().get("hits", []):
                if hit.get("title"):
                    items.append({"source": "HackerNews", "title": hit["title"]})
    except Exception as e:
        print(f"[Fetch HN Error]: {e}")

    # Fonte 2: Reddit (r/SaaS & r/SideProject)
    for sub in ["SaaS", "SideProject"]:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (BLING-AI Autonomous Market Scanner)"}
            r = await client.get(f"https://www.reddit.com/r/{sub}/new.json?limit=2", headers=headers)
            if r.status_code == 200:
                posts = r.json().get("data", {}).get("children", [])
                for p in posts:
                    title = p.get("data", {}).get("title")
                    if title:
                        items.append({"source": f"Reddit r/{sub}", "title": title})
        except Exception as e:
            print(f"[Fetch Reddit {sub} Error]: {e}")

    return items

# 3. Loop Autónomo de Análise e Execução
async def autonomous_scanner_loop():
    while True:
        try:
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                ai = Groq(api_key=groq_key)
                async with httpx.AsyncClient(timeout=12.0) as client:
                    feed = await fetch_feed_items(client)
                    
                    for item in feed:
                        prompt = f"""
                        Analisa esta necessidade de mercado / tópico recente: '{item['title']}'.
                        Fonte: {item['source']}.
                        Identifica o valor comercial, potencial de monetização ou criação de micro-SaaS / audiência.
                        Responde em JSON estrito:
                        {{"score": <inteiro de 1 a 10>, "summary": "<resumo de 1 frase do problema/oportunidade>", "action_plan": "<estratégia clara de monetização, copy ou micro-produto>"}}
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
                                action_plan=data.get("action_plan", "")
                            )
        except Exception as e:
            print(f"[Autonomous Scanner Error]: {e}")
            
        # Scan a cada 8 minutos
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
        "agent": "BLING-AI Multi-Channel Engine",
        "active_sources": ["HackerNews", "Reddit r/SaaS", "Reddit r/SideProject"],
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
            {"role": "system", "content": "És o agente de inteligência e estratégia de mercado BLING-AI."},
            {"role": "user", "content": req.prompt}
        ],
        temperature=0.3
    )
    return {"result": completion.choices[0].message.content}