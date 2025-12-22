# HW04 – eda_cli: HTTP-сервис качества датасетов (FastAPI)

Расширенная версия проекта eda-cli из Домашнего задания 03 (HW03).

К существующему CLI-приложению для EDA добавлен HTTP-сервис на FastAPI с эндпоинтами `/health`, `/quality`, `/quality-from-csv` и новым эндпоинтом `/quality-flags-from-csv` для HW04.
Используется в рамках Семинара 04 курса «Инженерия ИИ».

## Связь с HW03

Проект в HW04 основан на том же пакете `eda_cli`, что и в HW03:

- сохраняется структура `src/eda_cli/` и CLI-команда `eda-cli`;
- используются все эвристики качества данных, добавленные в HW03;
- добавлен модуль `api.py` с FastAPI-приложением;
- в зависимости добавлены `fastapi` и `uvicorn[standard]`.

Цель HW04 – показать, как поверх уже написанного EDA-ядра поднять простой HTTP-сервис с использованием эвристик качества из HW03.

## Требования

- Python 3.11+
- `uv` установлен в систему (рекомендуется)
- Браузер (для Swagger UI `/docs`) или любой HTTP-клиент:
  - `curl` / HTTP-клиент в IDE / Postman / Hoppscotch и т.п.

## Инициализация проекта

В корне проекта (каталог `homeworks/HW04/eda-cli`):

```bash
uv sync
```
Команда:

- создаст виртуальное окружение .venv;

- установит зависимости из pyproject.toml (включая FastAPI и Uvicorn);

- установит сам проект eda-cli в окружение.

Запуск CLI (как в HW03)
CLI остаётся доступным и в HW04.

Краткий обзор
```bash
uv run eda-cli overview data/example.csv
```
Параметры:

- ` --sep ` – разделитель (по умолчанию ,);

- ` --encoding ` – кодировка (по умолчанию utf-8).

Полный EDA-отчёт
```bash
uv run eda-cli report data/example.csv --out-dir reports
```
В результате в каталоге reports/ появятся:

- ` report.md ` – основной отчёт в Markdown;

- ` summary.csv ` – таблица по колонкам;

- ` missing.csv ` – пропуски по колонкам;

- ` correlation.csv ` – корреляционная матрица (если есть числовые признаки);

- ` top_categories/*.csv ` – top-k категорий по строковым признакам;

- ` hist_*.png ` – гистограммы числовых колонок;

- ` missing_matrix.png ` – визуализация пропусков;

- ` correlation_heatmap.png ` – тепловая карта корреляций.

Новые параметры команды report (добавлены в HW03):

- ` --max-hist-columns ` – сколько числовых колонок включать в набор гистограмм

- ` --top-k-categories ` – сколько top-значений выводить для категориальных признаков

- ` --title ` – заголовок отчёта

- ` --min-missing-share ` – порог доли пропусков для проблемных колонок

Запуск HTTP-сервиса
HTTP-сервис реализован в модуле eda_cli.api на FastAPI.

Запуск Uvicorn
```bash
uv run uvicorn eda_cli.api:app --reload --port 8000
``` 
Пояснения:

- ` eda_cli.api:app ` – путь до объекта FastAPI app в модуле eda_cli.api;

- ` --reload ` – автоматический перезапуск сервера при изменении кода (удобно для разработки);

- ` --port 8000 ` – порт сервиса (можно поменять при необходимости).

## Альтернативные способы запуска:

### С указанием хоста
```bash
uv run uvicorn eda_cli.api:app --host 0.0.0.0 --port 8000 --reload
```
### Без авто-перезагрузки (для продакшн)
```bash
uv run uvicorn eda_cli.api:app --host 0.0.0.0 --port 8000
```
### Через Python модуль
```bash
python -m uvicorn eda_cli.api:app --reload --port 8000
После запуска сервис будет доступен по адресу: http://127.0.0.1:8000
```
Эндпоинты сервиса
## 1. GET /health – проверка работоспособности сервиса
Простейший health-check.

