# AKSI Site + Bot API (Free + OpenAI)

Теперь платформа АКСИ работает в двух режимах:

1. **Free mode (по умолчанию)** — если `OPENAI_API_KEY` пустой:
   - ответы идут через бесплатный провайдер `text.pollinations.ai`;
   - интернет-контекст подмешивается через DuckDuckGo Search.
2. **OpenAI mode** — если задан `OPENAI_API_KEY`.

Также включены:
- память чата по `session_id`;
- история и очистка чата;
- заметки (создание/поиск/редактирование/удаление);
- JSON-экспорт данных;
- персональная карта предназначения для Башировой Альфии Ринатовны (`GET /api/purpose`);
- self-manifest и криптографический отпечаток/подпись АКСИ (`GET /api/identity`);
- SQLite-хранилище (`aksi_site/aksi.db`).

## Запуск

```bash
cd aksi_site
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

Откройте `http://localhost:8000`.

## API

- `GET /health`
- `GET /api/config`
- `GET /api/identity`
- `GET /api/purpose`
- `POST /api/chat` (`use_web=true|false`)
- `GET /api/notes?q=`
- `POST /api/notes`
- `PATCH /api/notes/{id}`
- `DELETE /api/notes/{id}`
- `GET /api/chat/history?session_id=`
- `DELETE /api/chat/history/{session_id}`
- `GET /api/export`

## Важно

Free mode не требует ключа, но зависит от доступности бесплатного внешнего провайдера. Офлайн-режим отключён: если провайдер недоступен, API возвращает ошибку.


## Диагностика

Есть endpoint `GET /api/diagnostics` и кнопка в UI для проверки: настроен ли ключ, доступен ли free-провайдер и web-search.
