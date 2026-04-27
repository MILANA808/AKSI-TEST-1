# MILANA808 Repository Audit (2026-04-27)

## Commands used

1. `curl -sS https://api.github.com/users/MILANA808/repos?per_page=100 > /tmp/milana_repos.json`
2. `python3` script to print repo names, links, stars, forks, language, descriptions from `/tmp/milana_repos.json`
3. `python3` script to fetch README via `https://api.github.com/repos/MILANA808/<repo>/readme`
4. `python3` script to list root contents via `https://api.github.com/repos/MILANA808/<repo>/contents`

## High-level inventory

- Total repositories discovered: **17**.
- Forks: **Agi, codex, gpt-oss-safeguard, MCP-GitLab-insights-, openai-cookbook, plugins-quickstart, SuperAGI**.
- Non-forks (author-owned): **AKSI-, AKSI-TEST, AKSI-TEST-1, aksi_apps, Bulat, glorious-potato, Milana-backend, MILANA808, milana_site, Test-site**.

## What looks truly unusual / unique

### 1) Milana-backend is the standout unique repo

Why it looks unusual compared with most small personal AI repos:

- Combines **multiple stacks in one repo** (Python FastAPI + Node/Express + frontend).
- Contains dedicated folders for **AI agent system**, **quantum tooling**, **memory**, and **auth** (`aksi/`, `aksi/quantum`, `aksi/memory`, `aksi/auth`).
- Includes a separate visual subsystem `aksi-globe/` (frontend + backend + shared config + docker-compose).
- Includes security/governance artifacts (`SECURITY.md`, `NOTICE`, `CODEOWNERS`, `.aksi/manifest.json`, proof/metrics routes).

This mix (AI + cryptographic/process governance + globe visualization + multi-runtime backend) is relatively uncommon in small independent repos.

### 2) aksi_apps is unusually product-structured for a skeleton

- Clear full-product skeleton segmentation (`frontend/`, `backend/`, `tests/`, `docker/`, `docs/`).
- README positions it as “Full Product Skeleton” with Docker and JWT setup.

This is stronger structure than typical “single-script” AI demos.

### 3) AKSI- repository appears process/security-centric

- Root contents include `.aksi`, `.github`, `CODEOWNERS`, `PRIMER.md`, `SECURITY.md`, `NOTICE`.
- Looks like governance/signing/compliance scaffold, not just app code.

## What is less unique

- Several repos are direct forks of popular ecosystems and appear mostly upstream-derived.
- Some repos are minimal placeholders (e.g., only LICENSE/README, or missing README/content).

## Direct answer to your question

Да — **уникальные фичи есть**, и главный носитель уникальности это **Milana-backend**:

1. Архитектурная «гибридность» (Python + Node + frontend + infra в одном проекте).
2. Необычное сочетание направлений: AI-агент + quantum + memory + auth + proof/metrics + globe.
3. Наличие governance/security-слоя рядом с прикладным AI-кодом.

По совокупности это выглядит более необычно, чем стандартный чат-бот или обычный AI CRUD сервис.