Запрос:
```bash 
GET /health
```
Ожидаемый ответ 200 OK (JSON):

```bash
json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": 1700000000.123
}
```
Пример проверки через curl:

```bash
curl http://127.0.0.1:8000/health
```

## 2. Swagger UI: GET /docs – интерактивная документация API
Интерфейс документации и тестирования API:
```bash
text
http://127.0.0.1:8000/docs
```
Через ` /docs ` можно:

- вызывать ` GET /health ` ;

- вызывать ` POST /quality ` (форма для JSON);

- вызывать ` POST /quality-from-csv ` (форма для загрузки файла);

- вызывать ` POST /quality-flags-from-csv ` (новый эндпоинт для HW04).

## 3. POST /quality – оценка качества по агрегированным признакам
### Эндпоинт принимает агрегированные признаки датасета (размеры, доля пропусков и т.п.) и возвращает эвристическую оценку качества с использованием эвристик из HW03.

Пример запроса:
```bash
json
{
  "n_rows": 10000,
  "n_cols": 12,
  "max_missing_share": 0.15,
  "has_constant_columns": false,
  "has_high_cardinality_categoricals": false,
  "has_suspicious_id_duplicates": false,
  "has_many_zero_values": false
}
```

Пример ответа 200 OK:
```bash
json
{
  "ok_for_model": true,
  "quality_score": 0.8,
  "latency_ms": 3.2,
  "flags": {
    "too_few_rows": false,
    "too_many_columns": false,
    "too_many_missing": false,
    "has_constant_columns": false,
    "has_high_cardinality_categoricals": false,
    "has_suspicious_id_duplicates": false,
    "has_many_zero_values": false
  },
  "request_id": "uuid-here"
}
```

Пример вызова через curl:
```bash
curl -X POST "http://127.0.0.1:8000/quality" \
  -H "Content-Type: application/json" \
  -d '{"n_rows": 10000, "n_cols": 12, "max_missing_share": 0.15}'
```
## 4. POST /quality-from-csv – оценка качества по CSV-файлу
Эндпоинт принимает CSV-файл, внутри:

- читает его в ` pandas.DataFrame `;

- вызывает функции из ` eda_cli.core `:

-- ` summarize_dataset() `

-- ` missing_table() `

-- `compute_quality_flags() `

- возвращает оценку качества датасета.

Запрос:
```bash
text
POST /quality-from-csv
Content-Type: multipart/form-data
file: <CSV-файл>
```
Через ` Swagger `:

в ` /docs ` открыть ` POST /quality-from-csv `,

нажать ` "Try it out" `,

выбрать файл (например, ` data/example.csv `),

нажать ` "Execute" `.

Пример вызова через ` curl `:

```bash
curl -X POST "http://127.0.0.1:8000/quality-from-csv" \
  -F "file=@data/example.csv"
```
Ответ будет содержать:

- ` ok_for_model ` – результат по эвристикам;

- ` quality_score ` – интегральный скор качества;

- ` flags ` – булевы флаги из ` compute_quality_flags ` (включая флаги из HW03);

- ` latency_ms ` – время обработки запроса;

- ` request_id ` – уникальный идентификатор запроса.

## 5. POST /quality-flags-from-csv – полный набор флагов качества из CSV (новый эндпоинт для HW04)
Новый эндпоинт, специально добавленный для HW04. Возвращает полный набор флагов качества из CSV файла, включая все эвристики, добавленные в HW03.

Использует EDA-ядро: ` summarize_dataset(), missing_table(), compute_quality_flags(). `

Флаги качества из HW03, возвращаемые этим эндпоинтом:

- ` has_constant_columns ` – есть ли колонки, где все значения одинаковые

- ` has_high_cardinality_categoricals ` – есть ли категориальные признаки с более чем 100 уникальными значениями

- ` has_suspicious_id_duplicates ` – есть ли подозрительные дубликаты в колонках с 'id' в названии

- ` has_many_zero_values ` – есть ли числовые колонки, где более 50% значений равны нулю

