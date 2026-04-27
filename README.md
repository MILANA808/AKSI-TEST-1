# AKSI-TEST-1

Полнофункциональная платформа АКСИ (web app):

- чат с ИИ (free/OpenAI режимы);
- интернет-контекст (опционально);
- заметки;
- задачи (todo manager);
- экспорт всех данных в JSON;
- диагностика доступов.

## Запуск

```bash
cd aksi_site
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

Готовый сайт локально: `http://localhost:8000`.
