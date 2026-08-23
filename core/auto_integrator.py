import os
import re
from pathlib import Path
from core.coder import generate_module_code

MODULES_DIR = Path("modules")

def auto_build_and_deploy_module(opportunity_details: dict) -> bool:
    """
    Recebe uma oportunidade viável, gera o código autónomo via Groq,
    valida a compilação e instala o módulo diretamente em modules/.
    """
    title = opportunity_details.get("title", "auto_module")
    market = opportunity_details.get("market", "general")
    details = opportunity_details.get("details", "")
    action = opportunity_details.get("action_required", "")

    # Define o nome do ficheiro limpo
    clean_name = re.sub(r'[^a-zA-Z0-9_]', '', title.lower().replace(" ", "_"))[:30]
    filename = f"auto_{market}_{clean_name}.py"
    filepath = MODULES_DIR / filename

    if filepath.exists():
        print(f"ℹ️ [Auto-Integrator] O módulo {filename} já existe. A saltar geração.")
        return True

    print(f"🛠️ [Auto-Integrator] A gerar código autónomo para: {title}...")

    prompt = f"""
    Cria um módulo Python de produção totalmente autónomo e funcional para executar a seguinte oportunidade:
    Mercado: {market}
    Título: {title}
    Detalhes: {details}
    Ação Necessária: {action}

    REQUISITOS OBRIGATÓRIOS DO CÓDIGO:
    1. Define uma função principal iniciada por 'scan_' ou 'execute_' (ex: def scan_{clean_name}():).
    2. A função DEVE retornar um dicionário ou lista com dados estruturados da execução/oportunidade.
    3. Trata TODAS as exceções internamente (try/except) para nunca interromper o main.py.
    4. Usa requests, asyncio ou a standard library de Python para interagir com APIS/web scrapers.
    5. Retorna APENAS o código Python sem sintaxe markdown ```python.
    """

    code = generate_module_code(prompt)

    if not code or len(code.strip()) < 50:
        print(f"❌ [Auto-Integrator] Falha ao gerar código válido para {title}.")
        return False

    # Validação de compilação básica
    try:
        compile(code, filename, 'exec')
    except Exception as e:
        print(f"❌ [Auto-Integrator] Erro de compilação no código gerado: {e}")
        return False

    # Escrita do novo módulo autónomo
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"✅ [Auto-Integrator] Módulo {filename} criado e pronto para a próxima varredura!")
    return True