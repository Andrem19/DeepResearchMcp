# Changelog

Все значимые изменения проекта документируются здесь.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

## [0.2.0] — 2026-06-05

### Добавлено

- Полный LLM adapter (`app/synthesize/llm.py`): OpenAI-compatible API, retry для transient errors (429/502/503/504), citation validation, fallback to extractive, configurable model/api_base (поддержка LM Studio).
- Async research jobs (`app/jobs.py`): `JobManager` с background worker, in-memory хранилище, TTL-based cleanup, concurrent job limit.
- Новые MCP tools: `start_deep_research`, `get_research_status`, `get_research_report`, `list_recent_research` — для долгих исследований без блокировки клиента.
- Модель `ResearchJob` и `JobStatus` enum в `app/models.py`.
- `_create_synthesizer()` factory в `ResearchEngine` — автоматически выбирает LLM или extractive по конфигурации.
- CI workflow (GitHub Actions): ruff, pytest, JSON validation, argparse check, secrets check — для Python 3.11/3.12/3.13.
- Автоматизированные validation scenarios (13 тестов): простой запрос, partial failure, SSRF, zero sources, citation integrity, async jobs lifecycle, MCP tool contract, JSON examples.

### Тесты

- 295 тестов: 193 unit, 64 integration, 25 contract, 13 validation — все offline, без сети, без API keys.
- 10 новых тестов для LLM adapter: successful response, hallucinated citations, timeout fallback, server error fallback, empty response, retry on 429, evidence truncation, prompt injection neutralization, request body format.
- 9 новых тестов для JobManager: create pending, complete, failure, empty query, unknown job, report not ready, list recent, cleanup expired, concurrent limit.
- 13 validation scenario тестов.

## [0.1.0] — 2026-06-04

### Добавлено

- Базовый каркас проекта (pyproject.toml, структура директорий).
- Конфигурация через env vars и AppConfig (`app/config.py`).
- Доменные модели: ResearchRequest, SearchResult, FetchedPage, ExtractedDocument, ResearchReport и другие (`app/models.py`).
- Типизированные ошибки: ResearchError, ValidationError, SearchError, FetchError, и т.д. (`app/errors.py`).
- MCP-сервер на FastMCP с tool `deep_research` (`app/mcp_server.py`).
- Research Engine — центральный оркестратор pipeline (`app/research_engine.py`).
- Deterministic Query Planner (`app/planning/query_planner.py`).
- Search provider interface (ABC) и fake provider (`app/search/`).
- Три реальных search provider adapter: Brave, Tavily, Serper (`app/search/`).
- URL Safety Guard — SSRF-защита (`app/fetch/url_safety.py`).
- HTTP Fetcher на httpx + FakeFetcher для тестов (`app/fetch/http_fetcher.py`).
- HTML Content Extractor и Text Cleaner (`app/extract/`).
- URL Deduplication и Source Normalization (`app/rank/dedupe.py`).
- Deterministic Source Ranker (`app/rank/source_ranker.py`).
- Evidence Builder и Citations (`app/report/citations.py`).
- Extractive Synthesis Engine (без LLM) (`app/synthesize/`).
- Markdown Report Renderer (`app/report/markdown_report.py`).
- SQLite Storage и Cache (`app/storage/`).
- Structured logging, correlation id, stage timing (`app/observability/`).
- Simple Metrics counters (`app/observability/metrics.py`).

### Тесты

- 263 теста: 183 unit, 55 integration, 25 contract — все offline, без сети, без API keys.
- Pytest markers: unit, integration, contract, security, live.
- Marker `live` выключен по умолчанию.

### Документация

- 11 документов: architecture, mcp-interface, configuration, deployment, security, testing, provider-contracts, report-format, opencode-integration, lmstudio-integration, troubleshooting.
- Примеры конфигураций: opencode.json, lmstudio.mcp.json.
- Пример запроса и пример отчёта.

### Инфраструктура

- Conda-окружение `dr1` (Python 3.12).
- Ruff для lint и форматирования — 0 предупреждений.
- `PYTHONNOUSERSITE=1` для изоляции от user site-packages.

### Примечания

- Dockerfile и docker-compose.yml **удалены** по решению пользователя. Запуск через conda-окружение.
