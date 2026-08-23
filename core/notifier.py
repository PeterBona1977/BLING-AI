import os
import html
import asyncio
from telegram import Bot
from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

async def send_telegram_alert(decision: dict):
    """Envia um alerta formatado em HTML para o Telegram com os detalhes da oportunidade."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram não configurado no .env (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID em falta).")
        return

    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Sanitiza os campos em HTML para evitar quebras de parsing
        market = html.escape(str(decision.get("market", "N/A")).upper())
        title = html.escape(str(decision.get("title", "Sem título")))
        roi = html.escape(str(decision.get("estimated_roi", "N/A")))
        risk = html.escape(str(decision.get("risk_level", "N/A")))
        details = html.escape(str(decision.get("details", "Sem detalhes")))
        action = html.escape(str(decision.get("action_required", "Sem ação especificada")))

        message = (
            f"🚨 <b>BLING AI — Oportunidade Detetada!</b>\n\n"
            f"📌 <b>Mercado:</b> {market}\n"
            f"💡 <b>Oportunidade:</b> {title}\n"
            f"💰 <b>ROI Estimado:</b> <code>{roi}</code>\n"
            f"⚠️ <b>Nível de Risco:</b> {risk}\n\n"
            f"📝 <b>Detalhes:</b> {details}\n\n"
            f"⚡ <b>Ação Recomendada:</b> {action}"
        )

        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem para o Telegram: {e}")