# AKSI-TEST-1

Восстановлена рабочая платформа АКСИ с бесплатным доступом по умолчанию:

- **Free AI режим без ключа** (через `text.pollinations.ai`);
- интернет-контекст через DuckDuckGo;
- OpenAI-режим при наличии `OPENAI_API_KEY`;
- чат + память + заметки.

## Быстрый старт

```bash
cd aksi_site
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

Откройте `http://localhost:8000`.


## Диагностика

Есть endpoint `GET /api/diagnostics` и кнопка в UI для проверки: настроен ли ключ, доступен ли free-провайдер и web-search.
