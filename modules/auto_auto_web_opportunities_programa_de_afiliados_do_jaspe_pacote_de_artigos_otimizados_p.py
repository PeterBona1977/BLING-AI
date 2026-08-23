import os
import json
import time
import random
import logging
import threading
from typing import List, Dict, Any
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ------------------- Helper Functions ------------------- #

def _load_token(name: str) -> str:
    try:
        token = os.getenv(name)
        if not token:
            raise ValueError(f"Token {name} not found in environment.")
        return token
    except Exception as e:
        logger.error(f"Error loading token {name}: {e}")
        return ""

def _safe_request(method: str, url: str, **kwargs) -> Dict[str, Any]:
    try:
        response = requests.request(method, url, timeout=15, **kwargs)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return {"text": response.text}
    except Exception as e:
        logger.error(f"Request error [{method}] {url}: {e}")
        return {"error": str(e)}

def _post_to_buffer(buffer_token: str, article_url: str, title: str) -> Dict[str, Any]:
    api_url = "https://api.bufferapp.com/1/updates/create.json"
    payload = {
        "text": f"{title} – Confira aqui: {article_url}",
        "profile_ids": [],  # fill with actual profile IDs if known
        "now": True
    }
    headers = {"Authorization": f"Bearer {buffer_token}"}
    return _safe_request("post", api_url, json=payload, headers=headers)

def _keyword_analysis(ubersuggest_key: str, article_url: str) -> Dict[str, Any]:
    api_url = f"https://api.neilpatel.com/v1/keyword_ideas"
    params = {"url": article_url, "apikey": ubersuggest_key}
    return _safe_request("get", api_url, params=params)

def _create_landing_page(articles: List[Dict[str, str]]) -> str:
    try:
        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='pt-BR'>",
            "<head><meta charset='UTF-8'><title>Pacote de Artigos Otimizados</title></head>",
            "<body>",
            "<h1>Pacote de Artigos Otimizados para Afiliados Jasper AI</h1>",
            "<ul>"
        ]
        for art in articles:
            html_parts.append(f"<li><a href='{art['url']}' target='_blank'>{art['title']}</a></li>")
        html_parts.extend([
            "</ul>",
            "<p>Adquira já o pacote completo e aumente suas comissões!</p>",
            "</body></html>"
        ])
        landing_path = os.path.abspath("landing_page.html")
        with open(landing_path, "w", encoding="utf-8") as f:
            f.write("\n".join(html_parts))
        logger.info(f"Landing page created at {landing_path}")
        return landing_path
    except Exception as e:
        logger.error(f"Error creating landing page: {e}")
        return ""

def _send_email_campaign(email_api_key: str, landing_url: str, recipients: List[str]) -> Dict[str, Any]:
    api_url = "https://api.sendgrid.com/v3/mail/send"
    headers = {"Authorization": f"Bearer {email_api_key}", "Content-Type": "application/json"}
    data = {
        "personalizations": [{"to": [{"email": r} for r in recipients]}],
        "from": {"email": "no-reply@yourdomain.com"},
        "subject": "Novo Pacote de Artigos Otimizados – Aproveite!",
        "content": [{"type": "text/html", "value": f"Confira a landing page: {landing_url}"}]
    }
    return _safe_request("post", api_url, json=data, headers=headers)

def _monitor_metrics(buffer_token: str) -> Dict[str, Any]:
    try:
        # Dummy implementation: fetch recent updates count
        api_url = "https://api.bufferapp.com/1/updates.json"
        params = {"limit": 5}
        headers = {"Authorization": f"Bearer {buffer_token}"}
        return _safe_request("get", api_url, params=params, headers=headers)
    except Exception as e:
        logger.error(f"Metrics monitoring failed: {e}")
        return {"error": str(e)}

# ------------------- Core Execution ------------------- #

def execute_pacote_de_artigos_otimizados() -> Dict[str, Any]:
    result: Dict[str, Any] = {"steps": [], "errors": [], "data": {}}
    try:
        # 1. Load tokens/keys
        buffer_token = _load_token("BUFFER_TOKEN")
        ubersuggest_key = _load_token("UBERSUGGEST_KEY")
        email_api_key = _load_token("SENDGRID_API_KEY")
        result["data"]["tokens_loaded"] = bool(buffer_token and ubersuggest_key and email_api_key)
        result["steps"].append("tokens_loaded")
    except Exception as e:
        result["errors"].append(f"Token loading error: {e}")
        return result

    # Mock list of already published articles
    articles = [
        {"title": f"Artigo {i+1}", "url": f"https://example.com/artigo-{i+1}"} for i in range(7)
    ]
    result["data"]["articles"] = articles

    # 2. Post to Buffer (or skip if token missing)
    buffer_responses = []
    if buffer_token:
        for art in articles:
            resp = _post_to_buffer(buffer_token, art["url"], art["title"])
            buffer_responses.append(resp)
            time.sleep(0.3)  # respect rate limits
        result["data"]["buffer_posts"] = buffer_responses
        result["steps"].append("buffer_posted")
    else:
        result["errors"].append("Buffer token missing – manual posting required.")
        result["steps"].append("buffer_skipped")

    # 3. Keyword analysis via Ubersuggest
    keyword_data = []
    if ubersuggest_key:
        for art in articles:
            resp = _keyword_analysis(ubersuggest_key, art["url"])
            keyword_data.append(resp)
            time.sleep(0.5)
        result["data"]["keyword_analysis"] = keyword_data
        result["steps"].append("keyword_analyzed")
    else:
        result["errors"].append("Ubersuggest key missing – SEO analysis skipped.")
        result["steps"].append("keyword_skipped")

    # 4. Create landing page
    landing_path = _create_landing_page(articles)
    if landing_path:
        result["data"]["landing_page"] = landing_path
        result["steps"].append("landing_created")
    else:
        result["errors"].append("Landing page creation failed.")
        result["steps"].append("landing_failed")

    # 5. Send email campaign (dummy recipient list)
    recipients = ["lead1@example.com", "lead2@example.com"]
    if email_api_key and landing_path:
        email_resp = _send_email_campaign(email_api_key, f"file://{landing_path}", recipients)
        result["data"]["email_campaign"] = email_resp
        result["steps"].append("email_sent")
    else:
        result["errors"].append("Email API key missing or landing page unavailable.")
        result["steps"].append("email_skipped")

    # 6. Monitor metrics (simple Buffer fetch)
    if buffer_token:
        metrics = _monitor_metrics(buffer_token)
        result["data"]["metrics"] = metrics
        result["steps"].append("metrics_fetched")
    else:
        result["steps"].append("metrics_skipped")

    # 7. Summary
    result["summary"] = {
        "total_articles": len(articles),
        "buffer_posts_success": sum(1 for r in buffer_responses if not r.get("error")),
        "keyword_success": sum(1 for r in keyword_data if not r.get("error")),
        "email_sent": not email_resp.get("error") if email_api_key else False,
    }

    return result

if __name__ == "__main__":
    try:
        execution_result = execute_pacote_de_artigos_otimizados()
        print(json.dumps(execution_result, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.critical(f"Unhandled exception in main: {e}")
        print(json.dumps({"error": str(e)}))