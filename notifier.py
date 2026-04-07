"""
notifier.py — Envio de notificações via Telegram Bot API
"""

import logging
import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _send(token: str, chat_id: str, text: str,
          parse_mode: str = "HTML", preview: bool = True) -> bool:
    """Envia uma mensagem de texto via Telegram Bot API."""
    url = TELEGRAM_API.format(token=token, method="sendMessage")
    payload = {
        "chat_id":                  chat_id,
        "text":                     text,
        "parse_mode":               parse_mode,
        "disable_web_page_preview": not preview,
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return True
    except requests.exceptions.HTTPError as e:
        logger.error(f"Telegram HTTP error {e.response.status_code}: {e.response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Telegram request error: {e}")
    return False


# ----------------------------------------------------------
# Mensagens públicas (chamadas pelo bot.py)
# ----------------------------------------------------------

def send_product_alert(token: str, chat_id: str, product: dict) -> bool:
    """Formata e envia alerta de novo produto."""
    platform_labels = {
        "yahoo":   "🏷️ Yahoo Auctions",
        "mercari": "🛍️ Mercari",
        "rakuten": "🛒 Rakuten",
    }
    platform_label = platform_labels.get(product["platform"],
                                         "🏪 " + product["platform"].title())

    msg = (
        f"🔔 <b>NOVO PRODUTO ENCONTRADO!</b>\n\n"
        f"📦 <b>{product['title']}</b>\n\n"
        f"💴 Preço: <b>{product['price']}</b>\n"
        f"🔍 Palavra-chave: <code>{product['keyword']}</code>\n"
        f"🏪 Plataforma: {platform_label}\n\n"
        f"🔗 <a href=\"{product['url']}\">Ver no ZenMarket →</a>"
    )
    return _send(token, chat_id, msg, preview=True)


def send_startup_message(token: str, chat_id: str,
                          keywords: list, platforms: list, interval: int) -> bool:
    """Envia mensagem ao inicializar o bot."""
    kw_text = "\n".join(f"  • <code>{kw}</code>" for kw in keywords)
    pl_text  = " | ".join(p.title() for p in platforms)

    msg = (
        f"🤖 <b>ZenMarket Bot Iniciado!</b>\n\n"
        f"🔍 <b>Monitorando:</b>\n{kw_text}\n\n"
        f"🏪 Plataformas: {pl_text}\n"
        f"⏱️ Intervalo: a cada {interval} minuto(s)\n\n"
        f"Aguardando novos produtos... 👀"
    )
    return _send(token, chat_id, msg, preview=False)


def send_heartbeat(token: str, chat_id: str, stats: dict, keywords: list) -> bool:
    """Envia status periódico do bot."""
    top_kw = "\n".join(
        f"  • <code>{kw}</code>: {cnt} produtos"
        for kw, cnt in stats.get("top_keywords", [])
    ) or "  (nenhum ainda)"

    msg = (
        f"💓 <b>ZenMarket Bot — Status</b>\n\n"
        f"📊 Total registrado: {stats['total']}\n"
        f"🆕 Últimas 24h: {stats['last_24h']}\n"
        f"🔍 Keywords ativas: {len(keywords)}\n\n"
        f"🏆 <b>Top keywords:</b>\n{top_kw}\n\n"
        f"✅ Bot rodando normalmente"
    )
    return _send(token, chat_id, msg, preview=False)


def send_error_alert(token: str, chat_id: str, error_msg: str) -> bool:
    """Alerta de erro crítico."""
    msg = (
        f"⚠️ <b>Erro no ZenMarket Bot</b>\n\n"
        f"<code>{error_msg[:400]}</code>\n\n"
        f"Verifique o arquivo de log."
    )
    return _send(token, chat_id, msg, preview=False)


def test_connection(token: str, chat_id: str) -> bool:
    """Testa se o token e chat_id estão corretos."""
    msg = "✅ Conexão com Telegram OK! O bot está configurado corretamente."
    return _send(token, chat_id, msg, preview=False)
