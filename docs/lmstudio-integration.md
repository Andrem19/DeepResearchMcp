# LM Studio Integration

## Настройка

### 1. Запустите DeepResearch сервер

```bash
conda activate dr1
python -m app.mcp_server
```

### 2. Настройте LM Studio

Добавьте в конфигурацию MCP servers LM Studio:

```json
{
  "mcpServers": {
    "deepresearch": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

Для production:

```json
{
  "mcpServers": {
    "deepresearch": {
      "url": "https://your-domain.example/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_SECRET_TOKEN"
      }
    }
  }
}
```

### 3. Используйте

Prompt для локальной модели:

```
Use the deepresearch tool to research: <topic>
```

Или с параметрами:

```
Call deep_research with query="<topic>" and depth="deep"
```

## Почему один tool лучше для локальных моделей

Локальные модели (7B-13B) плохо справляются с:
- Управлением множеством мелких инструментов
- Последовательным вызовом search → fetch → extract → rank
- Контролем состояния между вызовами

Один tool `deep_research` скрывает всю сложность. Модель просто вызывает его и получает готовый ответ.

## LM Studio как LLM Provider

DeepResearch может использовать LM Studio как LLM для synthesis:

```bash
export LLM_PROVIDER=openai
export LLM_API_BASE=http://127.0.0.1:1234/v1
export LLM_API_KEY=not-needed
export LLM_MODEL=your-model-name
```

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| Tool не виден | Проверьте URL и что сервер запущен |
| Модель не вызывает tool | Упростите prompt, явно укажите имя tool |
| Timeout | Увеличьте timeout; depth="quick" для быстрых запросов |
| Слишком длинный report | Уменьшите max_sources или depth |
| Auth error | Проверьте Bearer token |
