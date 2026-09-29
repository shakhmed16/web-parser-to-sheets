# Парсер каталога → Excel / CSV / Google Sheets

Собирает товары, объявления или любые карточки с сайта и выгружает в аккуратную таблицу. Под новый сайт не пишется код — только YAML-конфиг с CSS-селекторами. Может работать по расписанию и обновлять Google-таблицу автоматически.

Типовые задачи: мониторинг цен конкурентов, выгрузка каталога поставщика, сбор объявлений, наполнение своего магазина.

## Что умеет

- **Любой сайт с HTML-каталогом** — карточка и поля описываются селекторами в конфиге; поддержка атрибутов (`href`, `src`, `data-*`), регулярок для чистки («2 490 ₽» → `2490`), абсолютных ссылок.
- **Пагинация** — идёт по кнопке «следующая», лимит страниц, пауза между запросами, повторы при ошибках.
- **Excel с оформлением** — шапка, автоширина колонок, фильтр, закреплённая строка, числа как числа; лист `info` с датой обновления.
- **CSV в UTF-8 с BOM** — открывается в Excel без кракозябр.
- **Google Sheets** — перезаписывает лист в вашей таблице через сервисный аккаунт; клиент видит свежие данные по ссылке.
- **Расписание** — `--every 6h` или `--at 09:00`, работает как фоновый процесс на VPS.
- **Прокси** — одна строка в `.env`, если сайт режет регион.

## Пример

```bash
pip install -r requirements.txt
python run.py configs/books.yaml
```

```
Страница 1: https://books.toscrape.com/catalogue/page-1.html
  найдено 20 записей
...
CSV: output/books.csv (100 строк)
Excel: output/books.xlsx (100 строк)
Готово: 100 записей за 3.4 c
```

| title | price | in_stock | rating | url |
|---|---|---|---|---|
| A Light in the Attic | 51.77 | In stock | Three | https://books.toscrape.com/… |
| Tipping the Velvet | 53.74 | In stock | One | https://books.toscrape.com/… |

## Конфиг под свой сайт

```yaml
name: shop
start_url: https://example.com/catalog?page=1
delay_sec: 1.0
max_pages: 0              # 0 = все страницы

item: div.product-card    # карточка товара
fields:
  name:  .product-title
  price:
    selector: .price
    regex: "[\\d\\s]+"
  url:
    selector: a
    attr: href
    absolute: true

next_page: a.pagination__next

output:
  excel: output/shop.xlsx
  google_sheet_tab: shop
```

Селекторы берутся из инструментов разработчика браузера (F12 → правый клик по элементу → Copy selector). Шаблон: `configs/example_shop.yaml`.

## Google Sheets за 3 минуты

1. Google Cloud → создать сервисный аккаунт → скачать JSON-ключ → положить рядом как `service_account.json`.
2. Открыть доступ к таблице на email сервисного аккаунта (как обычному человеку).
3. В `.env` указать `GOOGLE_SHEET_ID` из адресной строки таблицы.

## Расписание

```bash
python run.py configs/shop.yaml --every 6h     # каждые 6 часов
python run.py configs/shop.yaml --at 09:00     # ежедневно в 9:00
```

## Стек

Python 3.11+, httpx, selectolax (быстрый HTML-парсер), openpyxl, gspread, PyYAML. Для сайтов, где каталог подгружается JavaScript, подключается Playwright — делается под задачу.

## Структура

```
run.py               запуск, расписание, экспорт
parser/scraper.py    загрузка страниц, извлечение полей, пагинация
parser/exporters.py  CSV, Excel, Google Sheets
configs/             конфиги сайтов (books.yaml — рабочий пример)
```

## Под заказ

Настрою парсер под ваш сайт за 1 день: нужные поля, обход защиты и JS-каталогов, выгрузка в вашу таблицу или CRM, уведомления в Telegram об изменении цен.
