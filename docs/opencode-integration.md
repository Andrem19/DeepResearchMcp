# OpenCode Integration

## Настройка

### 1. Запустите DeepResearch сервер

```bash
conda activate dr1
python -m app.mcp_server
```

Сервер будет доступен на `http://127.0.0.1:8000/mcp`.

### 2. Настройте OpenCode

Добавьте в конфигурацию OpenCode:

```json
{
  "mcp": {
    "deepresearch": {
      "type": "remote",
      "url": "http://127.0.0.1:8000/mcp",
      "enabled": true,
      "timeout": 120000
    }
  }
}
```

Для production с auth:

```json
{
  "mcp": {
    "deepresearch": {
      "type": "remote",
      "url": "https://your-domain.example/mcp",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer YOUR_SECRET_TOKEN"
      },
      "timeout": 120000
    }
  }
}
```

### 3. Проверьте подключение

В OpenCode проверьте, что tool `deep_research` доступен в списке MCP tools.

### 4. Используйте

Пример prompt для агента:

```
Use the deepresearch MCP tool to investigate this topic. Return the report as Markdown and keep citations intact: <topic>
```

## Рекомендации

- Установите `timeout: 120000` (120 секунд) — research может занять время
- Для локальной разработки Bearer token не нужен
- Агент должен вызвать **один** tool `deep_research`, а не пытаться искать сам

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| Tool не виден | Проверьте, что сервер запущен и URL верный |
| Timeout | Увеличьте timeout в конфигурации |
| Auth error | Проверьте Bearer token |
| Empty report | Проверьте SEARCH_PROVIDER и API key |
