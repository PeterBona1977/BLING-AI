import json
from groq import Groq
from core.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

def prospect_web_opportunities() -> str:
    """Procura e analisa ativamente oportunidades Web usando o DeepSeek R1 via Groq."""
    prompt = """
    És um prospetor financeiro autónomo de IA.
    Analisa tendências Web em tempo real e formula 2 oportunidades concretas para execução imediata.

    ÂMBITO DE PROSPEÇÃO:
    1. Bounties & Automações de Freelance (Tarefas técnicas pagas, scripts de scraping, bots).
    2. Programas de Afiliados de Alta Conversão (SaaS, Web3, Ferramentas de IA).
    3. Auditoria & Lead Generation de Negócios Locais.

    Responde ESTRITAMENTE num formato JSON válido contendo uma chave "opportunities" com a lista:
    {
        "opportunities": [
            {
                "category": "Categoria (Ex: Freelance Bounty / Affiliate / Lead Gen)",
                "title": "Título conciso do negócio/ativo",
                "estimated_profit": "+$XX.XX USD",
                "effort_level": "Baixo / Médio",
                "description": "Explicação detalhada do modelo de monetização e passos de execução",
                "target_link_or_source": "Fonte/Plataforma de prospeção"
            }
        ]
    }
    """
    
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )
        content = response.choices[0].message.content.strip()
        
        # Remove a tag de raciocínio <think> do DeepSeek R1
        if "<think>" in content and "</think>" in content:
            content = content.split("</think>")[-1].strip()
            
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()

        data = json.loads(content)
        return json.dumps(data.get("opportunities", []))
    except Exception as e:
        print(f"❌ Erro na prospeção Web Groq (DeepSeek R1): {e}")
        return json.dumps([])