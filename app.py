# app_v2.py - VERSÃO ARQUITETURALMENTE ROBUSTA
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
    CallbackQueryHandler,
)
import flask

# --- 1. CONFIGURAÇÃO E CONSTANTES ---
# Carregue as variáveis de ambiente. Para desenvolvimento local, use um .env
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
SEU_CHAT_ID = os.environ.get('SEU_CHAT_ID')
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'substitua-por-um-segredo-forte')
NOME_EMPRESA = os.environ.get('NOME_EMPRESA', 'Sua Empresa Inc.')


# --- 2. GESTÃO DE ESTADOS (ROBUSTEZ) ---
# Usamos Enum para tornar os estados da conversa legíveis e à prova de erros.
class ConversationState(Enum):
    CHOOSE_SERVICE = auto()
    GET_PROFILE = auto()


# --- 3. INICIALIZAÇÃO DO FLASK E LOGGING ---
app = flask.Flask(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- 4. LÓGICA DO BOT (FUNÇÕES DA CONVERSA) ---

async def start_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
    """Inicia a conversa com uma mensagem rica e botões inline."""
    user = update.effective_user
    logger.info(f"Usuário {user.first_name} ({user.id}) iniciou uma nova conversa.")
    
    # Limpa dados de conversas anteriores para garantir um fluxo limpo
    context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("App de Internet 🌐", callback_data="internet")],
        [InlineKeyboardButton("App de Streaming 📺", callback_data="streaming")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Olá, {user.first_name}! 👋\n\n"
        f"Sou o assistente virtual da *{NOME_EMPRESA}*. Estou aqui para ajudar você a "
        "encontrar a solução perfeita de forma rápida e fácil.\n\n"
        "Para começarmos, qual dos nossos serviços você tem mais interesse?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return ConversationState.CHOOSE_SERVICE


async def handle_service_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationState:
    """Processa a escolha do serviço e pergunta o perfil do cliente."""
    query = update.callback_query
    await query.answer() # Responde ao clique do botão para remover o "loading"

    service_map = {"internet": "App de Internet", "streaming": "App de Streaming"}
    service_choice = service_map.get(query.data)
    
    context.user_data['service'] = service_choice
    logger.info(f"Usuário {query.from_user.first_name} escolheu o serviço: {service_choice}")

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
    """Processa a escolha do perfil, finaliza a conversa e notifica a equipe."""
    query = update.callback_query
    await query.answer()

    profile_map = {"residencial": "Residencial", "comercial": "Comercial (B2B)"}
    profile_choice = profile_map.get(query.data)
    
    context.user_data['profile'] = profile_choice
    user_info = query.from_user
    
    logger.info(f"Usuário {user_info.first_name} se identificou com o perfil: {profile_choice}")

    # --- LÓGICA DE NOTIFICAÇÃO (COM TRATAMENTO DE ERROS) ---
    try:
        if not SEU_CHAT_ID:
            logger.error("FATAL: SEU_CHAT_ID não está configurado!")
            raise ValueError("ID do chat de destino não configurado.")

        user_link = f"tg://user?id={user_info.id}"
        username_part = f"(@{user_info.username})" if user_info.username else ""
        
        # Mensagem de notificação enriquecida
        mensagem_notificacao = (
            f"✅ **Novo Lead Qualificado ({context.user_data['profile']})**\n\n"
            f"**Cliente:** {user_info.first_name} {username_part}\n"
            f"**Serviço de Interesse:** {context.user_data['service']}\n\n"
            f"➡️ **[Conversar com o Cliente]({user_link})**"
        )
        
        await context.bot.send_message(
            chat_id=SEU_CHAT_ID, 
            text=mensagem_notificacao, 
            parse_mode='Markdown'
        )

        # Mensagem de confirmação para o usuário com gestão de expectativas
        await query.edit_message_text(
            text="Perfeito! Todas as informações foram recebidas.\n\n"
            "Um de nossos especialistas humanos entrará em contato com você aqui mesmo neste chat "
            "em breve para dar continuidade.\n\n"
            "Nosso tempo de resposta é de, em média, 2 horas durante o horário comercial. "
            f"Obrigado por escolher a *{NOME_EMPRESA}*!",
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Falha ao processar a finalização para o usuário {user_info.id}: {e}")
        await query.edit_message_text(
            text="Houve um problema ao processar sua solicitação. 😔\n"
            "Nossa equipe técnica já foi notificada. Por favor, tente iniciar a conversa novamente com /start."
        )
    
    finally:
        return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a conversa de forma explícita e limpa."""
    await update.message.reply_text(
        "Atendimento cancelado. Se precisar de algo, é só me chamar com /start.",
    )
    context.user_data.clear()
    return ConversationHandler.END


# --- 5. SETUP DA APLICAÇÃO E CONVERSATION HANDLER ---
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


# --- 6. ARQUITETURA DE WEBHOOK (ALTA PERFORMANCE) ---
# Inicializamos a aplicação PTB uma única vez fora do ciclo de requisição.
loop = asyncio.get_event_loop_policy().get_event_loop()
loop.run_until_complete(ptb_app.initialize())


@app.route(f'/{WEBHOOK_SECRET}', methods=['POST'])
def webhook_handler():
    """Lida com as atualizações do Telegram de forma não-bloqueante."""
    json_data = flask.request.get_json()
    
    async def process_update_async():
        update = Update.de_json(json_data, ptb_app.bot)
        await ptb_app.process_update(update)

    # Cria uma task para processar a atualização, liberando a requisição HTTP imediatamente.
    asyncio.run_coroutine_threadsafe(process_update_async(), loop)
    return 'ok', 200


@app.route('/')
def index():
    """Rota de 'health check' para o provedor de nuvem (Render, etc.)."""
    return f'Bot da {NOME_EMPRESA} está vivo e pronto!', 200
