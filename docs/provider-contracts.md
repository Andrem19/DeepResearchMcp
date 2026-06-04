# Provider Contracts

## Как добавить новый Search Provider

### 1. Создайте файл `app/search/your_provider.py`

```python
from app.models import SearchQuery, SearchResult
from app.search.base import SearchProvider


class YourProvider(SearchProvider):
    def __init__(self, api_key: str, **kwargs):
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "your_provider"

    async def search(
        self,
        queries: list[SearchQuery],
        *,
        max_results: int = 20,
    ) -> list[SearchResult]:
        # Реализуйте поиск
        results = []
        for query in queries:
            # Вызов API -> parse response
            results.append(SearchResult(
                title="...",
                url="https://...",
                snippet="...",
                source_provider=self.name,
            ))
        return results[:max_results]
```

### 2. Обязательные требования

- Наследуйте `SearchProvider` ABC
- Реализуйте `name` property
- Реализуйте `async search()` method
- Возвращайте `list[SearchResult]`
- Не fetch-ите страницы (это делает fetcher)
- Не делайте synthesis (это делает synthesizer)
- Обрабатывайте timeout и HTTP errors → `SearchError`
- Логируйте provider name, duration, count (без API key)

### 3. Добавьте в config

В `app/config.py` добавьте ваш provider в `Literal` тип:
```python
search_provider: Literal["fake", "brave", "tavily", "serper", "your_provider"]
```

### 4. Добавьте в engine factory

В `app/research_engine.py`, `_create_search_provider()`:
```python
elif config.search_provider == "your_provider":
    from app.search.your_provider import YourProvider
    return YourProvider(config.your_api_key)
```

### 5. Напишите тесты

```python
# tests/unit/test_your_provider.py
import pytest
import httpx
from app.search.your_provider import YourProvider

@pytest.mark.unit
async def test_search_success():
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json={...}))
    client = httpx.AsyncClient(transport=transport)
    provider = YourProvider("test-key")
    provider._client = client
    results = await provider.search([...])
    assert len(results) > 0
```

### 6. Добавьте env var

В `.env.example` и `docs/configuration.md`:
```
YOUR_PROVIDER_API_KEY=
```

## Provider Contract

| Input | Output |
|-------|--------|
| `list[SearchQuery]` | `list[SearchResult]` |
| `max_results: int` | Empty list if no results |
| | `SearchError` on failure |
| | Partial results allowed |

### SearchResult обязательные поля

- `url`: валидный HTTP/HTTPS URL
- `title`: строка (может быть пустой)
- `snippet`: строка (может быть пустой)
- `source_provider`: имя провайдера
