# -*- coding: utf-8 -*-
"""Экспорт результатов: CSV, Excel, Google Sheets."""
from __future__ import annotations

import csv
import logging
import os
from datetime import datetime
from pathlib import Path

log = logging.getLogger("export")


def _ensure_dir(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def to_csv(rows: list[dict], path: str) -> None:
    if not rows:
        return
    _ensure_dir(path)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log.info("CSV: %s (%d строк)", path, len(rows))


def to_excel(rows: list[dict], path: str, sheet: str = "data") -> None:
    if not rows:
        return
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    _ensure_dir(path)
    wb = Workbook()
    ws = wb.active
    ws.title = sheet[:31]
    headers = list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([_num(row.get(h, "")) for h in headers])

    # оформление шапки, ширина колонок, фильтр, заморозка
    fill = PatternFill("solid", fgColor="1F4E78")
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = fill
        c.alignment = Alignment(horizontal="center")
    for i, h in enumerate(headers, 1):
        width = max(len(str(h)), *(len(str(r.get(h, ""))) for r in rows[:200]))
        ws.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 8), 60)
    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = "A2"

    meta = wb.create_sheet("info")
    meta.append(["Обновлено", datetime.now().strftime("%Y-%m-%d %H:%M")])
    meta.append(["Строк", len(rows)])
    wb.save(path)
    log.info("Excel: %s (%d строк)", path, len(rows))


def to_google_sheet(rows: list[dict], tab: str) -> None:
    """Перезаписывает лист в Google-таблице. Требует .env: GOOGLE_SERVICE_ACCOUNT, GOOGLE_SHEET_ID."""
    if not rows:
        return
    sa = os.getenv("GOOGLE_SERVICE_ACCOUNT", "")
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    if not (sa and sheet_id and os.path.exists(sa)):
        log.info("Google Sheets не настроен — пропускаю")
        return
    import gspread

    gc = gspread.service_account(filename=sa)
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(tab)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(tab, rows=len(rows) + 10, cols=len(rows[0]) + 2)
    headers = list(rows[0].keys())
    values = [headers] + [[_num(r.get(h, "")) for h in headers] for r in rows]
    ws.update(values, "A1")
    ws.format("1:1", {"textFormat": {"bold": True}})
    ws.freeze(rows=1)
    log.info("Google Sheets: лист '%s' (%d строк)", tab, len(rows))


def _num(v):
    """Числа в ячейках как числа, а не текст."""
    if isinstance(v, str):
        s = v.replace(" ", "").replace(" ", "").replace(",", ".")
        try:
            return float(s) if "." in s else int(s)
        except ValueError:
            return v
    return v
