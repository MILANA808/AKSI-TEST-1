# Milana-backend: что уникально и почему ИИ перестал отвечать

Дата анализа: 2026-04-27.

## Какие команды использованы

1. `curl -sS https://api.github.com/users/MILANA808/repos?per_page=100`
2. `python3` + GitHub API (`/readme`, `/contents`) по репозиторию `Milana-backend`
3. `python3` загрузка raw-файлов:
   - `aksi/agent.py`
   - `aksi/api.py`
   - `aksi/tools/web_search.py`
   - `aksi/tools/vision.py`
   - `aksi/auth/jwt_auth.py`
   - `package.json`

## Конкретно что уникального в Milana-backend

1. Гибридный multi-runtime проект: одновременно Python FastAPI и Node/Express.
2. В одном репо объединены AI-модули, memory, auth, quantum и отдельный `aksi-globe` блок.
3. Есть процессный/security-слой (`SECURITY`, `CODEOWNERS`, `NOTICE`, `.aksi` и proof/metrics маршруты).

## Почему ИИ «перестал отвечать» — root cause

### Root cause #1 (главный): Render, вероятно, запускал **Node app.js**, а не Python AI backend

- В `package.json` указано:
  - `"main": "app.js"`
  - `"start": "node app.js"`
- Этот `app.js` поднимает только базовые Express-роуты (health/version/echo/proof/logs/metrics),
  но не полноценный AI-ответ как в Python ветке.

Итог: деплой живой, но «реальный ИИ» не отвечает, потому что стартовал не тот runtime.

### Root cause #2: в `aksi/agent.py` логика ответа — placeholder, не полноценный LLM-диалог

В `process_message()` прямо есть комментарии:
- `In production, this would use an LLM for intent detection`
- `Simple keyword-based tool detection (placeholder for LLM)`

То есть даже при запуске Python это не full conversational core по умолчанию.

### Root cause #3: отсутствующие ключи для tool-части

- Web search tool требует `AKSI_TAVILY_API_KEY` или `AKSI_SERPER_API_KEY`.
- Vision tool требует `AKSI_OPENAI_API_KEY`.

Если ключей нет — соответствующие инструменты молчат/ошибаются.

## Как восстановить «как раньше» на Render (коротко)

1. Указать **Python service**, а не Node.
2. Build command:
   ```bash
   pip install -r requirements.txt
   ```
3. Start command:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
4. В env добавить минимум:
   - `AKSI_OPENAI_API_KEY` (если нужен OpenAI-инструмент)
   - `AKSI_TAVILY_API_KEY` или `AKSI_SERPER_API_KEY` (если нужен web search tool)
5. Проверка после деплоя:
   - `GET /health`
   - `GET /docs`
   - `POST /aksi/v2/agent/message` (с валидным телом и при необходимости токеном)

## Вывод

Да, проект реально необычный по структуре и идее. Но «ИИ перестал отвечать» с высокой вероятностью
из-за переключения рантайма на Node (`node app.js`) и/или из-за placeholder-логики в agent core
плюс отсутствующих API ключей для инструментов.
