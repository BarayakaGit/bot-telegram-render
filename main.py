import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import flask

# --- CONFIGURAÇÃO ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
SEU_CHAT_ID = os.environ.get('SEU_CHAT_ID')
PORT = int(os.environ.get('PORT', 8443))
# O nome do app no Render é pego automaticamente
APP_NAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')

# --- INICIALIZAÇÃO DO FLASK (NOSSO SERVIDOR WEB) ---
app = flask.Flask(__name__)

# --- CÓDIGO DO BOT ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Bot funcionando via Render e Webhooks. Envie qualquer mensagem.")

# Adicione aqui a lógica completa do "Agente Triagem" que projetamos
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = update.message.from_user
    text = update.message.text

    logger.info(f"Mensagem recebida de {user_info.first_name}: {text}")

    # Lógica de notificação
    mensagem_notificacao = (
        f"🔔 Nova Mensagem Recebida!\n\n"
        f"De: {user_info.first_name} (@{user_info.username})\n"
        f"Mensagem: '{text}'"
    )
    await context.bot.send_message(chat_id=SEU_CHAT_ID, text=mensagem_notificacao)

    # Resposta para o cliente
    await update.message.reply_text("Obrigado pelo seu contato! Já recebemos sua mensagem e um especialista responderá em breve.")


# --- ROTA DO WEBHOOK ---
@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook_handler():
    if flask.request.is_json:
        json_str = flask.request.get_json()
        update = Update.de_json(json_str, bot)
        application.queue.put(update)
    return 'ok', 200

# Rota de saúde para o Render saber que o app está vivo
@app.route('/')
def index():
    return 'Bot está vivo!', 200

# Inicializa o bot e define o webhook
application = Application.builder().token(TELEGRAM_TOKEN).build()
bot = application.bot

# Comandos
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# Configura o webhook de forma assíncrona
import asyncio
asyncio.get_event_loop().run_until_complete(
    application.bot.set_webhook(url=f"https://{APP_NAME}/{TELEGRAM_TOKEN}")
)
