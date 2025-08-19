# app.py - VERSÃO DEFINITIVA
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

    mensagem_notificacao = (
        f"🔔 Nova Mensagem Recebida!\n\n"
        f"De: {user_info.first_name} (@{user_info.username})\n"
        f"Mensagem: '{text}'"
    )
    # Envia a notificação e a resposta em paralelo para mais eficiência
    await asyncio.gather(
        context.bot.send_message(chat_id=SEU_CHAT_ID, text=mensagem_notificacao),
        update.message.reply_text("Obrigado pelo seu contato! Sua mensagem foi recebida e um especialista responderá em breve.")
    )

# --- LÓGICA DE INICIALIZAÇÃO E WEBHOOK ---
# Pre-configura a aplicação do bot UMA VEZ.
ptb_app = Application.builder().token(TELEGRAM_TOKEN).build()
ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook_handler():
    """Lida com as atualizações vindas do Telegram."""
    
    async def process_telegram_update():
        # Inicializa a aplicação (liga o sistema elétrico)
        await ptb_app.initialize()
        
        update = Update.de_json(flask.request.get_json(), ptb_app.bot)
        
        # Processa a mensagem
        await ptb_app.process_update(update)
        
        # Desliga a aplicação de forma limpa
        await ptb_app.shutdown()

    # Roda o processo completo em um novo loop de eventos a cada chamada
    asyncio.run(process_telegram_update())
    
    return 'ok', 200

@app.route('/')
def index():
    """Rota de saúde para o Render saber que o app está vivo."""
    return 'Bot está vivo e pronto!', 200
