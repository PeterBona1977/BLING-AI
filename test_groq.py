import json
from groq import Groq
from core.config import GROQ_API_KEY

def test_connection():
    print("⚡ A testar conexão e parsing de resposta na Groq...")
    
    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "user", "content": "Responde apenas com o texto: OK_BLING_AI_ATIVO"}
            ]
        )
        content = response.choices[0].message.content.strip()
        
        # Trata tags de raciocínio se presentes
        if "</think>" in content:
            content = content.split("</think>")[-1].strip()
            
        print(f"\n✅ RESPOSTA DA GROQ: {content}\n")
    except Exception as e:
        print(f"\n❌ ERRO NA CHAMADA À GROQ: {e}\n")

if __name__ == "__main__":
    test_connection()