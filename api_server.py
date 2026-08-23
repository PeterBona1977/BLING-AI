import os
import glob
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from core.vault import _load_vault

app = FastAPI(title="BLING AI API & Dashboard")

# Permite acessos remotos sem bloqueios CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODULES_DIR = os.path.join(os.path.dirname(__file__), "modules")

@app.get("/api/status")
def get_status():
    """Retorna o estado do agente e os módulos ativos."""
    module_files = glob.glob(os.path.join(MODULES_DIR, "*.py"))
    modules = [
        os.path.basename(f).replace(".py", "") 
        for f in module_files 
        if not os.path.basename(f).startswith("__")
    ]
    
    return {
        "status": "ONLINE",
        "active_modules_count": len(modules),
        "modules": modules
    }

@app.get("/api/pending-inputs")
def get_pending_inputs():
    """Retorna os pedidos de dados/credenciais pendentes no Vault."""
    vault_data = _load_vault()
    pending = []
    for k, v in vault_data.items():
        if k.startswith("pending_req_") and v:
            pending.append({"key": k, "data": v})
    return {"pending_requests": pending}

if __name__ == "__main__":
    import uvicorn
    print("🚀 A iniciar API Server do BLING AI em http://0.0.0.0:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)