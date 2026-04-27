# AKSI-TEST-1

Полнофункциональная платформа АКСИ (web app):

- чат с ИИ (free/OpenAI режимы);
- интернет-контекст (опционально);
- заметки;
- задачи (todo manager);
- экспорт всех данных в JSON;
- диагностика доступов.
- GitHub-операции из сайта (статус аккаунта, список репозиториев, открытые PR, создание issue, запись файлов в репозиторий) при заданном `GITHUB_TOKEN`.

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

Для GitHub-функций добавьте в `aksi_site/.env`:

```bash
GITHUB_TOKEN=ghp_xxx
GITHUB_API_URL=https://api.github.com
```

## Публикация фронтенда на GitHub Pages

Добавлен workflow `.github/workflows/deploy-pages.yml`, который автоматически публикует `aksi_site/frontend/index.html` на GitHub Pages после push.

Ожидаемая ссылка после включения Pages в репозитории:

- `https://milana808.github.io/AKSI-TEST-1/`
