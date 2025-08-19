# app.py - VERSÃO CORRIGIDA E FINAL
import logging
import os
import asyncio
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

# --- INICIALIZAÇÃO DO FLASK (NOSSO SERVIDOR WEB) ---
app = flask.Flask(__name__)

# --- FUNÇÕES DO BOT (O que ele faz) ---
# Habilita o logging para vermos informações úteis
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Função que é chamada quando o usuário envia /start."""
    user_info = update.message.from_user
    logger.info(f"Usuário {user_info.first_name} iniciou o bot.")
    await update.message.reply_text("Olá! Bot funcionando. Envie qualquer mensagem e o administrador será notificado.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Função que lida com todas as outras mensagens de texto."""
    user_info = update.message.from_user
    text = update.message.text
    logger.info(f"Mensagem recebida de {user_info.first_name}: {text}")

    # Notificação para você (o administrador)
    mensagem_notificacao = (
        f"🔔 Nova Mensagem Recebida!\n\n"
        f"De: {user_info.first_name} (@{user_info.username})\n"
        f"Mensagem: '{text}'"
    )
    await context.bot.send_message(chat_id=SEU_CHAT_ID, text=mensagem_notificacao)

    # Resposta para o cliente
    await update.message.reply_text("Obrigado pelo seu contato! Sua mensagem foi recebida e um especialista responderá em breve.")

# --- LÓGICA DE INICIALIZAÇÃO E WEBHOOK ---
# Inicializa a aplicação do bot UMA VEZ
application = Application.builder().token(TELEGRAM_TOKEN).build()
# Adiciona os "ouvidos" do bot (handlers)
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
bot = application.bot

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook_handler():
    """Lida com as atualizações vindas do Telegram."""
    if flask.request.is_json:
        update_json = flask.request.get_json()
        update = Update.de_json(update_json, bot)

        # <<< MUDANÇA CRUCIAL AQUI >>>
        # Pega a "carta" e chama o "funcionário" para processá-la imediatamente.
        asyncio.run(application.process_update(update))

    return 'ok', 200

@app.route('/')
def index():
    """Rota de saúde para o Render saber que o app está vivo."""
    return 'Bot está vivo e pronto!', 200
