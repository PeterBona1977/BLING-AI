import json
from core.web_prospector import prospect_web_opportunities

def scan_web_opportunities() -> str:
    """Módulo ativo de varredura e extração de oportunidades monetizáveis na Web."""
    raw_json = prospect_web_opportunities()
    
    try:
        opportunities = json.loads(raw_json)
        if not opportunities:
            return "Nenhuma oportunidade viável encontrada no ciclo de prospeção atual."
            
        summary = "🌐 --- OPORTUNIDADES DETETADAS VIA PROSPEÇÃO WEB ATIVA ---\n\n"
        for idx, item in enumerate(opportunities, 1):
            summary += (
                f"[{idx}] Categoria: {item.get('category')}\n"
                f"    Título: {item.get('title')}\n"
                f"    Lucro Estimado: {item.get('estimated_profit')}\n"
                f"    Esforço: {item.get('effort_level')}\n"
                f"    Descrição: {item.get('description')}\n"
                f"    Fonte: {item.get('target_link_or_source')}\n\n"
            )
        return summary
    except Exception as e:
        return f"Erro ao processar oportunidades Web: {e}"