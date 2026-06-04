# Report Format

## Структура отчёта

Каждый Markdown-отчёт содержит обязательные секции:

```markdown
# Deep Research Report

**Query:** <оригинальный запрос>
**Depth:** quick | standard | deep
**Sources:** <количество источников>
**Generated:** YYYY-MM-DD HH:MM UTC
**Duration:** X.Xs

## Summary

Краткое резюме исследования.

## Key Findings

1. <утверждение> [1]
2. <утверждение> [2]
3. <утверждение> [1][3]

## Limitations

- <ограничение 1>
- <ограничение 2>

## Sources

[1] Title — domain — URL
[2] Title — domain — URL
[3] Title — domain — URL
```

## Citation Contract

1. Citation IDs начинаются с `[1]` и идут последовательно
2. Каждый `[n]` в тексте отчёта имеет соответствующую запись в Sources
3. Каждая запись в Sources ссылается хотя бы на один `[n]` в тексте
4. URL нормализованы (без UTM, без якорей)
5. Нет fake citations — все ссылки ведут на реальные источники

## Error Report Format

При ошибке отчёт всё равно возвращается как Markdown:

```markdown
# Deep Research Report

**Query:** <запрос>

## Error

Unable to complete research: <причина>

This may be due to a temporary issue. Please try again later.
```

## No Evidence Report

Если источников не найдено:

```markdown
# Deep Research Report

**Query:** <запрос>

## Summary

No relevant sources were found for this query.

## Limitations

- No sources available for analysis.
- Consider rephrasing the query or trying a different search depth.
```

## Ограничения длины

- Максимальная длина отчёта: `MAX_REPORT_LENGTH` (default: 15000 символов)
- При обрезке добавляется: `*Report truncated due to length limit.*`
- Максимальная длина запроса: 5000 символов
