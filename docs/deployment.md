# Deployment

## Локальный запуск (Conda)

```bash
# Создание окружения
conda create -n dr1 python=3.12 -y
conda activate dr1

# Установка
pip install -e ".[dev]"

# Запуск с fake provider (для разработки и тестирования)
python -m app.mcp_server

# Запуск с реальным search provider
export SEARCH_PROVIDER=brave
export BRAVE_API_KEY=your-api-key
export MCP_BEARER_TOKEN=your-secret-token
python -m app.mcp_server
```

Сервер запускается на `http://127.0.0.1:8000/mcp`.

## Запуск на сервере (systemd)

Для запуска на VPS без Docker:

```bash
# Создайте conda-окружение
conda create -n dr1 python=3.12 -y
conda activate dr1
pip install -e ".[dev]"
```

Создайте systemd service файл `/etc/systemd/system/deepresearch.service`:

```ini
[Unit]
Description=DeepResearch MCP Server
After=network.target

[Service]
Type=simple
User=deepresearch
WorkingDirectory=/opt/deepresearch
EnvironmentFile=/opt/deepresearch/.env
ExecStart=/home/deepresearch/miniconda3/envs/dr1/bin/python -m app.mcp_server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable deepresearch
sudo systemctl start deepresearch
```

## Reverse Proxy (Nginx)

Для HTTPS с Bearer token:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.example;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /mcp {
        proxy_pass http://127.0.0.1:8000/mcp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

## HTTPS

Всегда используйте HTTPS в production. Незашифрованный HTTP допустим только для локальной разработки на `127.0.0.1`.

## Backup

SQLite база находится по пути `CACHE_PATH` (default: `.cache/deepresearch.sqlite3`). Для backup достаточно скопировать файл при остановленном сервере.
