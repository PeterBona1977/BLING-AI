import json
import os
from core.vault import get_vault
from core.coder import generate_module_code

def process_opportunity_execution(opportunity: dict) -> dict:
    """Avalia a oportunidade, verifica o cofre e aciona a geração de código para execução."""
    category = opportunity.get("market", "Geral")
    title = opportunity.get("title", "Sem Título")
    details = opportunity.get("details", "")
    
    vault = get_vault()
    credentials = vault.get("user_credentials", {})
    
    missing_requirements = []
    if "payout_destination" not in credentials:
        missing_requirements.append("IBAN ou PayPal para recebimento das comissões")
        
    if missing_requirements:
        print(f"⚠️ [EXECUTOR] Para concluir '{title}', faltam dados no Cofre:")
        for req in missing_requirements:
            print(f"   - {req}")
        return {
            "status": "WAITING_CREDENTIALS",
            "missing": missing_requirements,
            "message": f"A IA precisa de: {', '.join(missing_requirements)} para finalizar o setup."
        }
    
    print(f"🚀 [EXECUTOR] A gerar módulo automático de execução para: {title}...")
    
    prompt_code = f"""
    Cria um módulo Python autónomo para a pasta /modules/ focado em executar a oportunidade:
    Título: {title}
    Categoria: {category}
    Detalhes: {details}
    
    O ficheiro deve conter uma função scan_ ou execute_ que efetue o scraping/integração necessária.
    """
    
    new_code = generate_module_code(prompt_code)
    file_name = f"exec_{category.lower().replace(' ', '_')}.py"
    module_path = os.path.join("modules", file_name)
    
    with open(module_path, "w", encoding="utf-8") as f:
        f.write(new_code)
        
    print(f"✅ [EXECUTOR] Novo módulo de execução criado e ativo em: {module_path}")
    return {"status": "EXECUTED", "module": file_name}