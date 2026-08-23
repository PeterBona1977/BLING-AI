import os
import json
import datetime
import random
import string
import requests
from pathlib import Path

def _safe_get(url, **kwargs):
    try:
        resp = requests.get(url, timeout=10, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception as e:
        return e

def _write_file(path, content):
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True, None
    except Exception as e:
        return False, str(e)

def _generate_seo_content(keywords):
    title = "PixelForge Pro – Gerador de Imagens IA Grátis e Alternativa ao Midjourney"
    description = ("Descubra como o PixelForge Pro pode gerar imagens IA de alta qualidade "
                   "gratuitamente e por que é a melhor alternativa ao Midjourney. "
                   "Veja análise completa, tutoriais e links de afiliado.")
    meta_keywords = ", ".join(keywords)
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <meta name="description" content="{description}">
    <meta name="keywords" content="{meta_keywords}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <h1>{title}</h1>
    <p>{description}</p>
    <h2>Principais Funcionalidades</h2>
    <ul>
        <li>Geração de imagens IA em segundos</li>
        <li>Modelos personalizáveis</li>
        <li>Integração com ferramentas de design</li>
    </ul>
    <h2>Como Começar</h2>
    <p>Inscreva‑se através do nosso link de afiliado e aproveite 30% de comissão recorrente.</p>
    <a href="https://pixelforge.ai/affiliates?ref=YOUR_AFFILIATE_ID">Começar agora</a>
</body>
</html>"""
    return html

def _simulate_video_creation(count=2):
    videos = []
    for i in range(1, count + 1):
        filename = f"video_demo_{i}.txt"
        content = f"Simulação de vídeo {i} - demonstração do PixelForge Pro (gerado em {datetime.datetime.utcnow().isoformat()})"
        success, err = _write_file(os.path.join("output", filename), content)
        videos.append({
            "filename": filename,
            "status": "created" if success else "error",
            "error": err
        })
    return videos

def _allocate_influencer_budget(min_usd=50, max_usd=100):
    budget = round(random.uniform(min_usd, max_usd), 2)
    # Simulação de campanha
    campaign_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return {
        "budget_usd": budget,
        "campaign_id": campaign_id,
        "platforms": ["TikTok", "Instagram"],
        "status": "planned"
    }

def _check_post_affiliate_pro(endpoint="https://api.postaffiliatepro.com/"):
    try:
        resp = requests.get(endpoint, timeout=5)
        return resp.status_code == 200
    except Exception:
        return False

def scan_programa_de_afiliados_pixelforge():
    result = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "overall_status": "failed",
        "steps": []
    }

    # Step 1: Verificar página de inscrição
    step = {"name": "check_affiliate_signup_page"}
    resp = _safe_get("https://pixelforge.ai/affiliates")
    if isinstance(resp, Exception):
        step["status"] = "error"
        step["error"] = str(resp)
    else:
        step["status"] = "ok"
        step["http_code"] = resp.status_code
    result["steps"].append(step)

    # Step 2: Gerar mini‑site SEO
    step = {"name": "generate_seo_page"}
    try:
        keywords = ["gerador de imagens IA grátis", "alternativa ao Midjourney"]
        html_content = _generate_seo_content(keywords)
        success, err = _write_file(os.path.join("output", "pixelforge_review.html"), html_content)
        if success:
            step["status"] = "ok"
            step["file"] = "pixelforge_review.html"
        else:
            step["status"] = "error"
            step["error"] = err
    except Exception as e:
        step["status"] = "error"
        step["error"] = str(e)
    result["steps"].append(step)

    # Step 3: Simular criação de vídeos
    step = {"name": "simulate_video_creation"}
    try:
        videos = _simulate_video_creation(count=3)
        step["status"] = "ok"
        step["videos"] = videos
    except Exception as e:
        step["status"] = "error"
        step["error"] = str(e)
    result["steps"].append(step)

    # Step 4: Alocar orçamento para micro‑influenciadores
    step = {"name": "allocate_influencer_budget"}
    try:
        campaign = _allocate_influencer_budget()
        step["status"] = "ok"
        step["campaign"] = campaign
    except Exception as e:
        step["status"] = "error"
        step["error"] = str(e)
    result["steps"].append(step)

    # Step 5: Configurar tracking via Post Affiliate Pro
    step = {"name": "check_post_affiliate_pro"}
    try:
        reachable = _check_post_affiliate_pro()
        if reachable:
            step["status"] = "ok"
        else:
            step["status"] = "warning"
            step["message"] = "API não respondeu ou indisponível"
    except Exception as e:
        step["status"] = "error"
        step["error"] = str(e)
    result["steps"].append(step)

    # Determinar status geral
    if all(s.get("status") == "ok" for s in result["steps"]):
        result["overall_status"] = "success"
    else:
        result["overall_status"] = "partial_success"

    return result