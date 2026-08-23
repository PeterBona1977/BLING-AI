from groq import Groq
from core.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

def research_market_deep(query: str) -> str:
    """Realiza uma pesquisa aprofundada usando o DeepSeek R1 via Groq."""
    prompt = f"""
    Realiza uma análise detalhada e pesquisa de mercado sobre:
    {query}

    Fornece um resumo com oportunidades de monetização, riscos e ações recomendadas.
    """
    
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )
        content = response.choices[0].message.content.strip()
        
        # Remove a tag de raciocínio <think> para apresentar apenas a análise final
        if "<think>" in content and "</think>" in content:
            content = content.split("</think>")[-1].strip()
            
        return content
    except Exception as e:
        print(f"❌ Erro na pesquisa profunda via Groq (DeepSeek R1): {e}")
        return "Falha ao obter dados de pesquisa."