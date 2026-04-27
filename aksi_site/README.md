# AKSI Site + Bot API (Full Platform)

## Что реализовано

- Chat AI (`POST /api/chat`) с режимами:
  - `free` через `text.pollinations.ai`;
  - `openai` при наличии `OPENAI_API_KEY`.
- Web context (DuckDuckGo) через флаг `use_web`.
- Notes: `GET/POST/DELETE /api/notes`.
- Todos: `GET/POST/PATCH/DELETE /api/todos`.
- Export: `GET /api/export` (все данные в JSON).
- Diagnostics: `GET /api/diagnostics`.

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

## Тесты

```bash
pytest -q aksi_site/backend/tests/test_api.py
```
