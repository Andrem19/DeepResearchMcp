# DeepResearch MCP Server

Лёгкий MCP-сервер глубокого исследования. Принимает короткий запрос, самостоятельно ищет, читает, сравнивает источники и возвращает готовый Markdown-отчёт с цитатами.

## Зачем

Слабые локальные модели и coding-агенты не могут эффективно управлять десятками low-level инструментов для веб-поиска. Этот сервер предоставляет **один понятный MCP-tool** `deep_research`, а вся сложность скрыта внутри.

## Быстрый старт

```bash
# Создание conda-окружения
conda create -n dr1 python=3.12 -y
conda activate dr1

# Установка зависимостей
pip install -e ".[dev]"

# Запуск с fake provider (без сети)
python -m app.mcp_server

# Запуск с реальным search provider
SEARCH_PROVIDER=brave BRAVE_API_KEY=your-key python -m app.mcp_server
```

## MCP Tool

```text
deep_research(
    query: str,                              # Исследовательский запрос
    depth: "quick" | "standard" | "deep" = "standard",
    max_sources: int = 8,                    # Лимит источников (сервер ограничивает сверху)
    recency_days: int | None = None,         # Свежесть источников
    output_format: "markdown" = "markdown"
) -> str                                     # Markdown-отчёт
```

## Подключение

### OpenCode

```json
{
  "mcp": {
    "deepresearch": {
      "type": "remote",
      "url": "http://127.0.0.1:8000/mcp",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer YOUR_SECRET_TOKEN"
      },
      "timeout": 120000
    }
  }
}
```

### LM Studio

```json
{
  "mcpServers": {
    "deepresearch": {
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_SECRET_TOKEN"
      }
    }
  }
}
```

## Принципы

- **Один MCP-tool** — клиент не управляет внутренними шагами.
- **Готовый отчёт** — Markdown с цитатами, а не сырые данные.
- **Безопасность** — SSRF-защита, Bearer token, лимиты, таймауты.
- **Offline-тесты** — все тесты работают без сети и без платных API.

## Разработка

```bash
conda activate dr1

# Тесты (offline, без API keys)
python -m pytest

# Lint
ruff check .

# Type check
python -m mypy app tests
```

## Лицензия

MIT
