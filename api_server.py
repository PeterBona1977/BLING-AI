import os
import asyncio
import json
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from groq import Groq
from supabase import create_client, Client

# Inicialização do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Optional[Client] = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_opportunity_to_supabase(source: str, title: str, score: int, summary: str, action_plan: str):
    if not supabase:
        print("[Supabase Warning]: Cliente não configurado.")
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
        print(f"[Supabase]: Oportunidade gravada - {title}")
    except Exception as e:
        print(f"[Supabase Error]: {e}")

def get_opportunities_from_supabase(limit: int = 10):
    if not supabase:
        return []
    try:
        response = supabase.table("opportunities").select("*").order("created_at", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        print(f"[Supabase Read Error]: {e}")
        return []

# Background Loop Autónomo
async def autonomous_scanner_loop():
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get("https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=3")
                if res.status_code == 200:
                    hits = res.json().get("hits", [])
                    groq_key = os.getenv("GROQ_API_KEY")
                    
                    if groq_key and hits:
                        ai = Groq(api_key=groq_key)
                        for item in hits:
                            title = item.get("title", "Sem título")
                            
                            prompt = f"""
                            Analisa este tópico recente da web: '{title}'.
                            Avalia o potencial de tráfego, interesse ou oportunidade digital associada.
                            Responde em JSON estrito:
                            {{"score": <número de 1 a 10>, "summary": "<resumo de 1 frase>", "action_plan": "<ideia de ação ou copy>"}}
                            """
                            
                            completion = ai.chat.completions.create(
                                model="llama-3.1-70b-versatile",
                                messages=[{"role": "user", "content": prompt}],
                                response_format={"type": "json_object"},
                                temperature=0.3
                            )
                            
                            data = json.loads(completion.choices[0].message.content)
                            if data.get("score", 0) >= 5:
                                save_opportunity_to_supabase(
                                    source="HackerNews Feed",
                                    title=title,
                                    score=data.get("score", 0),
                                    summary=data.get("summary", ""),
                                    action_plan=data.get("action_plan", "")
                                )
        except Exception as e:
            print(f"[Scanner Loop Error]: {e}")
        
        # Intervalo de 10 minutos (600s)
        await asyncio.sleep(600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    scanner_task = asyncio.create_task(autonomous_scanner_loop())
    yield
    scanner_task.cancel()

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
        "agent": "BLING-AI Autonomous Engine",
        "scanner_active": True,
        "database": "Supabase PostgreSQL"
    }

@app.get("/api/opportunities")
def list_opportunities():
    return {"opportunities": get_opportunities_from_supabase()}

@app.post("/api/agent")
def run_agent(req: AgentRequest):
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY não configurada")
    
    client = Groq(api_key=groq_key)
    completion = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[
            {"role": "system", "content": "És o agente de inteligência de mercado BLING-AI."},
            {"role": "user", "content": req.prompt}
        ],
        temperature=0.3
    )
    return {"result": completion.choices[0].message.content}