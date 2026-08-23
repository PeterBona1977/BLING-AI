import json
from groq import Groq
from core.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

def evaluate_opportunity(market_type: str, data_context: str) -> dict:
    """Envia dados brutos para a Groq e trata o output independentemente da estrutura."""
    prompt = f"""
    És um agente autónomo de elite especializado em arbitragem e investimento no mercado: {market_type}.
    A tua missão é identificar oportunidades de ALTO LUCRO (ROI) e BAIXO RISCO.

    Dados em tempo real recolhidos:
    {data_context}

    Responde ESTRITAMENTE num formato JSON válido com este objeto:
    {{
        "viable": true,
        "market": "{market_type}",
        "title": "Nome do ativo / oportunidade",
        "estimated_roi": "+XX% ou valor est. de revenda em $USD",
        "risk_level": "Baixo / Médio / Alto",
        "details": "Fundamentação do valor do ativo, comercialização e liquidez",
        "action_required": "Instruções exatas de aquisição/execução"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        
        # Trata raciocínio se presente
        if "</think>" in content:
            content = content.split("</think>")[-1].strip()

        data = json.loads(content)
        
        # Se o modelo devolver uma lista, pega na primeira oportunidade viável
        if isinstance(data, list):
            return data[0] if len(data) > 0 else {"viable": False}
        elif isinstance(data, dict) and "opportunities" in data:
            opps = data["opportunities"]
            return opps[0] if isinstance(opps, list) and len(opps) > 0 else {"viable": False}
            
        return data if isinstance(data, dict) else {"viable": False}
    except Exception as e:
        print(f"❌ Erro no processamento Groq: {e}")
        return {
            "viable": False,
            "market": market_type,
            "title": "Erro de análise",
            "estimated_roi": "0%",
            "risk_level": "Alto",
            "details": str(e),
            "action_required": "Nenhuma"
        }