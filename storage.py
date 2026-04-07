"""
storage.py — Gerenciamento do banco de dados SQLite
Armazena produtos já vistos para evitar notificações duplicadas.
"""

import sqlite3
from datetime import datetime

DB_PATH = "zenmarket_bot.db"


def init_db():
    """Cria as tabelas do banco de dados se não existirem."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS seen_products (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            price       TEXT,
            url         TEXT NOT NULL,
            keyword     TEXT NOT NULL,
            platform    TEXT NOT NULL,
            found_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            new_found   INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def is_new_product(product_id: str) -> bool:
    """Retorna True se o produto ainda não foi visto."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM seen_products WHERE id = ?", (product_id,))
    exists = cur.fetchone() is not None
    conn.close()
    return not exists


def save_product(product_id: str, title: str, price: str,
                 url: str, keyword: str, platform: str):
    """Salva um produto no banco. Ignora duplicatas silenciosamente."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO seen_products (id, title, price, url, keyword, platform, found_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (product_id, title, price, url, keyword, platform, datetime.now()))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Produto já estava no banco
    finally:
        conn.close()


def get_stats() -> dict:
    """Retorna estatísticas gerais do bot."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM seen_products")
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM seen_products
        WHERE found_at >= datetime('now', '-24 hours')
    """)
    last_24h = cur.fetchone()[0]

    cur.execute("""
        SELECT keyword, COUNT(*) as cnt
        FROM seen_products
        GROUP BY keyword
        ORDER BY cnt DESC
        LIMIT 5
    """)
    top_keywords = cur.fetchall()

    conn.close()
    return {
        "total": total,
        "last_24h": last_24h,
        "top_keywords": top_keywords,
    }
