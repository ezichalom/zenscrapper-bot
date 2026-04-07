"""
bot.py — Ponto de entrada principal do ZenMarket Bot
Execute com: python bot.py
"""

import logging
import sys
import time

import schedule

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    KEYWORDS,
    PLATFORMS,
    CHECK_INTERVAL_MINUTES,
    MAX_RESULTS_PER_SEARCH,
    MIN_PRICE_JPY,
    MAX_PRICE_JPY,
    SAVE_LOG_TO_FILE,
    LOG_FILE,
    HEARTBEAT_HOURS,
)
from scraper import search_zenmarket
from storage import init_db, is_new_product, save_product, get_stats
from notifier import (
    send_product_alert,
    send_startup_message,
    send_heartbeat,
    send_error_alert,
    test_connection,
)

# ----------------------------------------------------------
# Logging
# ----------------------------------------------------------
handlers = [logging.StreamHandler(sys.stdout)]
if SAVE_LOG_TO_FILE:
    handlers.append(logging.FileHandler(LOG_FILE, encoding="utf-8"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=handlers,
)
logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# Filtro de preço
# ----------------------------------------------------------
def _price_in_range(price_str: str) -> bool:
    """Retorna True se o preço está dentro do range configurado."""
    if MIN_PRICE_JPY == 0 and MAX_PRICE_JPY == 0:
        return True  # Sem filtro de preço

    try:
        # Extrai só os dígitos do texto de preço (ex: "¥ 1,500" → 1500)
        digits = int("".join(filter(str.isdigit, price_str)))
    except (ValueError, TypeError):
        return True  # Não conseguiu parsear → deixa passar

    if MIN_PRICE_JPY > 0 and digits < MIN_PRICE_JPY:
        return False
    if MAX_PRICE_JPY > 0 and digits > MAX_PRICE_JPY:
        return False
    return True


# ----------------------------------------------------------
# Ciclo principal de verificação
# ----------------------------------------------------------
def check_new_products():
    """Varre todas as keywords e plataformas e notifica novos produtos."""
    logger.info("=" * 55)
    logger.info("Iniciando rodada de verificação...")
    logger.info("=" * 55)

    new_count = 0

    for keyword in KEYWORDS:
        for platform in PLATFORMS:
            try:
                products = search_zenmarket(keyword, platform, MAX_RESULTS_PER_SEARCH)

                for product in products:
                    # Filtro de preço
                    if not _price_in_range(product["price"]):
                        continue

                    # Verifica se é novo
                    if not is_new_product(product["id"]):
                        continue

                    logger.info(f"🆕 NOVO: [{platform}] {product['title'][:70]}")

                    # Notifica
                    sent = send_product_alert(
                        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, product
                    )

                    if sent:
                        save_product(
                            product["id"],
                            product["title"],
                            product["price"],
                            product["url"],
                            product["keyword"],
                            product["platform"],
                        )
                        new_count += 1
                        time.sleep(0.8)  # Pausa entre notificações

            except Exception as e:
                logger.error(f"Erro ao processar '{keyword}' em {platform}: {e}")
                send_error_alert(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, str(e))

    if new_count == 0:
        logger.info("Nenhum produto novo nesta rodada.")
    else:
        logger.info(f"✅ Rodada finalizada: {new_count} produto(s) novo(s) notificado(s)!")

    return new_count


# ----------------------------------------------------------
# Heartbeat periódico
# ----------------------------------------------------------
def heartbeat():
    """Envia relatório de status para o Telegram."""
    stats = get_stats()
    send_heartbeat(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, stats, KEYWORDS)
    logger.info("Heartbeat enviado.")


# ----------------------------------------------------------
# Validação de configuração
# ----------------------------------------------------------
def validate_config() -> bool:
    """Verifica se as configurações mínimas estão preenchidas."""
    errors = []
    if TELEGRAM_BOT_TOKEN == "SEU_TOKEN_AQUI":
        errors.append("TELEGRAM_BOT_TOKEN não configurado em config.py")
    if TELEGRAM_CHAT_ID == "SEU_CHAT_ID_AQUI":
        errors.append("TELEGRAM_CHAT_ID não configurado em config.py")
    if not KEYWORDS:
        errors.append("Nenhuma KEYWORD definida em config.py")
    if not PLATFORMS:
        errors.append("Nenhuma PLATFORM definida em config.py")

    if errors:
        for e in errors:
            logger.error(f"❌ Configuração inválida: {e}")
        return False
    return True


# ----------------------------------------------------------
# Main
# ----------------------------------------------------------
def main():
    logger.info("╔══════════════════════════════════════╗")
    logger.info("║       ZenMarket Bot — Iniciando      ║")
    logger.info("╚══════════════════════════════════════╝")

    # 1. Valida configurações
    if not validate_config():
        logger.error("Corrija o arquivo config.py e tente novamente.")
        sys.exit(1)

    # 2. Inicializa banco de dados
    init_db()
    logger.info("Banco de dados SQLite inicializado.")

    # 3. Testa conexão com Telegram
    if not test_connection(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID):
        logger.error("Falha na conexão com o Telegram. Verifique TOKEN e CHAT_ID.")
        sys.exit(1)
    logger.info("Conexão com Telegram OK.")

    # 4. Envia mensagem de início
    send_startup_message(
        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
        KEYWORDS, PLATFORMS, CHECK_INTERVAL_MINUTES
    )

    # 5. Agenda verificações periódicas
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_new_products)
    logger.info(f"Agendado: verificar a cada {CHECK_INTERVAL_MINUTES} minuto(s)")

    # 6. Agenda heartbeat (se configurado)
    if HEARTBEAT_HOURS > 0:
        schedule.every(HEARTBEAT_HOURS).hours.do(heartbeat)
        logger.info(f"Heartbeat agendado a cada {HEARTBEAT_HOURS} hora(s)")

    # 7. Executa verificação imediata ao iniciar
    check_new_products()

    # 8. Loop principal
    logger.info("Bot em execução. Pressione Ctrl+C para parar.")
    while True:
        try:
            schedule.run_pending()
            time.sleep(15)
        except KeyboardInterrupt:
            logger.info("Bot interrompido pelo usuário.")
            break
        except Exception as e:
            logger.error(f"Erro no loop principal: {e}")
            time.sleep(60)  # Aguarda 1 min antes de tentar novamente


if __name__ == "__main__":
    main()
