import time
from core.vault import get_secret, set_secret

def request_user_input_for_account(service_name: str, required_fields: list, context_reason: str) -> dict:
    """
    Regista um pedido de dados na plataforma para criação autónoma de contas.
    Verifica se os dados já existem no Vault antes de solicitar ao utilizador.
    """
    missing_fields = []
    collected_data = {}

    # 1. Verifica o que já existe no Vault
    for field in required_fields:
        vault_key = f"{service_name.lower()}_{field.lower()}"
        val = get_secret(vault_key)
        if val:
            collected_data[field] = val
        else:
            missing_fields.append(field)

    # 2. Se não faltar nada, avança imediatamente
    if not missing_fields:
        print(f"✅ [Inputs] Todos os dados para {service_name} já estão disponíveis no Vault.")
        return {"status": "READY", "data": collected_data}

    # 3. Emite a solicitação de input para a Plataforma BLING AI
    payload_request = {
        "service": service_name,
        "reason": context_reason,
        "required_inputs": missing_fields,
        "timestamp": time.time()
    }

    print(f"\n📋 [PLATAFORMA BLING AI] Pedido de Inputs emitido para: {service_name}")
    print(f"⚠️ Campos necessários na UI: {', '.join(missing_fields)}")
    print(f"💡 Contexto: {context_reason}\n")

    # Guarda o estado do pedido pendente
    set_secret(f"pending_req_{service_name.lower()}", str(payload_request))

    return {
        "status": "AWAITING_USER_INPUT",
        "missing_fields": missing_fields,
        "message": f"A aguardar preenchimento dos campos {missing_fields} na Plataforma BLING AI para criar conta em {service_name}."
    }

def submit_user_input_from_platform(service_name: str, input_data: dict):
    """
    Callback chamado pela interface da tua plataforma quando o utilizador submete os dados.
    """
    for field, value in input_data.items():
        vault_key = f"{service_name.lower()}_{field.lower()}"
        set_secret(vault_key, value)
    
    # Limpa pedido pendente
    set_secret(f"pending_req_{service_name.lower()}", "")
    print(f"🚀 [Inputs] Dados recebidos da plataforma para {service_name}. A prosseguir com a criação da conta...")