# Troubleshooting

## Частые проблемы

### Сервер не запускается

**Симптом:** `ModuleNotFoundError` или `ImportError`

**Решение:**
```bash
conda activate dr1
pip install -e ".[dev]"
```

---

**Симптом:** `Address already in use`

**Решение:** Измените порт:
```bash
export MCP_PORT=8001
python -m app.mcp_server
```

---

### Search provider ошибки

**Симптом:** `SearchError: Brave Search timeout`

**Решение:**
- Проверьте интернет-соединение
- Увеличьте `FETCH_TIMEOUT_SECONDS`
- Для разработки используйте `SEARCH_PROVIDER=fake`

---

**Симптом:** `SearchError: rate limit exceeded`

**Решение:**
- Подождите и попробуйте снова
- Проверьте лимиты вашего API плана

---

**Симптом:** `ConfigError: Unknown SEARCH_PROVIDER`

**Решение:** Допустимые значения: `fake`, `brave`, `tavily`, `serper`

---

### MCP connection проблемы

**Симптом:** Tool `deep_research` не виден в клиенте

**Решение:**
1. Проверьте, что сервер запущен: `curl http://127.0.0.1:8000/health`
2. Проверьте URL в конфигурации клиента
3. Проверьте, что путь `/mcp` правильный

---

**Симптом:** `401 Unauthorized`

**Решение:**
- Проверьте Bearer token в конфигурации клиента
- Сравните с `MCP_BEARER_TOKEN` на сервере
- Для локальной разработки не устанавливайте token

---

**Симптом:** `Timeout`

**Решение:**
- Увеличьте timeout в конфигурации клиента (рекомендуется 120s)
- Используйте `depth="quick"` для быстрых запросов
- Проверьте `TOTAL_RESEARCH_TIMEOUT_SECONDS`

---

### Пустые или плохие отчёты

**Симптом:** Отчёт содержит "No relevant sources were found"

**Решение:**
- Проверьте `SEARCH_PROVIDER` (fake provider возвращает тестовые данные)
- Для реального поиска настройте API key
- Попробуйте другую формулировку запроса

---

**Симптом:** Отчёт обрезан

**Решение:**
- Увеличьте `MAX_REPORT_LENGTH`
- Уменьшите `max_sources`

---

### Тесты падают

**Симптом:** `ImportError` в тестах

**Решение:**
```bash
conda activate dr1
pip install -e ".[dev]"
python -m pytest tests/unit/ -v
```

---

**Симптом:** Tests пытаются выйти в интернет

**Решение:** Все тесты должны быть offline. Если тест ходит в сеть — это баг. Проверьте, что не используется marker `live`.

---

### Conda проблемы

**Симптом:** `conda: command not found`

**Решение:** Установите Miniconda или добавьте в PATH.

---

**Симптом:** Окружение `dr1` не найдено

**Решение:**
```bash
conda create -n dr1 python=3.12 -y
conda activate dr1
pip install -e ".[dev]"
```
