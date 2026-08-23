import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Configurações padrão (podem ser sobrescritas por variáveis de ambiente)
# ----------------------------------------------------------------------
DEFAULT_PRICES = {
    "license_one_time": 299.0,   # USD
    "license_monthly": 49.0      # USD / month
}
CONTENT_URLS = [
    "https://example.com/artigo-1",
    "https://example.com/artigo-2",
    "https://example.com/artigo-3",
    "https://example.com/artigo-4",
    "https://example.com/artigo-5",
    "https://example.com/artigo-6",
    "https://example.com/artigo-7"
]
SALES_PAGE_PATH = Path("sales_page.html")
REINVEST_PERCENTAGE = 0.20

# ----------------------------------------------------------------------
# Funções auxiliares
# ----------------------------------------------------------------------
def _load_env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except Exception as e:
        logger.warning(f"Falha ao ler variável de ambiente {key}: {e}")
        return default


def _safe_request(method: str, url: str, **kwargs) -> Optional[requests.Response]:
    try:
        resp = requests.request(method, url, timeout=15, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception as e:
        logger.error(f"Request falhou [{method} {url}]: {e}")
        return None


def _write_file(path: Path, content: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        logger.error(f"Erro ao escrever arquivo {path}: {e}")
        return False


# ----------------------------------------------------------------------
# Etapas da oportunidade
# ----------------------------------------------------------------------
def _define_prices() -> Dict[str, float]:
    return {
        "license_one_time": _load_env_float("LICENSE_ONE_TIME_PRICE", DEFAULT_PRICES["license_one_time"]),
        "license_monthly": _load_env_float("LICENSE_MONTHLY_PRICE", DEFAULT_PRICES["license_monthly"])
    }


def _generate_sales_page(prices: Dict[str, float]) -> bool:
    try:
        html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Pacote de artigos SEO + IA para afiliados</title>
    <style>
        body {{font-family:Arial,sans-serif; margin:2rem;}}
        .cta {{background:#f0c040; padding:1rem; text-align:center; margin-top:2rem;}}
        .price {{font-size:1.5rem; font-weight:bold;}}
        .articles {{margin-top:1rem;}}
        .articles li {{margin-bottom:0.5rem;}}
    </style>
</head>
<body>
    <h1>Pacote de artigos SEO + IA para afiliados</h1>
    <p>Sete artigos já criados, otimizados e publicados. Use-os como conteúdo premium em seu site ou ofereça a clientes.</p>
    <div class="price">
        <p>Licença única: <strong>US${prices["license_one_time"]:.2f}</strong></p>
        <p>Assinatura mensal: <strong>US${prices["license_monthly"]:.2f}/mês</strong></p>
    </div>
    <div class="cta">
        <a href="/checkout" style="text-decoration:none;color:#000;">Comprar agora</a>
    </div>
    <h2>Prova social</h2>
    <ul class="articles">
        {"".join(f'<li><a href="{url}" target="_blank">{url}</a></li>' for url in CONTENT_URLS)}
    </ul>
</body>
</html>"""
        return _write_file(SALES_PAGE_PATH, html_template)
    except Exception as e:
        logger.error(f"Erro ao gerar página de vendas: {e}")
        return False


def _setup_stripe_product(prices: Dict[str, float]) -> Dict[str, Any]:
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        logger.warning("Chave Stripe não configurada; pulando criação de produto.")
        return {"status": "skipped", "reason": "missing_stripe_key"}

    endpoint = "https://api.stripe.com/v1/products"
    headers = {"Authorization": f"Bearer {stripe_key}"}
    data = {
        "name": "Pacote de artigos SEO + IA para afiliados",
        "description": "7 artigos SEO otimizados + IA, licença de uso ou assinatura.",
        "type": "service"
    }

    resp = _safe_request("POST", endpoint, headers=headers, data=data)
    if not resp:
        return {"status": "error", "detail": "product_creation_failed"}

    product_id = resp.json().get("id")
    if not product_id:
        return {"status": "error", "detail": "no_product_id"}

    # Cria preços (price objects) para Stripe
    price_results = {}
    for mode, amount in [("one_time", prices["license_one_time"]), ("monthly", prices["license_monthly"])]:
        price_endpoint = "https://api.stripe.com/v1/prices"
        price_data = {
            "unit_amount": int(amount * 100),  # cents
            "currency": "usd",
            "product": product_id,
            "recurring[interval]": "month" if mode == "monthly" else None
        }
        # Remove chaves com None
        price_data = {k: v for k, v in price_data.items() if v is not None}
        price_resp = _safe_request("POST", price_endpoint, headers=headers, data=price_data)
        if price_resp:
            price_results[mode] = price_resp.json().get("id")
        else:
            price_results[mode] = None

    return {"status": "created", "product_id": product_id, "price_ids": price_results}


def _launch_google_ads(keywords: List[str]) -> Dict[str, Any]:
    # Placeholder: integração real exigiria OAuth2 e chamadas ao Google Ads API.
    # Aqui simulamos um registro de campanha.
    try:
        campaign_id = f"demo-{int(datetime.utcnow().timestamp())}"
        logger.info(f"Campanha simulada criada com ID {campaign_id} para palavras-chave: {keywords}")
        return {"status": "simulated", "campaign_id": campaign_id, "keywords": keywords}
    except Exception as e:
        logger.error(f"Falha ao criar campanha simulada: {e}")
        return {"status": "error", "detail": str(e)}


def _monitor_sales(stripe_key: Optional[str]) -> Dict[str, Any]:
    # Simulação de monitoramento: tenta buscar últimos pagamentos via Stripe se a chave existir.
    if not stripe_key:
        logger.warning("Chave Stripe ausente; monitoramento de vendas desativado.")
        return {"status": "skipped", "reason": "missing_stripe_key"}

    endpoint = "https://api.stripe.com/v1/checkout/sessions"
    headers = {"Authorization": f"Bearer {stripe_key}"}
    params = {"limit": 5}
    resp = _safe_request("GET", endpoint, headers=headers, params=params)
    if not resp:
        return {"status": "error", "detail": "failed_to_fetch_sessions"}

    sessions = resp.json().get("data", [])
    total_revenue = sum(float(s.get("amount_total", 0)) / 100.0 for s in sessions)
    reinvest_amount = total_revenue * REINVEST_PERCENTAGE

    return {
        "status": "fetched",
        "recent_sessions": len(sessions),
        "total_revenue_usd": round(total_revenue, 2),
        "reinvest_usd": round(reinvest_amount, 2)
    }


# ----------------------------------------------------------------------
# Função principal (exigência: iniciar com scan_ ou execute_)
# ----------------------------------------------------------------------
def scan_pacote_de_artigos_seo__ia_para() -> Dict[str, Any]:
    """
    Executa todo o fluxo de preparação e monitoramento da oportunidade
    "Pacote de artigos SEO + IA para afiliados".
    Retorna um dicionário estruturado com o resultado de cada etapa.
    """
    result: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(),
        "steps": {}
    }

    # 1. Definir preços
    try:
        prices = _define_prices()
        result["steps"]["prices"] = {"status": "ok", "data": prices}
    except Exception as e:
        result["steps"]["prices"] = {"status": "error", "detail": str(e)}

    # 2. Gerar página de vendas
    try:
        page_created = _generate_sales_page(prices)
        result["steps"]["sales_page"] = {"status": "ok" if page_created else "error"}
    except Exception as e:
        result["steps"]["sales_page"] = {"status": "error", "detail": str(e)}

    # 3. Configurar gateway de pagamento (Stripe)
    try:
        stripe_info = _setup_stripe_product(prices)
        result["steps"]["payment_gateway"] = stripe_info
    except Exception as e:
        result["steps"]["payment_gateway"] = {"status": "error", "detail": str(e)}

    # 4. Promover via anúncios de baixo custo (Google Ads simulado)
    try:
        keywords = ["conteúdo IA", "artigos SEO prontos", "conteúdo premium afiliados"]
        ad_info = _launch_google_ads(keywords)
        result["steps"]["ads"] = ad_info
    except Exception as e:
        result["steps"]["ads"] = {"status": "error", "detail": str(e)}

    # 5. Monitorar vendas e calcular reinvestimento
    try:
        stripe_key = os.getenv("STRIPE_SECRET_KEY")
        sales_info = _monitor_sales(stripe_key)
        result["steps"]["sales_monitor"] = sales_info
    except Exception as e:
        result["steps"]["sales_monitor"] = {"status": "error", "detail": str(e)}

    return result

# ----------------------------------------------------------------------
# Execução assíncrona opcional (não obrigatória)
# ----------------------------------------------------------------------
async def _run_async_flow():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, scan_pacote_de_artigos_seo__ia_para)

if __name__ == "__main__":
    # Execução direta para testes rápidos
    try:
        output = scan_pacote_de_artigos_seo__ia_para()
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except Exception as exc:
        logger.critical(f"Falha inesperada na execução principal: {exc}")