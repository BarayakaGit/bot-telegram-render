# app.py - VERSÃO COM FLUXO DE CONVERSA
import logging
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)
import flask

# --- CONFIGURAÇÃO ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
SEU_CHAT_ID = os.environ.get('SEU_CHAT_ID')

# --- INICIALIZAÇÃO DO FLASK (NOSSO SERVIDOR WEB) ---
app = flask.Flask(__name__)

# --- LÓGICA DO BOT ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Definindo "estados" para a nossa conversa.
CHOOSE_SERVICE = 1

async def start_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa (quando recebe /start ou uma mensagem de texto)."""
    user_info = update.message.from_user
    logger.info(f"Usuário {user_info.first_name} iniciou uma nova conversa.")

    # Cria um teclado com as opções para o cliente
    keyboard = [["1. App de Internet"], ["2. App de Streaming"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "Olá! Seja bem-vindo(a). Sou seu assistente virtual.\n\n"
        "Para começarmos, qual dos nossos serviços você tem interesse?",
        reply_markup=reply_markup,
    )
    
    # Diz ao ConversationHandler que agora estamos no estado CHOOSE_SERVICE
    return CHOOSE_SERVICE

async def handle_service_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa a escolha do serviço feita pelo cliente."""
    user_info = update.message.from_user
    choice = update.message.text
    
    # Determina o serviço escolhido com base no texto
    service = ""
    if "1" in choice:
        service = "App de Internet"
    elif "2" in choice:
        service = "App de Streaming"
    else:
        # Se o usuário digitar algo inesperado
        await update.message.reply_text("Por favor, escolha uma das opções usando os botões.")
        return CHOOSE_SERVICE # Permanece no mesmo estado

    logger.info(f"Usuário {user_info.first_name} escolheu o serviço: {service}")

    # Notificação para você (o administrador)
    mensagem_notificacao = (
        f"✅ Novo Lead Qualificado!\n\n"
        f"De: {user_info.first_name} (@{user_info.username})\n"
        f"Serviço de Interesse: **{service}**"
    )
    
    # Envia a notificação e a resposta de confirmação para o cliente
    await asyncio.gather(
        context.bot.send_message(chat_id=SEU_CHAT_ID, text=mensagem_notificacao, parse_mode='Markdown'),
        update.message.reply_text(
            f"Entendido, seu interesse é em **{service}**.\n\n"
            "Um de nossos especialistas humanos entrará em contato com você em breve aqui mesmo neste chat. Obrigado!",
            reply_markup=ReplyKeyboardRemove(), # Remove o teclado de botões
            parse_mode='Markdown'
        )
    )
    
    # Finaliza a conversa
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Função para cancelar a conversa a qualquer momento."""
    await update.message.reply_text(
        "Atendimento cancelado. Se precisar de algo, é só mandar um /start.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# --- LÓGICA DE INICIALIZAÇÃO E WEBHOOK ---
ptb_app = Application.builder().token(TELEGRAM_TOKEN).build()

# Criando o Gerente de Conversas (ConversationHandler)
conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("start", start_conversation),
        MessageHandler(filters.TEXT & ~filters.COMMAND, start_conversation) # Qualquer texto que não seja comando
    ],
    states={
        CHOOSE_SERVICE: [MessageHandler(filters.Regex("^(1|2)"), handle_service_choice)],
    },
    fallbacks=[CommandHandler("cancel", cancel_conversation)],
)

ptb_app.add_handler(conv_handler)

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook_handler():
    """Lida com as atualizações vindas do Telegram."""
    async def process_telegram_update():
        await ptb_app.initialize()
        update = Update.de_json(flask.request.get_json(), ptb_app.bot)
        await ptb_app.process_update(update)
        await ptb_app.shutdown()
    asyncio.run(process_telegram_update())
    return 'ok', 200

@app.route('/')
def index():
    """Rota de saúde para o Render saber que o app está vivo."""
    return 'Bot está vivo e pronto para conversar!', 200
