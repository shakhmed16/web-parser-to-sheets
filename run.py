# -*- coding: utf-8 -*-
"""Запуск парсера.

    python run.py configs/books.yaml            # один раз
    python run.py configs/books.yaml --every 6h # каждые 6 часов
    python run.py configs/books.yaml --at 09:00 # ежедневно в 9:00
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime

import yaml
from dotenv import load_dotenv

from parser.exporters import to_csv, to_excel, to_google_sheet
from parser.scraper import Scraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("run")


def job(config_path: str) -> int:
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    started = datetime.now()
    s = Scraper(cfg, proxy=os.getenv("PROXY"))
    try:
        rows = list(s.run())
    finally:
        s.close()
    out = cfg.get("output", {})
    if p := out.get("csv"):
        to_csv(rows, p)
    if p := out.get("excel"):
        to_excel(rows, p, sheet=cfg.get("name", "data"))
    if tab := out.get("google_sheet_tab"):
        to_google_sheet(rows, tab)
    log.info("Готово: %d записей за %.1f c", len(rows), (datetime.now() - started).total_seconds())
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Парсер каталога → CSV / Excel / Google Sheets")
    ap.add_argument("config", help="YAML-конфиг сайта, см. configs/")
    ap.add_argument("--every", help="повторять каждые N минут/часов: 30m, 6h")
    ap.add_argument("--at", help="ежедневно в HH:MM")
    args = ap.parse_args()
    load_dotenv()

    if not args.every and not args.at:
        job(args.config)
        return

    import schedule

    if args.every:
        n, unit = int(args.every[:-1]), args.every[-1]
        (schedule.every(n).minutes if unit == "m" else schedule.every(n).hours).do(job, args.config)
    if args.at:
        schedule.every().day.at(args.at).do(job, args.config)
    log.info("Расписание запущено. Ctrl+C для выхода.")
    job(args.config)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
