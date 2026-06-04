# MCP Interface

## Tool: `deep_research`

The single public MCP tool. Accepts a research query and returns a Markdown report.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `string` | *required* | Research question or topic |
| `depth` | `"quick" \| "standard" \| "deep"` | `"standard"` | Research depth |
| `max_sources` | `integer` | `8` | Max sources (server enforces upper limit) |
| `recency_days` | `integer \| null` | `null` | Only include sources from last N days |
| `output_format` | `"markdown"` | `"markdown"` | Output format (currently only markdown) |

### Return Value

A single Markdown string with the report structure:

```markdown
# Deep Research Report

**Query:** ...
**Depth:** standard
**Sources:** N
**Generated:** YYYY-MM-DD HH:MM UTC
**Duration:** X.Xs

## Summary
...

## Key Findings
1. ... [1]
2. ... [2]

## Limitations
- ...

## Sources
[1] Title — domain — URL
[2] Title — domain — URL
```

### Error Handling

Errors are returned as Markdown (not stack traces):

```markdown
# Deep Research Report

**Query:** ...

## Error

Unable to complete research: <reason>
```

### Example Call

```json
{
  "method": "tools/call",
  "params": {
    "name": "deep_research",
    "arguments": {
      "query": "What is MCP Streamable HTTP?",
      "depth": "standard",
      "max_sources": 5
    }
  }
}
```

### Depth Levels

| Depth | Search Queries | Typical Duration |
|-------|---------------|-----------------|
| `quick` | 2 | ~2s |
| `standard` | 4 | ~5s |
| `deep` | 6 | ~10s |
