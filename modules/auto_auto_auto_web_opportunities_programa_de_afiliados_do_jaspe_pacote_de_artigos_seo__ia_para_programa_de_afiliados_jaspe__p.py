import os
import json
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Union

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------- Helper Functions -------------------


def _configure_stripe(stripe_api_key: str) -> Dict[str, Any]:
    """Simula a configuração da chave Stripe via API fictícia."""
    try:
        if not stripe_api_key:
            raise ValueError("Chave Stripe não fornecida.")
        # Simulação de chamada a endpoint interno de configuração
        resp = requests.post(
            "https://api.mockstripe.com/v1/configure",
            headers={"Authorization": f"Bearer {stripe_api_key}"},
            json={"account": "jaspe_affiliate"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"status": "success", "details": data}
    except Exception as e:
        logger.error(f"Erro ao configurar Stripe: {e}")
        return {"status": "failed", "error": str(e)}


def _create_sales_page(product_name: str, price_one_time: float, price_recurring: float) -> Dict[str, Any]:
    """Gera uma página HTML otimizada para SEO e salva em disco."""
    try:
        html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{product_name} - Compra Segura</title>
    <meta name="description" content="Adquira o {product_name} por apenas ${price_one_time:.2f} e aproveite benefícios recorrentes de ${price_recurring:.2f} por mês.">
    <meta name="keywords" content="SEO, IA, afiliados, jaspe, pacote SEO IA, marketing digital">
    <meta name="robots" content="index,follow">
    <link rel="canonical" href="https://www.jaspe.com/afiliados/{product_name.lower().replace(' ', '-')}" />
    <style>
        body {{font-family:Arial,Helvetica,sans-serif; line-height:1.6; margin:2rem;}}
        .cta {{background:#0066cc;color:#fff;padding:1rem 2rem;text-decoration:none;display:inline-block;margin-top:1rem;}}
    </style>
</head>
<body>
    <h1>{product_name}</h1>
    <p>O melhor pacote SEO impulsionado por IA para afiliados que desejam escalar suas vendas.</p>
    <h2>Preço</h2>
    <ul>
        <li>Compra única: <strong>${price_one_time:.2f}</strong></li>
        <li>Assinatura mensal: <strong>${price_recurring:.2f}</strong></li>
    </ul>
    <a href="https://checkout.jaspe.com/pay?product={uuid.uuid4()}" class="cta">Comprar agora</a>
</body>
</html>"""
        output_path = Path(__file__).parent / "sales_page.html"
        output_path.write_text(html_template, encoding="utf-8")
        return {"status": "success", "file": str(output_path)}
    except Exception as e:
        logger.error(f"Erro ao criar página de vendas: {e}")
        return {"status": "failed", "error": str(e)}


def _start_ad_campaign(keywords: List[str], budget: float) -> Dict[str, Any]:
    """Inicia uma campanha de anúncios simulada."""
    try:
        if not keywords:
            raise ValueError("Lista de palavras‑chave vazia.")
        payload = {
            "campaign_name": "Jaspe SEO IA Launch",
            "budget": budget,
            "keywords": keywords,
            "landing_page": "https://www.jaspe.com/afiliados/pacote-seo-ia",
        }
        resp = requests.post(
            "https://api.mockads.com/v1/campaigns/create",
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"status": "success", "campaign_id": data.get("id"), "details": data}
    except Exception as e:
        logger.error(f"Erro ao iniciar campanha de anúncios: {e}")
        return {"status": "failed", "error": str(e)}


def _register_affiliate(user_email: str) -> Dict[str, Any]:
    """Registra o usuário como afiliado e gera link rastreado."""
    try:
        if not user_email or "@" not in user_email:
            raise ValueError("E‑mail de afiliado inválido.")
        payload = {"email": user_email, "program": "Jaspe_SEO_IA"}
        resp = requests.post(
            "https://api.mockaffiliates.com/v1/register",
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        affiliate_id = data.get("affiliate_id")
        tracking_link = f"https://track.jaspe.com/{affiliate_id}?ref={uuid.uuid4()}"
        return {"status": "success", "affiliate_id": affiliate_id, "tracking_link": tracking_link}
    except Exception as e:
        logger.error(f"Erro ao registrar afiliado: {e}")
        return {"status": "failed", "error": str(e)}


# ------------------- Main Execution Function -------------------


def scan_programa_de_afiliados_jaspe__p() -> Union[Dict[str, Any], List[Any]]:
    """
    Orquestra a configuração completa da oportunidade de afiliado Jaspe.
    Retorna um dicionário consolidado com o resultado de cada etapa.
    """
    result: Dict[str, Any] = {"steps": {}}

    # 1. Configurar Stripe
    stripe_key = os.getenv("STRIPE_API_KEY", "")
    result["steps"]["stripe_configuration"] = _configure_stripe(stripe_key)

    # 2. Criar página de vendas SEO
    result["steps"]["sales_page"] = _create_sales_page(
        product_name="Programa de Afiliados Jaspe - Pacote SEO IA",
        price_one_time=299.0,
        price_recurring=49.0,
    )

    # 3. Iniciar campanha de anúncios
    keywords = [
        "pacote seo ia",
        "afiliado jaspe",
        "marketing de afiliados IA",
        "seo automation",
        "ganhar dinheiro online",
    ]
    result["steps"]["ad_campaign"] = _start_ad_campaign(keywords=keywords, budget=150.0)

    # 4. Registrar como afiliado e gerar link rastreado
    affiliate_email = os.getenv("AFFILIATE_EMAIL", "usuario@example.com")
    result["steps"]["affiliate_registration"] = _register_affiliate(user_email=affiliate_email)

    # Resumo final
    result["summary"] = {
        "overall_status": "failed" if any(
            step.get("status") != "success" for step in result["steps"].values()
        ) else "success",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }

    return result