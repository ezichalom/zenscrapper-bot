"""
scraper.py — Raspador de dados do ZenMarket
Suporta Yahoo Auctions Japan, Mercari e Rakuten via ZenMarket.
"""

import hashlib
import time
import random
import logging
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ----------------------------------------------------------
# Headers que simulam um navegador real
# ----------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://zenmarket.jp/pt/",
}

# ----------------------------------------------------------
# URLs de busca por plataforma
# ----------------------------------------------------------
PLATFORM_SEARCH_URLS = {
    "yahoo":   "https://zenmarket.jp/pt/yahoo.aspx",
    "mercari": "https://zenmarket.jp/pt/mercari.aspx",
    "rakuten": "https://zenmarket.jp/pt/rakuten.aspx",
}

# Seletores CSS por plataforma (testados manualmente)
SELECTORS = {
    "yahoo": {
        "container": "li.auction-item, div.auction-item, .col-auction-item",
        "title":     ".auction-title a, h3 a, .title a, a[title]",
        "price":     ".auction-price, .price, [class*='price']",
        "link":      "a[href]",
    },
    "mercari": {
        "container": "li.mercari-item, div.item, .col-sm-6",
        "title":     ".item-name, .title, h4, h3",
        "price":     ".item-price, .price, [class*='price']",
        "link":      "a[href]",
    },
    "rakuten": {
        "container": "div.item, li.item, .product",
        "title":     ".item-name, .product-name, h3, h4",
        "price":     ".item-price, .price",
        "link":      "a[href]",
    },
}

# Fallback genérico
GENERIC_ITEM_PATTERNS = [
    "li.auction-item", "div.auction-item",
    "li.mercari-item", "div.mercari-item",
    "li.item", "div.item",
    "[class*='auction-item']",
    "[class*='product-item']",
    "[class*='item-card']",
]


def _make_id(url: str) -> str:
    """Hash MD5 da URL — serve como ID único do produto."""
    return hashlib.md5(url.encode()).hexdigest()


def _normalize_url(href: str) -> str:
    """Garante que a URL seja absoluta."""
    if href.startswith("http"):
        return href
    return "https://zenmarket.jp" + href


def _fetch_page(url: str, params: dict) -> Optional[BeautifulSoup]:
    """Faz a requisição HTTP e retorna o BeautifulSoup ou None."""
    try:
        session = requests.Session()
        # Primeira requisição à home para obter cookies
        session.get("https://zenmarket.jp/pt/", headers=HEADERS, timeout=10)
        time.sleep(random.uniform(0.5, 1.2))

        resp = session.get(url, params=params, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout ao acessar {url}")
    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP {e.response.status_code} ao acessar {url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro de rede: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado no fetch: {e}")
    return None


def _extract_items_from_soup(soup: BeautifulSoup, platform: str,
                              keyword: str, max_results: int) -> List[Dict]:
    """Extrai itens do HTML usando múltiplas estratégias."""
    products = []
    sel = SELECTORS.get(platform, SELECTORS["yahoo"])

    # --- Estratégia 1: seletores específicos da plataforma ---
    containers = soup.select(sel["container"])

    # --- Estratégia 2: seletores genéricos ---
    if not containers:
        for pattern in GENERIC_ITEM_PATTERNS:
            containers = soup.select(pattern)
            if containers:
                logger.debug(f"Usando seletor genérico: {pattern}")
                break

    # --- Estratégia 3: qualquer <li> ou <div> com link de produto ---
    if not containers:
        logger.debug("Usando estratégia de link direto")
        return _extract_by_links(soup, keyword, platform, max_results)

    for item in containers[:max_results]:
        try:
            # Link
            link_el = item.select_one("a[href]")
            if not link_el:
                continue
            href = _normalize_url(link_el.get("href", ""))
            if len(href) < 20:
                continue

            # Título (várias tentativas)
            title = None
            for t_sel in [sel["title"], "a[title]", "h3", "h4", "p.title", ".name"]:
                t_el = item.select_one(t_sel)
                if t_el:
                    title = t_el.get_text(strip=True) or t_el.get("title", "")
                    if title:
                        break
            if not title:
                title = link_el.get("title") or link_el.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            # Preço
            price = "Ver preço"
            for p_sel in [sel["price"], "[class*='price']", "[class*='Price']", "strong"]:
                p_el = item.select_one(p_sel)
                if p_el:
                    price = p_el.get_text(strip=True)
                    break

            products.append({
                "id":       _make_id(href),
                "title":    title[:120],
                "price":    price,
                "url":      href,
                "keyword":  keyword,
                "platform": platform,
            })

        except Exception as e:
            logger.debug(f"Erro ao parsear item: {e}")
            continue

    return products


def _extract_by_links(soup: BeautifulSoup, keyword: str,
                       platform: str, max_results: int) -> List[Dict]:
    """Estratégia de fallback: extrai produtos por padrões de URL."""
    products = []
    seen = set()

    # Padrões que indicam URL de produto
    product_url_hints = [
        "itemCode=", "item_id=", "/item/", "/auction/",
        "auctionID=", "itemid=", ".aspx?itemCode",
    ]

    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href", "")
        if not any(hint in href for hint in product_url_hints):
            continue
        href = _normalize_url(href)
        if href in seen:
            continue
        seen.add(href)

        title = (a_tag.get("title") or a_tag.get_text(strip=True) or "").strip()
        if len(title) < 4:
            continue

        # Tenta pegar preço nos elementos próximos
        price = "Ver preço"
        for ancestor in [a_tag.parent, a_tag.parent.parent if a_tag.parent else None]:
            if ancestor:
                p_el = ancestor.find(class_=lambda c: c and "price" in c.lower())
                if p_el:
                    price = p_el.get_text(strip=True)
                    break

        products.append({
            "id":       _make_id(href),
            "title":    title[:120],
            "price":    price,
            "url":      href,
            "keyword":  keyword,
            "platform": platform,
        })

        if len(products) >= max_results:
            break

    return products


def search_zenmarket(keyword: str, platform: str = "yahoo",
                     max_results: int = 30) -> List[Dict]:
    """
    Ponto de entrada principal do scraper.

    Args:
        keyword:     Palavra-chave a buscar.
        platform:    'yahoo', 'mercari' ou 'rakuten'.
        max_results: Máximo de itens por página a analisar.

    Returns:
        Lista de dicionários com dados dos produtos encontrados.
    """
    base_url = PLATFORM_SEARCH_URLS.get(platform, PLATFORM_SEARCH_URLS["yahoo"])
    params = {"q": keyword, "p": 1}

    logger.info(f"[{platform.upper()}] Buscando: '{keyword}'")

    soup = _fetch_page(base_url, params)
    if soup is None:
        return []

    products = _extract_items_from_soup(soup, platform, keyword, max_results)

    # Delay educado entre requisições
    time.sleep(random.uniform(2.0, 4.0))

    logger.info(f"[{platform.upper()}] '{keyword}' → {len(products)} itens encontrados")
    return products
