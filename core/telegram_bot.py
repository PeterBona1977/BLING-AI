import html
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

async def send_approval_request(task_id: str, title: str, details: str, estimated_roi: str, market: str = "Geral"):
    """Envia o alerta interativo no Telegram com opções de execução e piloto automático em HTML."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Token do Telegram ou Chat ID não configurados no .env")
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    safe_market = html.escape(str(market))
    safe_title = html.escape(str(title))
    safe_roi = html.escape(str(estimated_roi))
    safe_details = html.escape(str(details))
    
    message_text = (
        f"🚨 <b>OPORTUNIDADE DE LUCRO DETETADA</b>\n"
        f"🌐 <b>Categoria:</b> {safe_market}\n"
        f"📌 <b>Ativo/Estratégia:</b> {safe_title}\n"
        f"💰 <b>ROI Estimado:</b> {safe_roi}\n\n"
        f"📝 <b>Plano de Execução da IA:</b>\n{safe_details}\n\n"
        f"<i>Define como a IA deve proceder:</i>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🚀 Executar Agora", callback_data=f"exec_{task_id}"),
            InlineKeyboardButton("🤖 Executar & Piloto Automático", callback_data=f"auto_{market}")
        ],
        [
            InlineKeyboardButton("❌ Rejeitar", callback_data=f"reject_{task_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        print("✅ Alerta enviado para o Telegram com opções de Autonomia!")
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem para o Telegram: {e}")