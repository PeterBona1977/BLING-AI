import requests
from bs4 import BeautifulSoup

def fetch_page_text(url: str, timeout: int = 10) -> str:
    """Faz scraping em tempo real de uma página Web e devolve o texto limpo."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove scripts, estilos e tags não essenciais
            for script in soup(["script", "style", "header", "footer", "nav"]):
                script.decompose()
            
            text = soup.get_text(separator=" ", strip=True)
            # Limita a 4000 caracteres para poupar quota de contexto da API
            return text[:4000]
        else:
            return f"Erro HTTP {response.status_code} ao aceder a {url}"
    except Exception as e:
        return f"Falha no scraping de {url}: {e}"