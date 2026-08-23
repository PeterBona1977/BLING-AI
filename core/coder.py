from groq import Groq
from core.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

def generate_module_code(prompt_requirements: str) -> str:
    """Gera código Python autónomo usando o DeepSeek R1 via Groq."""
    prompt = f"""
    És um programador Python de elite focado em automação e Web Scraping.
    Cria o código Python completo para o seguinte requisito:
    {prompt_requirements}

    REGRAS DE CÓDIGO:
    - Retorna APENAS o código Python válido. Sem blocos markdown ```python ... ```, sem explicações.
    - O ficheiro deve conter pelo menos uma função que comece por scan_ ou execute_.
    - Trata todas as exceções para evitar que o main.py vá abaixo.
    """
    
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )
        code = response.choices[0].message.content.strip()
        
        # Remove a tag de raciocínio <think> do DeepSeek R1
        if "<think>" in code and "</think>" in code:
            code = code.split("</think>")[-1].strip()
            
        if code.startswith("```python"):
            code = code.replace("```python", "").replace("```", "").strip()
        elif code.startswith("```"):
            code = code.replace("```", "").strip()
            
        return code
    except Exception as e:
        print(f"❌ Erro ao gerar código via Groq (DeepSeek R1): {e}")
        return ""