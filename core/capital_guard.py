import os
from core.vault import get_or_create_wallet

# Teto máximo de gasto automático sem autorização direta (0.00 EUR / USD)
AUTO_SPEND_LIMIT_EUR = 0.0

def request_capital_approval(opportunity: dict, amount_needed: float, destination: str) -> dict:
    """
    Avalia e solicita aprovação para uso de capital ou criação de contas bancárias/fiat.
    """
    title = opportunity.get("title", "Oportunidade")
    roi = opportunity.get("estimated_roi", "N/A")
    
    if amount_needed > AUTO_SPEND_LIMIT_EUR:
        return {
            "approved": False,
            "reason": "REQUIRES_USER_APPROVAL",
            "message": (
                f"⚠️ <b>SOLICITAÇÃO DE CAPITAL / REQUER APROVAÇÃO</b>\n\n"
                f"📌 <b>Oportunidade:</b> {title}\n"
                f"💵 <b>Montante Solicitado:</b> <code>{amount_needed:.2f} €</code>\n"
                f"📈 <b>ROI Esperado:</b> {roi}\n"
                f"🎯 <b>Destino / Requisito:</b> {destination}\n\n"
                f"<i>O agente não movimentou quaisquer fundos. Responda para autorizar se desejar prosseguir.</i>"
            )
        }
    
    return {"approved": True, "reason": "ZERO_COST"}

def get_operational_solana_wallet():
    """Retorna a carteira Phantom/Solana gerada autonomamente (Custo zero)."""
    return get_or_create_wallet("solana")