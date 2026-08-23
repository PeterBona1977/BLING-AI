import requests
import random
import string
import json
import time
from urllib.parse import urljoin

BASE_URL = "https://growthai.com"
AFFILIATE_ENDPOINT = "/partner"
ARTICLES_COUNT = 3
KEYWORDS = [
    "como melhorar rankings com IA",
    "otimizar SEO usando inteligência artificial",
    "técnicas de IA para subir no Google",
    "estratégias de SEO AI para tráfego orgânico",
    "guia de IA para melhorar posicionamento"
]

def _safe_request(method, url, **kwargs):
    try:
        resp = requests.request(method, url, timeout=15, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception as e:
        return None

def _generate_random_text(length=200):
    words = []
    for _ in range(length):
        word = ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 10)))
        words.append(word)
    return ' '.join(words).capitalize() + '.'

def _register_affiliate():
    url = urljoin(BASE_URL, AFFILIATE_ENDPOINT)
    payload = {
        "email": f"user_{int(time.time())}@example.com",
        "first_name": "Auto",
        "last_name": "Bot",
        "website": "https://example.com",
        "agree_terms": True
    }
    resp = _safe_request("POST", url, json=payload)
    if resp and resp.status_code == 200:
        try:
            data = resp.json()
            return {"status": "registered", "affiliate_id": data.get("id", "unknown")}
        except Exception:
            return {"status": "registered", "affiliate_id": "unknown"}
    return {"status": "failed", "error": "registration request failed"}

def _create_article(keyword):
    title = f"Como {keyword}"
    body = f"<h1>{title}</h1>\n<p>{_generate_random_text(100)}</p>\n"
    affiliate_link = f"https://growthai.com/signup?ref=YOUR_REF_CODE"
    cta = f"<p><a href='{affiliate_link}'>Comece seu teste gratuito de 7 dias agora!</a></p>"
    article_html = body + cta
    return {"title": title, "content": article_html, "keyword": keyword, "url": f"https://example.com/{title.replace(' ', '-').lower()}"}

def _generate_articles():
    articles = []
    selected_keywords = random.sample(KEYWORDS, min(ARTICLES_COUNT, len(KEYWORDS)))
    for kw in selected_keywords:
        try:
            article = _create_article(kw)
            articles.append(article)
        except Exception:
            continue
    return articles

def _distribute_to_platform(article, platform):
    # Simulated distribution; real implementation would use platform APIs.
    try:
        time.sleep(0.2)  # simulate network latency
        return {"platform": platform, "status": "distributed", "url": article["url"]}
    except Exception:
        return {"platform": platform, "status": "failed"}

def _distribute_content(articles):
    platforms = ["Pinterest", "Reddit SEO", "Niche Newsletter"]
    distribution_results = []
    for article in articles:
        for plat in platforms:
            result = _distribute_to_platform(article, plat)
            distribution_results.append(result)
    return distribution_results

def _fetch_affiliate_metrics(affiliate_id):
    # Simulated metrics retrieval
    try:
        # In real case: GET request to affiliate dashboard API
        metrics = {
            "affiliate_id": affiliate_id,
            "total_clicks": random.randint(50, 500),
            "conversions": random.randint(5, 30),
            "revenue": round(random.uniform(100, 1000), 2),
            "payout_pending": round(random.uniform(20, 200), 2)
        }
        return metrics
    except Exception:
        return {"error": "metrics_fetch_failed"}

def scan_programa_de_afiliados_de_saas_():
    result = {
        "registration": None,
        "articles": [],
        "distribution": [],
        "metrics": {}
    }

    try:
        result["registration"] = _register_affiliate()
    except Exception as e:
        result["registration"] = {"status": "failed", "error": str(e)}

    try:
        result["articles"] = _generate_articles()
    except Exception as e:
        result["articles"] = []

    try:
        if result["articles"]:
            result["distribution"] = _distribute_content(result["articles"])
    except Exception as e:
        result["distribution"] = []

    try:
        aff_id = result["registration"].get("affiliate_id") if isinstance(result["registration"], dict) else None
        if aff_id:
            result["metrics"] = _fetch_affiliate_metrics(aff_id)
    except Exception as e:
        result["metrics"] = {"error": str(e)}

    return result

if __name__ == "__main__":
    output = scan_programa_de_afiliados_de_saas_()
    print(json.dumps(output, ensure_ascii=False, indent=2))