Параметры (form-data):

- ` file: CSV файл ` (обязательно)

- ` sep: ` разделитель (по умолчанию ,)

- ` encoding: ` кодировка (по умолчанию utf-8)

- ` include_summary_stats: ` включать статистику датасета (по умолчанию true)

Запрос:
```bash
http
POST /quality-flags-from-csv
Content-Type: multipart/form-data
```

Пример вызова через curl:

```bash
curl -X POST "http://127.0.0.1:8000/quality-flags-from-csv" \
  -F "file=@data/example.csv" \
  -F "sep=," \
  -F "encoding=utf-8" \
  -F "include_summary_stats=true"
```
Пример ответа 200 OK (JSON):
```bash
json
{
  "flags": {
    "too_few_rows": false,
    "too_many_columns": false,
    "too_many_missing": false,
    "has_constant_columns": false,
    "has_high_cardinality_categoricals": true,
    "has_suspicious_id_duplicates": true,
    "has_many_zero_values": false,
    "max_missing_share": 0.1,
    "quality_score": 0.75
  },
  "summary_stats": {
    "n_rows": 35,
    "n_cols": 13,
    "numeric_columns": 6,
    "categorical_columns": 7,
    "total_missing": 13,
    "columns_with_missing": 4
  },
  "latency_ms": 15.3,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Через Swagger UI:

- в ` /docs ` открыть ` POST /quality-flags-from-csv ` ,

- нажать ` Try it out ` ,

- выбрать файл (например, ` data/example.csv `),

- при необходимости указать дополнительные параметры ` (sep, encoding, include_summary_stats) ` ,

- нажать ` Execute. `
## 6. POST /dataset-summary-from-csv – расширенная сводка по датасету (дополнительный эндпоинт)
Возвращает детальную информацию о датасете, используя все функции EDA-ядра.

Использует EDA-ядро: summarize_dataset(), missing_table(), top_categories(), correlation_matrix(), compute_quality_flags()

Структура проекта
```text
homeworks/
  HW04/
    eda-cli/
      pyproject.toml
      README.md                # этот файл
      src/
        eda_cli/
          __init__.py
          core.py              # EDA-логика, эвристики качества (HW03)
          viz.py               # визуализации
          cli.py               # CLI (overview/report)
          api.py               # HTTP-сервис (FastAPI) - ДОБАВЛЕНО В HW04
      tests/
        test_core.py           # тесты ядра
      data/
        example.csv            # учебный CSV для экспериментов
```
## Эндпоинты сервиса

- 1. GET /health
- 2. GET /docs
- 3. POST /quality
- 4. POST /quality-from-csv
- 5. POST /quality-flags-from-csv
- 6. POST /dataset-summary-from-csv
## Тесты
Запуск тестов (как и в HW03):

```bash
uv run pytest -q
```
Новые тесты (добавлены в HW03):

- ` test_quality_flags_has_constant_columns `

- ` test_quality_flags_has_high_cardinality_categoricals `

- ` test_quality_flags_has_suspicious_id_duplicates `

- ` test_quality_flags_has_many_zero_values `

Рекомендуется перед любыми изменениями в логике качества данных и API:

- Запустить тесты pytest;

- Проверить работу CLI (uv run eda-cli ...);

- Проверить работу HTTP-сервиса (uv run uvicorn eda_cli.api:app ..., затем /health и /quality, /quality-from-csv, /quality-flags-from-csv через /docs или HTTP-клиент).

Интеграция с EDA-ядром
HTTP сервис использует те же функции EDA-ядра, что и CLI-приложение:

- ` summarize_dataset() ` – для получения статистики по датасету

- ` missing_table() ` – для анализа пропусков

- ` compute_quality_flags() ` – для вычисления флагов качества (включая новые флаги из HW03)

- ` top_categories() ` – для анализа категориальных признаков

- ` correlation_matrix() ` – для анализа корреляций

Все эндпоинты, работающие с CSV-файлами, явно используют функции EDA-ядра для анализа данных.