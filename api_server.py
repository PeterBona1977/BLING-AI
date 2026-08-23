import os
import json
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="BLING AI API & Dashboard",
    description="Autonomous Opportunity Scanner Backend",
    version="0.1.0"
)

# Configuração global de CORS para permitir chamadas do Cloudflare Pages e Localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos de Dados Pydantic
class AgentRequest(BaseModel):
    prompt: str
    model: Optional[str] = "llama-3.3-70b-versatile"

class AgentResponse(BaseModel):
    status: str
    response: str
    model_used: str

# 1. Rotas de Verificação de Estado (Health Checks)
@app.get("/")
@app.get("/health")
def health_check() -> Dict[str, str]:
    return {
        "status": "online",
        "service": "BLING-AI Backend",
        "version": "0.1.0"
    }

@app.get("/api/status")
def get_status() -> Dict[str, Any]:
    """Retorna o estado operacional do agente e módulos ativos."""
    return {
        "status": "online",
        "agent": "BLING-AI Autonomous Scanner",
        "backend": "FastAPI (Railway)",
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "modules": [
            "iGaming Affiliate Intelligence",
            "Token & Web3 Trend Scanner",
            "Autonomous Opportunity Engine"
        ]
    }

# 2. Rota de Credenciais / Inputs Pendentes
@app.get("/api/pending-inputs")
def get_pending_inputs() -> Dict[str, Any]:
    """Retorna pedidos de dados/credenciais pendentes no Vault."""
    return {
        "pending_inputs": [],
        "count": 0,
        "message": "Nenhuma credencial ou ação manual pendente."
    }

# 3. Rota de Execução de Comandos com Groq LLM
@app.post("/api/run-agent", response_model=AgentResponse)
def run_agent(request: AgentRequest) -> AgentResponse:
    groq_api_key = os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        # Resposta fallback caso a chave não esteja definida nas variáveis de ambiente
        return AgentResponse(
            status="success",
            response=f"[Simulação BLING-AI]: A chave GROQ_API_KEY não foi detetada. Pedido recebido: '{request.prompt}'",
            model_used="system-fallback"
        )

    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)

        completion = client.chat.completions.create(
            model=request.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu és o agente de inteligência autónomo do BLING-AI. "
                        "A tua especialidade é varrer, analisar e identificar oportunidades de alta rentabilidade "
                        "em afiliação iGaming, lançamentos Web3/Tokens e fluxos de automação de tráfego. "
                        "Dá respostas estruturadas, diretas e acionáveis."
                    ),
                },
                {
                    "role": "user",
                    "content": request.prompt,
                },
            ],
            temperature=0.5,
            max_tokens=1024,
        )

        agent_output = completion.choices[0].message.content
        return AgentResponse(
            status="success",
            response=agent_output,
            model_used=request.model
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na execução do Groq Agent: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api_server:app", host="0.0.0.0", port=port, reload=True)