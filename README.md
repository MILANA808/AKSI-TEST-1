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


## Безопасный форк (оригинал не трогаем)

Если нужно работать только в тестовом репозитории (как вы и просили), используйте скрипт:

```bash
./scripts/fork_to_test_repo.sh --source MILANA808/Milana-backend --dest ./apps/milana-backend-test
```

Что делает скрипт:
- создаёт fork в вашем GitHub-аккаунте;
- клонирует fork локально;
- добавляет `upstream` на оригинал **только для чтения** (push отключён);
- вы работаете и деплоите только fork, оригинал остаётся нетронутым.

Для Render можно использовать готовый `render.yaml` в этом репозитории.
