# app.py - VERSÃO OTIMIZADA E PROFISSIONAL
import logging
import os
import asyncio
from enum import Enum, auto
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler, # Importante: Usaremos para os botões inline
)
import flask

# --- 1. CONFIGURAÇÃO E CONSTANTES ---
# Buscando as variáveis de ambiente. A aplicação irá falhar se o token não for encontrado.
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
SEU_CHAT_ID = os.environ.get('SEU_CHAT_ID')
# Nova variável de segurança para a URL do webhook
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'coloque-um-segredo-forte-aqui')


# --- 2. GESTÃO DE ESTADOS COM ENUM (ROBUSTEZ) ---
# Substituímos números por um Enum para clareza e segurança.
class ConversationState(Enum):
    CHOOSE_SERVICE = auto()
    GET_PROFILE = auto()


# --- 3. INICIALIZAÇÃO DO FLASK E LOGGING ---
app = flask.Flask(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- 4. FUNÇÕES DA CONVERSA (LÓGICA DO BOT) ---

async def start_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
    """Inicia a conversa com uma mensagem rica e botões inline."""
    user = update.effective_user
    logger.info(f"Usuário {user.first_name} ({user.id}) iniciou uma nova conversa.")
    
    context.user_data.clear()

    # Usando InlineKeyboardMarkup para uma melhor experiência do usuário
    keyboard = [
        [InlineKeyboardButton("App de Internet 🌐", callback_data="internet")],
        [InlineKeyboardButton("App de Streaming 📺", callback_data="streaming")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Olá, {user.first_name}! 👋\n\n"
        "Sou seu assistente virtual. Estou aqui para ajudar você a "
        "encontrar a solução perfeita de forma rápida e fácil.\n\n"
        "Para começarmos, qual dos nossos serviços você tem mais interesse?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return ConversationState.CHOOSE_SERVICE


async def handle_service_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
    """Processa a escolha do serviço e avança para a qualificação do perfil."""
    query = update.callback_query
    await query.answer()

    service_map = {"internet": "App de Internet", "streaming": "App de Streaming"}
    service_choice = service_map.get(query.data)
    
    # Armazenamos a escolha no contexto da conversa
    context.user_data['service'] = service_choice
    logger.info(f"Usuário {query.from_user.first_name} escolheu: {service_choice}")

    keyboard = [
        [InlineKeyboardButton("Para minha casa 🏠", callback_data="residencial")],
        [InlineKeyboardButton("Para meu negócio 🏢", callback_data="comercial")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="Ótima escolha! E essa solução seria para qual finalidade?",
        reply_markup=reply_markup,
    )
    return ConversationState.GET_PROFILE


async def handle_profile_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa a escolha final, notifica a equipe e encerra a conversa."""
    query = update.callback_query
    await query.answer()

    profile_map = {"residencial": "Residencial", "comercial": "Comercial (B2B)"}
    profile_choice = profile_map.get(query.data)
    user_info = query.from_user
    
    logger.info(f"Usuário {user_info.first_name} se identificou como perfil: {profile_choice}")

    # Montando a notificação rica para a equipe
    user_link = f"tg://user?id={user_info.id}"
    username_part = f"(@{user_info.username})" if user_info.username else ""
    mensagem_notificacao = (
        f"✅ **Novo Lead Qualificado ({profile_choice})**\n\n"
        f"**Cliente:** {user_info.first_name} {username_part}\n"
        f"**Serviço de Interesse:** {context.user_data['service']}\n\n"
        f"➡️ **[Conversar com o Cliente]({user_link})**"
    )
    
    try:
        # Envio da notificação com tratamento de erro
        await context.bot.send_message(
            chat_id=SEU_CHAT_ID, 
            text=mensagem_notificacao, 
            parse_mode='Markdown'
        )
        
        # Mensagem final para o usuário, gerenciando expectativas
        await query.edit_message_text(
            text="Perfeito! Recebemos suas informações.\n\n"
            "Um de nossos especialistas entrará em contato com você.\n\n"
            "Nosso tempo de resposta é de, em média, 10 minutos durante o horário comercial. Obrigado!",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Falha ao enviar notificação ou confirmar com o usuário: {e}")
        await query.edit_message_text(
            text="Ocorreu um erro ao processar sua solicitação. Nossa equipe já foi notificada."
        )
    
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Função de fallback para cancelar a conversa."""
    await update.message.reply_text("Atendimento cancelado. Se precisar de algo, é só mandar um /start.")
    return ConversationHandler.END


# --- 5. LÓGICA DE INICIALIZAÇÃO E WEBHOOK (ALTA PERFORMANCE) ---
ptb_app = Application.builder().token(TELEGRAM_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start_conversation)],
    states={
        ConversationState.CHOOSE_SERVICE: [
            CallbackQueryHandler(handle_service_choice, pattern="^(internet|streaming)$")
        ],
        ConversationState.GET_PROFILE: [
            CallbackQueryHandler(handle_profile_choice, pattern="^(residencial|comercial)$")
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_conversation)],
)
ptb_app.add_handler(conv_handler)

# Inicialização da aplicação uma única vez, fora do ciclo de requisição
loop = asyncio.get_event_loop_policy().get_event_loop()
loop.run_until_complete(ptb_app.initialize())


@app.route(f'/{WEBHOOK_SECRET}', methods=['POST'])
def webhook_handler():
    """Lida com as atualizações do Telegram de forma não-bloqueante."""
    json_data = flask.request.get_json()
    
    async def process_update_async():
        update = Update.de_json(json_data, ptb_app.bot)
        await ptb_app.process_update(update)

    # Agenda a tarefa para ser executada sem bloquear a resposta HTTP
    asyncio.run_coroutine_threadsafe(process_update_async(), loop)
    return 'ok', 200


@app.route('/')
def index():
    """Rota de saúde para o Render."""
    return 'Bot está vivo e pronto!', 200
