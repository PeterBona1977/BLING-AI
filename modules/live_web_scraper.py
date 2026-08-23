import requests
import xml.etree.ElementTree as ET

FEEDS = [
    {"name": "Upwork Python Jobs", "url": "[https://www.upwork.com/ab/feed/jobs/rss?q=python+automation&sort=recency](https://www.upwork.com/ab/feed/jobs/rss?q=python+automation&sort=recency)"},
    {"name": "RemoteOK Dev Jobs", "url": "[https://remoteok.com/rss](https://remoteok.com/rss)"},
    {"name": "Freelancer Bounties", "url": "[https://www.freelancer.com/rss.xml](https://www.freelancer.com/rss.xml)"}
]

def scan_live_web() -> str:
    """Extrai oportunidades reais de feeds RSS limpos sem bloqueios de Cloudflare/Scraping."""
    extracted_items = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for feed in FEEDS:
        try:
            res = requests.get(feed["url"], headers=headers, timeout=10)
            if res.status_code == 200:
                root = ET.fromstring(res.text)
                count = 0
                for item in root.findall(".//item"):
                    if count >= 3:
                        break
                    title = item.find("title").text if item.find("title") is not None else ""
                    link = item.find("link").text if item.find("link") is not None else ""
                    desc = item.find("description").text if item.find("description") is not None else ""
                    
                    extracted_items.append(
                        f"FONTE: {feed['name']}\nOPORTUNIDADE: {title}\nLINK: {link}\nDETALHES: {desc[:400]}\n---"
                    )
                    count += 1
        except Exception:
            continue

    if not extracted_items:
        return "Nenhum feed RSS capturado neste ciclo."

    return "\n\n".join(extracted_items[:5])