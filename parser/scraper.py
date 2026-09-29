# -*- coding: utf-8 -*-
"""Универсальный парсер каталога по CSS-селекторам из YAML-конфига."""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Iterator
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser, Node

log = logging.getLogger("scraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ru,en;q=0.8",
}


class Scraper:
    def __init__(self, config: dict[str, Any], proxy: str | None = None):
        self.cfg = config
        self.client = httpx.Client(
            headers=HEADERS,
            timeout=30,
            follow_redirects=True,
            proxy=proxy or None,
        )

    # ---------- сеть ----------

    def fetch(self, url: str, retries: int = 3) -> str:
        for attempt in range(1, retries + 1):
            try:
                r = self.client.get(url)
                r.raise_for_status()
                return r.text
            except httpx.HTTPError as e:
                log.warning("%s: %s (попытка %d/%d)", url, e, attempt, retries)
                time.sleep(2 * attempt)
        raise RuntimeError(f"Не удалось загрузить {url}")

    # ---------- извлечение ----------

    def _extract(self, node: Node, spec: dict[str, Any] | str, base_url: str) -> str:
        if isinstance(spec, str):
            spec = {"selector": spec}
        el = node.css_first(spec["selector"]) if spec.get("selector") else node
        if el is None:
            return ""
        if attr := spec.get("attr"):
            value = el.attributes.get(attr, "") or ""
        else:
            value = el.text(strip=True)
        if spec.get("absolute") and value:
            value = urljoin(base_url, value)
        if rx := spec.get("regex"):
            m = re.search(rx, value)
            value = (m.group(1) if m.lastindex else m.group(0)) if m else ""
        if spec.get("clean"):
            value = re.sub(r"\s+", " ", value).strip()
        return value.strip()

    def parse_page(self, html: str, url: str) -> tuple[list[dict[str, str]], str | None]:
        tree = HTMLParser(html)
        rows = []
        for card in tree.css(self.cfg["item"]):
            row = {name: self._extract(card, spec, url) for name, spec in self.cfg["fields"].items()}
            if any(row.values()):
                rows.append(row)
        next_url = None
        if sel := self.cfg.get("next_page"):
            a = tree.css_first(sel)
            if a and a.attributes.get("href"):
                next_url = urljoin(url, a.attributes["href"])
        return rows, next_url

    # ---------- обход ----------

    def run(self) -> Iterator[dict[str, str]]:
        url: str | None = self.cfg["start_url"]
        max_pages = int(self.cfg.get("max_pages", 0) or 0)
        delay = float(self.cfg.get("delay_sec", 1.0))
        page = 0
        seen: set[str] = set()
        while url and url not in seen:
            seen.add(url)
            page += 1
            log.info("Страница %d: %s", page, url)
            rows, url = self.parse_page(self.fetch(url), url)
            log.info("  найдено %d записей", len(rows))
            yield from rows
            if max_pages and page >= max_pages:
                break
            if url:
                time.sleep(delay)

    def close(self) -> None:
        self.client.close()
