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
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json={"chat_id": chat_id, "text": message_text, "parse_mode": "Markdown"})
            if r.status_code == 200:
                return "Mensagem enviada com sucesso para o Telegram."
            return f"Erro Telegram: {r.text}"
    except Exception as e:
        return f"Erro de conexão Telegram: {e}"

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
        return "Oportunidade gravada com sucesso no Supabase."
    except Exception as e:
        return f"Erro Supabase: {e}"

def get_opportunities_from_supabase(limit: int = 25):
    if not supabase:
        return []
    try:
        response = supabase.table("opportunities").select("*").order("created_at", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        print(f"[Supabase Read Error]: {e}")
        return []

# 3. Coletor Multi-Fontes
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

async def process_item_and_save(ai: Groq, item: Dict[str, str]):
    prompt = f"""
    Analisa esta necessidade de mercado / tendência recente: '{item['title']}'.
    Fonte: {item['source']}.
    Cria o ecossistema completo de monetização em JSON estrito.
    
    {{
        "score": <inteiro de 1 a 10>,
        "summary": "<resumo conciso de 1 frase>",
        "action_plan": "<estratégia de monetização>",
        "social_post": "<post viral formatado com gancho, 2 pontos-chave e CTA>",
        "product_concept": "<ideia de micro-SaaS ou ferramenta>",
        "code_payload": "<código Python ou JavaScript funcional>",
        "landing_page_html": "<código HTML standalone moderno com Tailwind CDN no head, cabeçalho de alta conversão, hero section, 3 benefícios e CTA>"
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
            code_payload=data.get("code_payload", ""),
            landing_page_html=data.get("landing_page_html", "")
        )
        
        if score >= 8:
            msg = f"🚨 *NOVA OPORTUNIDADE (Score: {score}/10)*\n\n📌 *Fonte:* {item['source']}\n💡 *Tópico:* {item['title']}\n\n📦 *Produto:* {data.get('product_concept')}\n\n📱 *Post:*\n{data.get('social_post')}"
            await send_telegram_alert(msg)
    
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
                        await process_item_and_save(ai, item)
        except Exception as e:
            print(f"[Autonomous Scanner Error]: {e}")
            
        await asyncio.sleep(480)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(autonomous_scanner_loop())
    yield
    task.cancel()

app = FastAPI(title="BLING AI Action Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentRequest(BaseModel):
    prompt: str

# 5. Ferramentas Reais que o Agente Executa
TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "trigger_market_scan",
            "description": "Executa um scan imediato no mercado (HackerNews, Reddit, GitHub) e grava os novos produtos na base de dados agora.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_telegram_notification",
            "description": "Envia um alerta ou mensagem de texto diretamente para o Telegram do utilizador.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Texto da mensagem a enviar para o Telegram"}
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_custom_product",
            "description": "Cria um produto digital completo (código, landing page, post e estratégia) sobre um tema específico instruído pelo utilizador e grava no Supabase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Tema ou nicho do produto"},
                    "product_concept": {"type": "string", "description": "Conceito do produto/micro-SaaS"},
                    "code_payload": {"type": "string", "description": "Código fonte funcional completo"},
                    "landing_page_html": {"type": "string", "description": "HTML com Tailwind da Landing Page"},
                    "social_post": {"type": "string", "description": "Post pronto para redes sociais"}
                },
                "required": ["topic", "product_concept", "code_payload", "landing_page_html", "social_post"]
            }
        }
    }
]

@app.get("/")
@app.get("/health")
def health():
    return {"status": "online"}

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "agent": "BLING-AI Autonomous Action Engine",
        "execution_mode": "Tool-Calling Enabled (Real Actions)",
        "database": "Supabase PostgreSQL"
    }

@app.get("/api/opportunities")
def list_opportunities():
    return {"opportunities": get_opportunities_from_supabase(limit=25)}

@app.post("/api/agent")
async def run_agent(req: AgentRequest):
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY não configurada")
    
    client = Groq(api_key=groq_key)
    
    messages = [
        {
            "role": "system", 
            "content": "És o Agente Autónomo Executivo BLING-AI. Tens ferramentas reais para executar ações no sistema. Quando o utilizador te pedir para fazer um scan, enviar mensagem para o Telegram, ou criar um produto/landing page/código, deves OBRIGATORIAMENTE invocar a ferramenta correspondente para executar a ação no mundo real."
        },
        {"role": "user", "content": req.prompt}
    ]

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=messages,
        tools=TOOLS_DEFINITIONS,
        tool_choice="auto",
        temperature=0.2
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # Se a IA decidiu executar ferramentas reais:
    if tool_calls:
        action_results = []
        for tool_call in tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            if func_name == "trigger_market_scan":
                async with httpx.AsyncClient(timeout=25.0) as http_c:
                    feed = await fetch_feed_items(http_c)
                    count = 0
                    for item in feed:
                        await process_item_and_save(client, item)
                        count += 1
                action_results.append(f"⚡ [AÇÃO EXECUTADA]: Scan de mercado realizado com sucesso! Processados {count} itens.")

            elif func_name == "send_telegram_notification":
                msg = args.get("message", "")
                res = await send_telegram_alert(msg)
                action_results.append(f"📲 [AÇÃO EXECUTADA]: {res}")

            elif func_name == "create_custom_product":
                topic = args.get("topic", "Custom Product")
                save_opportunity_to_supabase(
                    source="Direct Agent Action",
                    title=topic,
                    score=10,
                    summary=f"Produto criado sob ordem direta: {topic}",
                    action_plan="Lançamento e monetização imediata via landing page.",
                    social_post=args.get("social_post", ""),
                    product_concept=args.get("product_concept", ""),
                    code_payload=args.get("code_payload", ""),
                    landing_page_html=args.get("landing_page_html", "")
                )
                action_results.append(f"📦 [AÇÃO EXECUTADA]: Produto '{topic}' criado, código gerado, landing page compilada e gravado no Supabase com sucesso!")

        return {"result": "\n\n".join(action_results)}

    return {"result": response_message.content}