# ============================================================
#  CONFIGURAÇÕES DO ZENMARKET BOT
#  Edite este arquivo com seus dados antes de rodar o bot
# ============================================================

# ----------------------------------------------------------
# 1. TELEGRAM
# ----------------------------------------------------------
# Obtenha o TOKEN falando com @BotFather no Telegram
# Obtenha o CHAT_ID rodando: python get_chat_id.py
TELEGRAM_BOT_TOKEN = "SEU_TOKEN_AQUI"
TELEGRAM_CHAT_ID   = "SEU_CHAT_ID_AQUI"

# ----------------------------------------------------------
# 2. PALAVRAS-CHAVE PARA MONITORAR
# ----------------------------------------------------------
# Adicione quantas quiser. Suporta japonês, inglês e português.
# Dica: palavras em japonês têm resultados mais precisos no ZenMarket
KEYWORDS = [
    "pokemon card",
    "gundam",
    "one piece",
    # "ポケモン",       # pokemon em japonês
    # "フィギュア",     # figure em japonês
]

# ----------------------------------------------------------
# 3. PLATAFORMAS DO ZENMARKET
# ----------------------------------------------------------
# Escolha quais plataformas monitorar
# Opções disponíveis: "yahoo", "mercari", "rakuten"
PLATFORMS = ["yahoo", "mercari"]

# ----------------------------------------------------------
# 4. FILTROS DE PREÇO (em JPY - Yens japoneses)
# ----------------------------------------------------------
# Preço mínimo (0 = sem limite)
MIN_PRICE_JPY = 0

# Preço máximo (0 = sem limite)
MAX_PRICE_JPY = 0

# ----------------------------------------------------------
# 5. AGENDAMENTO
# ----------------------------------------------------------
# Intervalo de verificação em MINUTOS
CHECK_INTERVAL_MINUTES = 3

# Máximo de resultados analisados por busca
MAX_RESULTS_PER_SEARCH = 30

# ----------------------------------------------------------
# 6. AVANÇADO
# ----------------------------------------------------------
# Salvar log em arquivo?
SAVE_LOG_TO_FILE = True
LOG_FILE = "zenmarket_bot.log"

# Enviar relatório de status a cada X horas (0 = desativado)
HEARTBEAT_HOURS = 6
