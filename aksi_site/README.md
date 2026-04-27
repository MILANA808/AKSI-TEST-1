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
- GitHub direct API:
  - `GET /api/github/status`;
  - `GET /api/github/repos`;
  - `POST /api/github/issues`.
- Безопасный рендер заметок и задач на фронтенде через `textContent` (без вставки пользовательских данных в `innerHTML`).

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

### GitHub доступ из сайта

Добавьте в `.env`:

```bash
GITHUB_TOKEN=ghp_xxx
GITHUB_API_URL=https://api.github.com
```

После этого в правой панели сайта станут доступны:
- проверка аккаунта GitHub;
- список репозиториев;
- создание issue в формате `owner/repo`.

## Тесты

```bash
pytest -q aksi_site/backend/tests/test_api.py
```
