import os
import json
import logging
import time
import uuid
import requests
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)

# --------------------------- CONFIGURAÇÕES ---------------------------
AFFILIATE_SIGNUP_URL = "https://jasper.ai/affiliates"
AFFILIATE_LINK = os.getenv("JASPER_AFFILIATE_LINK", "https://jasper.ai/affiliates?ref=YOUR_ID")
UBERSUGGEST_API_KEY = os.getenv("UBERSUGGEST_API_KEY", "")
UBERSUGGEST_ENDPOINT = "https://api.neilpatel.com/v1/keyword/overview"
BUFFER_ACCESS_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN", "")
BUFFER_ENDPOINT = "https://api.bufferapp.com/1/updates/create.json"
TIKTOK_API_TOKEN = os.getenv("TIKTOK_API_TOKEN", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
# ---------------------------------------------------------------------


def _safe_request(method: str, url: str, **kwargs) -> Dict[str, Any]:
    """Wrapper para requests que captura exceções e devolve um dicionário padrão."""
    try:
        resp = requests.request(method, url, timeout=15, **kwargs)
        resp.raise_for_status()
        try:
            return {"success": True, "data": resp.json()}
        except ValueError:
            return {"success": True, "data": resp.text}
    except Exception as exc:
        LOGGER.error("Request falhou %s %s: %s", method, url, exc)
        return {"success": False, "error": str(exc)}


def _generate_article(topic: str, affiliate_link: str) -> str:
    """Cria um artigo simples em markdown com CTA de afiliado."""
    title = f"Como usar IA para copywriting em e‑commerce: {topic}"
    intro = (
        f"Neste artigo, vamos explorar como a inteligência artificial pode transformar "
        f"o copywriting de lojas virtuais, aumentando conversões e reduzindo custos."
    )
    body = (
        f"### Benefícios da IA no copywriting\n"
        f"- **Velocidade**: gera textos em segundos.\n"
        f"- **Personalização**: adapta mensagens ao público‑alvo.\n"
        f"- **Escalabilidade**: produz centenas de descrições de produtos sem esforço.\n\n"
        f"### Passo a passo para aplicar IA\n"
        f"1. Escolha uma ferramenta de IA (ex.: Jasper AI).\n"
        f"2. Defina o tom e o público‑alvo.\n"
        f"3. Insira palavras‑chave do produto.\n"
        f"4. Revise e ajuste conforme necessário.\n"
    )
    cta = f"\n---\n**Pronto para turbinar suas vendas?** Experimente o Jasper AI e ganhe **30 % de comissão recorrente** ao se inscrever através deste link: [{affiliate_link}]({affiliate_link})\n"
    return "\n".join([f"# {title}", intro, body, cta])


def _save_article(content: str, slug: str) -> str:
    """Salva o artigo em um diretório local e devolve o caminho completo."""
    directory = "articles"
    os.makedirs(directory, exist_ok=True)
    filename = f"{slug}.md"
    path = os.path.join(directory, filename)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        LOGGER.info("Artigo salvo em %s", path)
        return path
    except Exception as exc:
        LOGGER.error("Falha ao salvar artigo %s: %s", path, exc)
        return ""


def _schedule_buffer_post(content: str) -> Dict[str, Any]:
    """Agenda uma publicação no Buffer usando o token de acesso."""
    if not BUFFER_ACCESS_TOKEN:
        return {"success": False, "error": "Token Buffer não configurado"}
    payload = {
        "text": content,
        "profile_ids[]": [],  # opcional: IDs das contas conectadas
        "scheduled_at": int(time.time()) + 3600,  # agenda para 1h à frente
        "access_token": BUFFER_ACCESS_TOKEN,
    }
    return _safe_request("POST", BUFFER_ENDPOINT, data=payload)


def _track_keyword_rank(keyword: str) -> Dict[str, Any]:
    """Consulta a posição de palavra‑chave no Ubersuggest."""
    if not UBERSUGGEST_API_KEY:
        return {"success": False, "error": "Chave Ubersuggest não configurada"}
    params = {"keyword": keyword, "country": "us", "apikey": UBERSUGGEST_API_KEY}
    return _safe_request("GET", UBERSUGGEST_ENDPOINT, params=params)


def _create_retarg_campaign(platform: str, article_url: str) -> Dict[str, Any]:
    """Placeholder para criar campanha de retargeting em TikTok ou YouTube Shorts."""
    if platform == "tiktok":
        if not TIKTOK_API_TOKEN:
            return {"success": False, "error": "Token TikTok não configurado"}
        # Simulação de chamada de API
        campaign_id = str(uuid.uuid4())
        LOGGER.info("Campanha TikTok criada (simulada) ID=%s", campaign_id)
        return {"success": True, "campaign_id": campaign_id, "platform": "tiktok"}
    elif platform == "youtube":
        if not YOUTUBE_API_KEY:
            return {"success": False, "error": "Chave YouTube não configurada"}
        campaign_id = str(uuid.uuid4())
        LOGGER.info("Campanha YouTube Shorts criada (simulada) ID=%s", campaign_id)
        return {"success": True, "campaign_id": campaign_id, "platform": "youtube"}
    else:
        return {"success": False, "error": f"Plataforma desconhecida: {platform}"}


def _signup_affiliate_program() -> Dict[str, Any]:
    """Tenta acessar a página de inscrição para validar disponibilidade."""
    try:
        resp = requests.get(AFFILIATE_SIGNUP_URL, timeout=10)
        resp.raise_for_status()
        return {"success": True, "status_code": resp.status_code}
    except Exception as exc:
        LOGGER.error("Falha ao acessar página de afiliados: %s", exc)
        return {"success": False, "error": str(exc)}


def scan_programa_de_afiliados_do_jasper() -> Dict[str, Any]:
    """
    Executa todo o fluxo de preparação para o programa de afiliados Jasper AI.
    Retorna um dicionário estruturado com resultados e status de cada etapa.
    """
    resultado: Dict[str, Any] = {
        "signup": None,
        "articles": [],
        "buffer_posts": [],
        "keyword_ranks": [],
        "retarget_campaigns": [],
        "overall_success": True,
    }

    # 1. Inscrição no programa
    resultado["signup"] = _signup_affiliate_program()
    if not resultado["signup"]["success"]:
        resultado["overall_success"] = False

    # 2. Gerar artigos SEO
    topics = [
        "Aumente suas conversões com IA",
        "Reduza custos de produção de conteúdo",
        "Personalização de descrições de produtos",
        "Como otimizar SEO usando Jasper AI",
        "Estratégias de copywriting para lojas Shopify",
        "Automatizando anúncios de Facebook com IA",
        "Melhores práticas de CTA em e‑commerce"
    ]

    for topic in topics:
        try:
            slug = topic.lower().replace(" ", "-")
            content = _generate_article(topic, AFFILIATE_LINK)
            path = _save_article(content, slug)
            article_url = f"https://seusite.com/articles/{slug}.html"  # URL fictícia
            resultado["articles"].append({
                "topic": topic,
                "slug": slug,
                "path": path,
                "url": article_url,
                "saved": bool(path)
            })
        except Exception as exc:
            LOGGER.error("Erro ao processar artigo '%s': %s", topic, exc)
            resultado["overall_success"] = False

    # 3. Agendar posts no Buffer
    for art in resultado["articles"]:
        try:
            post_content = f"Novo artigo: {art['topic']} – Leia agora: {art['url']} #IA #Copywriting"
            buffer_resp = _schedule_buffer_post(post_content)
            resultado["buffer_posts"].append({
                "article_slug": art["slug"],
                "buffer_response": buffer_resp
            })
            if not buffer_resp["success"]:
                resultado["overall_success"] = False
        except Exception as exc:
            LOGGER.error("Erro ao agendar post Buffer para %s: %s", art["slug"], exc)
            resultado["overall_success"] = False

    # 4. Rank‑tracking no Ubersuggest
    for art in resultado["articles"]:
        try:
            rank_resp = _track_keyword_rank(art["topic"])
            resultado["keyword_ranks"].append({
                "keyword": art["topic"],
                "rank_response": rank_resp
            })
            if not rank_resp["success"]:
                resultado["overall_success"] = False
        except Exception as exc:
            LOGGER.error("Erro ao rastrear rank para %s: %s", art["topic"], exc)
            resultado["overall_success"] = False

    # 5. Criar campanhas de retargeting (simulação)
    for platform in ["tiktok", "youtube"]:
        try:
            camp_resp = _create_retarg_campaign(platform, "https://seusite.com")
            resultado["retarget_campaigns"].append(camp_resp)
            if not camp_resp["success"]:
                resultado["overall_success"] = False
        except Exception as exc:
            LOGGER.error("Erro ao criar campanha %s: %s", platform, exc)
            resultado["overall_success"] = False

    return resultado