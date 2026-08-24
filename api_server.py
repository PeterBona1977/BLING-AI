import os
import asyncio
import json
import re
import traceback
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

# 2. Despacho Telegram
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

# 3. Gestor de Auto-Evolução e Competências Dinâmicas
def get_all_skills():
    if not supabase:
        return []
    try:
        res = supabase.table("agent_skills").select("*").eq("status", "active").execute()
        return res.data
    except Exception as e:
        print(f"[Skills Fetch Error]: {e}")
        return []

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
    """A IA programa a sua própria ferramenta em Python, testa-a e regista-a"""
    prompt = f"""
    Precisas de criar uma nova competência/função Python pura e auto-suficiente para resolver a seguinte necessidade:
    '{required_task}'
    
    Regras estritas:
    1. O código tem de definir uma função principal chamada `execute(params: dict) -> dict`.
    2. Usa apenas bibliotecas padrão ou httpx/json.
    3. Trata exceções internamente.
    
    Responde EXCLUSIVAMENTE em formato JSON:
    {{
        "skill_name": "<identificador_unico_snake_case>",
        "description": "<resumo do que a ferramenta faz>",
        "python_code": "def execute(params: dict) -> dict:\\n    # Logica aqui\\n    return {{'result': 'ok'}}"
    }}
    """
    try:
        completion = ai.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "És o motor de meta-programação e auto-melhoramento da BLING AI."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        raw = completion.choices[0].message.content
        data = {}
        try:
            data = json.loads(raw)
        except Exception:
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                data = json.loads(m.group(0))

        name = data.get("skill_name", "skill_generica")
        desc = data.get("description", "Ferramenta auto-gerada")
        code = data.get("python_code", "")

        # Teste dinâmico de sintaxe (Sandbox check)
        compile(code, "<string>", "exec")
        
        # Guarda na base de dados
        register_new_skill(name, desc, code)

        # Notifica o criador no Telegram
        await send_telegram_alert(
            f"🧠 *[AUTO-EVOLUÇÃO]: NOVA FERRAMENTA CRIADA!*\n\n"
            f"🛠 *Nome:* `{name}`\n"
            f"📋 *Capacidade:* {desc}\n\n"
            f"A IA expandiu as suas próprias capacidades de forma autónoma."
        )
        return {"status": "success", "skill_name": name, "description": desc}
    except Exception as e:
        print(f"[Self-Evolve Error]: {e}")
        return {"status": "error", "error": str(e)}

def execute_dynamic_skill(skill_code: str, params: dict) -> dict:
    """Executa dinamicamente a competência criada pela IA"""
    local_scope = {}
    exec(skill_code, {}, local_scope)
    if "execute" in local_scope:
        return local_scope["execute"](params)
    raise ValueError("Função 'execute' não encontrada no módulo dinâmico.")

# 4. Loop de Auto-Reflexão e Otimização
async def autonomous_self_improvement_loop():
    while True:
        try:
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                ai = Groq(api_key=groq_key)
                
                # Auto-Auditoria: Avalia se precisa de criar uma nova ferramenta
                audit_prompt = """
                Avalia o estado do ecossistema e sugere 1 nova ferramenta operacional que o agente BLING-AI ainda deva construir para si mesmo (ex: analisador de concorrentes, gerador de slugs, validador de SEO, calculador de precificação).
                Responde apenas com o nome da tarefa a automatizar em 1 frase.
                """
                comp = ai.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=[{"role": "user", "content": audit_prompt}],
                    temperature=0.7
                )
                suggested_need = comp.choices[0].message.content.strip()
                
                # Cria a nova função autonomamente
                await self_evolve_create_skill(ai, suggested_need)

        except Exception as e:
            print(f"[Self Improvement Loop Error]: {e}")
            
        await asyncio.sleep(1800) # Auto-auditoria e evolução a cada 30 minutos

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(autonomous_self_improvement_loop())
    yield
    task.cancel()

app = FastAPI(title="BLING AI Self-Evolving Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvolveRequest(BaseModel):
    task_description: str

class RunSkillRequest(BaseModel):
    skill_name: str
    params: dict

@app.get("/")
@app.get("/health")
def health():
    return {"status": "online", "mode": "Self-Evolving Meta-Agent"}

@app.get("/api/skills")
def list_skills():
    return {"skills": get_all_skills()}

# Endpoint para forçar a IA a criar uma função nova sob pedido
@app.post("/api/evolve")
async def trigger_evolution(req: EvolveRequest):
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY em falta")
    ai = Groq(api_key=groq_key)
    res = await self_evolve_create_skill(ai, req.task_description)
    return res

# Endpoint para executar qualquer ferramenta criada dinamicamente pela IA
@app.post("/api/run-skill")
def run_skill(req: RunSkillRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase não configurado")
    res = supabase.table("agent_skills").select("*").eq("name", req.skill_name).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Competência não encontrada")
    
    code = res.data[0]["code"]
    try:
        output = execute_dynamic_skill(code, req.params)
        return {"status": "success", "output": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))