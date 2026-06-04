# Testing

## Быстрый старт

```bash
conda activate dr1

# Все тесты (offline)
python -m pytest

# Только unit
python -m pytest tests/unit/ -v

# Только integration
python -m pytest tests/integration/ -v

# Только contract
python -m pytest tests/contract/ -v

# С покрытием
python -m pytest --cov=app --cov-report=term-missing
```

## Правила тестирования

1. **Без сети** — все тесты работают offline
2. **Без API keys** — никто не должен настраивать ключи для CI
3. **Без реального LLM** — все LLM responses мокаются
4. **Без браузера** — только HTTP fetcher
5. **Без `argparse`** — в проекте нет CLI-парсинга

## Структура тестов

```text
tests/
  conftest.py              — общие fixtures
  unit/                    — быстрые unit тесты
    test_config.py
    test_models.py
    test_query_planner.py
    test_url_safety.py
    test_html_extractor.py
    test_text_cleaner.py
    test_dedupe.py
    test_source_ranker.py
    test_citations.py
    test_markdown_report.py
    test_extractive_synthesizer.py
    test_sqlite_store.py
  integration/             — mocked integration
    test_research_engine_with_fakes.py
    test_mcp_tool_contract.py
    test_cache_pipeline.py
    test_partial_failures.py
    test_security_guards.py
  contract/                — schema и format contracts
    test_report_contract.py
    test_provider_contract.py
    test_mcp_schema_contract.py
```

## Pytest Markers

| Marker | Описание | CI |
|--------|----------|----|
| `@pytest.mark.unit` | Unit тесты | ✅ |
| `@pytest.mark.integration` | Integration (mocked) | ✅ |
| `@pytest.mark.contract` | Контракты схем | ✅ |
| `@pytest.mark.security` | Security тесты | ✅ |
| `@pytest.mark.live` | Live (реальная сеть) | ❌ skipped |

## Fake Providers

### FakeSearchProvider

```python
from app.search.fake import FakeSearchProvider

# С кастомными результатами
provider = FakeSearchProvider(results=[...])

# С ошибкой
provider = FakeSearchProvider(fail=True, error_message="test error")
```

### FakeFetcher

```python
from app.fetch.http_fetcher import FakeFetcher

# С кастомными страницами
fetcher = FakeFetcher(pages={"https://example.com": b"<html>...</html>"})

# С падающими URL
fetcher = FakeFetcher(fail_urls={"https://bad.example.com"})
```

## Создание нового теста

1. Определите тип: unit / integration / contract
2. Положите в правильную директорию
3. Добавьте marker
4. Используйте `tmp_path` для filesystem
5. Мокайте все внешние вызовы

```python
import pytest
from app.models import ResearchRequest

@pytest.mark.unit
def test_something():
    req = ResearchRequest(query="test query")
    assert req.depth == "standard"
```
